"""
Baseline fraud/risk classifier for H1.

Deliberately a small MLP, not a big GNN — EZKL proving cost scales with
model size, and the whole point of H1 is proving cheaply. Start small,
only grow the model if accuracy demands it AND you've checked the
proving-cost tradeoff. (In practice, proving cost here is dominated by
fixed circuit overhead, not model size — see the README — so there's
been real room to grow capacity for free.)

Works with EITHER the synthetic data (make_synthetic_elliptic.py) or the
real Kaggle Elliptic dataset — same three filenames, same schema, so no
code changes needed to swap. Get the real data from:
https://www.kaggle.com/datasets/ellipticco/elliptic-data-set

SPLIT MODES:
  --split temporal (default): train on early time_steps, test on later
      ones — matches the original Elliptic paper's protocol (Weber et al.
      2019) and avoids a documented leakage issue with random splits.
  --split random: old behavior, comparison only, optimistic due to leakage.

TRAINING IMPROVEMENTS (v3):
  --batch-size: mini-batch SGD instead of full-batch gradient descent.
      Full-batch on 27k examples was a real limiter — mini-batches with
      shuffling give the optimizer many more update steps per epoch and
      usually generalize better.
  --loss {bce, focal}: focal loss down-weights easy (already-confident)
      examples and focuses gradient on hard ones — often stronger than
      class-weighted BCE on severely imbalanced data like this.
  --scaler {standard, robust}: robust scaling uses median/IQR instead of
      mean/std, less thrown off by extreme outliers (financial features
      are often heavy-tailed).
  --clip-percentile: clips extreme feature values before scaling.
  --smote: oversample the minority (illicit) class in the TRAINING split
      only via SMOTE synthetic interpolation — does not touch val/test,
      so it can't leak.

Run: python3 train_baseline.py [--data-dir PATH] [options]
Outputs: baseline_model.pt (weights), baseline_model.onnx (for EZKL), metrics printed to stdout
"""

import argparse
import copy
import sys

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split

N_FEATURES = 165
SEED = 42

torch.manual_seed(SEED)
np.random.seed(SEED)


def validate_schema(feat_df, class_df, edge_df):
    """Catch a bad/mismatched download early instead of failing deep in training."""
    errors = []

    expected_feat_cols = 2 + N_FEATURES  # tx_id, time_step, 165 features
    if feat_df.shape[1] != expected_feat_cols:
        errors.append(
            f"elliptic_txs_features.csv has {feat_df.shape[1]} columns, "
            f"expected {expected_feat_cols} (tx_id + time_step + {N_FEATURES} features). "
            "Real Elliptic releases occasionally differ slightly — check the source."
        )

    if list(class_df.columns[:2]) != ["tx_id", "class"]:
        errors.append(
            f"elliptic_txs_classes.csv columns are {list(class_df.columns)}, "
            "expected ['tx_id', 'class']. Check header naming from your download."
        )

    seen_classes = set(class_df["class"].astype(str).unique())
    expected_classes = {"1", "2", "unknown"}
    if not seen_classes.issubset(expected_classes):
        errors.append(
            f"Unexpected class labels found: {seen_classes - expected_classes}. "
            f"Expected only {expected_classes}."
        )

    if edge_df.shape[1] < 2:
        errors.append("elliptic_txs_edgelist.csv has fewer than 2 columns.")

    n_labeled = (class_df["class"].astype(str) != "unknown").sum()
    if n_labeled < 50:
        errors.append(
            f"Only {n_labeled} labeled transactions found — too few to train/test on. "
            "Check you're not accidentally loading a tiny sample."
        )

    if errors:
        print("\n--- Schema validation FAILED ---", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        print(
            "\nFix the data files or --data-dir path before continuing.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        f"Schema OK: {len(feat_df)} transactions, {n_labeled} labeled "
        f"({(class_df['class'].astype(str) == '1').sum()} illicit, "
        f"{(class_df['class'].astype(str) == '2').sum()} licit), "
        f"{len(edge_df)} edges."
    )


class FraudClassifier(nn.Module):
    """Small MLP: 165 -> hidden1 -> hidden2 -> 1 (sigmoid), with BatchNorm
    and Dropout for regularization. Kept to 2 hidden layers on purpose —
    split_model.py's EarlyHalf/LateHalf slice this net's layers by fixed
    index (0-7), so changing the NUMBER of layers (not just their width)
    requires updating split_model.py's slice indices too.

    NOTE: BatchNorm layers behave differently in train() vs eval() mode.
    Always call model.eval() before exporting to ONNX / proving, so the
    running statistics (not batch statistics) are used."""

    def __init__(self, n_features=N_FEATURES, hidden1=32, hidden2=16, dropout=0.2):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_features, hidden1),
            nn.BatchNorm1d(hidden1),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden1, hidden2),
            nn.BatchNorm1d(hidden2),
            nn.ReLU(),
            nn.Linear(hidden2, 1),
        )

    def forward(self, x):
        return self.net(x)  # raw logits; sigmoid applied at loss/eval time


