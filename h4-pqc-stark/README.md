# H4 — Post-Quantum ZK-STARK Migration

## Hypothesis

> **“A lattice-based ZK-STARK construction can secure ZKML proof verification for the model classes used in H1-H3 while keeping proof size and verifier latency within a bounded overhead factor relative to classical (non-quantum-resistant) ZK-STARKs, making PQC migration practical without re-architecting the settlement layer.”**

## Objective

H4 investigates whether a STARK proof system can incorporate a lattice-based, post-quantum relation while maintaining practical proof size and verifier latency relative to a classical STARK performing the same computation.

The current prototype evaluates this question using a small matrix-multiplication workload combined with an SIS-style lattice relation.

This repository records the implementation, validation tests, and benchmark results used for the H4 feasibility study.

## Repository Structure

```text
h4-pqc-stark/
├── classical/
│   ├── matrix_stark/
│   └── matched_matrix_stark/
├── pq/
│   └── matched_matrix_stark/
├── experiments/
│   └── benchmark_results.csv
├── docs/
└── README.md
```

## 1. Classical STARK Baseline

The original baseline proves a 2×2 matrix multiplication computation using Winterfell v0.13.1.

```text
A = [1 2]       B = [5 6]       C = [19 22]
    [3 4]           [7 8]           [43 50]
```

The AIR enforces all four matrix-product equations:

```text
C00 = A00*B00 + A01*B10
C01 = A00*B01 + A01*B11
C10 = A10*B00 + A11*B10
C11 = A10*B01 + A11*B11
```

### Original baseline benchmark

10 successful runs produced:

- Proof size: 7,677 bytes
- Mean proving time: 6.363 ms
- Mean verification time: 2.244 ms
- Verification runs: 10/10

## 2. Matched Classical Baseline

A second classical implementation uses the same older Winterfell `f23` environment used by the lattice-backed prototype.

The matched comparison uses the same matrix workload and proof configuration.

10 successful runs produced:

- Proof size: 2,233 bytes
- Mean proving time: 0.448 ms
- Mean verification time: 0.187 ms
- Verification runs: 10/10

## 3. Lattice-Backed STARK Prototype

The PQ prototype combines the same 2×2 matrix multiplication computation with an SIS-style lattice relation inside a single STARK AIR.

The lattice relation is:

```text
C = A*s + B*r (mod q)
```

where:

- `A` and `B` are lattice matrices
- `C` is the public commitment
- `s` and `r` form the private witness
- `q` is the lattice modulus

The matrix computation and lattice relation are enforced by the same STARK proof.

The production-candidate parameter profile evaluated in this phase is:

```text
Profile: research-candidate-128x256
q       = 8,380,417
M       = 128
N       = 256
β       = 131,071
```

The profile is treated as a research candidate rather than a production cryptographic parameter set. A specific post-quantum security category is not claimed without a concrete SIS attack-cost analysis.

## 4. Validation

The matched PQ prototype was tested using the valid 2×2 matrix multiplication shown above.

### Test 1 — Valid matrix

Result: PASS

### Test 2 — Tampered matrix output

The first output element was changed from 19 to 20.

Result: PASS — correctly rejected

### Test 3 — Tampered matrix input

The first input element was changed from 1 to 2.

Result: PASS — correctly rejected

These tests demonstrate that the current AIR rejects invalid matrix computations.

## 5. Pre-registered Bound

Before evaluating the production-parameter benchmark results, the following overhead bounds were pre-registered relative to the matched classical STARK baseline:

| Metric | Pre-registered bound |
|---|---:|
| Proof size | ≤ 20× |
| Proving time | ≤ 200× |
| Verification time | ≤ 10× |

These bounds define a practical feasibility threshold rather than a cryptographic security target.

The verification-time bound is the most operationally constrained because proof verification is on the critical path for settlement validation. A 10× bound over the matched classical verification time of 0.187 ms corresponds to approximately 1.87 ms, which remains in the low-millisecond range.

A looser 200× bound is used for proving time because proving is expected to occur off the critical settlement-verification path.

The 20× proof-size bound allows substantial post-quantum overhead while keeping the resulting proof below approximately 45 KB relative to the 2,233-byte matched classical proof.

These bounds were fixed before evaluating the production-parameter results below and are not adjusted based on the observed measurements.

