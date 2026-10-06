# H1 — Verifiable Off-Chain Inference (zk-OPML): Method, Results, Verdict

**Hypothesis.** Restructuring AML inference as a bisectable ONNX computation graph under an
optimistic dispute protocol reduces proof-generation latency and on-chain verification cost by
≥10× relative to a monolithic ZKML proof, with ≤1 pp accuracy loss.

**Verdict.** The accuracy target is met at every depth. The 10× latency target is met **only on the 60-block model**.
- **Proof latency.** Passes only at 60 blocks: 14.9× worst case on a single-core machine, 12.6× on a
  multi-core laptop (the multi-core run was done at 60 blocks only). Fails on shallower models
  (7.7× at 24 blocks, 3.9× at 8, 1.07× at 1; single-core).
- **Accuracy.** Passes: the circuit's fixed-point arithmetic costs at most 0.13 pp.
- **On-chain cost.** Passes for undisputed inferences (13.9× cheaper). Fails per dispute: settling one
  dispute costs up to 2.4× more gas than one monolithic verification (worst case; about 1.8× in the
  typical case). The 10× gas target therefore holds on average only if fewer than about 1.2% of
  inferences are disputed (worst-case dispute cost; about 1.6% with the typical cost).

**Caveats to report with any speedup number:**
- The 10× latency result holds only for the 60-block model, which is a benchmark, not a better AML model
  (its F1 matches the shallow one).
- Speedup depends on hardware (14.9× single-core, 12.6× multi-core, both at 60 blocks). Always state the hardware.
- The gas target is an average over disputes, not a per-dispute win. The 2.4× and 1.2% figures are
  worst-case; the typical figures are 1.8× and 1.6%.
- The gain is in proof generation, not time-to-finality (the challenge window still applies).

## 1. Setup

**Data.** Kaggle Elliptic, 46,564 labelled transactions. Temporal split: time steps 1–30 train,
31–34 validation, 35–49 test.

**Preprocessing.** Features are clipped to the 1st/99th percentile, then divided by max(IQR, std). The
previous version divided by IQR + 1e-8 and produced values up to 1e9; all values now lie within ±9.4.

**Model selection.** All choices (early stopping, threshold, seed) use the validation set only.

**Models.** A residual MLP of width 32: a 165→32 projection, then B residual blocks
(h ← h + ReLU(Wh + b)), then a 32→1 output layer. It is trained for B ∈ {1, 8, 24, 60}, with 3 seeds each.

**Proof system.** EZKL 23.0.5 (Halo2/KZG).
- Fixed-point scale 2⁹. Weights are baked into the verifying key (`fixed` parameters).
- Every circuit is calibrated on real transactions and tuned the same way: the faster of two column
  layouts (`num_inner_cols` ∈ {2, 4}).
- Prove times are the mean of 3 trials on a single-CPU machine. Absolute times will be lower on a
  multi-core laptop, and the speedup ratio also shrinks (14.9× to 12.6× at 60 blocks), so always state
  the hardware alongside any speedup number.

## 2. Method

**Bisectable graph.** The model becomes a chain of *steps*, and each step can be proven on its own.
The largest layer, the 165→32 projection, is split into two 16-neuron halves. The first block joins
the halves. The B=60 model ends up with 63 steps.

**Commitments.**
- For each step *i*, `leaf_i` is the Poseidon hash of that step's fixed-point output. This is the same
  hash EZKL computes inside its circuits, and I checked that the two match.
- A running hash `P_i = H(P_{i−1} ‖ leaf_i)` accumulates the leaves. A Merkle root over all
  (leaf_i, P_i) is posted with the output.
- The arithmetic is deterministic fixed-point. My NumPy emulation of EZKL's arithmetic reproduces its
  outputs exactly, so an honest asserter and an honest challenger always compute identical traces.

