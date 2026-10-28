# Verifiable, Accountable and Post-Quantum AI for CBDC Systems — Complete Results

**Project:** CBDC – AI – Blockchain research (proposal: `docs/CBDC_AI_Blockchain_Research_Proposal.pdf`)
**Repository:** github.com/maanas1234/CBDC (all results on `main`, PRs #1–#43)
**Team:** Aman (H1), Indrakshi (H2), Anjali (H3), Simran (H4); mentor Maanas Tyagi
**Updated:** 28 Oct 2026 (adds the hardware integration, §6B)
**Status:** all experiments complete. This document collects every result, how it was obtained, what it does and does not show, and where the raw evidence lives. **October 2026 update:** the four mechanisms now run as one integrated system on a Byzantine-fault-tolerant ledger, validated on 1,000 real Elliptic transactions (§6A), and a second run split across two people and two machines in which the fourth validator's key was held by someone other than the host (§6A); sections 2–5 describe the original experiments and §6A lists what changed in each track. **Hardware update (late October 2026):** after a faculty review of the invention disclosure, hardware was made part of the method and measured (§6B): a model decomposition sized to the prover node's memory, a TPM-anchored operator identity, and simulated TEE signing and offline payment devices.

---

## Abstract

We test four falsifiable hypotheses about running AI inside a central-bank digital currency (CBDC) stack, and the cross-cutting findings (C1–C7) that emerged from them. All confirmatory runs were pre-registered: parameters, bounds and analysis code were committed before the runs.

| Hypothesis | Verdict |
|---|---|
| **H1, verifiable off-chain inference** | **Partly supported.** Bisection-based dispute resolution cuts proof latency 14.9× on a 60-block model with fixed-weight step verifiers, with ≤ 0.13 pp accuracy loss (with the later shared verifiers the step proof is no faster than the whole-model proof, §6A). It misses 10× on shallower models, and a single dispute costs 2.4× more gas than monolithic verification. |
| **H2, federated AML under label scarcity** | **Formally met, substantively not supported.** The pre-registered "≥ 20% fewer false positives" criterion holds at every scarcity level, but only because federated models flag less. At matched recall the criterion fails at every evaluable level, and with ample labels federation produces 67–80% *more* false positives. |
| **H3, cryptoeconomic liability (AgentBound Tokens)** | **Supported,** with a 41% fewer violations (agent-level p ≈ 10⁻⁶). The original design wears out as stakes are slashed to zero, and is defeated by identity resets. Stake maintenance plus operator-bound history restores durable deterrence (violations 50.7% → 2.0%). A registration bond at an analytically derived break-even value does the same. |
| **H4, post-quantum ZK-STARK migration** | **Supported.** A STARK that also proves a short opening of a statistically binding lattice (SIS) commitment stays within all pre-registered overhead bounds on the complete trained H1, H2 and H3 models (≤ 1.2× size, ≤ 1.5× prove, ≤ 2.0× verify). The "≥ 2⁶¹⁵ quantum" figure covers only the commitment's binding; the whole proof is estimated at about 63 bits quantum (§6A). |

The H4 result also includes **one proof covering H1 risk inference → H3 decision → the post-quantum-committed amount**, at 1.15× / 1.28× / 1.77× overhead.

**Integrated system (October 2026, §6A).** The mechanisms were later run together on a 4-validator Hyperledger Besu (QBFT) ledger: on 1,000 real Elliptic transactions with 111 deliberately falsified, all 889 honest transfers settled and none of the falsified ones did, at about 2 s per transfer. In a second run split across two people and two machines, a validator whose key only the reviewer held signed exactly the 166 honest transfers and refused all 34 falsified ones, under a contract that needs all four signatures. This is a lab-scale (technology readiness level 4) demonstration. Its detection quality is limited by the underlying model (recall 0.72 on the real-data run, and none after time step 43), and the proof's quantum security is about 62–63 bits, not the 2⁶¹⁵ of the commitment alone.

**Hardware integration (late October 2026, §6B).**
- **Memory-budgeted decomposition:** the prover node now splits the model into dispute steps from its own measured memory. Every step of every plan was proven within node budgets of 128 MB to 1 GB, where the whole model needs 1,243 MB.
- **TPM-anchored operator identity:** prototyped with software TPMs. The honest flow was accepted and 9 of 9 attacks were refused.
- **TEE signing and offline payment devices:** simulated. The TEE simulation signed the honest request and refused 5 of 5 falsified ones. The offline simulation settled 4 honest payments, refused the invalid ones offline, and caught a hidden overspend at synchronisation.

---

## 1. Contributions (candidate claims for the paper, strongest first)

1. **C1 — End-to-end post-quantum verifiable CBDC decision.** A single hash-based STARK proves four things together:
   - exact integer inference of a trained AML model, with the risk score kept private;
   - the risk flag;
   - an autonomous agent's policy decision that uses the flag;
   - that the amount decided on is the amount inside a lattice commitment whose binding is statistical (about 2⁻⁶³⁶ expected collisions; lattice-estimator attack cost ≥ 2⁶¹⁵ quantum).

   **Qualifier:** the 2⁶¹⁵ figure describes the *commitment only*. The STARK itself, whose soundness rests on hash functions, is estimated at about 63 bits quantum under the conservative argument (126-bit conjectured classical); the zero-knowledge Plonky3 version at about 62 bits (§6A). "Post-quantum" here means no known efficient quantum attack at these parameters, not 128-bit quantum security.

   Overhead versus the same proof without post-quantum binding: 1.15× size, 1.28× prove, 1.77× verify. Without the commitment, a decision on a different amount than the committed one is accepted; with it, it is rejected. (§5.4)
2. **C2 — Post-quantum binding in ZKML has a near-constant additive cost.** Across six workloads, the commitment adds about +12 ms verify, +28 ms prove and +8.4 KB, so the overhead ratio is about 1 + c / classical cost and falls as models grow. Fitted post-hoc on five workloads; predicted the sixth within 0.02× for size and prove time. (§5.5)
3. **C3 — Slashing-based agent liability wears out and is Sybil-fragile; two protocol fixes make it durable.** Pre-registered on 200 fresh agents per regime. (§4)
   - Flat stakes lose most of their effect as agents are slashed to zero: 19% → 45% violations, against control's 50%.
   - Free identity resets nullify escalating penalties exactly.
   - Stake maintenance (z = −13.1) and operator-bound history (z = −18.5) fix both problems.
   - A registration bond blocks resets at exactly the derived break-even B* = V_max − p·s − C_min.
4. **C4 — False-positive targets for federated AML are gameable.** A pre-registered matched-recall analysis shows the "≥ 20% fewer false positives" criterion is met only because federated models flag less. At equal recall, federation is never significantly better, and it is significantly worse with ample labels (+67–80% false positives). Such targets must be stated at fixed recall. (§3.3)
5. **C5 — Optimistic bisection for ZKML.** It isolates a tampered step in ⌈log₂ n⌉ rounds (7/7 scenarios) with zero accuracy cost from bisection itself. The 10× latency gain needs deep models (crossover between 24 and 60 blocks). On-chain, it only pays off if fewer than ≈ 0.8% of inferences are disputed (the earlier first-accounting figure was 1.2%; §2). (§2) With the later shared verifiers, a disputed step is no faster than proving the whole model (§6A).
6. **C6 — The four mechanisms work together on a BFT ledger, with the gate enforced by validators, not by the operator.** 889 / 889 honest transfers settled and 0 / 111 falsified ones did on 1,000 real transactions; every settled row reproduces exactly from the replayed ledger; a four-of-four run with one validator held by another person gave the same decisions on all 200 requests. Lab-scale, not production. (§6A)
7. **C7 — Hardware as a step of the method.** The decomposition of the model is computed from the prover node's memory, so disputes can be settled on machines that cannot hold the whole-model proof. The operator identity is a TPM, so escaping a violation history needs new hardware. Prototype and simulations, measured on one machine (§6B).

Negative and boundary results are part of the contribution. In particular:
- H2's federated detection is worse than centralized.
- Institution-level differential privacy with three institutions destroys utility (ε ≈ 50 → F1 0.29).
- H4 v2 missed its verify bound on the smallest workload.

---

## 2. H1 — Verifiable off-chain inference (zk-OPML)

**Hypothesis.** Restructuring AML inference as a bisectable ONNX computation graph under an optimistic dispute protocol reduces proof-generation latency and on-chain verification cost by ≥ 10× relative to a monolithic ZKML proof, with ≤ 1 pp accuracy loss.

### Setup

- **Data:** Elliptic, 46,564 labelled transactions. Temporal split: time steps 1–30 train, 31–34 validation, 35–49 test. Features clipped at the 1st/99th percentile.
- **Model:** residual MLP of width 32 (165→32 projection, B residual blocks, 32→1 head), B ∈ {1, 8, 24, 60}, 3 seeds each. All selection was done on validation.
- **Proof system:** EZKL 23.0.5 (Halo2/KZG), fixed-point scale 2⁹.
- **Bisection:** the model is split into steps (63 for B = 60, with the projection split into two halves).
  - Each step's output is Poseidon-committed; the leaves are chained by a running hash under a Merkle root.
  - A dispute binary-searches for the first differing step, then proves only that step on agreed inputs.

### Results

| Blocks | Steps | Full proof | Slowest step | Worst-case speedup | Bisection rounds |
|---|---|---|---|---|---|
| 1 | 4 | 2.11 s | 1.98 s | 1.07× | 2 |
| 8 | 11 | 7.67 s | 1.98 s | 3.88× | 4 |
| 24 | 27 | 15.16 s | 1.98 s | 7.67× | 5 |
| 60 | 63 | 29.43 s | 1.98 s | **14.9×** (single-core); 12.6× multi-core | 6 |

- **Dispute game, B = 60.** 7 of 7 tampering scenarios were localized exactly in ≤ 6 rounds, and the correct party won every time. Two of the scenarios flipped the AML decision (illicit ↔ licit); both were caught.
- **Accuracy.** The fixed-point circuit loses at most 0.13 pp accuracy (0.32 pp F1), with ≥ 99.81% of decisions unchanged. Bisection itself adds zero error.
- **Gas (local anvil chain):**

| Item | Gas |
|---|---|
| Monolithic verification | 696,984 |
| Optimistic commit | 49,962 (13.9× cheaper) |
| Full dispute (6 rounds + one step verification) | 1.26 M typical, 1.67 M worst (1.8–2.4× *more* than monolithic) |

**Break-even:** with the figures above, the 10× gas target holds on average only if the dispute rate is below ≈ 1.2% (worst case) or ≈ 1.6% (typical). The table above is the first accounting (v1); the complete one (v2: challenge, opening and adjudication included, real step verifiers: commit 54,673 gas = 12.8× cheaper, dispute 1.58 M typical / 1.91 M worst) gives **≈ 0.8% worst / ≈ 0.9% typical**, which is the figure to cite.

### Verdict against the pre-registered criteria

| Criterion | Result |
|---|---|
| ≥ 10× latency | **PASS only at 60 blocks**; FAIL at ≤ 24 |
| ≥ 10× on-chain cost | **PASS amortized** at a dispute rate below about 0.8%; **FAIL per dispute** |
| ≤ 1 pp accuracy loss | **PASS** (0.13 pp) |
| Bounded localization | **PASS** (⌈log₂ n⌉ rounds) |

### Limitations

- The 60-block model is a depth benchmark, not a better AML model: its F1 is 0.516, versus 0.77 for a random forest.
- Only 4 depths were measured, so the crossover depth lies somewhere between 24 and 60 blocks.
- Preprocessing is outside the circuit.
- The dispute game has no bonds or timeouts.
- The latency gain is in proof generation, not in time-to-finality.

Evidence: `h1-zkopml-v2/WRITEUP.md`, `h1-zkopml-v2/results/`.

---

## 3. H2 — Federated AML detection under label scarcity

**Hypothesis (original).** Under per-institution scarcity of illicit labels, federated GCN training across institutions achieves ≥ 20% fewer false positives than a centralized baseline. A boundary-embedding channel mitigates scarcity, and a privacy bound is achievable.

### 3.1 Protocol v2 (pre-registered: `h2-federated-aml/experiments/PREREGISTRATION_v2.md`)

- **Data and institutions:** Elliptic1 with 203,769 nodes and 234,355 edges. K = 3 institutions from a graph-aware partition.
- **Seeds:** 10 (42–51). The earlier v1 used 5 seeds, which cannot reach two-sided Wilcoxon p < 0.05.
- **Matched budget:** 200 epochs for every method (FedAvg = 40 rounds × 5 local epochs). Every method keeps its best checkpoint by validation F1.
- **Centralized baseline:** pooled training on the *identical* scarce label mask the federated run sees.
- **Scarcity levels:** 100%, 50%, 20%, 10%, 5% and 1% of illicit training labels kept.
- **Primary test:** one-sided paired Wilcoxon on test false positives, Holm correction over the 6 levels. The criterion is met when FP reduction ≥ 20% and Holm p < 0.05.

### 3.2 Results (default 0.5 threshold)

| Labels kept | FP centralized | FP FedAvg | FP reduction | Holm p | Criterion | F1 centralized | F1 FedAvg | ΔF1 (p) | Recall centralized → FedAvg |
|---|---|---|---|---|---|---|---|---|---|
| 100% | 113.7 | 62.3 | 45% | 0.025 | met | 0.757 | 0.649 | −0.109 (0.002) | 0.712 → 0.526 |
| 50% | 52.7 | 9.5 | 82% | 0.006 | met | 0.705 | 0.517 | −0.188 (0.002) | 0.589 → 0.354 |
| 20% | 27.1 | 9.0 | 67% | 0.031 | met | 0.495 | 0.314 | −0.181 (0.004) | 0.346 → 0.189 |
| 10% | 504.3 | 0.5 | 99.9% | 0.008 | met | 0.324 | 0.148 | −0.177 (0.002) | 0.331 → 0.080 |
| 5% | 500.3 | 24.7 | 95% | 0.012 | met | 0.166 | 0.041 | −0.125 (0.002) | 0.227 → 0.024 |
| 1% | 515.9 | 26.5 | 95% | 0.006 | met | 0.096 | 0.030 | −0.066 (0.031) | 0.190 → 0.019 |

FedAvg also has significantly lower F1 than **local-only** training at every level.

- **PR-AUC:** FedAvg is significantly worse with 50–100% labels and not different at 5–20%.
- **Boundary channel (refined H2):** **not supported.** It lowers F1 at 5 of 6 levels (p ≤ 0.037). In the λ ablation at 10% labels, F1 falls monotonically from 0.148 at λ = 0 to 0.029 at λ = 1.
- **Institution count (10% labels):** FedAvg F1 is 0.126 / 0.148 / 0.134 for K = 2 / 3 / 5, against centralized 0.31–0.32. The deficit does not depend on K.
- **Privacy:** institution-level DP with clip C = 1.5, Gaussian noise, 40 rounds, RDP accounting and δ = 1e-5.

| Noise z | ε | F1 | PR-AUC | False positives |
|---|---|---|---|---|
| 0 (no DP) | — | 0.649 | 0.782 | 62.3 |
| 0.01 | 2.0 × 10⁵ | 0.653 | 0.786 | 47.0 |
| 0.1 | 2.3 × 10³ | 0.527 | 0.495 | 511.5 |
| 1.0 | 50.3 | 0.287 | 0.164 | 1,810.7 |

With three institutions, the noise averages over only three updates, so no setting gives both meaningful privacy and usable detection.

### 3.3 Finding C4 — the false-positive criterion is gameable

Pre-registered in `h2-federated-aml/experiments/PREREGISTRATION_matched_recall.md` before the rerun.

**Rerun:** `main_scarcity` for the same 10 seeds, with per-node scores saved. The rerun reproduces v2 exactly: false positives are identical in 240 of 240 seed × method × level cases, and F1 differs by at most 0.017.

**Matching procedure:**
1. Target recall = the centralized model's *validation* recall at the 0.5 threshold.
2. Every method uses the largest threshold that reaches that target on validation.
3. Test false positives are counted once at that threshold.

Matched test recalls differ by ≤ 0.009.

| Labels kept | FP reduction at 0.5 | FP centralized (matched) | FP FedAvg (matched) | FP reduction (matched) | Holm p (one-sided) | Criterion | FedAvg significantly worse? (Holm, two-sided) |
|---|---|---|---|---|---|---|---|
| 100% | 45% | 112.9 | 203.7 | −80% | 1.0 | **fails** | yes, p = 0.012 |
| 50% | 82% | 52.7 | 87.8 | −67% | 1.0 | **fails** | yes, p = 0.049 |
| 20% | 67% | 27.0 | 51.6 | −91% | 1.0 | **fails** | no (p = 0.78) |
| 10% | 99.9% | 503.5 | 100.5 | +80% | 0.070 | **fails** (not significant) | — |
| 5% | 95% | 499.4 | 401.6 | +20% | 1.0 | **fails** | no |
| 1% | 95% | 993.8 | 1,135.0 | −14% | 1.0 | not evaluable (5/10 seeds)* | no |

\*In 5 seeds the centralized model had zero validation recall at 1% labels, so no recall could be matched. Per the pre-registration, this level does not count toward the verdict.

**Pre-registered verdict: supported.** The criterion fails at all 5 fully evaluable levels, where at the default threshold it passed at all 6.

**Honest exception:** at 10% labels, FedAvg's whole precision–recall curve sits above centralized's (figure `h2-federated-aml/results/v2_scores/pr_curves.png`). At matched recall it has 80% fewer false positives (unadjusted p = 0.012), but this does not survive the Holm correction (p = 0.070). In this regime the pooled model trained on few labels is the weak one.

### H2 verdict

- The original criterion is met as written but **not supported in substance**: federation detects worse and its false-positive advantage is a threshold artefact.
- The boundary channel is not supported.
- DP has no useful operating point with K = 3.

### Limitations

- Institutions are simulated by partitioning one dataset.
- One architecture (a 2-layer GCN).
- The DP guarantee covers the model-update channel only.

Evidence: `h2-federated-aml/README.md`, `results/v2/`, `results/v2_scores/`.

---

## 4. H3 — Cryptoeconomic liability via AgentBound Tokens

**Hypothesis.** Binding autonomous financial agents to staked, non-transferable AgentBound Tokens (ABTs) with coded slashing conditions reduces policy-violating actions relative to an unstaked control.

**Separate test:** does it resist Sybil attacks (identity resets)?

### 4.1 Setup

- **Agents:** 20 staked and 20 unstaked, 50 steps each.
- **Decision rule:** identical myopic expected-payoff rule for both groups. The only difference is the expected slash.
- **Violation (machine-checkable):** amount > 50 or a sanctioned destination.
- **Economics:** stake 100, slash 15, detection probability 1.
- **Payoffs:** compliant payoff in [1, 10], violation payoff in [1, 30].
- **Paired design:** both groups receive the identical opportunity stream.

### 4.2 Confirmatory result (seed 42)

| Group | Violations | Rate |
|---|---|---|
| Control (unstaked) | 542 / 1,000 | 54.2% |
| Treatment (staked) | 319 / 1,000 | 31.9% |

- **Agent-level tests (the correct unit):** Mann–Whitney U = 25.5, z = −4.73, p = 1.1 × 10⁻⁶; permutation p ≤ 10⁻⁵.
- **Action-level test:** z-test p = 3.7 × 10⁻²⁴. It is pseudo-replicated, so do not cite it.
- **Majority bar (post-hoc definition: rate ≤ 50%):** staked 19 / 20, control 7 / 20.
- **Sybil probe:** `SYBIL_SUCCEEDED`. The registry is keyed by agent id, so a slashed agent re-registers with a fresh ABT, fresh stake and a clean history.

### 4.3 Finding C3 — durable liability

Pre-registered in `h3-abt/docs/PREREGISTRATION_durable.md`.

**Post-hoc observation that motivated it:** on seed 42, 19 of 20 staked agents were slashed to zero stake. Once depleted, they violated at 53%, against control's 54%.

**Design:**
- 10 new seeds (43–52) × 20 agents = **200 agents per regime**, all regimes paired on the same opportunity stream.
- The simulator reproduces the confirmatory seed-42 counts (542 / 319) exactly.
- Regimes:

| Regime | What it adds |
|---|---|
| control | unstaked |
| flat | the original design: no top-up |
| maintained | stake topped back up before each action, enough to cover the next slash |
| escalating_id | maintained + repeat-offender slash 15·(1+k), with violation history k keyed by agent id; an agent may reset to a fresh id when that is strictly better one step ahead |
| escalating_operator | as escalating_id, but history k is keyed by the operator credential, so a new id keeps it |

| Regime | Violations | Steps 1–10 | Steps 41–50 | Resets | Mean slashed / agent |
|---|---|---|---|---|---|
| Control | 50.7% | 49.8% | 50.5% | 0 | 0 |
| Flat ABT (original) | 30.6% | 19.1% | **45.2%** | 0 | 98.3 (180 / 200 agents depleted) |
| + stake maintenance | 19.6% | 19.1% | 18.3% | 0 | 146.8 |
| + escalation, id-keyed (free reset) | 19.6% | 19.1% | 18.3% | 1,757 | 146.8 |
| + escalation, **operator-bound** | **2.0%** | 8.7% | 0.0% | 0 | 15.0 |

**Primary tests** (one-sided agent-level Mann–Whitney, Holm across both; permutation p ≤ 10⁻⁵ for each):
- **T1:** maintenance beats flat in steps 41–50: 18.4% vs 45.2%, z = −13.1. **Supported.**
- **T2:** operator-bound escalation beats id-keyed escalation with free resets: 2.0% vs 19.6%, z = −18.5. **Supported.**

**Secondary results:**
- Flat < control replicates on the new seeds over all steps: 30.6% vs 50.7%, z = −15.0.
- In steps 41–50 the flat-vs-control gap shrinks to −5 pp (z = −2.7, p = 0.003).
- Maintenance beats control in steps 41–50 (z = −15.3).

**Registration-bond sweep** (id-keyed registry, bond B paid per new identity):
- Analytic break-even: B* = V_max − p·s − C_min = 30 − 15 − 1 = 14.
- The prediction matched exactly: zero resets at B ≥ 14.

| B | 0 | 5 | 10 | **14** | 20 | 40 |
|---|---|---|---|---|---|---|
| Resets | 1,757 | 833 | 176 | **0** | 0 | 0 |
| Violation rate | 19.6% | 10.3% | 3.8% | **2.0%** | 2.0% | 2.0% |

Figure: `h3-abt/results/durable_figure.png`.

### H3 verdict

- Deterrence is **supported**.
- In its original form it **wears out**, and **Sybil resistance fails** with id-keyed identity.
- Both are fixed by stake maintenance together with operator-bound history, or with a registration bond ≥ B*.
- Combined, the fixes reduce violations from 50.7% to 2.0%, and each operator pays only one slash (15) over 50 steps.

### Limitations

- Simulation only, with myopic agents and a one-step-ahead reset rule.
- Detection probability is 1.
- Operators are assumed to have unlimited capital for top-ups.
- The operator credential is assumed to exist; establishing it is a regulatory question.
- The original simulation had no on-chain contract. One was built later (`LiabilityRegistry`, 9 tests) and exercised in the integrated system (§6A); the learning-agent study (§6A) relaxes the myopic-agent and perfect-detection assumptions.

Evidence: `h3-abt/README.md`, `results/confirmatory_seed42.*`, `results/agent_level_seed42.json`, `results/durable_*`.

---

## 5. H4 — Post-quantum ZK-STARK migration

**Hypothesis.** A lattice-based ZK-STARK construction can secure ZKML proof verification for the H1–H3 model classes, keeping proof size and verifier latency within a bounded overhead factor relative to classical ZK-STARKs.

**Pre-registered bounds (2026-10-06, unchanged):** mean PQ/classical proof size ≤ 20×, prove time ≤ 200×, verify time ≤ 10×.

### 5.1 Construction

- **Proof system:** Winterfell (fork with field f23201, p = 7,340,033).
  - Sextic extension (138-bit), blowup 8, 42 queries, 16-bit grinding, Blake3-256.
  - Conjectured security 125–128 bits for both classical and PQ proofs.
- **Statement:** the workload, plus knowledge of a short opening of a public SIS commitment c = G·bits + B·r mod p:
  - n = 80 rows, 64 boolean amount bits and 448 ternary r;
  - G and B are verifier-computed and uniform.
- **Binding is statistical:** the expected number of short collisions is ≈ 2⁻⁶³⁶. The lattice estimator (MATZOV / ADPS16 / ChaLoy21 cost models) puts the best attack at ≥ 2⁶¹⁵ quantum cost.
- **v3 proof technique:** after s = (bits, r) is committed, the verifier draws γ ∈ F_{p⁶}. One extension-field accumulator then checks Σ γʲ(Aⱼ·s − cⱼ) = 0. The extra soundness error is ≤ 2⁻¹³⁰·⁵.
- **Hiding:** the commitment is binding only; no zero-knowledge masking is claimed.

### 5.2 Version history (kept as recorded)

- **v1 — withdrawn as unsound:**
  - the SIS matrix was prover-controlled;
  - the relation was checked under the wrong modulus;
  - r was not range-checked;
  - security was only about 11–17 bits.
- **v2** (pre-registered). Results below.
- **v3** — same commitment, new proof. It was pre-registered after the v2 miss, and that is disclosed.

| Version | 2×2 matmul (size / prove / verify) | H1 dense 165→32 |
|---|---|---|
| v2 | 9.10× / 71.5× / **14.10× (FAIL)** | 1.88× / 9.90× / 4.37× (PASS) |
| v3 | 4.97× / 14.20× / 7.40× (PASS) | 1.23× / 2.58× / 3.45× (PASS) |

### 5.3 Coverage of the complete trained H1–H3 models (v3; pre-registered in `docs/h4_coverage.md`)

Exact integer circuits with the following properties:
- inputs are range-checked;
- every requantization and ReLU is proven, with windows ≤ 2²² < p so each decomposition is unique;
- interval bounds keep all accumulators below (p − 1) / 2.

| Workload | What is proven | Size | Prove | Verify | Verdict | Fidelity vs float |
|---|---|---|---|---|---|---|
| H1 MLP (full) | trained W32_B1, all layers, one real illicit transaction | 1.18× | 1.28× | 1.92× | PASS | F1 0.505 vs 0.512; 99.5% agreement |
| H2 GCN | trained 2-layer GCN, node 36333, 3-node field | 1.13× | 1.36× | 1.76× | PASS | F1 0.732 vs 0.743; 99.0% agreement (declared 0.1–99.9 percentile clip) |
| H3 rule ×64 | `choose_action` + `is_violation`, 64 real decisions | 1.20× | 1.51× | 1.96× | PASS | 100% agreement |

### 5.4 Finding C1 — one post-quantum proof for a whole CBDC transaction decision

Pre-registered in `h4-pqc-stark/docs/h4_composed.md` before timing. One trace, one proof:
1. **H1 inference:** full inference of the trained H1 model on one real transaction. The logit stays private.
2. **Risk flag:** RISK = [logit > T_q], proven by a two-sided sign window. A test checks the window is unique over the circuit's whole interval-bounded logit range.
3. **H3 decision:** the H3 rule for one real decision, with RISK added as a violation condition: VIOL = (amount > limit) ∨ sanctioned ∨ RISK.
4. **Amount binding:** the rule's amount equals Σ 2ⁱ·bitᵢ of the SIS-committed amount, and committed bits 16–63 must be zero.

**Instance:** decision 1 (amount 7,558, compliant under the original rule) with the flagged H1 transaction. The risk flag turns a compliant transfer into a violation.

**Width:** a narrow single-decision rule (19 register columns plus one shared 22-bit window reused across 7 rows) keeps the trace within Winterfell's 255-column limit: 207 columns classical, 220 main columns PQ.

**Tests: 20 / 20 pass.** Each of the following is rejected:
- a forged risk flag;
- a wrong EXEC or VIOL output;
- committed high bits;
- a register changed mid-trace;
- a decision made on an amount different from the committed one (the **classical circuit accepts this one; the PQ circuit rejects it**).

| Metric | Classical (no commitment) | PQ (SIS v3 + link) | Ratio | Bound | Result |
|---|---|---|---|---|---|
| Proof size | 61,659 B | 71,191 B | 1.15× | ≤ 20× | PASS |
| Prove time | 111.0 ms | 142.2 ms | 1.28× | ≤ 200× | PASS |
| Verify time | 19.6 ms | 34.8 ms | 1.77× | ≤ 10× | PASS |

Measured over 30 runs, with conjectured security of 126 bits.

Marginal cost of adding the decision and the link on top of H1-only PQ inference: about +6.0 KB, +32 ms prove and +3.4 ms verify (unpaired runs).

### 5.5 Finding C2 — overhead law (post-hoc)

Across the v3 workloads, PQ ≈ classical + c. The ratio is about 1 + c / classical cost, so it falls as the proven computation grows.

| Metric | c (added cost) | Range across workloads |
|---|---|---|
| Verify | ≈ 12 ms | 8–15 ms |
| Prove | ≈ 28 ms | 15–39 ms |
| Size | ≈ 8.4 KB | 7.8–10.2 KB, excluding the 2×2 workload |

The 2×2 workload is the exception: its 8-row trace is padded to 128 rows for the SIS block, which adds 26.5 KB.

**Out-of-sample check on the composed workload:**

| Metric | Predicted ratio | Measured ratio |
|---|---|---|
| Size | 1.14× | 1.15× |
| Prove | 1.26× | 1.28× |
| Verify | 1.61× (underpredicted) | 1.77× |

Figure: `h4-pqc-stark/benchmark_v2/results/overhead_law.png`.

### H4 verdict

**Supported (v3)** for every workload, including complete H1, H2 and H3 inference and the composed transaction proof. v2's primary-workload miss stays recorded.

### Limitations

- One instance per model class.
- One machine; the ratios are the reported quantity.
- The commitment provides binding, not hiding.
- The v3 benchmarks do not include a settlement layer. A lab-scale integration on a Besu QBFT ledger (Plonky3 proof, §6A) was added later; it is not a production or central-bank ledger.
- H1's input features are not tied to the amount (Elliptic features are anonymized).

Evidence: `h4-pqc-stark/README.md`, `docs/h4_*.md`, `benchmark_v2/results/`.

---

## 6. How the pieces fit (the system story for the paper)

A CBDC transfer passes through four layers:
1. A risk model scores the transaction (H1, trained with or without federation, H2).
2. An autonomous agent decides whether to execute it, with financial liability attached (H3).
3. The decision is verifiable off-chain, with disputes settled by bisection (H1).
4. The cryptography stays secure against quantum adversaries (H4).

C1 makes this concrete: one post-quantum proof binds the model's output, the agent's decision and the committed amount. The overhead is under 2×, and per C2 it shrinks for larger models. §6A shows the layers running together on a BFT ledger with validators that verify the proof and sign, so that falsified requests do not settle.

The negative results define where the design must change:
- federation needs a recall-anchored target, and more than three parties for DP to be usable (H2);
- liability needs stake maintenance and operator-bound identity (H3);
- on-chain dispute settlement only pays off at low dispute rates (H1).

---

## 6A. Integrated system and follow-up work (October 2026; technology readiness level 4)

Code: `integration/` (README there has every table), `h1-zkopml-v2/` (v2, v2.1), `h3-abt/contracts/`,
`h3-abt/docs/PREREGISTRATION_learning.md`, `h4-pqc-stark/zk_composed/`, `h4-pqc-stark/docs/h4_zk_composed.md`.

### System
- **Ledger:** Hyperledger Besu 25.10, 4 validators, QBFT (tolerates 1 faulty), 1-second blocks.
- **Operator node:** for each transfer it proves, in one zero-knowledge Plonky3 STARK, the H1 inference
  (W32_B1), the risk flag, the H3 decision under public policy values (limit, sanctioned id, the
  registry's current escalated slash) and the link between the decided amount and an SIS commitment.
- **Validators:** each verifies the proof natively (not in the EVM), the model digest, the commitment
  opening against the settled amount, the outputs and the current policy read from its own node, and
  signs (EIP-191).
- **Contracts:** `SettlementGate` (3-of-4 quorum, customer mandates; outcomes Executed / AgentRefused /
  Blocked + slash / NotCovered) and H3's `LiabilityRegistry`.

### Results
| Run | Honest settled as required | Faulty reaching quorum / changing ledger | End to end |
|---|---|---|---|
| 1,000 real Elliptic test-period tx, 4 honest validators | 889 / 889 | 0 / 111 · 0 | 1.98 s mean |
| 300 synthetic, 1 Byzantine validator | 244 / 244 | 0 / 56 · 0 | 1.96 s |
| 60 synthetic, 2 Byzantine | 26 / 26 | 0 / 34 · 0 | 1.61 s |
| 40 synthetic, 1 crashed | 25 / 25 | 0 / 15 · 0 | 1.66 s |
| 1,000 synthetic, real node crash (OOM) mid-run | 899 / 900 | 0 / 100 · 0 | 2.51 s |

In the Elliptic run, H1's in-proof risk flag had precision 0.53 and recall 0.72 (69 illicit among 889):
recall 0.81 on time steps 35–42 and 0 on 43–49, the known post-shutdown collapse of Elliptic models. 61 of
69 illicit transfers were not executed; the 8 executed were all model misses. Settle gas: Executed
103 k, AgentRefused 84 k, Blocked incl. slash 108 k; proof ≈ 170 KB off-chain, only its hash on-chain.

### Defects found by integration (fixed, with regression tests)
1. The composed proof's 22-bit comparison window could not hold the decision term once the registry
   escalated the slash; honest proofs failed (145/244 in the first run). Now 30 bits with a stated
   domain (policy values and stake < 2²⁰) checked by prover and verifier.
2. The proven rule refused every compliant transfer (H3 refuse-on-tie) and the gate slashed declined
   violations. Now compliant transfers execute and only attempted violations are slashed.

### Follow-up work per track
- **H1 v2 / v2.1.** Hardened dispute contract with full on-chain adjudication: prefix-consistency check
  (blocks a malformed-chain attack that v1 allowed), bonds, per-turn deadlines, per-challenger disputes,
  slashable delayed withdrawals (17 Foundry + 66 Python tests). Complete games with real EZKL verifiers on
  a local chain: 7/7 scenarios correct on two real transactions. Steps of one shape share a verifier
  (weights as a hashed instance checked by the contract): 4 verifiers, 17.2 M deploy gas instead of
  ~251 M; a valid proof of another block's weights is rejected. Measured dispute 1.58–1.91 M gas;
  undisputed saving 12.8×; the 10× target holds below a 0.79 % (worst) / 0.93 % (typical) dispute rate.
  **Trade-off:** shared verifiers give up the proving gain: on one machine the whole 60-block proof takes
  18.2 s, a fixed-weight block step 1.4 s (13.4× faster), a shared-verifier block step 16.1 s and the slowest
  shared-verifier step (a projection half) 50.1 s, 2.8× slower than the whole model. The 14.9× figure holds
  for the fixed-weights design only.
- **H3.** On-chain `LiabilityRegistry` (9 tests). Pre-registered learning-agent study (ε-greedy,
  detection p = 0.5 and 0.8, 10 seeds, 500 steps): stake maintenance beats a flat stake late in the run
  (20.9 % vs 25.7 % at p = 0.5; 16.1 % vs 26.2 % at p = 0.8) and operator-bound history beats ID-keyed
  history (4.3 % vs 11.5 %; 3.3 % vs 8.6 %), all four Holm-corrected p ≤ 3.2 × 10⁻⁷; a bond at the
  break-even B* removes strategic resets (only exploration resets remain).
- **H4 v4 / v4.1.** The composed proof is re-implemented on Plonky3 with hiding (zero-knowledge; the v3
  Winterfell proof was not). SIS re-derived for BabyBear (48 rows, statistical binding 2⁻²⁹⁴·⁷), opening
  checked row by row. Security of the whole proof: 124-bit conjectured / 111-bit proven classical, ≈ 62
  bits quantum under the conservative QROM bound (the earlier "2⁶¹⁵" figure described only the
  commitment). Overhead of post-quantum binding under ZK: 1.07× size, 1.10× prove, 0.98× verify; deployed
  proof 170 KB, ≈ 0.6 s prove, 15 ms verify. 17 tests.
  **Note:** this quantum estimate is weaker than the earlier construction's. Under the same argument the v3 Winterfell proof gets ≈ 63 bits (126-bit conjectured), and the "≥ 2⁶¹⁵ quantum" figure quoted for H4 earlier described only the lattice commitment, not the proof. Zero-knowledge was gained; about 2 bits of conjectured security were lost.

### Readiness
Technology validated in a lab (TRL 4): the components run together on a BFT ledger with real data and
injected faults. A two-person, two-machine run over Tailscale (20–21 Oct 2026) also showed the gate working with
one validator key held by someone other than the host. Not yet shown: a relevant environment (several
organisations, realistic network delays, a real central-bank ledger, real amounts), throughput beyond one
sequential operator, and privacy of amounts towards validators.

### Independent-validator run and what has been checked independently
- **Run (20–21 Oct 2026):** host (a person outside the team, his own MacBook) ran the network, three validators and 200 real Elliptic transfers (34 falsified); the reviewer (Aman Hooda, his own MacBook Air) ran a separate Besu node and the fourth validator with a key generated on his machine and his own build of the verifier. The contract required all four signatures. Result: the reviewer's validator signed exactly the 166 honest transfers and refused all 34 falsified ones, each for the matching reason; the three host validators decided identically on all 200 requests; with the reviewer unreachable, nothing settled.
- **Checked by the mentor on his own machine:** all 234 tests; every summary recomputed from the raw records; the exported ledger re-executed in a fresh Besu 25.10 node (audit table of 2,197 settlements byte-identical to the team's); all 116 recorded dispute transactions replayed on an empty `anvil` (116 / 116 match; 7 / 7 winners agree; all proofs verify); the independent-validator records rechecked with separately written code.
- **Not independently verified:** the live runs and all timings (they come from the team's machines), the re-execution of the reviewer's exported ledger in Besu (done by the reviewer; the mentor checked the export by decoding it, see §6A), and the H3 learning study and H4 v4 results beyond their test suites.
- **Limits:** the reviewer is a team member and the host followed the team's instructions; the run shows the gate needs a key the host does not hold, not an audit by an unrelated third party.

## 6B. Hardware integration (late October 2026)

Code: `h1-zkopml-v2/bench_resources.py`, `h1-zkopml-v2/memory_planner.py`, `h4-pqc-stark/zk_composed/measure_resources.py`, `integration/hw_identity/`, `integration/embodiments/` (PR #43). All runs: one 2-vCPU, 8 GB cloud machine, software TPMs (swtpm). Not yet independently verified.

**Why.** A faculty review of the invention disclosure noted that an Indian examiner would likely object under Section 3(k) of the Patents Act (computer programme *per se*). The 2025 Guidelines for Computer Related Inventions and recent Delhi and Madras High Court decisions ask for a technical effect on the machine, not new hardware. This work makes hardware properties and components steps of the method and measures their effect.

### What each proof costs the machine

| Proof | Circuit rows | Proving key | Peak memory | Prove time |
|---|---|---|---|---|
| Whole 60-block model | 2¹⁷ | 554 MB | 1,243 MB | 18.2 s |
| One block step, weights fixed (own verifier) | 2¹² | 41 MB | 107 MB | 1.4 s |
| One block step, weights hashed (shared verifier) | 2¹⁶ | 659 MB | 1,373 MB | 16.1 s |
| Composed post-quantum proof of one transfer (prove / verify) | 256 rows × 270 columns | none (transparent) | 20 MB / 12.5 MB | 0.6 s / 15 ms |

- **Ledger storage:** each ledger node stores a 32-byte hash of the ~170 KB composed proof.
- **Cache simulation (Valgrind Cachegrind):** 99.9% of the prover's 1.15 billion data accesses hit a simulated 1 MiB cache. No other trace layout was compared, so no causal claim is made.

### Memory-budgeted decomposition

**Method.** The prover node:
1. reads its memory budget M;
2. uses a profile of its own machine (peak memory of each candidate step shape);
3. chooses the smallest projection split k and the largest block group g that fit within 0.9·M.

| Node budget | Plan | Steps | Bisection rounds | Measured peak (other positions) |
|---|---|---|---|---|
| 128 MB | k = 2, g = 1 | 63 | 6 | 107 MB |
| 256 MB | k = 1, g = 4 | 18 | 5 | 190 MB |
| 512 MB | k = 1, g = 8 | 11 | 4 | 357 MB |
| 1 GB | k = 1, g = 16 | 7 | 3 | 691 MB |
| 2 GB | whole model | 1 | 0 | 1,243 MB |

- **Results:** every step of every plan stayed within budget and every proof verified.
- **Unified verification mode:** the same profile decides whether a model is proven in full for every transfer or posted optimistically with step disputes.
- **Closest prior art:** DSperse (2025) slices models to lower prover memory, but slice sizes are set by hand.

### TPM-anchored operator identity (prototype)

**Design.**
- **Identity:** k(O) is the SHA-256 of the operator node's TPM endorsement key, which is certified by the TPM manufacturer.
- **Enrolment:** checks the certificate chain and the attestation key's TPM attributes. A credential activation proves that key lives in the same TPM.
- **New agent identities:** each needs a TPM2_NV_Certify attestation of the TPM's monotonic counter, bound to a registry nonce. Otherwise it needs a deposit of at least B*.

**Results** (two software TPMs and `LiabilityRegistry` on anvil):
- the honest flow was accepted;
- 9 of 9 attacks were refused (replay, re-binding, tampering, software signature, forged certificate, software key as attestation key, activation by another TPM, the same TPM as a second operator, stale or cloned state);
- a deleted and re-created counter resumed above its old value;
- attesting took 47 ms on the TPM and 0.4 ms to verify.

### Verify-then-sign in a trusted execution environment (simulation)

**Design.**
- **Isolation:** the environment is a separate process with an in-memory key and a private copy of the verifier.
- **Measurement:** the launcher measures it into a TPM PCR.
- **Attestation:** a TPM quote naming its key is its remote attestation.

**Results:**
- the honest request was signed;
- 5 of 5 falsified requests were refused, each for its reason;
- a patched verifier that accepts everything was never registered, so its signature did not count;
- replayed quotes, outside keys and unenrolled TPMs were refused.

**Limit:** no hardware memory isolation, and the launcher, not the CPU, takes the measurement.

### Offline payment devices with a secure element (simulation)

**Design.**
- **Payer device:** proves offline.
- **Secure element (a TPM):** supplies the commitment randomness and certifies a monotonic counter bound to commitment, proof, payee, amount and cumulative spending.
- **Payee devices:** check everything without a network.
- **On reconnection:** validators settle in counter order.

**Results:**
- 4 honest payments were accepted and settled (11,000).
- Refused offline:
  - replay;
  - a redirected bundle;
  - an amount raised in transit;
  - a sanctioned payee;
  - expired or altered snapshots;
  - a forged signature;
  - a software wallet.
- A manipulated app hiding earlier spending was accepted offline but refused at synchronisation as an overspend, and the device was flagged.
- Payer side 0.76 s per payment; payee check 64 ms; bundle 174 KB.

### IDF changes
- **Size:** the invention disclosure grew from 13 to 22 pages.
- **Generic framing:** the first claim is about execution gating of AI-driven state transfers on a distributed ledger, with CBDC as one application.
- **New sections and claims:** sections on node hardware, the offline device and the TEE; claims for the memory-budgeted dispute method, TPM-based admission control and the offline device.
- **Prior art:** DSperse and zkComposer were added.

**Open:**
- the TPM identity has not been run on a manufacturer TPM;
- the TEE and offline device have not been run on real TEE hardware or phones;
- the IPR cell has not yet advised on prior public disclosure (the repositories are public).

---

## 7. Methodology and threats to validity

**Pre-registration.** The following were committed before their confirmatory runs, with commit hashes in each PR:
- H2 v2 and its matched-recall test;
- H3 durable liability;
- H4 v2, v3, coverage and the composed proof;
- the H3 learning-agent study (§6A).

**Post-hoc work (labelled as such everywhere):**
- H3's majority-bar definition;
- the H3 wear-out observation on seed 42 (then confirmed on fresh seeds);
- the H4 overhead law.

**Disclosed iterations.** H4 v3 was designed after v2 missed its bound. Superseded results stay in the repository: H2 v1 and H4 v1.

**Statistics:**
- The unit of analysis is the seed (H2) or the agent (H3).
- Holm correction is applied across levels and primary tests.
- Paired designs are used throughout.
- The H3 action-level p-value is not cited (pseudo-replication).

**Main threats:**
- **Single dataset:** all ML results use Elliptic.
- **Simulation:** H2 institutions are simulated, and the H3 agents are simulated and myopic.
- **Hardware:** H4 timings come from one machine; the integrated-system timings come from the team's machines and were not independently re-run.
- **Hardware integration (§6B):** software TPMs stand in for manufacturer TPMs; the TEE and the offline devices are simulations on one machine, not runs on TEE hardware, phones or terminals.
- **Integration scale and independence:** the integrated runs are lab-scale (one sequential operator, one ledger of four validators). The two-machine run involved a team member and a person following the team's instructions.
- **Detection quality:** the system enforces what its proven rule says. With the H1 model's recall of 0.72 on real data (0 after time step 43), some illicit transfers still execute.
- **Synthetic composition:** the composed proof pairs a real H1 transaction with a real H3 decision; Elliptic has no amount field.

---

## 8. Reproducibility index

| Result | Command (from the hypothesis folder) | Output |
|---|---|---|
| H1 latency, accuracy, gas | see `h1-zkopml-v2/README.md` | `h1-zkopml-v2/results/` |
| H2 v2 | `python src/protocol_v2.py run --config experiments/configs/protocol_v2.yaml --seed <42..51>`, then `aggregate` | `results/v2/` |
| H2 matched recall | `python src/protocol_v2.py scores ... --seed <42..51>`; `python src/matched_recall.py --config experiments/configs/protocol_v2.yaml` | `results/v2_scores/` |
| H3 confirmatory | `python run_experiment.py --config configs/experiment.yaml`; `python run_agent_level.py` | `results/confirmatory_seed42.*`, `agent_level_seed42.json` |
| H3 durable liability | `python run_durable.py` | `results/durable_report.json`, `durable_actions.csv`, `durable_figure.png` |
| H3 Sybil probe | `python run_sybil.py` | stdout |
| H4 v2 / v3 / coverage / composed | `cd benchmark_v2 && cargo test --release && cargo run --release -- 30 [v3\|coverage\|composed] > results/benchmark_<x>.csv && python analyze.py results/benchmark_<x>.csv` | `benchmark_v2/results/` |
| H4 overhead law | `python benchmark_v2/overhead_law.py` | `results/overhead_law.*` |
| Hardware: resources, memory plans | `python3 h1-zkopml-v2/bench_resources.py`; `python3 h1-zkopml-v2/memory_planner.py <data>`; `python3 h4-pqc-stark/zk_composed/measure_resources.py` | `h1-zkopml-v2/results/dispute_resources.json`, `memory_plans.json`; `zk_composed/results/resources.json` |
| Hardware: TPM identity, TEE, offline devices | `python3 integration/hw_identity/run_demo.py`; `python3 integration/embodiments/tee_sim.py`; `python3 integration/embodiments/offline_sim.py` | `results/hw_identity.json`, `tee_sim.json`, `offline_sim.json` |
| H4 lattice estimate | `docker run --rm -v "$PWD:/work" sagemath/sagemath:latest sage -python /work/est_h4.py` (in `docs/`) | `docs/h4_lattice_estimator.json` |

**Data:** Elliptic, from `https://data.pyg.org/datasets/elliptic/`. It is not committed.

**Toolchain:**
- Python 3.10, PyTorch 2.x, torch_geometric 2.8;
- Rust stable, with Winterfell fork `bwesterb/winterfell@b964cfd`;
- EZKL 23.0.5.
