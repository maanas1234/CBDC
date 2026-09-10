# H4 — Post-Quantum ZK-STARK Migration

## Hypothesis

> **“A lattice-based ZK-STARK construction can secure ZKML proof verification for the model classes used in H1-H3 while keeping proof size and verifier latency within a bounded overhead factor relative to classical (non-quantum-resistant) ZK-STARKs, making PQC migration practical without re-architecting the settlement layer.”**

This work evaluates whether a lattice-based, post-quantum ZK-STARK approach can provide practical proof verification for small ML-relevant computations without excessive proof-size or verification-time overhead.

## Project Status

* [x] Classical ZK-STARK baseline
* [x] Baseline proof-size measurement
* [x] Baseline prover/verifier latency measurement
* [ ] Lattice-based PQ-STARK prototype
* [ ] PQ/classical overhead comparison
* [ ] Migration conclusion

## Classical Baseline

The baseline proves a **2×2 matrix multiplication** computation using **Winterfell v0.13.1**.

The AIR enforces all four matrix-product equations:

$$
C_{00}=A_{00}B_{00}+A_{01}B_{10}
$$

$$
C_{01}=A_{00}B_{01}+A_{01}B_{11}
$$

$$
C_{10}=A_{10}B_{00}+A_{11}B_{10}
$$

$$
C_{11}=A_{10}B_{01}+A_{11}B_{11}
$$

The implementation uses a 12-column, 8-row execution trace and BLAKE3-based Merkle commitments.

### Baseline Measurements

10 successful proof-generation and verification runs produced:

| Metric                   |                    Result |
| ------------------------ | ------------------------: |
| Proof size               | **7,677 bytes (7.50 KB)** |
| Mean proving time        |              **6.363 ms** |
| Proving-time SD          |              **0.619 ms** |
| Mean verification time   |              **2.244 ms** |
| Verification-time SD     |              **0.261 ms** |
| Successful verifications |                 **10/10** |

These measurements form the fixed classical reference point for the PQ comparison.

## PQ Implementation

The PQ phase will investigate a **lattice-backed STARK construction** based on an SIS-style lattice relation.

The planned architecture is:

```text
Matrix computation
       +
SIS-style lattice relation
       ↓
Custom AIR
       ↓
STARK proof system
       ↓
Post-quantum prototype
```

The implementation will use the existing SIS-based STARK work as a reference and investigate `stark-rings` as supporting lattice/ring infrastructure where appropriate.

The PQ construction will be evaluated using the **same core matrix computation** so that proof-size and verification-time comparisons remain meaningful.

> The PQ implementation will be described precisely according to what is actually implemented. A lattice-backed STARK relation will not be presented as a new lattice-based FRI construction unless the implementation establishes that property.

## Comparison

The final experiment will compare the classical and PQ prototypes on:

1. **Proof size**
2. **Verifier latency**
3. **Prover latency** as a secondary metric
4. **Successful proof verification**
5. **Relative overhead**

The primary comparison is:

$$
\text{Proof-size overhead}
=
\frac{\text{PQ proof size}}{\text{Classical proof size}}
$$

$$
\text{Verification overhead}
=
\frac{\text{PQ verification time}}{\text{Classical verification time}}
$$

The results will determine whether the observed overhead remains practically bounded for the tested computation.

## Conclusion

The classical baseline establishes a working reference implementation and reproducible performance measurements.

The final H4 conclusion will be based on the measured PQ overhead rather than an assumed threshold. The result will state whether the tested lattice-based construction provides a practical migration path while preserving the settlement-layer architecture, or whether the measured overhead makes the proposed migration impractical for the tested model class.

## Repository Structure

```text
h4-pqc-stark/
├── README.md
├── classical/
│   └── matrix_stark/
├── pq/
│   └── sis_matrix_stark/
├── docs/
│   ├── literature-review.md
│   └── methodology.md
└── results/
    ├── raw_results.csv
    └── analysis.md
```

## References

* [Winterfell](https://github.com/facebook/winterfell) — STARK proving framework used for the classical baseline.
* SIS-based STARK reference implementation — used as a research reference for the lattice-backed PQ phase.
* `stark-rings` — supporting reference for lattice/ring arithmetic in STARK-friendly fields.

