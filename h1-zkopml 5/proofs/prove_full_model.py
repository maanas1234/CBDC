"""
Full-model EZKL proving pipeline for H1.

This proves the ENTIRE forward pass of baseline_model.onnx for a single
input. This is the denominator: your later "prove only the disputed
part" mechanism has to beat this by >=10x on time/cost while losing
<=1pp accuracy, per the H1 target.

Run: python3 prove_full_model.py
Requires: baseline_model.onnx in ../model/ (from train_baseline.py)

Note: all ezkl calls here are synchronous in ezkl==23.0.5. Older/newer
versions expose some of these as async — check with
inspect.iscoroutinefunction before adding awaits if you upgrade.
"""

import asyncio
import json
import os
import time

import ezkl
import numpy as np

MODEL_PATH = "../model/baseline_model.onnx"
COMPILED_PATH = "network.compiled"
SETTINGS_PATH = "settings.json"
SRS_PATH = "kzg.srs"
PK_PATH = "test.pk"
VK_PATH = "test.vk"
WITNESS_PATH = "witness.json"
PROOF_PATH = "full_model_proof.json"
INPUT_PATH = "input.json"

N_FEATURES = 165


def make_sample_input():
    x = np.random.default_rng(1).normal(size=(1, N_FEATURES)).astype(np.float32)
    data = dict(input_data=[x.reshape(-1).tolist()])
    with open(INPUT_PATH, "w") as f:
        json.dump(data, f)
    return x


async def run_pipeline():
    timings = {}
    make_sample_input()

    t0 = time.time()
    run_args = ezkl.PyRunArgs()
    run_args.input_visibility = "public"
    run_args.output_visibility = "public"
    run_args.param_visibility = "private"
    res = ezkl.gen_settings(MODEL_PATH, SETTINGS_PATH, py_run_args=run_args)
    assert res, "gen_settings failed"
    timings["gen_settings"] = time.time() - t0

    t0 = time.time()
    ezkl.calibrate_settings(INPUT_PATH, MODEL_PATH, SETTINGS_PATH, "resources")
    timings["calibrate"] = time.time() - t0

    t0 = time.time()
    res = ezkl.compile_circuit(MODEL_PATH, COMPILED_PATH, SETTINGS_PATH)
    assert res, "compile_circuit failed"
    timings["compile_circuit"] = time.time() - t0

    # get_srs downloads a pre-generated SRS from EZKL's servers — not
    # reachable from this sandboxed network, so generate one locally
    # instead. Reads logrows from the settings we just calibrated.
    t0 = time.time()
    with open(SETTINGS_PATH) as f:
        logrows = json.load(f)["run_args"]["logrows"]
    ezkl.gen_srs(SRS_PATH, logrows)
    timings["get_srs"] = time.time() - t0

    t0 = time.time()
    res = ezkl.setup(COMPILED_PATH, VK_PATH, PK_PATH, srs_path=SRS_PATH)
    assert res, "setup failed"
    timings["setup"] = time.time() - t0

    t0 = time.time()
    ezkl.gen_witness(INPUT_PATH, COMPILED_PATH, WITNESS_PATH)
    timings["gen_witness"] = time.time() - t0

    t0 = time.time()
    res = ezkl.prove(WITNESS_PATH, COMPILED_PATH, PK_PATH, PROOF_PATH, srs_path=SRS_PATH)
    assert res, "prove failed"
    timings["prove"] = time.time() - t0

    t0 = time.time()
    res = ezkl.verify(PROOF_PATH, SETTINGS_PATH, VK_PATH, srs_path=SRS_PATH)
    assert res, "verify failed — proof is invalid!"
    timings["verify"] = time.time() - t0

    total_prove_side = timings["gen_witness"] + timings["prove"]

    print("\n--- Full-model EZKL proving pipeline (H1 baseline denominator) ---")
    for stage, t in timings.items():
        print(f"{stage:20s} {t:8.3f}s")
    print(f"{'TOTAL':20s} {sum(timings.values()):8.3f}s")
    print(f"\nProve-side cost (witness+prove) = {total_prove_side:.3f}s  <- this is what")
    print("the partial 'disputed part' proof must beat by >=10x.")

    proof_size_kb = os.path.getsize(PROOF_PATH) / 1024
    print(f"Proof size: {proof_size_kb:.2f} KB")

    with open("baseline_timings.json", "w") as f:
        json.dump({**timings, "prove_side_total_s": total_prove_side,
                   "proof_size_kb": proof_size_kb}, f, indent=2)
    print("\nSaved baseline_timings.json — this is your reference number going forward.")


if __name__ == "__main__":
    asyncio.run(run_pipeline())
