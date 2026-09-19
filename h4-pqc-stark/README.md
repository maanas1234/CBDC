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
│   ├── matched_matrix_stark/
├── experiments/
│   └── benchmark_results.csv
├── docs/
└── README.md

## 1. Classical STARK Baseline

The original baseline proves a 2×2 matrix multiplication computation using Winterfell v0.13.1.

```text
A = [1 2]       B = [5 6]       C = [19 22]
    [3 4]           [7 8]           [43 50]
The AIR enforces all four matrix-product equations:
C00 = A00*B00 + A01*B10
C01 = A00*B01 + A01*B11
C10 = A10*B00 + A11*B10
C11 = A10*B01 + A11*B11
Original baseline benchmark
10 successful runs produced:
Proof size: 7,677 bytes
Mean proving time: 6.363 ms
Mean verification time: 2.244 ms
Verification runs: 10/10

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
where:
A and B are lattice matrices
C is the public commitment
s and r form the private witness
q is the lattice modulus
The current prototype uses small research/debug parameters. It is intended for architectural and performance evaluation rather than a production cryptographic security claim.
The matrix computation and lattice relation are enforced by the same STARK proof.

### PART 5 — Validation + results

```markdown
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

## 5. Matched PQ Benchmark

The valid PQ implementation was benchmarked for 10 runs.

| Metric | Classical matched | PQ matched |
|---|---:|---:|
| Proof size | 2,233 B | 2,491 B |
| Mean proving time | 0.448 ms | 0.639 ms |
| Mean verification time | 0.187 ms | 0.193 ms |
| Successful runs | 10/10 | 10/10 |

Observed ratios:

| Metric | PQ / Classical | Increase |
|---|---:|---:|
| Proof size | 1.116× | 11.6% |
| Proving time | 1.426× | 42.6% |
| Verification time | 1.032× | 3.2% |

These measurements apply only to the current prototype and parameterization.
## 6. Current Findings

For the evaluated 2×2 matrix-multiplication workload, incorporating the SIS-style lattice relation resulted in approximately:

- 11.6% proof-size increase
- 42.6% proving-time increase
- 3.2% verification-time increase

The verifier latency remained close to the matched classical baseline.

These results provide preliminary evidence supporting the bounded-overhead component of H4 for the evaluated prototype.

They do not establish the complete H4 hypothesis.

## 7. Limitations

1. The lattice parameters are small research/debug parameters and are not a production cryptographic parameter set.
2. The evaluated computation is a small 2×2 matrix multiplication rather than a complete ML model.
3. Coverage of the model classes used in H1-H3 has not yet been established.
4. The current prototype is not an externally reviewed post-quantum cryptographic construction.
5. The settlement-layer migration claim has not been validated through a production CBDC implementation.

## 8. Next Research Step

The next experimental phase will investigate realistic lattice parameters corresponding to a defensible post-quantum security target.

The same matched workload will then be benchmarked again to measure the effect on:

- proof size
- proving time
- verifier latency

The results will be compared against the matched classical baseline.## 9. Reproducibility

### Original classical baseline

```bash
cd classical/matrix_stark
cargo run --release

Matched classical baseline
cd classical/matched_matrix_stark
cargo run --release

Matched lattice-backed prototype
cd pq/matched_matrix_stark
cargo run --release

Benchmark data:
experiments/benchmark_results.csv
