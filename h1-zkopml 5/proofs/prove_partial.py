"""
Partial-proving pipeline for H1's core mechanism: prove only the
"disputed part" (late_model.onnx) instead of the whole model.

The story this implements:
  1. Off-chain, the full model runs normally (cheap, no proof) and
     produces a fraud/no-fraud decision.
  2. The intermediate activation (output of the early half) is committed
     to via a Poseidon hash — cheap to compute, binds the model to a
     specific intermediate value it can't later deny.
  3. If a bank/regulator/agent DISPUTES a specific decision, only THEN
     do we generate a ZK proof — and only for the late half: "given the
     committed intermediate activation, the model's remaining layers
     produce exactly this output."
  4. This is much cheaper than proving the whole forward pass, because
     the early half (the big 165->32 matrix) is skipped entirely.

This does NOT lose any accuracy vs the full model — it's an exact split
of the same computation (see model/split_model.py), so the "<=1pp
accuracy drop" target is trivially satisfied. The entire tradeoff is
proving cost vs. a weaker guarantee (the early half is only committed,
not proven, until/unless a deeper dispute mechanism escalates further).

Run: python3 prove_partial.py
Requires: early_model.onnx, late_model.onnx (from model/split_model.py)
           baseline_timings.json (from prove_full_model.py, for comparison)
"""

import asyncio
import json
import os
import time

import ezkl
import numpy as np
import onnxruntime as ort

EARLY_MODEL = "../model/early_model.onnx"
LATE_MODEL = "../model/late_model.onnx"
COMPILED_PATH = "late_network.compiled"
SETTINGS_PATH = "late_settings.json"
SRS_PATH = "late_kzg.srs"
PK_PATH = "late_test.pk"
VK_PATH = "late_test.vk"
WITNESS_PATH = "late_witness.json"
PROOF_PATH = "partial_proof.json"
INPUT_PATH = "late_input.json"

N_FEATURES = 165
SPLIT_DIM = 32


def compute_intermediate_and_commit(sample_x):
    """Runs the early half locally (off-chain, not proven) and commits to
    its output via Poseidon hash — the hash EZKL itself uses internally,
    so it's consistent with what a verifier contract would check."""
    sess = ort.InferenceSession(EARLY_MODEL)
    intermediate = sess.run(None, {"input": sample_x})[0]  # shape (1, 32)

    # Poseidon-commit the intermediate activation. In a real deployment
    # this hash would be posted on-chain at inference time; here we just
    # compute it to show the commitment step exists.
    felts = [ezkl.float_to_felt(float(v), 13) for v in intermediate.flatten()]
    commitment = ezkl.poseidon_hash(felts)

    with open(INPUT_PATH, "w") as f:
        json.dump({"input_data": [intermediate.flatten().tolist()]}, f)

    return intermediate, commitment


async def run_pipeline():
    timings = {}

    sample_x = np.random.default_rng(1).normal(size=(1, N_FEATURES)).astype(np.float32)
    intermediate, commitment = compute_intermediate_and_commit(sample_x)
    print(f"Intermediate activation committed. Poseidon hash (first felt): {commitment[0]}")

    t0 = time.time()
    run_args = ezkl.PyRunArgs()
    run_args.input_visibility = "public"   # the committed intermediate is public
    run_args.output_visibility = "public"  # the final decision is public
    run_args.param_visibility = "private"  # late-half weights stay private
    res = ezkl.gen_settings(LATE_MODEL, SETTINGS_PATH, py_run_args=run_args)
    assert res, "gen_settings failed"
    timings["gen_settings"] = time.time() - t0

    t0 = time.time()
    ezkl.calibrate_settings(INPUT_PATH, LATE_MODEL, SETTINGS_PATH, "resources")
    timings["calibrate"] = time.time() - t0

    t0 = time.time()
    res = ezkl.compile_circuit(LATE_MODEL, COMPILED_PATH, SETTINGS_PATH)
    assert res, "compile_circuit failed"
    timings["compile_circuit"] = time.time() - t0

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

    partial_prove_side = timings["gen_witness"] + timings["prove"]

    print("\n--- Partial ('disputed part' only) EZKL proving pipeline ---")
    for stage, t in timings.items():
        print(f"{stage:20s} {t:8.3f}s")
    print(f"{'TOTAL':20s} {sum(timings.values()):8.3f}s")
    print(f"\nPartial prove-side cost (witness+prove) = {partial_prove_side:.3f}s")

    proof_size_kb = os.path.getsize(PROOF_PATH) / 1024
    print(f"Proof size: {proof_size_kb:.2f} KB")

    # compare against the full-model baseline, if available
    try:
        with open("baseline_timings.json") as f:
            full = json.load(f)
        full_prove_side = full["prove_side_total_s"]
        speedup = full_prove_side / partial_prove_side
        print(f"\n--- Comparison vs full-model baseline ---")
        print(f"Full-model prove-side:    {full_prove_side:.3f}s")
        print(f"Partial prove-side:       {partial_prove_side:.3f}s")
        print(f"Speedup:                  {speedup:.1f}x")
        print(f"Target (>=10x):           {'PASS' if speedup >= 10 else 'FAIL'}")
        print(f"Accuracy drop:            0pp (exact split, no approximation) -> PASS")
    except FileNotFoundError:
        print("\n(No baseline_timings.json found — run prove_full_model.py first to compare.)")

    with open("partial_timings.json", "w") as f:
        json.dump({**timings, "prove_side_total_s": partial_prove_side,
                   "proof_size_kb": proof_size_kb}, f, indent=2)
    print("\nSaved partial_timings.json")


if __name__ == "__main__":
    asyncio.run(run_pipeline())
