"""
Pulls together the full metrics table for H1's final results section:
  - PR-AUC (average precision) — threshold-independent, better than F1
    alone for imbalanced classification since it summarizes the full
    precision/recall tradeoff curve rather than one operating point.
  - ZK feasible — whether the model's architecture can practically be
    proven in EZKL's circuit model (fixed-width MLP: yes; tree ensembles
    with arbitrary branching: no).
  - Proving time, Verification time, Proof size — read from
    proofs/baseline_timings.json (produced by prove_full_model.py).
    These only exist for the MLP, since Random Forest / Gradient
    Boosting were never run through the proving pipeline (see above).

Run: python3 final_metrics.py --data-dir ../data/elliptic_bitcoin_dataset
Requires: baseline_model.pt (from train_baseline.py)
          ../proofs/baseline_timings.json (from prove_full_model.py) — optional,
          script still runs without it but leaves proving columns blank for the MLP.
"""

import argparse
import json
import os

import numpy as np
import torch
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import (accuracy_score, average_precision_score, f1_score,
                              precision_score, recall_score)

from train_baseline import FraudClassifier, SEED, load_data, scale_features, temporal_split

TIMINGS_PATH = "../proofs/baseline_timings.json"


def eval_mlp(X_train_raw, y_train, X_val_raw, y_val, X_test_raw, y_test, scaler, clip_percentile):
    # MLP needs scaling; RF/GB (evaluated separately in main()) use the raw
    # features directly, since scaling/clipping is unnecessary for trees and
    # clipping in particular would throw away real outlier signal they could use.
    X_train, X_val, X_test = scale_features(
        X_train_raw.copy(), X_val_raw.copy(), X_test_raw.copy(), scaler, clip_percentile
    )

    state_dict = torch.load("baseline_model.pt")
    hidden1 = state_dict["net.0.weight"].shape[0]
    hidden2 = state_dict["net.4.weight"].shape[0]
    model = FraudClassifier(hidden1=hidden1, hidden2=hidden2)
    model.load_state_dict(state_dict)
    model.eval()

    with open("decision_threshold.txt") as f:
        threshold = float(f.read().strip())

    with torch.no_grad():
        test_probs = torch.sigmoid(model(torch.tensor(X_test))).squeeze().numpy()

    preds = (test_probs > threshold).astype(int)
    pr_auc = average_precision_score(y_test, test_probs)

    return {
        "name": f"Your MLP (165->{hidden1}->{hidden2}->1)",
        "accuracy": accuracy_score(y_test, preds),
        "precision": precision_score(y_test, preds, zero_division=0),
        "recall": recall_score(y_test, preds, zero_division=0),
        "f1": f1_score(y_test, preds, zero_division=0),
        "pr_auc": pr_auc,
        "zk_feasible": "Yes",
    }


def eval_sklearn_model(clf, X_train, y_train, X_val, y_val, X_test, y_test, name, **fit_kwargs):
    clf.fit(X_train, y_train, **fit_kwargs)
    val_probs = clf.predict_proba(X_val)[:, 1]
    best_t, best_f1 = 0.5, -1
    for t in np.arange(0.05, 0.95, 0.01):
        f1_t = f1_score(y_val, (val_probs > t).astype(int), zero_division=0)
        if f1_t > best_f1:
            best_f1, best_t = f1_t, t

    test_probs = clf.predict_proba(X_test)[:, 1]
    preds = (test_probs > best_t).astype(int)
    pr_auc = average_precision_score(y_test, test_probs)

    return {
        "name": name,
        "accuracy": accuracy_score(y_test, preds),
        "precision": precision_score(y_test, preds, zero_division=0),
        "recall": recall_score(y_test, preds, zero_division=0),
        "f1": f1_score(y_test, preds, zero_division=0),
        "pr_auc": pr_auc,
        "zk_feasible": "No",
    }


