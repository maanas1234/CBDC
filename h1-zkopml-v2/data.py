"""Elliptic loading + preprocessing (fixed version of the H1 repo's pipeline).
Fixes: scale = max(IQR, std) after clipping, so near-constant features — the original
divided by 1e-8 for 29 features and produced values up to ~1e9."""
import numpy as np

def load(path="."):
    return np.load(f"{path}/X.npy"), np.load(f"{path}/y.npy"), np.load(f"{path}/ts.npy")

def temporal_split(X, y, ts):
    tr, va, te = ts <= 30, (ts > 30) & (ts <= 34), ts > 34
    return (X[tr], y[tr]), (X[va], y[va]), (X[te], y[te]), ts[te]

def fit_scaler(Xtr, clip_pct=1.0):
    lo = np.percentile(Xtr, clip_pct, 0); hi = np.percentile(Xtr, 100 - clip_pct, 0)
    Xc = np.clip(Xtr, lo, hi)
    center = np.median(Xc, 0)
    iqr = np.percentile(Xc, 75, 0) - np.percentile(Xc, 25, 0)
    std = Xc.std(0)
    # max(IQR, std): IQR for heavy-tailed features, std when IQR collapses.
    scale = np.maximum(np.maximum(iqr, std), 1e-6)
    return dict(lo=lo, hi=hi, center=center, scale=scale)

def apply_scaler(X, s):
    return ((np.clip(X, s["lo"], s["hi"]) - s["center"]) / s["scale"]).astype(np.float32)
