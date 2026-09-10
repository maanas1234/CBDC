"""
Curated sweep across model capacity, loss function, scaling, and SMOTE
oversampling — a full grid across all of these would be too slow to run
casually, so this tries a hand-picked set of promising combinations
instead. All use the correct TEMPORAL split.

Does NOT overwrite baseline_model.pt/onnx — trains throwaway models in
memory. Once you pick the best config, re-run train_baseline.py with
those exact flags to save the real model files.

Run: python3 sweep_v2.py --data-dir ../data/elliptic_bitcoin_dataset
"""

import argparse
import copy

import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
import torch
import torch.nn as nn

from train_baseline import (
    FraudClassifier, FocalLoss, SEED, load_data, temporal_split,
    scale_features, maybe_smote,
)

# (hidden1, hidden2, loss_type, pos_weight_power_or_None, focal_alpha_or_None,
#  focal_gamma_or_None, scaler, clip_percentile, use_smote, batch_size)
CONFIGS = [
    ("32-16 bce pw0.7",       32, 16, "bce",   0.7,  None, None, "standard", None, False, 256),
    ("64-32 bce pw0.7 batch256",  64, 32, "bce", 0.7, None, None, "standard", None, False, 256),
    ("64-32 bce pw0.7 fullbatch", 64, 32, "bce", 0.7, None, None, "standard", None, False, None),
    ("64-32 bce pw0.7 smote", 64, 32, "bce",   0.7,  None, None, "standard", None, True,  256),
    ("64-32 bce pw0.7 smote fullbatch", 64, 32, "bce", 0.7, None, None, "standard", None, True, None),
    ("64-32 focal a.75 g2",   64, 32, "focal", None, 0.75, 2.0,  "standard", None, False, 256),
    ("64-32 focal a.75 g2 fullbatch", 64, 32, "focal", None, 0.75, 2.0, "standard", None, False, None),
    ("64-32 focal a.5 g2",    64, 32, "focal", None, 0.5,  2.0,  "standard", None, False, 256),
    ("64-32 focal a.75 g2 smote", 64, 32, "focal", None, 0.75, 2.0, "standard", None, True, 256),
    ("64-32 bce pw0.7 robust+clip", 64, 32, "bce", 0.7, None, None, "robust", 1.0, False, 256),
    ("64-32 bce pw0.7 robust+clip fullbatch", 64, 32, "bce", 0.7, None, None, "robust", 1.0, False, None),
    ("128-64 bce pw0.7 fullbatch", 128, 64, "bce", 0.7, None, None, "standard", None, False, None),
    ("128-64 focal a.75 g2 smote", 128, 64, "focal", None, 0.75, 2.0, "standard", None, True, 256),
]


def train_one(X_train, y_train, X_val, y_val, X_test, y_test, hidden1, hidden2,
              loss_type, pw_power, f_alpha, f_gamma, batch_size, epochs=300, patience=30):
    torch.manual_seed(SEED)
    model = FraudClassifier(hidden1=hidden1, hidden2=hidden2, dropout=0.2)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs)

    if loss_type == "focal":
        loss_fn = FocalLoss(alpha=f_alpha, gamma=f_gamma)
    else:
        full_ratio = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
        loss_fn = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([full_ratio ** pw_power]))

    X_train_t = torch.tensor(X_train)
    y_train_t = torch.tensor(y_train).unsqueeze(1)
    X_val_t = torch.tensor(X_val)
    n_train = len(X_train_t)
    bs = batch_size or n_train

    best_val_f1, best_state, no_improve = -1, None, 0
    for epoch in range(epochs):
        model.train()
        perm = torch.randperm(n_train)
        for start in range(0, n_train, bs):
            idx = perm[start:start + bs]
            opt.zero_grad()
            loss = loss_fn(model(X_train_t[idx]), y_train_t[idx])
            loss.backward()
            opt.step()
        scheduler.step()

        model.eval()
        with torch.no_grad():
            val_preds = (torch.sigmoid(model(X_val_t)).squeeze() > 0.5).int().numpy()
        val_f1 = f1_score(y_val, val_preds, zero_division=0)
        if val_f1 > best_val_f1:
            best_val_f1, best_state, no_improve = val_f1, copy.deepcopy(model.state_dict()), 0
        else:
            no_improve += 1
        if no_improve >= patience:
            break

    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        val_probs = torch.sigmoid(model(X_val_t)).squeeze().numpy()

    best_t, best_f1 = 0.5, -1
    for t in np.arange(0.05, 0.95, 0.01):
        f1_t = f1_score(y_val, (val_probs > t).astype(int), zero_division=0)
        if f1_t > best_f1:
            best_f1, best_t = f1_t, t

    with torch.no_grad():
        test_probs = torch.sigmoid(model(torch.tensor(X_test))).squeeze().numpy()
    preds = (test_probs > best_t).astype(int)

    return {
        "threshold": best_t,
        "accuracy": accuracy_score(y_test, preds),
        "precision": precision_score(y_test, preds, zero_division=0),
        "recall": recall_score(y_test, preds, zero_division=0),
        "f1": f1_score(y_test, preds, zero_division=0),
    }


def main(data_dir):
    X, y, time_steps = load_data(data_dir)
    X_train_raw, y_train_raw, X_val_raw, y_val, X_test_raw, y_test = temporal_split(X, y, time_steps)

    print(f"Temporal split: train={len(X_train_raw)}, val={len(X_val_raw)}, test={len(X_test_raw)}\n")
    print(f"{'config':<32} {'thresh':>7} {'acc':>7} {'prec':>7} {'rec':>7} {'f1':>7}")

    results = []
    for (name, h1, h2, loss_type, pw, f_alpha, f_gamma, scaler, clip_pct, smote, bs) in CONFIGS:
        X_train, X_val, X_test = scale_features(
            X_train_raw.copy(), X_val_raw.copy(), X_test_raw.copy(), scaler, clip_pct
        )
        X_train, y_train = maybe_smote(X_train, y_train_raw.copy(), smote)

        r = train_one(X_train, y_train, X_val, y_val, X_test, y_test,
                       h1, h2, loss_type, pw, f_alpha, f_gamma, bs)
        r["name"] = name
        results.append(r)
        print(f"{name:<32} {r['threshold']:>7.2f} {r['accuracy']:>7.4f} "
              f"{r['precision']:>7.4f} {r['recall']:>7.4f} {r['f1']:>7.4f}")

    best = max(results, key=lambda r: r["f1"])
    print(f"\nBest: {best['name']} -> F1={best['f1']:.4f} "
          f"(precision={best['precision']:.4f}, recall={best['recall']:.4f})")
    print("\nFind that config's exact settings in the CONFIGS list at the top of this file,")
    print("then re-run train_baseline.py with the matching flags to save the real model.")
    print("IMPORTANT: after saving, re-run prove_full_model.py to check the proving-cost")
    print("impact before locking in a larger capacity (128-64) as your final model.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="../data/elliptic_bitcoin_dataset")
    args = parser.parse_args()
    main(args.data_dir)
