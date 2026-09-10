"""Fixed-point emulation of the EZKL circuit (input/param scale S, rebase to S
after each matmul). Used to (a) run the deterministic trace that the dispute
protocol commits to, and (b) measure quantized accuracy on the full test set.
Validated bit-exact against EZKL witnesses in check_quant.py."""
import numpy as np

S = 9

def qround(x):  # round half away from zero
    return np.sign(x) * np.floor(np.abs(x) + 0.5)

def quantize_units(units, s=S):
    return [dict(kind=u["kind"], Wq=qround(u["W"] * 2 ** s).astype(np.int64),
                 bq=(qround(u["b"] * 2 ** s) * 2 ** s).astype(np.int64))  # bias at scale S, lifted to 2S
            for u in units]

def rebase(z, s=S):  # divide by 2^s with rounding
    return qround(z / 2 ** s).astype(np.int64)

def unit_fwd(qu, h, s=S):
    z = rebase(h @ qu["Wq"] + qu["bq"], s)
    if qu["kind"] == "proj": return np.maximum(z, 0)
    if qu["kind"] == "block": return h + np.maximum(z, 0)
    return z

def trace(qunits, x, s=S):
    """x: float (n, F). Returns list of int64 activations [a0=q(x), a1, ..., aL]."""
    h = qround(x * 2 ** s).astype(np.int64)
    acts = [h]
    for qu in qunits:
        h = unit_fwd(qu, h, s)
        acts.append(h)
    return acts

def logits(qunits, x, s=S):
    return trace(qunits, x, s)[-1][:, 0] / 2 ** s
