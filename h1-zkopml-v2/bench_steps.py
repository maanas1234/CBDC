"""Benchmark proving cost of individual dispute steps and of the monolithic model.
Usage: python3 bench_steps.py B [step names...|mono] ; appends to results/steps_B{B}.json"""
import json, os, pickle, subprocess, sys, time
import numpy as np
from data import load, temporal_split, apply_scaler
from onnx_builder import build, build_join_block, dispute_steps
from steps import quantize_steps, run_steps
from quant import S

B = int(sys.argv[1]); targets = sys.argv[2:]
TRIALS = int(os.environ.get("TRIALS", 3)); INNER = [int(c) for c in os.environ.get("INNER_SET", "2,4").split(",")]
WD = f"work/S{B}"; os.makedirs(WD, exist_ok=True)
m = pickle.load(open(f"models/W32_B{B}.pkl", "rb"))
X, y, ts = load(); _, _, (Xte, yte), _ = temporal_split(X, y, ts); Xte = apply_scaler(Xte, m["scaler"])
steps = quantize_steps(dispute_steps(m["units"]))
rng = np.random.default_rng(0); cidx = rng.choice(len(Xte), 16, replace=False)
sample = int(np.where(yte == 1)[0][0])
cx, couts = run_steps(steps, Xte[cidx]); sx, souts = run_steps(steps, Xte[sample:sample + 1])
deq = lambda a: (a / 2 ** S)


def ins_of(i, xq, outs):
    return [xq if j == -1 else outs[j] for j in steps[i]["inputs"]]


def prove(onnx, inputs, calib_inputs, name, iv, ov):
    json.dump({"input_data": [deq(c).reshape(-1).tolist() for c in calib_inputs]}, open(f"{WD}/{name}_calib.json", "w"))
    json.dump([deq(a).reshape(-1).tolist() for a in inputs], open(f"{WD}/{name}_in.json", "w"))
    best = None
    for ic in INNER:
        r = subprocess.run(["python3", "prover.py", onnx, f"{WD}/{name}_in.json", f"{WD}/{name}_ic{ic}", iv, ov,
                            str(TRIALS), f"{WD}/{name}_calib.json"], capture_output=True, text=True,
                           env=dict(os.environ, ZK_INNER_COLS=str(ic)))
        line = [l for l in r.stdout.splitlines() if l.startswith("RESULT_JSON")]
        if not line: print(f"  {name} ic={ic} FAILED {r.stderr[-300:]}", flush=True); continue
        res = json.loads(line[0][12:])
        print(f"  {name:6s} ic={ic} logrows={res['logrows']:2d} rows={res['num_rows']:6d} prove={res['prove_mean_s']:.2f}s "
              f"(trials {[round(t,2) for t in res['prove_times']]}) verify={res['verify_s']:.3f}s ok={res['verified']} rss={res['peak_rss_mb']:.0f}MB", flush=True)
        if best is None or res["prove_mean_s"] < best["prove_mean_s"]: best = res
    return best


path = f"results/steps_B{B}.json"
out = json.load(open(path)) if os.path.exists(path) else {}
for t in targets:
    if t == "mono":
        build(m["units"], f"{WD}/mono.onnx")
        out["mono"] = prove(f"{WD}/mono.onnx", [sx], [cx], "mono", "public", "public")
        continue
    i = [k for k, s in enumerate(steps) if s["name"] == t][0]; st = steps[i]
    iv = "public" if st["inputs"] == [-1] else "hashed"; ov = "public" if i == len(steps) - 1 else "hashed"
    onnx = f"{WD}/{t}.onnx"
    if len(st["inputs"]) > 1: build_join_block(st["unit"], [souts[j].shape[1] for j in st["inputs"]], onnx)
    else: build([st["unit"]], onnx)
    r = prove(onnx, ins_of(i, sx, souts), ins_of(i, cx, couts), t, iv, ov)
    r["step_index"] = i; r["kind"] = st["kind"]; out[t] = r
    json.dump(out, open(path, "w"), indent=2, default=float)
json.dump(out, open(path, "w"), indent=2, default=float)
