import pandas as pd

# File paths
features_path = "data/elliptic1/elliptic_txs_features.csv"
edges_path = "data/elliptic1/elliptic_txs_edgelist.csv"
classes_path = "data/elliptic1/elliptic_txs_classes.csv"

# Load the three files
features = pd.read_csv(features_path, header=None)
edges = pd.read_csv(edges_path)
classes = pd.read_csv(classes_path)

# Basic information
print("FEATURES")
print("Shape:", features.shape)
print(features.head())

print("\nEDGES")
print("Shape:", edges.shape)
print(edges.head())

print("\nCLASSES")
print("Shape:", classes.shape)
print(classes.head())

print("\nCLASS COUNTS")
print(classes["class"].value_counts())