import pandas as pd
import numpy as np
import os

from utils import (
    build_transaction_index,
    convert_class_labels,
    map_edge_ids
)

# ============================================================
# 1. File paths
# ============================================================

features_path = "data/elliptic1/elliptic_txs_features.csv"
edges_path = "data/elliptic1/elliptic_txs_edgelist.csv"
classes_path = "data/elliptic1/elliptic_txs_classes.csv"

output_dir = "data/elliptic1/processed"
os.makedirs(output_dir, exist_ok=True)


# ============================================================
# 2. Check that files exist
# ============================================================

print("Checking files...")

for path in [features_path, edges_path, classes_path]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

print("All input files found.\n")


# ============================================================
# 3. Load data
# ============================================================

print("Loading data...")

features = pd.read_csv(features_path, header=None)
edges = pd.read_csv(edges_path)
classes = pd.read_csv(classes_path)

print("Features:", features.shape)
print("Edges:", edges.shape)
print("Classes:", classes.shape)


# ============================================================
# 4. Check column structure
# ============================================================

print("\nChecking columns...")

print("Edge columns:", list(edges.columns))
print("Class columns:", list(classes.columns))

if features.shape[1] < 2:
    raise ValueError(
        "Features file must contain transaction ID + feature columns."
    )

if len(edges.columns) < 2:
    raise ValueError(
        "Edges file must contain source and target transaction IDs."
    )

if len(classes.columns) < 2:
    raise ValueError(
        "Classes file must contain transaction ID and class."
    )


# ============================================================
# 5. Extract transaction IDs
# ============================================================

print("\nBuilding transaction index...")

# First column of features = transaction ID
tx_ids = pd.to_numeric(
    features.iloc[:, 0],
    errors="coerce"
)

# Check for invalid IDs
if tx_ids.isna().any():
    raise ValueError(
        f"Found {tx_ids.isna().sum()} invalid transaction IDs "
        "in features file."
    )

tx_ids = tx_ids.astype(np.int64)


# Check duplicate transaction IDs
duplicate_count = tx_ids.duplicated().sum()

if duplicate_count > 0:
    raise ValueError(
        f"Found {duplicate_count} duplicate transaction IDs."
    )


# Bitcoin transaction ID -> GNN node index
tx_to_idx = build_transaction_index(tx_ids)

print("Number of nodes:", len(tx_to_idx))

if len(tx_to_idx) != len(tx_ids):
    raise ValueError(
        "Transaction index size does not match number of feature rows."
    )


# ============================================================
# 6. Extract node features
# ============================================================

print("\nExtracting node features...")

# First column = transaction ID
# Remaining columns = actual node features
X = features.iloc[:, 1:].to_numpy(dtype=np.float32)

print("Feature matrix shape:", X.shape)

if X.shape[0] != len(tx_ids):
    raise ValueError(
        "Number of feature rows does not match number of transaction IDs."
    )

print("Number of node features:", X.shape[1])


# ============================================================
# 7. Convert edges from transaction IDs -> node indices
# ============================================================

print("\nMapping edges...")

raw_edge_count = len(edges)

edges = map_edge_ids(edges, tx_to_idx)

missing_edge_count = raw_edge_count - len(edges)

print("Original edges:", raw_edge_count)
print("Valid edges:", len(edges))
print("Edges with missing nodes:", missing_edge_count)

if len(edges) == 0:
    raise ValueError(
        "No valid edges remain after transaction-ID mapping."
    )

required_edge_columns = {"source_idx", "target_idx"}

if not required_edge_columns.issubset(edges.columns):
    raise ValueError(
        "map_edge_ids() must return 'source_idx' and 'target_idx' columns."
    )


# ============================================================
# 8. Check edge indices
# ============================================================

print("\nChecking edge indices...")

num_nodes = len(tx_to_idx)

invalid_source = (
    (edges["source_idx"] < 0) |
    (edges["source_idx"] >= num_nodes)
).sum()

invalid_target = (
    (edges["target_idx"] < 0) |
    (edges["target_idx"] >= num_nodes)
).sum()

print("Invalid source indices:", invalid_source)
print("Invalid target indices:", invalid_target)

if invalid_source > 0 or invalid_target > 0:
    raise ValueError(
        "Some mapped edge indices are outside the valid node range."
    )


# ============================================================
# 9. Convert labels
# ============================================================

print("\nConverting labels...")

y = convert_class_labels(classes, tx_to_idx)

print("Label array shape:", y.shape)

if len(y) != num_nodes:
    raise ValueError(
        f"Label count ({len(y)}) does not match "
        f"number of nodes ({num_nodes})."
    )


# ============================================================
# 10. Check label values
# ============================================================

unique_labels, label_counts = np.unique(
    y,
    return_counts=True
)

print("\nRaw label distribution:")

for label, count in zip(unique_labels, label_counts):
    print(f"  Label {label}: {count}")


# Expected:
# -1 = unknown
#  0 = licit
#  1 = illicit

unexpected_labels = set(unique_labels) - {-1, 0, 1}

if unexpected_labels:
    raise ValueError(
        f"Unexpected label values found: {unexpected_labels}"
    )


# ============================================================
# 11. Create masks
# ============================================================

trainable_mask = y != -1
illicit_mask = y == 1
licit_mask = y == 0
unknown_mask = y == -1

print("\nLabel statistics:")
print("Illicit:", int(illicit_mask.sum()))
print("Licit:", int(licit_mask.sum()))
print("Unknown:", int(unknown_mask.sum()))
print("Trainable:", int(trainable_mask.sum()))


# ============================================================
# 12. Verify masks
# ============================================================

if not np.all(
    trainable_mask == (licit_mask | illicit_mask)
):
    raise ValueError(
        "Trainable mask is inconsistent with labels."
    )

if not np.all(
    unknown_mask == ~trainable_mask
):
    raise ValueError(
        "Unknown mask is inconsistent with trainable mask."
    )


# ============================================================
# 13. Save processed data
# ============================================================

print("\nSaving processed data...")

np.save(
    os.path.join(output_dir, "features.npy"),
    X
)

np.save(
    os.path.join(output_dir, "labels.npy"),
    y
)

np.save(
    os.path.join(output_dir, "trainable_mask.npy"),
    trainable_mask
)

edges[
    ["source_idx", "target_idx"]
].to_csv(
    os.path.join(output_dir, "edges.csv"),
    index=False
)


# ============================================================
# 14. Final verification
# ============================================================

print("\nVerifying saved files...")

saved_files = [
    "features.npy",
    "labels.npy",
    "trainable_mask.npy",
    "edges.csv"
]

for filename in saved_files:
    path = os.path.join(output_dir, filename)

    if not os.path.exists(path):
        raise RuntimeError(
            f"Failed to create: {path}"
        )

    print("✓", path)


# ============================================================
# 15. Final summary
# ============================================================

print("\n" + "=" * 50)
print("PREPROCESSING COMPLETE")
print("=" * 50)

print("Nodes       :", num_nodes)
print("Features    :", X.shape[1])
print("Edges       :", len(edges))
print("Licit       :", int(licit_mask.sum()))
print("Illicit     :", int(illicit_mask.sum()))
print("Unknown     :", int(unknown_mask.sum()))
print("Trainable   :", int(trainable_mask.sum()))
print("Output dir  :", output_dir)

print("=" * 50)
