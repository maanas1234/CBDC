# H4 Final Matched Benchmark Comparison

## Experimental status

The PQ implementation was corrected to enforce commitment binding.
A negative test that tampers with the public lattice commitment fails
verification in both debug and release builds.

Both matched implementations completed 10/10 successful benchmark runs.

## Parameters

PQ research-candidate profile:

- Profile: research-candidate-128x256
- q: 8,380,417
- M: 128
- N: 256
- beta: 131,071

## Steady-state benchmark

Run 1 is treated as warm-up. Statistics below use runs 2–10.

| Metric | Classical matched | PQ matched | PQ / Classical |
|---|---:|---:|---:|
| Proof size | 2,233 B | 33,214 B | 14.87x |
| Proving time (mean) | 0.3402 ms | 68.7434 ms | 202.05x |
| Verification time (mean) | 0.1584 ms | 1.1353 ms | 7.17x |

## Pre-registered feasibility bounds

| Criterion | Bound | Observed | Result |
|---|---:|---:|---|
| Proof-size overhead | <= 20x | 14.87x | PASS |
| Verification-latency overhead | <= 10x | 7.17x | PASS |

## Interpretation

The corrected research-candidate PQ-STARK prototype satisfies the
pre-registered proof-size and verification-latency overhead bounds
against the matched classical STARK baseline.

The PQ construction incurs substantially higher proving cost
(approximately 202x in the steady-state matched benchmark), which is
reported explicitly.

These results establish a feasibility/performance result for the
research-candidate prototype. They do not establish production-grade
post-quantum cryptographic security, standardized lattice security
parameters, or end-to-end ZKML performance for realistic model sizes.

## Raw benchmark sources

PQ:
pq/matched_matrix_stark/benchmark_results/pq_research_candidate_128x256.txt

Classical:
classical/matched_matrix_stark/benchmark_results/classical_matched.txt
