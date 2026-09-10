"""
Random Forest baseline on the EXACT SAME temporal split as train_baseline.py.

Why this exists: published Elliptic benchmarks use varying splits,
preprocessing, and feature subsets, so citing "SOTA F1 = X" from a paper
isn't a fair comparison to your MLP's number. This trains the classic
strong baseline from the original Elliptic paper (Weber et al. 2019
found Random Forest outperformed their GCN) on your own data pipeline,
so the comparison is apples-to-apples.

This does NOT need to be provable in EZKL — it exists purely as a
reference point for your paper's results table, to show where your
provable MLP sits relative to a strong non-provable baseline.

Run: python3 sota_baseline.py --data-dir ../data/elliptic_bitcoin_dataset
"""

import argparse

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import numpy as np

from train_baseline import load_data, temporal_split, SEED


def evaluate(clf, X_val, y_val, X_test, y_test, name):
    val_probs = clf.predict_proba(X_val)[:, 1]
    best_t, best_f1 = 0.5, -1
    for t in np.arange(0.05, 0.95, 0.01):
        f1_t = f1_score(y_val, (val_probs > t).astype(int), zero_division=0)
        if f1_t > best_f1:
            best_f1, best_t = f1_t, t

    test_probs = clf.predict_proba(X_test)[:, 1]
    preds = (test_probs > best_t).astype(int)

    result = {
        "name": name,
        "threshold": best_t,
        "accuracy": accuracy_score(y_test, preds),
        "precision": precision_score(y_test, preds, zero_division=0),
        "recall": recall_score(y_test, preds, zero_division=0),
        "f1": f1_score(y_test, preds, zero_division=0),
    }
    print(f"\n--- {name} (temporal split, held-out test) ---")
    print(f"threshold (max F1 on val): {best_t:.2f}")
    print(f"accuracy:  {result['accuracy']:.4f}")
    print(f"precision: {result['precision']:.4f}")
    print(f"recall:    {result['recall']:.4f}")
    print(f"f1:        {result['f1']:.4f}")
    return result


def main(data_dir, n_estimators, mlp_acc, mlp_prec, mlp_rec, mlp_f1):
    X, y, time_steps = load_data(data_dir)
    X_train, y_train, X_val, y_val, X_test, y_test = temporal_split(X, y, time_steps)

    print(f"Temporal split: train={len(X_train)}, val={len(X_val)}, test={len(X_test)}")

    print(f"\nTraining RandomForestClassifier(n_estimators={n_estimators})...")
    rf = RandomForestClassifier(
        n_estimators=n_estimators, max_depth=None, class_weight="balanced",
        random_state=SEED, n_jobs=-1,
    )
    rf.fit(X_train, y_train)
    rf_result = evaluate(rf, X_val, y_val, X_test, y_test, "Random Forest")

    print(f"\nTraining GradientBoostingClassifier(n_estimators={n_estimators})...")
    # GradientBoostingClassifier has no built-in class_weight, so we
    # approximate it with sample_weight on the minority class.
    sample_weight = np.where(y_train == 1, (y_train == 0).sum() / max((y_train == 1).sum(), 1), 1.0)
    gb = GradientBoostingClassifier(n_estimators=n_estimators, max_depth=3, random_state=SEED)
    gb.fit(X_train, y_train, sample_weight=sample_weight)
    gb_result = evaluate(gb, X_val, y_val, X_test, y_test, "Gradient Boosting")

    print(f"\n--- Comparison table for your paper ---")
    print(f"{'Model':<30} {'Accuracy':>10} {'Precision':>10} {'Recall':>8} {'F1':>7} {'Provable?':>10}")
    print(f"{'Your MLP (165->64->32->1)':<30} {mlp_acc:>10.4f} {mlp_prec:>10.4f} {mlp_rec:>8.4f} {mlp_f1:>7.4f} {'Yes':>10}")
    print(f"{'Random Forest (reference)':<30} {rf_result['accuracy']:>10.4f} {rf_result['precision']:>10.4f} "
          f"{rf_result['recall']:>8.4f} {rf_result['f1']:>7.4f} {'No':>10}")
    print(f"{'Gradient Boosting (reference)':<30} {gb_result['accuracy']:>10.4f} {gb_result['precision']:>10.4f} "
          f"{gb_result['recall']:>8.4f} {gb_result['f1']:>7.4f} {'No':>10}")

    best_ref = max([rf_result, gb_result], key=lambda r: r["f1"])
    gap = best_ref["f1"] - mlp_f1
    print(f"\nGap to strongest non-provable reference ({best_ref['name']}): {gap:.4f} F1 points")
    print(f"Note: Random Forest / Gradient Boosting are NOT provable in EZKL in this")
    print(f"pipeline — they're reference points only, to quantify the accuracy cost of")
    print(f"choosing a provable architecture.")

    top_idx = np.argsort(rf.feature_importances_)[::-1][:10]
    print(f"\nTop 10 most important features (by Random Forest importance):")
    for i in top_idx:
        print(f"  feat_{i+1}: {rf.feature_importances_[i]:.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="../data/elliptic_bitcoin_dataset")
    parser.add_argument("--n-estimators", type=int, default=100)
    parser.add_argument("--mlp-accuracy", type=float, default=0.9660,
                         help="Your MLP's test accuracy, for the comparison table. "
                              "Update this to match your latest train_baseline.py run.")
    parser.add_argument("--mlp-precision", type=float, default=0.8241)
    parser.add_argument("--mlp-recall", type=float, default=0.6057)
    parser.add_argument("--mlp-f1", type=float, default=0.6982)
    args = parser.parse_args()
    main(args.data_dir, args.n_estimators, args.mlp_accuracy, args.mlp_precision,
         args.mlp_recall, args.mlp_f1)
