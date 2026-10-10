# H4 v2 — design, security estimate, and pre-run amendment

Committed before the v2 benchmark is run. Code: `benchmark_v2/`.

## Why v1 results are withdrawn

The v1 circuit (`pq/matched_matrix_stark`, PR #9/#12) does not prove what it claims:

1. **SIS matrix B is prover-supplied.** B lives in unconstrained trace columns. A prover can set B = 0.
2. **Selectors are unconstrained.** The amount/final selector columns have no constraints, so the amount term can be scaled freely.
3. **Wrong modulus, free quotient.** The relation is checked mod p = 0x700001, not mod Q = 8,380,417, and the quotient k has no range check. Any amount satisfies it.
4. **Randomness is not range-checked**, so the "short vector" condition SIS needs is never enforced.
5. **Proof options give ~11–17 bits of security on both sides.** `FieldExtension::None` over a 23-bit field, 16 queries, blowup 4. Winterfell's own formula: PQ ≈ 11 bits, classical ≈ 17 bits.

PR #18 removed the matrix-multiplication constraints and did not address 1–5.

## v2 construction

Statement: "I know a 2×2 matrix product C = A·B (public A, B, C), and a short opening (bits, r) of the public commitment c."

- Commitment over the STARK field itself: **c = G·bits + B·r mod p**, p = 7·2²⁰ + 1 = 7,340,033. No quotient exists.
- **G, B are public** (deterministic PRG, uniform mod p). B and the row-0 selector are **periodic columns**, so the verifier computes them.
- **bits ∈ {0,1}⁶⁴**, boolean and constant across rows.
- **r ∈ {−1, 0, 1}^448 exactly**, via r + 1 = u₀ + 2u₁, u₀ and u₁ boolean, u₀·u₁ = 0.
- Accumulators: acc₀ = 0, acc_{i+1} = acc_i + sel₀·(G·bits) + B_col·r, asserted equal to c at row 449.
- Same matmul block (plus a clock column) in both circuits.

Tests (`cargo test --release`, 10/10): the AIR is evaluated directly on every row and assertion. Honest traces are accepted. Rejected: a different amount against the same commitment, r = 5 and r = 2 (even when they genuinely open c), a non-boolean bit, and a wrong matrix product. End-to-end prove/verify tests also pass.

## Binding security estimate

Two openings of one commitment give z = (Δbits, Δr) ≠ 0 with [G|B]·z = 0 mod p, ‖z‖∞ ≤ 2, and dimension m = 64 + 448 = 512. So ‖z‖₂ ≤ 2√512 ≈ 45.3. Breaking binding means solving SIS with n = 80, m = 512, q = 7,340,033, ℓ₂ ≤ 45.3. That is conservative: an L2 bound is weaker than the actual ‖z‖∞ ≤ 2.

Method: root-Hermite heuristic. The attacker picks a sub-dimension d ≤ m; BKZ-b reaches length δ(b)^d · q^{n/d}. Find the smallest b ≤ d reaching ℓ. Cost model: classical 0.292·b, quantum 0.265·b.

| n (SIS rows) | block b | quantum bits | classical bits |
|---|---|---|---|
| 64 | 464 | ≈123 | ≈135 |
| 68 | 512 (= m) | ≈136 | ≈150 |
| 72 | > m (no b ≤ 512 suffices) | > 136 | > 150 |
| **80 (chosen)** | > m | **> 136** | **> 150** |

This is a heuristic estimate, not a lattice-estimator run. Run the lattice estimator (Albrecht et al.) before any external claim.

Not claimed: hiding (r is ternary and short) and zero-knowledge. This Winterfell fork does not add ZK masking, so the proofs are succinct arguments of knowledge, not zero-knowledge.

## STARK soundness

Both circuits use the same options: sextic extension (138-bit field), blowup 8, 42 queries (126 bits), 16-bit grinding, Blake3-256 (128-bit collision resistance). Winterfell conjectured security = min(138 − log₂(LDE size), 126 + 16) − 1, capped at the hash bound. That gives ≈125 bits for the PQ trace (LDE 4096) and 128 bits for the classical trace. The benchmark records the per-proof value. Hash-based STARK soundness is already post-quantum apart from generic Grover speedups on the hash.

## Amendment to the PR #16 pre-registration

| Item | PR #16 | v2 (this amendment, before any v2 run) |
|---|---|---|
| Construction | v1 AIR | v2 AIR above (v1 is unsound) |
| SIS dimensions | M = 576, N = 1152, q = 8,380,417 | n = 80, m = 64 + 448, q = p = 7,340,033 |
| Norm bound | β = 2¹⁷ − 1 | ‖z‖∞ ≤ 2 (bits boolean, r ternary) |
| Security target | 128-bit quantum (heuristic) | unchanged; estimate > 136 bits |
| Proof options | not specified (v1: ~11–17 bits) | identical secure options for both circuits |
| **Overhead bounds** | **size ≤ 20×, prove ≤ 200×, verify ≤ 10×** | **unchanged** |

Pass/fail rule: each metric passes if its mean PQ/classical ratio over the measured runs is within its bound. H4 overhead is confirmed only if all three pass. Workload stays a 2×2 matrix product; coverage of the H1–H3 model classes is a separate limitation and is not tested here.

The bounds were committed on 2026-10-06. That predates v2 entirely, so the v2 result cannot have influenced them. The Oct 6 commit came after the v1 numbers, which is why PR #12 labeled them post-hoc for v1.