class FocalLoss(nn.Module):
    """Focal loss (Lin et al. 2017) for binary classification with logits.
    Down-weights easy/already-confident examples so the gradient focuses
    on hard ones — often stronger than class-weighted BCE for severe
    imbalance like Elliptic's ~10% illicit rate.

    alpha: class balance weight for the positive (illicit) class.
    gamma: focusing parameter — higher means more down-weighting of easy
        examples. gamma=0 reduces to plain weighted BCE.
    """

    def __init__(self, alpha=0.75, gamma=2.0):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma

    def forward(self, logits, targets):
        bce = nn.functional.binary_cross_entropy_with_logits(logits, targets, reduction="none")
        probs = torch.sigmoid(logits)
        p_t = probs * targets + (1 - probs) * (1 - targets)
        alpha_t = self.alpha * targets + (1 - self.alpha) * (1 - targets)
        focal_weight = alpha_t * (1 - p_t) ** self.gamma
        return (focal_weight * bce).mean()


def load_data(data_dir):
    feat_df = pd.read_csv(f"{data_dir}/elliptic_txs_features.csv", header=None)
    class_df = pd.read_csv(f"{data_dir}/elliptic_txs_classes.csv")
    class_df.columns = ["tx_id", "class"]
    edge_df = pd.read_csv(f"{data_dir}/elliptic_txs_edgelist.csv")

    validate_schema(feat_df, class_df, edge_df)

    feat_df.columns = ["tx_id", "time_step"] + [f"feat_{i}" for i in range(1, N_FEATURES + 1)]

    merged = feat_df.merge(class_df, on="tx_id")
    labeled = merged[merged["class"] != "unknown"].copy()
    labeled["label"] = (labeled["class"] == "1").astype(int)  # 1 = illicit

    X = labeled[[f"feat_{i}" for i in range(1, N_FEATURES + 1)]].values.astype(np.float32)
    y = labeled["label"].values.astype(np.float32)
    time_steps = labeled["time_step"].values

    return X, y, time_steps


def temporal_split(X, y, time_steps, train_end=34, val_start=30):
    """Matches the original Elliptic paper's protocol: train on early
    time_steps, test on later ones — no shuffling, no random split."""
    train_mask = time_steps <= val_start
    val_mask = (time_steps > val_start) & (time_steps <= train_end)
    test_mask = time_steps > train_end

    return (
        X[train_mask], y[train_mask],
        X[val_mask], y[val_mask],
        X[test_mask], y[test_mask],
    )


def random_split(X, y):
    """Old behavior — kept for comparison only. Numbers from this split
    are optimistic due to a documented leakage issue."""
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.30, random_state=SEED, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=SEED, stratify=y_temp
    )
    return X_train, y_train, X_val, y_val, X_test, y_test


