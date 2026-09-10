"""Convert the Kaggle Elliptic CSVs into X.npy / y.npy / ts.npy (labeled rows only).
Usage: python3 prepare_data.py /path/to/elliptic_bitcoin_dataset"""
import sys, numpy as np, pandas as pd
d = sys.argv[1] if len(sys.argv) > 1 else "elliptic_bitcoin_dataset"
feat = pd.read_csv(f"{d}/elliptic_txs_features.csv", header=None)
cls = pd.read_csv(f"{d}/elliptic_txs_classes.csv"); cls.columns = ["tx_id", "class"]
assert feat.shape[1] == 167, f"expected 167 columns, got {feat.shape[1]}"
feat.columns = ["tx_id", "time_step"] + [f"f{i}" for i in range(165)]
df = feat.merge(cls, on="tx_id"); df = df[df["class"].astype(str) != "unknown"]
np.save("X.npy", df[[f"f{i}" for i in range(165)]].values.astype(np.float32))
np.save("y.npy", (df["class"].astype(str) == "1").values.astype(np.float32))
np.save("ts.npy", df["time_step"].values)
print(f"{len(df)} labeled transactions ({int((df['class'].astype(str) == '1').sum())} illicit)")
