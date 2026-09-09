import pandas as pd
import numpy as np
import os

# --------------------------------------------------
# 1. File paths
# --------------------------------------------------

features_path = "data/elliptic1/elliptic_txs_features.csv"
edges_path = "data/elliptic1/elliptic_txs_edgelist.csv"
classes_path = "data/elliptic1/elliptic_txs_classes.csv"

output_dir = "data/elliptic1/processed"
os.makedirs(output_dir, exist_ok=True)


# --------------------------------------------------
# 2. Load data
# --------------------------------------------------

print("Loading data...")

features = pd.read_csv(features_path, header=None)
edges = pd.read_csv(edges_path)
classes = pd.read_csv(classes_path)

print("Features:", features.shape)
print("Edges:", edges.shape)
print("Classes:", classes.shape)


# --------------------------------------------------
# 3. Give each transaction a node index
# --------------------------------------------------

# First column of features = transaction ID
tx_ids = features.iloc[:, 0].astype(int)

# Mapping:
# Bitcoin transaction ID -> GNN node index
tx_to_idx = {
    tx_id: idx
    for idx, tx_id in enumerate(tx_ids)
}

print("\nNumber of nodes:", len(tx_to_idx))


# --------------------------------------------------
# 4. Convert edges from transaction IDs to indices
# --------------------------------------------------

edges["source_idx"] = edges["txId1"].map(tx_to_idx)
edges["target_idx"] = edges["txId2"].map(tx_to_idx)

# Check whether any edge contains an unknown transaction
missing_edges = edges[
    edges["source_idx"].isna() |
    edges["target_idx"].isna()
]

print("Edges with missing nodes:", len(missing_edges))

# Keep only valid edges
edges = edges.dropna(subset=["source_idx", "target_idx"]).copy()

edges["source_idx"] = edges["source_idx"].astype(int)
edges["target_idx"] = edges["target_idx"].astype(int)


# --------------------------------------------------
# 5. Extract node features
# --------------------------------------------------

# First column is transaction ID.
# Remaining 166 columns are the actual features.
X = features.iloc[:, 1:].values.astype(np.float32)

print("Feature matrix shape:", X.shape)


# --------------------------------------------------
# 6. Convert labels
# --------------------------------------------------

# Start with all nodes as unknown (-1)
y = np.full(len(tx_ids), -1, dtype=np.int64)

for _, row in classes.iterrows():

    tx_id = int(row["txId"])
    label = row["class"]

    if tx_id not in tx_to_idx:
        continue

    idx = tx_to_idx[tx_id]

    if label == "1":
        y[idx] = 1       # illicit

    elif label == "2":
        y[idx] = 0       # licit

    # unknown remains -1


# --------------------------------------------------
# 7. Create masks
# --------------------------------------------------

trainable_mask = y != -1
illicit_mask = y == 1
licit_mask = y == 0
unknown_mask = y == -1

print("\nLabel statistics:")
print("Illicit:", illicit_mask.sum())
print("Licit:", licit_mask.sum())
print("Unknown:", unknown_mask.sum())


# --------------------------------------------------
# 8. Save processed data
# --------------------------------------------------

np.save(
    f"{output_dir}/features.npy",
    X
)

np.save(
    f"{output_dir}/labels.npy",
    y
)

np.save(
    f"{output_dir}/trainable_mask.npy",
    trainable_mask
)

edges[
    ["source_idx", "target_idx"]
].to_csv(
    f"{output_dir}/edges.csv",
    index=False
)

print("\nProcessed data saved to:")
print(output_dir)

print("\nDone!")