def scale_features(X_train, X_val, X_test, scaler="standard", clip_percentile=None):
    """Fits scaling on TRAIN ONLY, applies to all three splits. Optionally
    clips extreme values first (computed from train only) — financial
    features are often heavy-tailed, and a few extreme values can distort
    standard scaling in particular."""
    if clip_percentile is not None:
        lo = np.percentile(X_train, clip_percentile, axis=0)
        hi = np.percentile(X_train, 100 - clip_percentile, axis=0)
        X_train = np.clip(X_train, lo, hi)
        X_val = np.clip(X_val, lo, hi)
        X_test = np.clip(X_test, lo, hi)

    if scaler == "robust":
        center = np.median(X_train, axis=0)
        iqr = np.percentile(X_train, 75, axis=0) - np.percentile(X_train, 25, axis=0)
        scale = iqr + 1e-8
    else:
        center = X_train.mean(axis=0)
        scale = X_train.std(axis=0) + 1e-8

    X_train = (X_train - center) / scale
    X_val = (X_val - center) / scale
    X_test = (X_test - center) / scale
    return X_train, X_val, X_test


def maybe_smote(X_train, y_train, use_smote):
    if not use_smote:
        return X_train, y_train
    from imblearn.over_sampling import SMOTE
    sm = SMOTE(random_state=SEED)
    X_res, y_res = sm.fit_resample(X_train, y_train)
    print(f"SMOTE: train size {len(X_train)} -> {len(X_res)} "
          f"(illicit {int(y_train.sum())} -> {int(y_res.sum())})")
    return X_res.astype(np.float32), y_res.astype(np.float32)