def load_proving_numbers():
    if not os.path.exists(TIMINGS_PATH):
        return None
    with open(TIMINGS_PATH) as f:
        t = json.load(f)
    return {
        "prove_s": t.get("prove_side_total_s", t.get("prove")),
        "verify_s": t.get("verify"),
        "proof_kb": t.get("proof_size_kb"),
    }


def main(data_dir, scaler, clip_percentile):
    X, y, time_steps = load_data(data_dir)
    X_train_raw, y_train, X_val_raw, y_val, X_test_raw, y_test = temporal_split(X, y, time_steps)

    mlp_result = eval_mlp(X_train_raw, y_train, X_val_raw, y_val, X_test_raw, y_test,
                           scaler, clip_percentile)

    print("Training Random Forest and Gradient Boosting references "
          "(raw, unscaled, unclipped features — fair reference, no scaling needed for trees)...")
    rf = RandomForestClassifier(n_estimators=100, class_weight="balanced",
                                 random_state=SEED, n_jobs=-1)
    rf_result = eval_sklearn_model(rf, X_train_raw, y_train, X_val_raw, y_val,
                                    X_test_raw, y_test, "Random Forest")

    sample_weight = np.where(y_train == 1, (y_train == 0).sum() / max((y_train == 1).sum(), 1), 1.0)
    gb = GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=SEED)
    gb_result = eval_sklearn_model(gb, X_train_raw, y_train, X_val_raw, y_val,
                                    X_test_raw, y_test, "Gradient Boosting",
                                    sample_weight=sample_weight)

    proving = load_proving_numbers()
    if proving is None:
        print(f"\nNOTE: {TIMINGS_PATH} not found — run prove_full_model.py first for "
              f"proving time/verification time/proof size. Table below leaves those blank.")
        proving = {"prove_s": None, "verify_s": None, "proof_kb": None}

    def fmt(v, suffix=""):
        return f"{v:.3f}{suffix}" if v is not None else "N/A"

    print(f"\n{'='*115}")
    print(f"{'Model':<28} {'Acc':>7} {'Prec':>7} {'Rec':>7} {'F1':>7} {'PR-AUC':>7} "
          f"{'ZK?':>5} {'Prove(s)':>10} {'Verify(s)':>10} {'Proof(KB)':>10}")
    print(f"{'='*115}")
    for r in [mlp_result, rf_result, gb_result]:
        is_mlp = r["zk_feasible"] == "Yes"
        prove_s = fmt(proving["prove_s"]) if is_mlp else "N/A"
        verify_s = fmt(proving["verify_s"]) if is_mlp else "N/A"
        proof_kb = fmt(proving["proof_kb"]) if is_mlp else "N/A"
        print(f"{r['name']:<28} {r['accuracy']:>7.4f} {r['precision']:>7.4f} {r['recall']:>7.4f} "
              f"{r['f1']:>7.4f} {r['pr_auc']:>7.4f} {r['zk_feasible']:>5} "
              f"{prove_s:>10} {verify_s:>10} {proof_kb:>10}")
    print(f"{'='*115}")

    print(f"\nColumn notes:")
    print(f"  PR-AUC: average precision — threshold-independent summary of the full")
    print(f"    precision/recall curve. More informative than a single F1 point for")
    print(f"    imbalanced classification, since it doesn't depend on picking one threshold.")
    print(f"  ZK feasible: whether the architecture can practically be proven in EZKL's")
    print(f"    circuit model. Tree ensembles' branching structure does not map cleanly")
    print(f"    to arithmetic circuits, unlike a fixed-width MLP's matrix multiplications.")
    print(f"  Prove/Verify/Proof size: only meaningful for ZK-feasible models — Random")
    print(f"    Forest and Gradient Boosting were never run through the proving pipeline.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="../data/elliptic_bitcoin_dataset")
    parser.add_argument("--scaler", choices=["standard", "robust"], default="robust",
                         help="Must match whatever train_baseline.py used to save "
                              "baseline_model.pt, or the MLP's numbers won't reproduce.")
    parser.add_argument("--clip-percentile", type=float, default=1.0)
    args = parser.parse_args()
    main(args.data_dir, args.scaler, args.clip_percentile)
