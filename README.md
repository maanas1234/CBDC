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
| [`h1-zkopml/`](h1-zkopml) | H1 — Verifiable Off-Chain Inference | Aman | Only prove the disputed part of an AI decision, not the whole thing, when challenged | ≥10x faster/cheaper than proving the whole model, ≤1pp accuracy drop |
| [`h2-federated-aml/`](h2-federated-aml) | H2 — Federated AML Detection | Indrakshi | Banks train fraud-detection AI together without sharing raw customer data | ≥20% fewer false-positive fraud flags vs a single bank alone |
| [`h3-abt/`](h3-abt) | H3 — Cryptoeconomic Liability (AgentBound Tokens) | Anjali | AI agents put down a financial stake; break a rule, lose the stake automatically | Staked agents violate rules statistically significantly less than unstaked agents |
| [`h4-pqc-stark/`](h4-pqc-stark) | H4 — Post-Quantum ZK Proof Feasibility | Simran | Swap in quantum-resistant proof math, check it doesn't get impractically slow/big | Overhead vs classical proof system stays within an agreed bound |

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
