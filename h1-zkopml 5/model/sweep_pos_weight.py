"""
Grid sweep over pos_weight_power AND hidden layer sizes, using the
correct TEMPORAL split (matches train_baseline.py's default protocol —
train on early time_steps, test on later ones). The old random-split
sweep numbers are not comparable to this; re-run if you have old results
saved.

Does NOT overwrite baseline_model.pt/onnx — trains throwaway models in
memory just to compare metrics. Once you pick the best config, re-run
train_baseline.py normally with those flags to save the real model files.

Run: python3 sweep_pos_weight.py --data-dir ../data/elliptic_bitcoin_dataset
"""

import argparse
import copy

import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
import torch
import torch.nn as nn

from train_baseline import FraudClassifier, SEED, load_data, temporal_split

POWERS_TO_TRY = [0.0, 0.3, 0.5, 0.7, 1.0]
CAPACITIES_TO_TRY = [(32, 16), (64, 32)]  # (hidden1, hidden2) — check proving cost if you go bigger


def train_one(X_train, y_train, X_val, y_val, X_test, y_test, power, hidden1, hidden2,
              epochs=300, patience=30, dropout=0.2):
    torch.manual_seed(SEED)
    model = FraudClassifier(hidden1=hidden1, hidden2=hidden2, dropout=dropout)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs)

    full_ratio = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
    pos_weight = torch.tensor([full_ratio ** power])
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    X_train_t = torch.tensor(X_train)
    y_train_t = torch.tensor(y_train).unsqueeze(1)
    X_val_t = torch.tensor(X_val)

    best_val_f1, best_state, no_improve = -1, None, 0
    for epoch in range(epochs):
        model.train()
        opt.zero_grad()
        loss = loss_fn(model(X_train_t), y_train_t)
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
        "power": power,
        "hidden": f"{hidden1}-{hidden2}",
        "threshold": best_t,
        "accuracy": accuracy_score(y_test, preds),
        "precision": precision_score(y_test, preds, zero_division=0),
        "recall": recall_score(y_test, preds, zero_division=0),
        "f1": f1_score(y_test, preds, zero_division=0),
    }


def main(data_dir):
    X, y, time_steps = load_data(data_dir)
    X_train, y_train, X_val, y_val, X_test, y_test = temporal_split(X, y, time_steps)

    mean, std = X_train.mean(axis=0), X_train.std(axis=0) + 1e-8
    X_train = (X_train - mean) / std
    X_val = (X_val - mean) / std
    X_test = (X_test - mean) / std

    print(f"Temporal split: train={len(X_train)}, val={len(X_val)}, test={len(X_test)}\n")
    print(f"{'power':>6} {'hidden':>8} {'threshold':>10} {'accuracy':>9} {'precision':>10} {'recall':>8} {'f1':>7}")

    results = []
    for hidden1, hidden2 in CAPACITIES_TO_TRY:
        for power in POWERS_TO_TRY:
            r = train_one(X_train, y_train, X_val, y_val, X_test, y_test, power, hidden1, hidden2)
            results.append(r)
            print(f"{r['power']:>6.1f} {r['hidden']:>8} {r['threshold']:>10.2f} {r['accuracy']:>9.4f} "
                  f"{r['precision']:>10.4f} {r['recall']:>8.4f} {r['f1']:>7.4f}")

    best = max(results, key=lambda r: r["f1"])
    h1, h2 = best["hidden"].split("-")
    print(f"\nBest F1: power={best['power']}, hidden={best['hidden']} -> F1={best['f1']:.4f} "
          f"(precision={best['precision']:.4f}, recall={best['recall']:.4f})")
    print("\nTo save this model for real, re-run:")
    print(f"  python3 train_baseline.py --data-dir {data_dir} --pos-weight-power {best['power']} "
          f"--hidden1 {h1} --hidden2 {h2}")
    print("\nIf you pick a larger hidden size than 32-16, re-run prove_full_model.py to check")
    print("the proving-cost impact before locking it in as your final model.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="../data/elliptic_bitcoin_dataset")
    args = parser.parse_args()
    main(args.data_dir)
