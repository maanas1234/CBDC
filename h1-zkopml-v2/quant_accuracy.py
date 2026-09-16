"""Accuracy of the circuit's fixed-point arithmetic vs float, full test set.
The bisected pipeline computes exactly the same fixed-point function as the
monolithic circuit (checked in the dispute run), so float->fixed-point is the
only possible source of accuracy loss."""
import numpy as np, pickle, json, sys
from sklearn.metrics import f1_score, accuracy_score, average_precision_score
from data import load, temporal_split, apply_scaler
from onnx_builder import forward_units
from quant import quantize_units, logits
S = int(sys.argv[1]) if len(sys.argv) > 1 else 7
X, y, ts = load(); _, _, (Xte, yte), _ = temporal_split(X, y, ts)
out = {}
for B in [1, 8, 24, 60]:
    m = pickle.load(open(f"models/W32_B{B}.pkl", "rb"))
    x = apply_scaler(Xte, m["scaler"]); thr = m["res"]["threshold"]
    pf = 1 / (1 + np.exp(-np.clip(forward_units(m["units"], x)[-1][:, 0], -50, 50)))
    pq = 1 / (1 + np.exp(-np.clip(logits(quantize_units(m["units"], S), x, S), -50, 50)))
    r = dict(float_acc=accuracy_score(yte, pf > thr), fixed_acc=accuracy_score(yte, pq > thr),
             float_f1=f1_score(yte, pf > thr), fixed_f1=f1_score(yte, pq > thr),
             float_pr_auc=average_precision_score(yte, pf), fixed_pr_auc=average_precision_score(yte, pq),
             decision_agreement=float(((pf > thr) == (pq > thr)).mean()))
    r["acc_drop_pp"] = 100 * (r["float_acc"] - r["fixed_acc"])
    r["f1_drop_pp"] = 100 * (r["float_f1"] - r["fixed_f1"])
    out[B] = r
    print(B, {k: round(v, 4) for k, v in r.items()}, flush=True)
json.dump(out, open(f"results/quant_accuracy_S{S}.json", "w"), indent=2)
