# CBDC – AI – Blockchain Research Project

Research project testing 4 independent hypotheses on combining Central Bank Digital Currencies (CBDC), AI, and blockchain. Each hypothesis is owned end-to-end by one person: build the prototype, measure it against a target number, report pass or fail honestly.

Full research proposal: `docs/CBDC_AI_Blockchain_Research_Proposal.pdf`

## The 3 Problems We're Solving

1. **Privacy vs catching criminals** — blockchain is traceable (bad for privacy), hiding transactions blocks fraud detection (bad for AML/CFT).
2. **Nobody's responsible when AI messes up** — no legal or technical framework assigns liability when an autonomous AI agent makes a bad financial call.
3. **AI and blockchain don't mix technically** — blockchain needs deterministic consensus, AI is probabilistic. Can't run real AI directly on-chain.

## The 4 Hypotheses

| Folder | Hypothesis | Owner | One-line idea | Target |
|---|---|---|---|---|
| [`h1-zkopml-v2/`](h1-zkopml-v2) | H1 — Verifiable Off-Chain Inference | Aman | Only prove the disputed part of an AI decision, not the whole thing, when challenged | ≥10x faster/cheaper than proving the whole model, ≤1pp accuracy drop |
| [`h2-federated-aml/`](h2-federated-aml) | H2 — Federated AML Detection | Indrakshi | Banks train fraud-detection AI together without sharing raw customer data | ≥20% fewer false-positive fraud flags vs a centralized baseline, under label scarcity, with a privacy bound |
| [`h3-abt/`](h3-abt) | H3 — Cryptoeconomic Liability (AgentBound Tokens) | Anjali | AI agents put down a financial stake; break a rule, lose the stake automatically | Staked agents violate rules statistically significantly less than unstaked agents |
| [`h4-pqc-stark/`](h4-pqc-stark) | H4 — Post-Quantum ZK Proof Feasibility | Simran | Swap in quantum-resistant proof math, check it doesn't get impractically slow/big | Overhead vs classical proof system stays within an agreed bound |

## Final Results

All four experiments are complete and merged. Each hypothesis README has the full method, numbers, and limitations.

**Complete write-up with every result, method, limitation and reproduction command: [`docs/FULL_REPORT.md`](docs/FULL_REPORT.md).** Exhaustive record of every experiment ever run (including withdrawn and superseded versions, every per-seed/per-run table generated from the result files, all pre-registrations, corrections log): [`docs/EXHAUSTIVE_REPORT.md`](docs/EXHAUSTIVE_REPORT.md), rebuilt by `python docs/exhaustive/build.py`.

| | Verdict | Key numbers | Main caveat |
|---|---|---|---|
| **H1** zk-OPML | **Partly supported** | Bisection isolates the disputed step in ≤ 6 rounds (7/7 scenarios); accuracy drop ≤ 0.13 pp. Proof latency 14.9× (single-core) / 12.6× (multi-core) faster, **only at 60 blocks** and only with fixed-weight step verifiers; 7.7× at 24 blocks, 1.07× at 1 block. With the shared verifiers of v2.1 the dispute proof is no faster than the whole-model proof (worst step 2.8× slower). | On-chain gas: 13.9× cheaper when undisputed, but a dispute costs 2.4× more than monolithic verification. The 10× gas target holds only if < 0.8% of inferences are disputed. |
| **H2** federated AML | **Criterion met, hypothesis not supported in substance** | Pre-registered FP test met at all 6 scarcity levels (10 seeds, Holm p < 0.05). But FedAvg F1 is significantly **lower** than the centralized baseline at every level (−0.07 to −0.19), with much lower recall. | The FP drop comes from flagging fewer transactions: at **matched recall** (pre-registered rerun) the criterion fails at all 5 fully evaluable levels, and with 50–100% labels FedAvg makes 67–80% *more* false positives. Boundary channel lowers F1 (refined H2 not supported). Institution-level DP: ε ≈ 50 drops F1 0.65 → 0.29. |
| **H3** AgentBound Tokens | **Deterrence supported; wears out and is Sybil-fragile as designed — both fixed by stake maintenance + operator-bound history (pre-registered, violations 50.7% → 2.0%)** | Staked agents violate 31.9% vs 54.2% unstaked (41% reduction). Agent-level tests: Mann–Whitney p = 1.1 × 10⁻⁶, permutation p ≤ 10⁻⁵. Majority bar: 19/20 staked vs 7/20 unstaked. | `SYBIL_SUCCEEDED`: a slashed agent re-registers under a new id with a clean history. One simulation configuration. |
| **H4** PQ ZK-STARK | **Supported (v3)**; v2 missed one bound | Sound SIS-STARK, 125–128-bit conjectured security, statistically binding commitment (lattice estimator ≥ 2⁶¹⁵ quantum — this figure is for the commitment only; the whole v3 proof is ≈ 63-bit quantum under the conservative QROM bound, and the later zero-knowledge v4 proof ≈ 62-bit). v3 overhead vs classical: 2×2 matmul 5.0× / 14.2× / 7.4×; **complete inference of the trained H1 MLP, H2 GCN and H3 rule: ≤ 1.2× size, ≤ 1.5× prove, ≤ 2.0× verify.** One composed proof of H1 risk → H3 decision → committed amount: 1.15× / 1.28× / 1.77×. All within bounds. | v2 failed the 2×2 verify bound (14.1× > 10×); v3 was designed after that miss (disclosed). One instance per model class (one transaction, one 3-node GCN neighborhood, 64 decisions). v1 withdrawn (unsound). |