## 6. Matched PQ Benchmark

The production-parameter PQ implementation was benchmarked against the matched classical baseline.

| Metric | Matched classical | PQ production candidate | PQ / Classical | Pre-registered bound | Result |
|---|---:|---:|---:|---:|---|
| Proof size | 2,233 B | 31,792 B | 14.2× | ≤ 20× | PASS |
| Mean proving time | 0.448 ms | ~70 ms | ~156× | ≤ 200× | PASS |
| Mean verification time | 0.187 ms | 1.10 ms | 5.9× | ≤ 10× | PASS |

The observed overheads therefore remain within the pre-registered bounds for the evaluated 2×2 matrix-multiplication workload.

These measurements apply only to the current prototype, parameterization, and workload. They do not establish the security or production readiness of the parameter set.

## 7. Current Findings

For the evaluated 2×2 matrix-multiplication workload, incorporating the lattice relation with the production-candidate parameters resulted in approximately:

- 14.2× proof-size overhead
- 156× proving-time overhead
- 5.9× verification-time overhead

All three observed overheads are within the pre-registered bounds.

These results provide preliminary evidence supporting the bounded-overhead component of H4 for the evaluated prototype and workload.

The verification overhead is approximately 1.10 ms, remaining in the low-millisecond range despite the addition of the lattice-backed relation.

The results do not establish the complete H4 hypothesis because the model classes used in H1-H3 have not yet been evaluated and a concrete post-quantum security analysis of the parameter set has not yet been completed.

## 8. Security Assessment

The current parameter profile is:

```text
research-candidate-128x256
q = 8,380,417
M = 128
N = 256
β = 131,071
```

This profile is designated a **research candidate**.

No specific NIST post-quantum security category is claimed for these parameters.

The dimensions, modulus, and bound alone do not establish a 128-bit or other specific post-quantum security level. A concrete SIS security analysis, including an appropriate attack-cost estimate for the instantiated parameters, is required before assigning a defensible security category or considering the parameters production-ready.

Therefore, the current benchmark should be interpreted as a performance and feasibility evaluation, not as evidence of production-grade post-quantum cryptographic security.

## 9. Limitations

1. The `research-candidate-128x256` parameter profile is a research candidate and is not a production cryptographic parameter set.
2. The current H4 test covers only a 2×2 matrix multiplication and does not cover the model classes used in H1-H3.
3. Consequently, the bounded-overhead result applies only to the evaluated 2×2 workload and cannot yet be generalized to the H1-H3 model classes.
4. The current prototype is not an externally reviewed post-quantum cryptographic construction.
5. The settlement-layer migration claim has not been validated through a production CBDC implementation.
6. The current benchmark does not establish end-to-end ZKML performance for realistic model sizes or inference workloads.

## 10. Next Research Step

The next experimental phase should investigate realistic lattice parameters corresponding to a defensible post-quantum security target.

The same matched workload should then be benchmarked again to measure the effect on:

- proof size
- proving time
- verifier latency

The results should be compared against the matched classical baseline.

A subsequent phase should extend the workload beyond the current 2×2 matrix multiplication to representative model classes used in H1-H3. This is necessary before the bounded-overhead result can be generalized to the full H4 hypothesis.

## 11. Reproducibility

### Original classical baseline

```bash
cd classical/matrix_stark
cargo run --release
```

### Matched classical baseline

```bash
cd classical/matched_matrix_stark
cargo run --release
```

### Matched lattice-backed prototype

```bash
cd pq/matched_matrix_stark
cargo run --release
```

### Benchmark data

```text
experiments/benchmark_results.csv
```

## Conclusion

For the currently evaluated 2×2 matrix-multiplication workload, the production-candidate lattice-backed STARK remains within all three pre-registered overhead bounds:

- **Proof size:** 14.2× ≤ 20× — PASS
- **Proving time:** ~156× ≤ 200× — PASS
- **Verification time:** 5.9× ≤ 10× — PASS

The results therefore support the bounded-overhead component of H4 for this specific experimental workload.

However, H4 is **not yet fully established**. The current experiment does not cover the model classes used in H1-H3, and the `research-candidate-128x256` parameters have not been assigned a defensible post-quantum security level through a concrete SIS security analysis.

Accordingly, these results should be interpreted as a **research feasibility result**, not a production-readiness or cryptographic-security claim.