**Dispute.**
1. The asserter posts the output and the Merkle root. No proof is generated at this point.
2. A challenger who disagrees opens a dispute.
3. Both sides binary-search over the running hashes. Once any leaf differs, every later running hash
   differs too, so the search finds the **first** step *k* whose output differs. It takes ⌈log₂ n⌉
   rounds, which is 6 rounds for 63 steps.
4. Every step before *k* is agreed, so step *k*'s inputs are agreed as well.
5. Exactly **one** EZKL proof is generated: for step *k*, on those agreed inputs.
6. The verifier checks that the proof is valid and that its input hashes equal the agreed leaves. It
   then compares the proof's output hash with the asserter's `leaf_k`. A mismatch rejects the
   asserter's claim; a match rejects the challenge.

## 3. Results

### Proof latency across model depths

| Blocks | Steps | Full-model circuit size | Full-model proof | Slowest single step | Worst-case speedup | Average speedup | Bisection rounds |
|---|---|---|---|---|---|---|---|
| 1  | 4  | 2¹³ rows | 2.11 s  | 1.98 s | **1.07×** | 1.38× | 2 |
| 8  | 11 | 2¹⁵ rows | 7.67 s  | 1.98 s | **3.88×** | 4.24× | 4 |
| 24 | 27 | 2¹⁶ rows | 15.16 s | 1.98 s | **7.67×** | 7.94× | 5 |
| 60 | 63 | 2¹⁷ rows | 29.43 s | 1.98 s | **14.9×** | 15.1× | 6 |

*All speedups above were measured on a single-CPU machine. Only the 60-block row clears 10×. The
multi-core figure (12.6×) was measured at 60 blocks only; the other depths have no multi-core
measurement.*

*The "slowest single step" (1.98 s) is the largest per-step time measured on the B=60 model. The
worst-case speedups for 1, 8 and 24 blocks reuse that figure, on the grounds that every step has the
same shape at every depth; they are not separate per-depth measurements of the slowest step.*

**Per-step proof times on the B=60 model:**
- Projection halves: 1.50 s and 1.63 s.
- Join block: 1.95 s.
- Other blocks: 1.86–1.98 s.
- Output layer: 1.01 s.

Splitting the projection matters: the unsplit projection took about 3.1 s and was the worst-case
step. See `results/speedup_vs_depth.png` for the speedup curve.

**Why depth matters.** Every step has the same size at every depth (width 32), so the slowest
step always takes about 2 s. The full proof grows with the number of layers. The speedup therefore
rises with depth. Only four depths were measured (1, 8, 24, 60), and the 10× threshold falls between
the last two, so the exact crossover depth is not known and should not be quoted.

### Dispute prototype (B=60, 7 scenarios)

The scenarios covered:
- cheating on either projection half, a middle block, the last block, and the output decision itself;
- one false dispute raised against an honest asserter.

In all 7 cases, bisection located **exactly** the tampered step in ≤6 rounds. The single-step proof
verified, and the correct party won. Two scenarios flipped the AML decision:
- an illicit transaction reported as licit;
- a licit transaction reported as illicit.

Both were caught. The average proof time per dispute was 1.64 s.

### Accuracy (fixed-point circuit vs float model, full test set)

| Blocks | Accuracy change | F1 change | Decisions unchanged |
|---|---|---|---|
| 1  | 0.02 pp | 0.12 pp | 99.94% |
| 8  | 0.00 pp | 0.00 pp | 99.86% |
| 24 | −0.03 pp | 0.03 pp | 99.81% |
| 60 | 0.13 pp | 0.32 pp | 99.81% |

A negative change means the fixed-point version scored slightly higher. Bisection itself adds zero
error, because the per-step chain reproduces the full circuit's output exactly. At scale 2⁷ instead
of 2⁹, the 24-block model lost 1.4 pp, so the choice of scale matters.

