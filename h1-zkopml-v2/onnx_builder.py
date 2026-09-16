"""Build ONNX graphs for a residual MLP directly from numpy weights.

Architecture (all ops EZKL-friendly: MatMul, Add, Relu):
  unit 0  proj : h = relu(x @ W0 + b0)              (F -> W)
  unit k  block: h = h + relu(h @ Wk + bk)          (W -> W), k = 1..B
  unit B+1 head: logit = h @ Wh + bh                 (W -> 1)

Each unit is a bisection leaf: the dispute protocol commits to the
activation after every unit, and a dispute is settled by proving one unit.
"""
import numpy as np
import onnx
from onnx import helper, TensorProto, numpy_helper


def _lin(nodes, inits, x, W, b, tag):
    Wn, bn = f"{tag}_W", f"{tag}_b"
    inits += [numpy_helper.from_array(W.astype(np.float32), Wn),
              numpy_helper.from_array(b.astype(np.float32), bn)]
    nodes += [helper.make_node("MatMul", [x, Wn], [f"{tag}_mm"]),
              helper.make_node("Add", [f"{tag}_mm", bn], [f"{tag}_lin"])]
    return f"{tag}_lin"


def _unit(nodes, inits, x, unit, tag):
    kind = unit["kind"]
    if kind == "proj":
        z = _lin(nodes, inits, x, unit["W"], unit["b"], tag)
        nodes.append(helper.make_node("Relu", [z], [f"{tag}_out"]))
    elif kind == "block":
        z = _lin(nodes, inits, x, unit["W"], unit["b"], tag)
        nodes.append(helper.make_node("Relu", [z], [f"{tag}_r"]))
        nodes.append(helper.make_node("Add", [x, f"{tag}_r"], [f"{tag}_out"]))
    elif kind == "head":
        z = _lin(nodes, inits, x, unit["W"], unit["b"], tag)
        nodes.append(helper.make_node("Identity", [z], [f"{tag}_out"]))
    else:
        raise ValueError(kind)
    return f"{tag}_out"


def unit_dims(unit):
    return unit["W"].shape  # (in, out)


def build(units, path):
    """Export a contiguous list of units as one ONNX graph (batch=1)."""
    nodes, inits = [], []
    d_in = unit_dims(units[0])[0]
    d_out = unit_dims(units[-1])[1]
    x = "input"
    for i, u in enumerate(units):
        x = _unit(nodes, inits, x, u, f"u{i}")
    nodes.append(helper.make_node("Identity", [x], ["output"]))
    g = helper.make_graph(
        nodes, "resmlp",
        [helper.make_tensor_value_info("input", TensorProto.FLOAT, [1, d_in])],
        [helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, d_out])],
        inits)
    m = helper.make_model(g, opset_imports=[helper.make_opsetid("", 13)])
    m.ir_version = 8
    onnx.checker.check_model(m)
    onnx.save(m, path)
    return path


def forward_units(units, x):
    """Float reference forward; returns list of activations after each unit."""
    acts = []
    h = x
    for u in units:
        z = h @ u["W"] + u["b"]
        if u["kind"] == "proj":
            h = np.maximum(z, 0)
        elif u["kind"] == "block":
            h = h + np.maximum(z, 0)
        else:
            h = z
        acts.append(h)
    return acts


def random_units(n_feat, width, n_blocks, seed=0):
    rng = np.random.default_rng(seed)
    units = [{"kind": "proj", "W": rng.normal(0, np.sqrt(2 / n_feat), (n_feat, width)),
              "b": np.zeros(width)}]
    for _ in range(n_blocks):
        units.append({"kind": "block", "W": rng.normal(0, np.sqrt(2 / width) * 0.3, (width, width)),
                      "b": np.zeros(width)})
    units.append({"kind": "head", "W": rng.normal(0, np.sqrt(1 / width), (width, 1)), "b": np.zeros(1)})
    return units


def build_join_block(unit, in_dims, path):
    """A residual block whose input arrives as several committed pieces
    (e.g. the two halves of a split projection). Pieces are concatenated
    inside the circuit, so each piece keeps its own Poseidon commitment."""
    nodes, inits = [], []
    names = [f"in{i}" for i in range(len(in_dims))]
    nodes.append(helper.make_node("Concat", names, ["x"], axis=1))
    out = _unit(nodes, inits, "x", unit, "u0")
    nodes.append(helper.make_node("Identity", [out], ["output"]))
    d_out = unit_dims(unit)[1]
    g = helper.make_graph(
        nodes, "join",
        [helper.make_tensor_value_info(n, TensorProto.FLOAT, [1, d]) for n, d in zip(names, in_dims)],
        [helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, d_out])], inits)
    m = helper.make_model(g, opset_imports=[helper.make_opsetid("", 13)]); m.ir_version = 8
    onnx.checker.check_model(m); onnx.save(m, path)
    return path


def dispute_steps(units, n_proj_parts=2):
    """Restructure the model into a bisectable DAG of steps, in topological order.
    Each step: dict(name, kind, unit, inputs=[step indices or -1 for the tx input]).
    The projection (the largest layer) is split column-wise into n_proj_parts
    independent steps; the first block joins them."""
    proj = units[0]; W = proj["W"].shape[1]
    cuts = np.array_split(np.arange(W), n_proj_parts)
    steps = []
    for p, cols in enumerate(cuts):
        steps.append(dict(name=f"proj{p}", kind="proj", cols=cols,
                          unit={"kind": "proj", "W": proj["W"][:, cols], "b": proj["b"][cols]}, inputs=[-1]))
    parts = list(range(n_proj_parts))
    for k, u in enumerate(units[1:], start=1):
        prev = parts if k == 1 else [len(steps) - 1]
        steps.append(dict(name=f"u{k}", kind=u["kind"], unit=u, inputs=prev))
    return steps