## Integrated system: the four tracks as one running CBDC settlement pipeline (TRL 4)

After the individual experiments, the mechanisms were joined into one system and validated in the lab
([`integration/`](integration)). A transfer passes through all of them:

1. the operator node runs the H1 risk model **inside a zero-knowledge, post-quantum-bound proof** (H4 v4,
   Plonky3) that also proves the H3 agent's decision under the registry's **current escalated slash** and
   binds the decision to the amount inside a lattice commitment;
2. each of the **4 validator nodes of a Hyperledger Besu QBFT network** verifies the proof natively,
   checks the commitment opening and the current policy against its own node, and signs;
3. the **SettlementGate** contract acts on a 3-of-4 quorum: a compliant transfer is executed, an
   attempted violation is blocked and the operator slashed by the on-chain **LiabilityRegistry** (H3),
   a declined violation moves nothing.

| Run | Result |
|---|---|
| **1,000 real Elliptic test-period transactions** | **889 / 889** honest transactions settled exactly as the rules require (4/4 signatures); **0 / 111** injected faults (forged outputs, swapped amounts, stale slash, corrupted proofs, wrong model) reached quorum or changed the ledger; **1.98 s** end to end (mean); H1's in-proof risk flag: precision 0.53, recall 0.72 (0.81 recall before time step 43, 0 after) |
| 300 synthetic transactions, 1 Byzantine validator | 244 / 244 honest settled; 0 / 56 faults reached quorum |
| 60 synthetic transactions, 2 Byzantine validators | 26 / 26; 0 / 34 |
| 40 synthetic transactions, 1 crashed validator | 25 / 25 settled with 3 signatures; 0 / 15 |
| 1,000 synthetic transactions, real node crash mid-run | 899 / 900 (one honest tx lost to a second, transient fault while a node was down; nothing moved) |

Integration found two real defects, both fixed with regression tests: the composed proof was incomplete
once H3's slash escalated (a 22-bit comparison window; now 30 bits with a stated domain), and the proven
rule could never execute a compliant transfer.

Reviewers: the raw logs, the exported ledger and scripts that check every number against the chain are described in [`docs/EVIDENCE.md`](docs/EVIDENCE.md). A run with one validator key and Besu node on a second person's machine (4-of-4 gate, 200 Elliptic transfers, all 34 falsified ones refused, nothing settled without that validator) is in [`integration/evidence/independent_validator/`](integration/evidence/independent_validator/README.md). Hardware integration (28 Oct 2026): a model decomposition sized to the prover node's memory (`h1-zkopml-v2/memory_planner.py`), a TPM-anchored operator identity ([`integration/hw_identity/`](integration/hw_identity/README.md)) and simulated TEE signing and offline payment devices ([`integration/embodiments/`](integration/embodiments/README.md)); summarised in §6B of [`docs/FULL_REPORT.md`](docs/FULL_REPORT.md).

Follow-up work per track (details in each README):
- **H1 v2/v2.1:** hardened dispute contract (on-chain adjudication, prefix-consistency check, bonds,
  timeouts, per-challenger disputes; 17 Foundry tests) and complete on-chain games with **real EZKL
  verifiers**: 7/7 scenarios correct on two real transactions, one shared verifier per step shape
  (4 verifiers instead of 63: 17.2 M vs ~251 M deploy gas), measured dispute 1.58–1.91 M gas. The 10×
  on-chain target now holds below a 0.8 % dispute rate (v1: 1.2 %).
