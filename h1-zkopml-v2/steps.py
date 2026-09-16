"""Step-level fixed-point trace for the bisectable DAG (see onnx_builder.dispute_steps)."""
import numpy as np
from quant import quantize_units, rebase, qround, S


def quantize_steps(steps, s=S):
    for st in steps:
        st["q"] = quantize_units([st["unit"]], s)[0]
    return steps


def step_fwd(st, ins, s=S):
    h = np.concatenate(ins, axis=1)
    qu = st["q"]
    z = rebase(h @ qu["Wq"] + qu["bq"], s)
    if qu["kind"] == "proj": return np.maximum(z, 0)
    if qu["kind"] == "block": return h + np.maximum(z, 0)
    return z


def run_steps(steps, x, s=S, corrupt=None):
    """x float (n, F). Returns (xq, outs) where outs[i] is step i's int output.
    corrupt=(step_idx, fn) lets a dishonest prover tamper with one step's output;
    the tampered value then propagates honestly through later steps."""
    xq = qround(x * 2 ** s).astype(np.int64)
    outs = []
    for i, st in enumerate(steps):
        ins = [xq if j == -1 else outs[j] for j in st["inputs"]]
        o = step_fwd(st, ins, s)
        if corrupt is not None and corrupt[0] == i:
            o = corrupt[1](o.copy())
        outs.append(o)
    return xq, outs
