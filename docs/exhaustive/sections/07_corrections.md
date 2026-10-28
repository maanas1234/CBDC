# Part 7 — Corrections, deviations, withdrawn work, and what was not done

## 7.1 Corrections and errors, in order

| # | What happened | Effect | Resolution |
|---|---|---|---|
| 1 | H1 content committed into a misfiled folder `h1-zkopml 5` | Layout only | Moved (PR #4) |
| 2 | H1 v1 used a random split first (F1 0.7405) | Leakage via neighbour-aggregated features | Switched to the temporal split (v1 itself) |
| 3 | H1 v1 tuned its configuration and threshold using the test set (F1 0.6982) | Optimistic accuracy | v2 selects on validation only; the v2 write-up states 0.6982 is not comparable |
| 4 | H1 v1 reported a ~2.9× speedup from numbers measured on different models and settings | The ratio is not reconstructible | Recorded here (§2.1); v1 is superseded |
| 5 | H1 v2 preprocessing divided by IQR + 1e-8, giving values up to 1e9 | Numerically unstable circuits | Replaced by division by max(IQR, std) after clipping; values now within ±9.4 |
| 6 | H1 v2 write-up says multi-core was measured only at 60 blocks, but the committed `summary.json` contains multi-core values for all four depths (0.91×, 2.84×, 5.98×, 12.6×) | Documentation inconsistency; the single-core raw files are not committed | Recorded here (§2.3, §7.2). Both sets reach the same conclusion (10× only at 60 blocks). |
| 7 | H2 v1 compared methods trained for unequal budgets, without a centralized model under scarcity | The criterion was untestable | Protocol v2 |
| 8 | H2 v1 used 5 seeds: minimum two-sided p = 0.0625 | No significance possible | Protocol v2 with 10 seeds |
| 9 | H2 status was initially over-read ("federation robust to scarcity") | Overclaim | Corrected in PR #15; the floor artefact is documented |
| 10 | During the v2 sweep, a branch switch in the working tree that the sweep imported from briefly reverted `federated.py` / `model.py` | Risk of mixed code | Switched back immediately; later work used separate git worktrees. The 10-seed rerun for C4 reproduced v2's false positives exactly in 240/240 cases, so the v2 results were not affected. |
| 11 | PR #17 (client-level DP-FedAvg) duplicated PR #19's DP path | Redundancy | Closed; the accountant and the centralized-under-scarcity baseline were ported into v2 |
| 12 | H3 action-level z-test (p = 3.7e-24) is pseudo-replicated | Overstated significance | Agent-level re-analysis (PR #20): p = 1.1e-6. Cite only that. |
| 13 | H3 majority bar: control count transcribed as 6/20 | Typo | Corrected to 7/20 |
| 14 | H3 majority-bar definition fixed after seeing the data | Post-hoc | Labelled post-hoc everywhere |
| 15 | H4 v1 circuit unsound (five defects, §5.1) | Its numbers are meaningless | Withdrawn; confirmatory run halted (PR #16) |
| 16 | PR #18 claimed a fix but kept the defect and removed constraints | Would have recorded an unsound PASS | Closed without merge |
| 17 | H4 SIS security first estimated with a root-Hermite heuristic | Heuristic only | Replaced by the lattice estimator (PR #24) |
| 18 | H4: an all-constant classical trace failed Winterfell's composition-degree check ("expected … degree 15, but was 0") | Build error | Clock column added to the matmul block |
| 19 | H4 build: MSVC `LNK1104` from long paths | Build error | Short `CARGO_TARGET_DIR` |
| 20 | H4 v2 verify bottleneck: first blamed on the public-matrix evaluation (a Vandermonde attempt gave no gain) | Wasted iteration | Instrumentation showed DEEP composition; this led to v3 |
| 21 | H4 coverage: the H2 GCN was first assumed to have 165 features; it has 166 (time step included) | Circuit mismatch | Fixed (`gcn.rs` F = 166) |
| 22 | H4 coverage: the raw H2 feature box (max 289) cannot be quantized into a 23-bit field | Infeasible circuit | Declared 0.1–99.9 percentile clip, chosen on validation |
| 23 | H4 coverage: a heuristic picked scales that hurt accuracy | Fidelity loss | Scales selected by validation PR-AUC instead |
| 24 | H3 durable-liability outputs (`durable_report.json`, `durable_actions.csv`) were blocked by `h3-abt/.gitignore` (`results/*.json`, `results/*.csv`) | The README referenced files missing from the repo | Force-added in the PR that adds this document |
| 25 | H4 composed pre-registration (`h4_composed.md`) states the PQ main trace width as 219; it is 220 (12 SIS + 207 workload + 1 link accumulator) | Descriptive typo; no effect on the circuit or the timing | Corrected in this document and in `FULL_REPORT.md`; the pre-registration is left as committed |
| 26 | The first versions of `FULL_REPORT.md` and the exhaustive report quoted "≥ 2⁶¹⁵ quantum" next to the composed proof. That figure covers only the SIS commitment's binding; the proof as a whole is about 63 bits quantum (v3) or 62 bits (v4) | Overstated the quantum security of the proof | Reworded everywhere (Part 6A.5, C1); found during the review of PR #37 |
| 27 | The report title and abstract called the system "quantum-safe" | Overclaim given the estimates above | Title changed to "Post-Quantum"; abstract qualified |
| 28 | PR #36 and PR #37 were the same branch (#36 closed, #37 merged); PR #37 omitted the audit script, evidence and logs it relied on | Claims in `EVIDENCE.md` could not be checked from `main` | Added in PR #38 |
| 29 | The H1 v2.1 shared verifiers (4 verifiers, 17.2 M deploy gas instead of about 251 M) remove the proving-time gain: a disputed block step takes about as long as the whole-model proof, and a projection step is 2.8× slower | The 14.9× speedup was still quoted as if it applied to the on-chain design | H1 README, FULL_REPORT and Part 6A now state that 14.9× applies to the fixed-weights design only (PR #38) |
| 30 | The recorded `anvil_state.json` of the on-chain dispute run could not be loaded by current Foundry builds (written by 1.5.1) | The 116-transaction record was not re-checkable with a current toolchain | `verify_dispute_record.py` gained a replay mode that re-sends the original signed transactions (PR #38); reproduced independently |
| 31 | The independent-validator run (host outside the team, reviewer a team member) does not export the ledger | The reviewer's own-ledger checks are self-reported | Stated as a limit in Part 6A.6; ledger exported in PR #41 and decoded by the mentor (Besu re-execution by the reviewer only) |
| 32 | `FULL_REPORT.md`, the H1 README and the exhaustive report quoted a 10× gas break-even dispute rate of 1.2% / 1.6%, from the first (v1) gas accounting. The complete v2 accounting (challenge, opening and adjudication included; real step verifiers) gives 0.79% worst / 0.93% typical, as the invention disclosure form states | Overstated the dispute rate at which the gas target holds | Updated to 0.8% / 0.9%, with the v1 figure kept and labelled |
| 33 | The exhaustive report listed the 20 H4 `benchmark_v2` Rust tests as "0 tests" (no Rust toolchain at build time), and with a toolchain every name printed as `tests` (cut at the first colon) | The test list was missing | Fixed in `build.py` in the report update of 28 Oct 2026; the 20 names now print in full |

## 7.2 Provenance gaps that remain

- **H1 single-core raw timings** behind the headline 14.9× are not committed; only the multi-core files are.
- **H2 data** is not committed (licence and size). Results are reproducible from the PyG mirror.
- **H1 v1 code and results** exist only in git history (commit `3d6e84c^`).
- **Hardware integration (Part 6B)** has not been independently re-run. The TPMs are software TPMs, and the TEE and offline devices are simulations on one machine.

## 7.3 Deviations from pre-registrations

- **H4 bounds:** first written as post-hoc bounds for v1, then reused unchanged as the pre-registered bounds for every later run.
- **H4 v2:** the dense-layer workload and the analysis script were added by amendment before the run (`ee6519b`).
- **H4 v3:** designed after v2's miss; disclosed in `h4_v3.md`, including the exploratory development timings.
- **H2 matched recall:** the 1% level was not evaluable in 5 of 10 seeds. As pre-registered, it does not count toward the verdict.
- **H3 durable:** the flat-vs-control late-window test was predicted "not significant or much weaker". It came out much weaker (gap 31 pp → 5 pp) but still significant (p = 0.003). Reported as such.

## 7.4 Proposal items not attempted

| Proposal item | Status |
|---|---|
| Deep-RL monetary policy engine; Reverse-Kelly AMM | Not attempted (outside the 2–3 month scope) |
| ExpProof-style verifiable explanations bound to the ABT | Not attempted |
| Blockchain orchestration of FL; secure multi-party aggregation; encrypted gradients | Not attempted (FedAvg is simulated in-process) |
| On-chain ABT contract (Solidity) | Not built in the original programme; built later as `LiabilityRegistry` (Part 6A) |
| Settlement-layer integration of the PQ proofs | Not attempted in the original programme; a lab-scale integration on a Besu QBFT ledger was added later (Part 6A). Not a production or central-bank ledger |
| Real VASP institutions | Simulated by graph partitioning |
| Transaction-level DP | Not attempted; only institution-level DP |
| Hiding (zero-knowledge) commitments in H4 | Not claimed; binding only |