- **H3:** the registry is a deployed contract (soulbound ids, stake maintenance, escalating slash,
  registration bond, slashable delayed withdrawals; 9 tests) and a pre-registered study with **learning
  agents under imperfect detection** (p = 0.5, 0.8) supports all 4 primary tests (Holm p ≤ 3.2 × 10⁻⁷).
- **H4 v4/v4.1:** the composed proof is now **zero-knowledge** (Plonky3 hiding FRI and salted Merkle
  trees); end-to-end security 124-bit conjectured / 111-bit proven classical, ≈ 62-bit quantum under the
  conservative QROM bound; post-quantum binding under ZK costs 1.07× size and 1.10× prove time.
  **Note:** this quantum estimate is weaker than the earlier construction's. Under the same argument the v3 Winterfell proof gets ≈ 63 bits (126-bit conjectured), and the "≥ 2⁶¹⁵ quantum" figure quoted for H4 earlier described only the lattice commitment, not the proof. Zero-knowledge was gained; about 2 bits of conjectured security were lost.

## Cross-cutting findings

1. **One post-quantum proof for a whole CBDC transaction decision.** A single STARK proves four things:
   - the trained H1 risk model's inference, with the score kept private;
   - the risk flag;
   - the H3 agent's decision, with the flag as a violation condition;
   - that the amount decided on is the amount inside the post-quantum SIS commitment.

   This costs 1.15× size, 1.28× prove and 1.77× verify versus the same proof without post-quantum binding. A decision made on a different amount than the committed one passes the classical proof but fails the post-quantum one. Details: [`h4-pqc-stark/docs/h4_composed.md`](h4-pqc-stark/docs/h4_composed.md).
2. **False-positive targets for federated AML are gameable.** At the default threshold, FedAvg "meets" the ≥ 20% fewer-false-positives criterion at every level. At matched recall it fails at every fully evaluable level, and with ample labels it is significantly worse. FP targets must be stated at a fixed recall. Details: [`h2-federated-aml/README.md`](h2-federated-aml/README.md#matched-recall-test-the-false-positive-criterion-is-gameable-finding-b-pre-registered).
3. **Durable agent liability.** Flat stakes wear out as agents are slashed to zero (19% → 45% violations vs control 50%), and free identity resets nullify escalating penalties. Stake maintenance and operator-bound history fix both (pre-registered, z = −13.1 and −18.5); a registration bond blocks resets exactly at the analytic break-even B* = 14. Details: [`h3-abt/README.md`](h3-abt/README.md).
4. **Post-quantum overhead law (post-hoc).** The commitment adds a near-constant cost: about +12 ms verify, +28 ms prove and +8.4 KB per proof. So the ratio is about 1 + c / classical, and it falls as models grow. On the composed workload, which was not used to fit it, the law predicted size and prove time within 0.02× and underpredicted verify time (1.61× predicted, 1.77× measured). Details: [`h4-pqc-stark/README.md`](h4-pqc-stark/README.md).

Methodology notes:
- H2 v2, the H2 matched-recall test, H4 v2/v3, coverage and the composed proof had their parameters, workloads, bounds and analysis code committed before their runs. The overhead law is post-hoc. H3's majority-bar definition was set after viewing per-agent data and is labeled post-hoc.
- Superseded results stay in the repo for the record and are marked as such: H2 v1 (5 seeds, unequal budgets) and H4 v1 (unsound circuit).

## How These 4 Connect

H1 builds the fraud/risk detector. H3 builds the agents that act on what H1 flags — H1 predicts, H3 decides and is held accountable for that decision. H2 makes the detection in H1 possible across multiple banks without sharing private data. H4 makes the cryptography underneath H1 (and eventually H3) safe against future quantum computers. None of the 4 tracks share code — each is a standalone prototype answering its own falsifiable question — but together they answer: can a CBDC system detect fraud accurately and privately (H1+H2), hold autonomous agents accountable for what they do about it (H3), and stay secure long-term (H4)?

## Repo Rules

- `main` is the stable branch.
- Each person works on their own branch off `main` — name it `<yourname>/<what-you're-doing>`, e.g. `aman/h1-baseline`.
- Work only inside your own hypothesis folder unless coordinating with someone else first.
- Open a PR into `main` when a milestone is done (baseline, then core mechanism, etc.) — don't hold one giant branch for weeks.
- PR description should say: what you built, what number you got, pass or fail vs your target.
- Maanas reviews and merges every PR.

## Status Tracking

Each hypothesis folder has its own `README.md` — hypothesis statement, target, and current status. Keep it updated; it's the fastest way for anyone to see where a track stands without asking.