For context, the selected B=60 model scores test F1 0.516, accuracy 93.3% and PR-AUC 0.514; across
seeds, F1 is 0.485 ± 0.024. The earlier F1 of 0.698 is not comparable, because that model was chosen
using the test set. A Random Forest on the same split scores F1 0.77.

### On-chain cost (gas measured on a local anvil chain)

| Item | Gas |
|---|---|
| Monolithic verification (every inference, B=60) | 696,984 |
| Optimistic commit (every inference) | 49,962 |
| One bisection round (reveal + respond) | ~102,000 |
| Single-step verification (block / join / output layer) | ~646,000 |
| Single-step verification (projection half) | 1,057,745 |
| **Full dispute: 6 rounds + one step verification** | **1.26 M typical, 1.67 M worst** |

- **Undisputed inference:** 13.9× cheaper than monolithic verification (passes).
- **Per dispute (fails):**
  - Worst case (1.67 M gas): 0.42× relative to a monolithic verification, i.e. 2.4× more expensive.
  - Typical case (1.26 M gas): about 0.55×, i.e. about 1.8× more expensive.
  - Verification gas barely depends on circuit size, so proving one small step saves almost no gas.
- **Break-even:** the 10× gas target holds on average only if the dispute rate is below about 1.2%
  (using the worst-case dispute cost of 1.67 M) or about 1.6% (using the typical cost of 1.26 M).

## 4. Pass/fail against the pre-registered criteria

| Criterion | Result |
|---|---|
| ≥10× proof-generation latency | **PASS only at 60 blocks** (14.9× worst case single-core, 12.6× multi-core; multi-core measured at 60 blocks only). **FAIL** at 24 blocks or fewer (7.7× at 24, 3.9× at 8, 1.07× at 1; single-core). |
| ≥10× on-chain verification cost | **FAIL per dispute** (0.42× worst case, about 0.55× typical). **PASS amortized** (13.9×) when disputes stay below about 1.2% (worst-case cost; about 1.6% with the typical cost). |
| ≤1 pp accuracy drop | **PASS** (worst 0.13 pp). |
| Bisection isolates the step in bounded rounds | **PASS** (⌈log₂ n⌉, ≤6 rounds for 63 steps; 7/7 scenarios). |

## 5. Limitations

1. **The 10× latency result depends on model depth.** The 60-block model is a benchmark chosen to
   test the mechanism. It is not a better AML model: its F1 matches the shallow one. The realistic
   use case is models whose full proof is expensive (e.g., GNNs over the transaction graph).
2. **Not every step was timed.** The blocks share one shape, so 3 of the 59 regular blocks were timed
   directly; the dispute runs proved 4 more. The slowest-step time measured on the B=60 model (1.98 s)
   is reused for the 1-, 8- and 24-block worst-case speedups rather than re-measured at each depth.
   Key generation happens once per step and is excluded from the comparison, just as it is for the
   monolithic proof.
3. **Preprocessing isn't proven.** Clipping and scaling are deterministic and public but run outside
   the circuit, so the committed input is the scaled feature vector.
4. **Optimistic finality is slow.** A result only becomes final after the challenge window closes.
   The latency gain applies to proof generation, not to time-to-finality.
5. **The dispute game is simplified.** It has no bonds or timeouts. The simulation uses SHA-256 for
   the running hashes, while the contract uses keccak256.
6. **The projection halves use the more expensive column layout.** They use `num_inner_cols`=4 because
   it proves faster, and that raises their verification gas. The cheaper layout wasn't gas-measured.
7. **The speedup depends on hardware.** It is 14.9× on a single-core machine and 12.6× on a multi-core
   laptop, because fixed per-proof overhead is a larger share of a small proof's time when cores are
   available. The multi-core figure exists for the 60-block model only. The margin over 10× should be
   reported with the hardware.
8. **Only four depths were measured.** The speedup curve is interpolated between 1, 8, 24 and 60
   blocks, so the depth at which the 10× threshold is crossed is unknown beyond "between 24 and 60".