def train(data_dir, split="temporal", hidden1=32, hidden2=16, epochs=300,
          pos_weight_power=0.5, lr=1e-3, weight_decay=1e-4, patience=30, dropout=0.2,
          batch_size=None, loss_type="bce", focal_alpha=0.75, focal_gamma=2.0,
          scaler="standard", clip_percentile=None, use_smote=False):
    X, y, time_steps = load_data(data_dir)

    if split == "temporal":
        X_train, y_train, X_val, y_val, X_test, y_test = temporal_split(X, y, time_steps)
        print(f"Temporal split: train={len(X_train)}, val={len(X_val)}, test={len(X_test)} "
              f"(matches Weber et al. 2019 protocol — no random-split leakage)")
    else:
        X_train, y_train, X_val, y_val, X_test, y_test = random_split(X, y)
        print(f"Random split (comparison only, optimistic due to leakage): "
              f"train={len(X_train)}, val={len(X_val)}, test={len(X_test)}")

    X_train, X_val, X_test = scale_features(X_train, X_val, X_test, scaler, clip_percentile)
    X_train, y_train = maybe_smote(X_train, y_train, use_smote)

    model = FraudClassifier(hidden1=hidden1, hidden2=hidden2, dropout=dropout)
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs)

    if loss_type == "focal":
        loss_fn = FocalLoss(alpha=focal_alpha, gamma=focal_gamma)
        print(f"Using focal loss (alpha={focal_alpha}, gamma={focal_gamma})")
    else:
        full_ratio = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
        pos_weight = torch.tensor([full_ratio ** pos_weight_power])
        loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
        print(f"Using weighted BCE (pos_weight_power={pos_weight_power})")

    X_train_t = torch.tensor(X_train)
    y_train_t = torch.tensor(y_train).unsqueeze(1)
    X_val_t = torch.tensor(X_val)
    n_train = len(X_train_t)
    batch_size = batch_size or n_train  # None/0 -> full-batch (old behavior)

    best_val_f1, best_state, epochs_without_improvement = -1, None, 0

    for epoch in range(epochs):
        model.train()
        perm = torch.randperm(n_train)
        for start in range(0, n_train, batch_size):
            idx = perm[start:start + batch_size]
            opt.zero_grad()
            logits = model(X_train_t[idx])
            loss = loss_fn(logits, y_train_t[idx])
            loss.backward()
            opt.step()
        scheduler.step()

        model.eval()
        with torch.no_grad():
            val_preds = (torch.sigmoid(model(X_val_t)).squeeze() > 0.5).int().numpy()
        val_f1 = f1_score(y_val, val_preds, zero_division=0)

        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            best_state = copy.deepcopy(model.state_dict())
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1

        if (epoch + 1) % 30 == 0:
            print(f"epoch {epoch+1}: loss {loss.item():.4f}  val_f1 {val_f1:.4f}  "
                  f"best_val_f1 {best_val_f1:.4f}")

        if epochs_without_improvement >= patience:
            print(f"Early stopping at epoch {epoch+1} (no val F1 improvement for {patience} epochs)")
            break

    model.load_state_dict(best_state)
    print(f"Restored best weights (val F1 at save time: {best_val_f1:.4f})")

    model.eval()
    with torch.no_grad():
        val_probs = torch.sigmoid(model(X_val_t)).squeeze().numpy()

    best_threshold, best_thresh_f1 = 0.5, -1
    for t in np.arange(0.05, 0.95, 0.01):
        f1_t = f1_score(y_val, (val_probs > t).astype(int), zero_division=0)
        if f1_t > best_thresh_f1:
            best_thresh_f1, best_threshold = f1_t, t
    print(f"\nChosen threshold (max F1 on val set): {best_threshold:.2f} (val F1: {best_thresh_f1:.4f})")

    with torch.no_grad():
        test_probs = torch.sigmoid(model(torch.tensor(X_test))).squeeze().numpy()
    preds = (test_probs > best_threshold).astype(int)

    acc = accuracy_score(y_test, preds)
    prec = precision_score(y_test, preds, zero_division=0)
    rec = recall_score(y_test, preds, zero_division=0)
    f1 = f1_score(y_test, preds, zero_division=0)

    print(f"\n--- Held-out TEST metrics ({split} split, threshold picked on val, never test) ---")
    print(f"accuracy:  {acc:.4f}")
    print(f"precision: {prec:.4f}  (of flagged-illicit, how many were right)")
    print(f"recall:    {rec:.4f}  (of actual illicit, how many were caught)")
    print(f"f1:        {f1:.4f}")

    torch.save(model.state_dict(), "baseline_model.pt")
    with open("decision_threshold.txt", "w") as f:
        f.write(str(best_threshold))

    model.eval()
    dummy_input = torch.randn(1, N_FEATURES)
    torch.onnx.export(
        model, dummy_input, "baseline_model.onnx",
        input_names=["input"], output_names=["output"],
        opset_version=11,
        dynamo=False,
    )
    print("\nSaved baseline_model.pt, baseline_model.onnx, decision_threshold.txt")

    return acc, prec, rec, f1, X_test, y_test


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="../data")
    parser.add_argument("--split", choices=["temporal", "random"], default="temporal")
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--patience", type=int, default=30)
    parser.add_argument("--pos-weight-power", type=float, default=0.5)
    parser.add_argument("--hidden1", type=int, default=32)
    parser.add_argument("--hidden2", type=int, default=16)
    parser.add_argument("--dropout", type=float, default=0.2)
    parser.add_argument("--batch-size", type=int, default=None,
                         help="Mini-batch size. Default (unset) = full-batch, matching old behavior.")
    parser.add_argument("--loss", choices=["bce", "focal"], default="bce")
    parser.add_argument("--focal-alpha", type=float, default=0.75)
    parser.add_argument("--focal-gamma", type=float, default=2.0)
    parser.add_argument("--scaler", choices=["standard", "robust"], default="standard")
    parser.add_argument("--clip-percentile", type=float, default=None,
                         help="e.g. 1 to clip to the 1st/99th percentile before scaling.")
    parser.add_argument("--smote", action="store_true",
                         help="Oversample the minority class in TRAINING data only via SMOTE.")
    args = parser.parse_args()
    train(args.data_dir, split=args.split, hidden1=args.hidden1, hidden2=args.hidden2,
          epochs=args.epochs, pos_weight_power=args.pos_weight_power, patience=args.patience,
          dropout=args.dropout, batch_size=args.batch_size, loss_type=args.loss,
          focal_alpha=args.focal_alpha, focal_gamma=args.focal_gamma, scaler=args.scaler,
          clip_percentile=args.clip_percentile, use_smote=args.smote)
