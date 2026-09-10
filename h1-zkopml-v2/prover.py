"""EZKL proving harness. Each call runs the full EZKL pipeline for one ONNX
graph and returns timings/sizes. Settings are identical for the monolithic
and per-unit circuits except where noted, so comparisons are like-for-like."""
import json, os, time, resource, sys
import ezkl

SCALE = int(os.environ.get("ZK_SCALE", 9))


def run(onnx_path, input_vec, workdir, input_vis="hashed", output_vis="public",
        param_vis="fixed", trials=3, calib_data=None, do_verify=True):
    os.makedirs(workdir, exist_ok=True)
    p = lambda n: os.path.join(workdir, n)
    with open(p("input.json"), "w") as f:
        vecs = input_vec if isinstance(input_vec, list) else [input_vec]
        json.dump({"input_data": [list(map(float, v)) for v in vecs]}, f)
    calib = calib_data or p("input.json")

    out = {}
    ra = ezkl.PyRunArgs()
    ra.input_visibility = input_vis
    ra.output_visibility = output_vis
    ra.param_visibility = param_vis
    ra.input_scale = SCALE
    ra.param_scale = SCALE
    ra.num_inner_cols = int(os.environ.get("ZK_INNER_COLS", 2))
    ra.decomp_base = int(os.environ.get("ZK_DECOMP_BASE", 256))
    ra.decomp_legs = int(os.environ.get("ZK_DECOMP_LEGS", 4))
    t = time.time(); assert ezkl.gen_settings(onnx_path, p("settings.json"), py_run_args=ra)
    ezkl.calibrate_settings(calib, onnx_path, p("settings.json"), "resources",
                            scales=[SCALE], scale_rebase_multiplier=[1])
    out["calibrate_s"] = time.time() - t
    t = time.time(); assert ezkl.compile_circuit(onnx_path, p("net.compiled"), p("settings.json"))
    out["compile_s"] = time.time() - t
    s = json.load(open(p("settings.json")))
    out["logrows"] = s["run_args"]["logrows"]
    out["num_rows"] = s.get("num_rows")
    out["total_assignments"] = s.get("total_assignments")
    out["input_scale"] = s["run_args"]["input_scale"]
    srs = os.path.join(os.path.dirname(workdir), f"srs_{out['logrows']}.srs")
    if not os.path.exists(srs):
        ezkl.gen_srs(srs, out["logrows"])
    t = time.time(); assert ezkl.setup(p("net.compiled"), p("vk.key"), p("pk.key"), srs_path=srs)
    out["setup_s"] = time.time() - t
    t = time.time(); ezkl.gen_witness(p("input.json"), p("net.compiled"), p("witness.json"))
    out["witness_s"] = time.time() - t
    times = []
    for _ in range(trials):
        t = time.time()
        assert ezkl.prove(p("witness.json"), p("net.compiled"), p("pk.key"), p("proof.json"), srs_path=srs)
        times.append(time.time() - t)
    out["prove_times"] = times
    out["prove_mean_s"] = sum(times) / len(times)
    if do_verify:
        t = time.time(); out["verified"] = bool(ezkl.verify(p("proof.json"), p("settings.json"), p("vk.key"), srs_path=srs))
        out["verify_s"] = time.time() - t
    out["proof_kb"] = os.path.getsize(p("proof.json")) / 1024
    out["instances"] = json.load(open(p("proof.json")))["instances"][0]
    out["num_inner_cols"] = ra.num_inner_cols
    out["pk_mb"] = os.path.getsize(p("pk.key")) / 1e6
    out["peak_rss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    return out


if __name__ == "__main__":
    # subprocess entry: python prover.py onnx input.npy workdir [input_vis output_vis trials]
    import numpy as np
    onnx_path, inp, wd = sys.argv[1:4]
    iv = sys.argv[4] if len(sys.argv) > 4 else "hashed"
    ov = sys.argv[5] if len(sys.argv) > 5 else "public"
    tr = int(sys.argv[6]) if len(sys.argv) > 6 else 3
    calib = sys.argv[7] if len(sys.argv) > 7 else None
    import asyncio
    async def main():
        arr = json.load(open(inp)) if inp.endswith(".json") else np.load(inp)
        if isinstance(arr, list): arr = [np.array(a) for a in arr]
        return run(onnx_path, arr, wd, iv, ov, trials=tr, calib_data=calib)
    res = asyncio.run(main())
    print("RESULT_JSON " + json.dumps(res))
