# H4 confirmatory pre-registration

Committed before any confirmatory run. Parameters and bounds below must not change after the run starts.

## 0. Status: run HALTED, soundness defect

Before running, the AIR was inspected and found not to bind the commitment:

- The commitment `C` is a constant in the AIR (`lattice_c[j]`).
- The only relation is `acc_final = C + k·Q` over the Winterfell field F_p, with p = 0x700001 = 7,340,033.
- Q = 8,380,417 is not p. Since gcd(Q, p) = 1, for any amount and any randomness r the prover can choose `k = (acc_final − C)·Q⁻¹ mod p`. The relation holds for any amount.
- The quotient `k` has no range check. The trace also computes the lattice relation mod p, not mod Q, so the arithmetic does not match the commitment definition.

Consequence: the circuit does not enforce the lattice commitment. The benchmark in PR #9 / #12 measures the cost of a circuit that does not verify what it claims to. Those overhead numbers cannot support a security or H4 verdict.

Required before any confirmatory run: non-native arithmetic mod Q (or a field where Q-arithmetic is exact), range checks on `r` and `k`, and a negative test that a witness with a wrong amount is rejected. Until then, sections 1–4 below are not executed.

The parameters (section 3) and bounds (section 1) are unchanged. They are not evaluated.

## 1. Overhead bounds (unchanged from PR #12)

Set on 2026-10-06 (commit `67bb47e`, as the post-hoc exploratory bounds). Reused here for the confirmatory run. They were committed before this run, so they bind it. They were **not** derived from the new run's results.

| Metric | Bound (PQ / matched classical) |
|---|---|
| Proof size | ≤ 20× |
| Proving time | ≤ 200× |
| Verification time | ≤ 10× |

Baseline: matched classical STARK, `classical_matched` (2,233 B, same Winterfell `f23` environment).

## 2. Security target

Target: **128-bit post-quantum security**, estimated as quantum core-SVP for the SIS instance.

Method: root-Hermite heuristic (BKZ block size `b` from the required root-Hermite factor `δ = (β / q^(n/m))^(1/m)`, with `b ≤ m`), using the standard cost model:
- classical core-SVP ≈ 0.292·b bits
- quantum core-SVP (sieve) ≈ 0.265·b bits

This is a **heuristic estimate, not a full lattice-estimator run.** The block-size search is clamped at its lower bound, so small-parameter estimates are upper bounds on security. Before any external claim, run the lattice estimator (Albrecht et al.) on the final parameters.

## 3. Parameters

| Parameter | Current (PR #12) | Confirmatory |
|---|---|---|
| Rows M (SIS n) | 128 | **576** |
| Columns N (SIS m) | 256 | **1152** |
| Modulus q | 8,380,417 | 8,380,417 (unchanged) |
| Norm bound β | 2^17 − 1 | 2^17 − 1 (unchanged) |

Estimate for the confirmatory set: block `b = 519`, classical core-SVP ≈ 152 bits, quantum core-SVP ≈ 138 bits. Both clear the 128-bit target. Block size ≤ dimension (519 ≤ 1152), so the model applies.

Current set (PR #12): block `b = 40` (clamped), classical ≈ 12 bits. **Not secure.** PR #12's results are therefore an insecure-parameter benchmark, not a security-level one.

Why this set: smallest of the candidates scanned (512×1024, 512×2048, 576×1152, 640×1280, 640×1536, 768×1536) that clears 128 bits quantum. 512×1024 gives ≈117 bits quantum, which fails.

## 4. Pass/fail rule

Pass for each metric if the observed PQ/classical ratio is within its bound in section 1. H4 is confirmed only if all three pass on the confirmatory run **and** the security estimate in section 2 holds. Otherwise report the failing metric or the security shortfall, without changing any bound or parameter.

## 5. Scope

Workload: 2×2 matrix multiplication (as in PR #12). Coverage of the H1–H3 model classes is **not** tested by this run and stays a limitation.
