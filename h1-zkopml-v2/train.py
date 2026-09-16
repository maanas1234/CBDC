"""NumPy trainer for the residual MLP family used in the H1 depth sweep.
Model selection uses the VALIDATION split only (early stopping on val PR-AUC,
threshold tuned on val). Test is touched once, at the end."""
import numpy as np, json, pickle, sys
from sklearn.metrics import f1_score, average_precision_score, precision_score, recall_score, accuracy_score
from data import load, temporal_split, fit_scaler, apply_scaler
from onnx_builder import forward_units


def init(n_feat, W, B, rng):
    u = [{"kind": "proj", "W": rng.normal(0, np.sqrt(2 / n_feat), (n_feat, W)), "b": np.zeros(W)}]
    for _ in range(B):  # residual branches start small so the deep net trains stably
        u.append({"kind": "block", "W": rng.normal(0, np.sqrt(2 / W) / np.sqrt(max(B, 1)), (W, W)), "b": np.zeros(W)})
    u.append({"kind": "head", "W": rng.normal(0, np.sqrt(1 / W), (W, 1)), "b": np.zeros(1)})
    return u


def fwd(units, x):
    cache, h = [], x
    for u in units:
        z = h @ u["W"] + u["b"]
        cache.append((h, z))
        if u["kind"] == "proj": h = np.maximum(z, 0)
        elif u["kind"] == "block": h = h + np.maximum(z, 0)
        else: h = z
    return h[:, 0], cache


def bwd(units, cache, dlogit):
    grads = [None] * len(units)
    dh = dlogit[:, None]
    for i in range(len(units) - 1, -1, -1):
        u, (hin, z) = units[i], cache[i]
        if u["kind"] == "head": dz = dh
        else: dz = dh * (z > 0)
        grads[i] = (hin.T @ dz, dz.sum(0))
        dx = dz @ u["W"].T
        dh = dh + dx if u["kind"] == "block" else dx
    return grads


def predict(units, x, bs=8192):
    return np.concatenate([1 / (1 + np.exp(-fwd(units, x[i:i + bs])[0])) for i in range(0, len(x), bs)])


def train(W, B, seed=0, epochs=150, bs=512, lr=1e-3, wd=1e-4, pw_power=0.7, patience=20, verbose=False):
    rng = np.random.default_rng(seed)
    X, y, ts = load()
    (Xtr, ytr), (Xva, yva), (Xte, yte), tste = temporal_split(X, y, ts)
    sc = fit_scaler(Xtr)
    Xtr, Xva, Xte = apply_scaler(Xtr, sc), apply_scaler(Xva, sc), apply_scaler(Xte, sc)
    pw = ((ytr == 0).sum() / (ytr == 1).sum()) ** pw_power
    units = init(Xtr.shape[1], W, B, rng)
    m = [(np.zeros_like(u["W"]), np.zeros_like(u["b"])) for u in units]
    v = [(np.zeros_like(u["W"]), np.zeros_like(u["b"])) for u in units]
    t, best, best_units, bad = 0, -1, None, 0
    for ep in range(epochs):
        perm = rng.permutation(len(Xtr))
        for s in range(0, len(Xtr), bs):
            idx = perm[s:s + bs]; xb, yb = Xtr[idx], ytr[idx]
            logit, cache = fwd(units, xb)
            p = 1 / (1 + np.exp(-logit))
            w = np.where(yb == 1, pw, 1.0)
            grads = bwd(units, cache, w * (p - yb) / len(yb))
            t += 1
            for i, u in enumerate(units):
                for j, key in enumerate(("W", "b")):
                    g = grads[i][j] + (wd * u[key] if key == "W" else 0)
                    m[i][j][...] = 0.9 * m[i][j] + 0.1 * g
                    v[i][j][...] = 0.999 * v[i][j] + 0.001 * g * g
                    u[key] -= lr * (m[i][j] / (1 - 0.9 ** t)) / (np.sqrt(v[i][j] / (1 - 0.999 ** t)) + 1e-8)
        ap = average_precision_score(yva, predict(units, Xva))
        if ap > best:
            best, bad = ap, 0
            best_units = [{k: (val.copy() if isinstance(val, np.ndarray) else val) for k, val in u.items()} for u in units]
        else:
            bad += 1
        if verbose and ep % 10 == 0: print(ep, round(ap, 4), flush=True)
        if bad >= patience: break
    units = best_units
    pva = predict(units, Xva)
    thr = max(np.arange(0.05, 0.95, 0.01), key=lambda th: f1_score(yva, pva > th))
    pte = predict(units, Xte)
    pred = pte > thr
    pre = tste < 43
    res = dict(W=W, B=B, seed=seed, val_pr_auc=best, threshold=float(thr),
               test_f1=f1_score(yte, pred), test_prec=precision_score(yte, pred), test_rec=recall_score(yte, pred),
               test_acc=accuracy_score(yte, pred), test_pr_auc=average_precision_score(yte, pte),
               f1_35_42=f1_score(yte[pre], pred[pre]), f1_43_49=f1_score(yte[~pre], pred[~pre]))
    return units, sc, res


if __name__ == "__main__":
    W, B, seed = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 0
    import time; t = time.time()
    units, sc, res = train(W, B, seed, verbose=True)
    print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in res.items()}, "time", round(time.time() - t, 1))
    pickle.dump(dict(units=units, scaler=sc, res=res), open(f"model_W{W}_B{B}_s{seed}.pkl", "wb"))
