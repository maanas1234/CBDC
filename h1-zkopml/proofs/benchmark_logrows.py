"""
Rigorous benchmark of partial ("disputed part") proving cost across
different logrows settings.

Why this exists: EZKL/Halo2 proving cost is dominated by the PADDED
circuit size (2^logrows), not the actual constraint count. Simply
compiling the smaller late_model.onnx doesn't automatically drop
logrows into a cheaper bucket — calibrate_settings may be conservative.
This script explicitly tries forcing several logrows values (as long as
they're large enough to fit num_rows) and measures each with multiple
trials, since single-run timings in a shared/noisy environment can be
misleading (see: logrows=10 measuring SLOWER than logrows=12 in one
early test run here).

Run: python3 benchmark_logrows.py
Requires: late_model.onnx (from model/split_model.py)
           late_input.json (from prove_partial.py — run it once first)
Outputs: logrows_benchmark.json, printed comparison table
"""

import json
import math
import time

import ezkl

LATE_MODEL = "../model/late_model.onnx"
BASE_SETTINGS = "late_settings.json"
N_TRIALS = 3


def get_num_rows():
    with open(BASE_SETTINGS) as f:
        return json.load(f)["num_rows"]


def bench_one_logrows(logrows, n_trials=N_TRIALS):
    with open(BASE_SETTINGS) as f:
        settings = json.load(f)
    settings["run_args"]["logrows"] = logrows
    forced_settings_path = f"bench_settings_{logrows}.json"
    with open(forced_settings_path, "w") as f:
        json.dump(settings, f)

    compiled_path = f"bench_{logrows}.compiled"
    srs_path = f"bench_{logrows}.srs"
    pk_path = f"bench_{logrows}.pk"
    vk_path = f"bench_{logrows}.vk"
    witness_path = f"bench_{logrows}_witness.json"
    proof_path = f"bench_{logrows}_proof.json"

    ok = ezkl.compile_circuit(LATE_MODEL, compiled_path, forced_settings_path)
    if not ok:
        return None  # too small to fit the circuit

    ezkl.gen_srs(srs_path, logrows)
    ezkl.setup(compiled_path, vk_path, pk_path, srs_path=srs_path)

    prove_times = []
    for _ in range(n_trials):
        ezkl.gen_witness("late_input.json", compiled_path, witness_path)
        t0 = time.time()
        ezkl.prove(witness_path, compiled_path, pk_path, proof_path, srs_path=srs_path)
        prove_times.append(time.time() - t0)

    verified = ezkl.verify(proof_path, forced_settings_path, vk_path, srs_path=srs_path)

    return {
        "logrows": logrows,
        "prove_times": prove_times,
        "prove_mean": sum(prove_times) / len(prove_times),
        "prove_min": min(prove_times),
        "verified": verified,
    }


def main():
    num_rows = get_num_rows()
    min_logrows = math.ceil(math.log2(num_rows))
    print(f"late_model.onnx needs num_rows={num_rows}, "
          f"minimum feasible logrows={min_logrows}\n")

    results = []
    for logrows in range(min_logrows, min_logrows + 4):
        print(f"Benchmarking logrows={logrows} ({N_TRIALS} trials)...")
        r = bench_one_logrows(logrows)
        if r is None:
            print(f"  logrows={logrows} too small, circuit didn't fit")
            continue
        results.append(r)
        print(f"  mean prove time: {r['prove_mean']:.3f}s  "
              f"(min: {r['prove_min']:.3f}s)  verified: {r['verified']}")

    print("\n--- Summary ---")
    print(f"{'logrows':>8} {'mean_prove_s':>14} {'min_prove_s':>13} {'verified':>10}")
    for r in results:
        print(f"{r['logrows']:>8} {r['prove_mean']:>14.3f} {r['prove_min']:>13.3f} {str(r['verified']):>10}")

    with open("logrows_benchmark.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nSaved logrows_benchmark.json")

    print(
        "\nUse the SMALLEST logrows that still verifies for your reported partial-proving "
        "number — that's the honest best-case for the mechanism. Compare its mean (not "
        "single-run) time against the full-model baseline's mean for your speedup claim."
    )


if __name__ == "__main__":
    main()
