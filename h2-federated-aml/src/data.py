"""Elliptic1 preparation, graph loading, reproducibility, and labelled-only splits."""
from __future__ import annotations

import argparse
import random
from pathlib import Path
from typing import Dict, Iterable

import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from torch_geometric.data import Data

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "elliptic1"
PROCESSED_DIR = DATA_DIR / "processed"
RESULTS_DIR = PROJECT_ROOT / "results"


def set_seed(seed: int) -> None:
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True; torch.backends.cudnn.benchmark = False


def device_from_config(name: str = "auto") -> torch.device:
    return torch.device("cuda" if name == "auto" and torch.cuda.is_available() else ("cpu" if name == "auto" else name))


def build_transaction_index(transaction_ids: Iterable[int]) -> dict[int, int]:
    ids = [int(tx_id) for tx_id in transaction_ids]
    if len(ids) != len(set(ids)): raise ValueError("Transaction IDs must be unique")
    return {tx_id: index for index, tx_id in enumerate(ids)}


def map_edge_ids(edges: pd.DataFrame, tx_to_idx: dict[int, int]) -> pd.DataFrame:
    if not {"txId1", "txId2"}.issubset(edges.columns): raise ValueError("Raw edge data must contain txId1 and txId2")
    mapped = edges.copy()
    mapped["source_idx"] = mapped["txId1"].map(tx_to_idx); mapped["target_idx"] = mapped["txId2"].map(tx_to_idx)
    mapped = mapped.dropna(subset=["source_idx", "target_idx"]).copy()
    mapped[["source_idx", "target_idx"]] = mapped[["source_idx", "target_idx"]].astype(np.int64)
    return mapped


def convert_class_labels(classes: pd.DataFrame, tx_to_idx: dict[int, int]) -> np.ndarray:
    """Return 1=illicit, 0=licit, and -1=unknown; unknown is never inferred as licit."""
    if not {"txId", "class"}.issubset(classes.columns): raise ValueError("Class data must contain txId and class")
    labels = np.full(len(tx_to_idx), -1, dtype=np.int64)
    for tx_id, raw_label in classes[["txId", "class"]].itertuples(index=False):
        index = tx_to_idx.get(int(tx_id))
        if index is not None:
            if str(raw_label) == "1": labels[index] = 1
            elif str(raw_label) == "2": labels[index] = 0
    return labels


def prepare_data() -> None:
    """Build processed Elliptic1 arrays from the supplied raw CSV files."""
    features = pd.read_csv(DATA_DIR / "elliptic_txs_features.csv", header=None)
    edges = pd.read_csv(DATA_DIR / "elliptic_txs_edgelist.csv")
    classes = pd.read_csv(DATA_DIR / "elliptic_txs_classes.csv")
    tx_to_idx = build_transaction_index(features.iloc[:, 0].astype(int))
    mapped_edges = map_edge_ids(edges, tx_to_idx)
    labels = convert_class_labels(classes, tx_to_idx)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    np.save(PROCESSED_DIR / "features.npy", features.iloc[:, 1:].values.astype(np.float32))
    np.save(PROCESSED_DIR / "labels.npy", labels)
    np.save(PROCESSED_DIR / "trainable_mask.npy", labels != -1)
    mapped_edges[["source_idx", "target_idx"]].to_csv(PROCESSED_DIR / "edges.csv", index=False)
    print(f"Processed {len(labels)} nodes and {len(mapped_edges)} edges in {PROCESSED_DIR}")


def inspect_data() -> None:
    for name, path, kwargs in (("FEATURES", DATA_DIR / "elliptic_txs_features.csv", {"header": None}), ("EDGES", DATA_DIR / "elliptic_txs_edgelist.csv", {}), ("CLASSES", DATA_DIR / "elliptic_txs_classes.csv", {})):
        frame = pd.read_csv(path, **kwargs); print(name, "shape:", frame.shape); print(frame.head())
        if name == "CLASSES": print("CLASS COUNTS\n", frame["class"].value_counts())


def load_graph() -> Data:
    required = [PROCESSED_DIR / f for f in ("features.npy", "labels.npy", "trainable_mask.npy", "edges.csv")]
    missing = [str(p) for p in required if not p.exists()]
    if missing: raise FileNotFoundError("Processed Elliptic1 files are missing. Run `python src/main.py prepare-data` first: " + ", ".join(missing))
    x = torch.from_numpy(np.load(PROCESSED_DIR / "features.npy").astype(np.float32, copy=False))
    y = torch.from_numpy(np.load(PROCESSED_DIR / "labels.npy").astype(np.int64, copy=False))
    edges = pd.read_csv(PROCESSED_DIR / "edges.csv", usecols=["source_idx", "target_idx"]).to_numpy(np.int64)
    if edges.ndim != 2 or edges.shape[1] != 2 or edges.min() < 0 or edges.max() >= len(y): raise ValueError("edges.csv does not contain valid contiguous node indices")
    return Data(x=x, y=y, edge_index=torch.from_numpy(edges.T).long(), num_nodes=len(y))


def make_splits(y: torch.Tensor, seed: int = 42, train: float = .70, val: float = .15) -> Dict[str, torch.Tensor]:
    """Deterministic stratified 70/15/15 split over labelled nodes only."""
    labelled = torch.where(y >= 0)[0].cpu().numpy(); labels = y[labelled].cpu().numpy()
    train_i, hold_i = train_test_split(labelled, train_size=train, random_state=seed, stratify=labels)
    val_i, test_i = train_test_split(hold_i, train_size=val / (1 - train), random_state=seed + 1, stratify=y[hold_i].cpu().numpy())
    output = {}
    for name, indices in (("train", train_i), ("val", val_i), ("test", test_i)):
        mask = torch.zeros(y.numel(), dtype=torch.bool); mask[torch.as_tensor(indices)] = True; output[name] = mask
    return output


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("action", choices=["prepare", "inspect"]); args = parser.parse_args()
    prepare_data() if args.action == "prepare" else inspect_data()


if __name__ == "__main__": main()
