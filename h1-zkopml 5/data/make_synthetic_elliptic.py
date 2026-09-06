"""
Generates a synthetic dataset that mirrors the structure of the real
Kaggle Elliptic dataset (Bitcoin transaction graph, fraud/AML detection):

  - elliptic_txs_features.csv : 1 tx_id + 165 features (94 local + 72 aggregated)
  - elliptic_txs_classes.csv  : tx_id -> class (1 = illicit, 2 = licit, unknown = unlabeled)
  - elliptic_txs_edgelist.csv : txId1 -> txId2 (graph edges between transactions)

This exists so H1 has a working, runnable pipeline from day one.
Swap this out for the real Kaggle CSVs later — the loader in
train_baseline.py expects exactly this schema, so the swap should be a
one-line path change, not a rewrite.
"""

import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)

N_TX = 4000          # number of synthetic transactions
N_FEATURES = 165      # matches real Elliptic feature count
ILLICIT_FRAC = 0.10   # real dataset is heavily imbalanced toward licit/unknown
UNKNOWN_FRAC = 0.55    # real dataset has ~77% unknown; keep more labeled here for a usable baseline


def make_features_and_labels():
    labels = RNG.choice(
        ["1", "2", "unknown"],
        size=N_TX,
        p=[ILLICIT_FRAC, 1 - ILLICIT_FRAC - UNKNOWN_FRAC, UNKNOWN_FRAC],
    )

    # illicit transactions get a shifted feature distribution so the
    # classification task is learnable but not trivial
    illicit_mask = labels == "1"
    base = RNG.normal(loc=0.0, scale=1.0, size=(N_TX, N_FEATURES))
    base[illicit_mask] += RNG.normal(loc=1.2, scale=0.3, size=(illicit_mask.sum(), N_FEATURES))

    tx_ids = np.arange(1, N_TX + 1)

    feat_cols = ["tx_id", "time_step"] + [f"feat_{i}" for i in range(1, N_FEATURES + 1)]
    time_steps = RNG.integers(1, 50, size=N_TX)  # Elliptic has 49 time steps
    feat_df = pd.DataFrame(
        np.column_stack([tx_ids, time_steps, base]), columns=feat_cols
    )
    feat_df["tx_id"] = feat_df["tx_id"].astype(int)
    feat_df["time_step"] = feat_df["time_step"].astype(int)

    class_df = pd.DataFrame({"txId": tx_ids, "class": labels})

    return feat_df, class_df


def make_edges(tx_ids, avg_degree=2):
    n_edges = len(tx_ids) * avg_degree
    src = RNG.choice(tx_ids, size=n_edges)
    dst = RNG.choice(tx_ids, size=n_edges)
    keep = src != dst
    edge_df = pd.DataFrame({"txId1": src[keep], "txId2": dst[keep]}).drop_duplicates()
    return edge_df


if __name__ == "__main__":
    feat_df, class_df = make_features_and_labels()
    edge_df = make_edges(feat_df["tx_id"].values)

    feat_df.to_csv("elliptic_txs_features.csv", index=False, header=False)
    class_df.to_csv("elliptic_txs_classes.csv", index=False)
    edge_df.to_csv("elliptic_txs_edgelist.csv", index=False)

    print(f"Wrote {len(feat_df)} transactions, {len(edge_df)} edges")
    print(class_df["class"].value_counts())
