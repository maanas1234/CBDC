# CBDC – AI – Blockchain Research Programme: Exhaustive Record of Every Experiment

**Repository:** github.com/maanas1234/CBDC (`main`)
**Team:** Aman Hooda (H1), Indrakshi (H2), Anjali (H3), Simran Pundir (H4). Mentor and reviewer: Maanas Tyagi.
**Source proposal:** *Architecting a Secure, Compliant, and Intelligent CBDC Ecosystem* (`docs/CBDC_AI_Blockchain_Research_Proposal.pdf`)
**Updated:** 28 Oct 2026 (includes Aman's integration work, PRs #36–#39, and the hardware integration, Part 6B, PR #43).
**Companion summary:** `docs/FULL_REPORT.md` (short version). This document is the long version.

---

## How this document is built and how to read it

This is the complete record of the programme. It covers:
- every experiment that was run, including versions later withdrawn or superseded;
- every result table;
- every pre-registration;
- every correction and every closed pull request.

Nothing that was run is left out.

**Generated tables.** Tables marked *(generated)* are produced by `docs/exhaustive/build.py` directly from the committed result files (CSV/JSON) at build time. No number in them was retyped by hand. To rebuild, run `python docs/exhaustive/build.py` from the repository root.

**Why a rebuild can differ from the committed copy.** Most of the document is generated from committed
result files and is identical on every rebuild. Five generated parts depend on when and where the build
runs:
1. **Commit count and authors** (§1) are read from `git log` at build time. The committed copy is built
   before the commit that adds it, so a rebuild on a later checkout always shows more commits.
2. **The tracked-file index** (reproducibility section) lists `git ls-files` with file sizes, so any
   added, removed or edited file changes it. (Before 20 Oct 2026 it also listed this report's own size,
   which changed on every rebuild; it now shows "(this file)".)
3. **Embedded Markdown** (the READMEs and write-ups pulled in by `md` include directives) changes whenever those
   files change.
4. **Test listings** are collected live: H2 with `pytest --collect-only`, which needs `torch` and
   `torch-geometric` installed (without them collection fails and the H2 list comes out nearly empty);
   H4 with `cargo test -- --list` in `benchmark_v2`, which needs a working Rust toolchain (an earlier
   committed copy showed "0 tests" for that reason; the correct count is 20). H3 uses `pytest` only.
5. **H3 Sybil output** is produced by running `h3-abt/run_sybil.py` (deterministic, seeded).

Rebuilding twice in a row on the same checkout and environment gives a byte-identical file.

**Hand-written text.** The narrative text was written for this document. Where a number appears in the narrative, it is quoted from a generated table or from a committed write-up, and the source is named.

**Status labels.** Every result carries one of these labels:

| Label | Meaning |
|---|---|
| **Confirmatory, pre-registered** | Parameters, bounds and analysis code were committed to git before the run; the commit is named. |
| **Exploratory** | Run without pre-registration; reported for completeness. |
| **Post-hoc** | Defined or analysed after seeing the data. |
| **Superseded** | Replaced by a later, better-designed version. Kept for the record. |
| **Withdrawn** | Found to be invalid (for example, an unsound circuit). Its numbers must not be cited. |

**Structure:**

| Part | Content |
|---|---|
| 1 | Programme: proposal, hypotheses, team, process, timeline, every PR |
| 2 | H1: verifiable off-chain inference (v1 partial proving; v2 bisection) |
| 3 | H2: federated AML under label scarcity (v1, 5-seed v1, protocol v2, matched-recall test) |
| 4 | H3: AgentBound Tokens (baseline, treatment, confirmatory, agent-level, Sybil, durable liability) |
| 5 | H4: post-quantum ZK-STARK (v1 prototypes, halt, v2, v3, model coverage, composed proof, overhead law) |
| 6 | Cross-cutting findings and the system picture |
| 6A | The integrated system (TRL 4): Besu pipeline, on-chain disputes and registry, Plonky3 proof, independent-validator run, and what was independently verified |
| 6B | Hardware integration (after the faculty review): machine resources, memory-budgeted decomposition, TPM-anchored identity, simulated TEE and offline devices |
| 7 | Corrections, deviations, withdrawn work, and what was not done |
| 8 | Reproducibility and the full artifact index |
| Appendices | Configurations, pre-registrations and original documentation, verbatim |

## Glossary

| Term | Meaning |
|---|---|
| AML / CFT | Anti-money-laundering / countering the financing of terrorism |
| CBDC | Central bank digital currency |
| Elliptic | Public Bitcoin transaction graph dataset: 203,769 transactions, 234,355 edges, 49 time steps. 4,545 transactions are labelled illicit, 42,019 licit, and the rest unknown. |
| ZKML | Zero-knowledge proofs of machine-learning inference |
| zk-OPML | Optimistic ML with zero-knowledge dispute resolution: results are assumed correct unless challenged; a challenge is settled by a targeted proof |
| EZKL | Halo2/KZG-based ZKML toolchain (version 23.0.5 used) |
| Bisection | Binary search over committed intermediate results to find the first step where two parties disagree |
| FedAvg | Federated averaging: each institution trains locally; the server averages the model weights |
| GCN | Graph convolutional network |
| DP, ε, δ | Differential privacy and its privacy-loss parameters |
| RDP | Rényi differential privacy (used here for accounting) |
| Recall / FP | Share of illicit transactions caught / number of licit transactions wrongly flagged |
| Matched recall | Comparing models at thresholds that give them the same recall |
| ABT | AgentBound Token: a non-transferable token binding an AI agent to staked collateral and a violation history |
| Slashing | Automatic confiscation of stake when a violation is detected |
| Sybil attack | Escaping penalties by creating a new identity |
| Judgment-proof | An agent with nothing left to lose: stake fully slashed, so the deterrent is gone |
| STARK | Hash-based transparent proof system; plausibly post-quantum |
| AIR | Algebraic intermediate representation: the constraint system a STARK proves |
| SIS | Short Integer Solution: lattice problem behind the commitment c = G·bits + B·r mod p |
| PQ | Post-quantum |
| RLC | Random linear combination (the v3 proof technique) |
| Winterfell | Rust STARK library (fork `bwesterb/winterfell@b964cfd`, field f23201, p = 7,340,033) |
| Holm | Holm–Bonferroni correction for multiple tests |
| Wilcoxon / Mann–Whitney | Rank-based paired / unpaired tests |
