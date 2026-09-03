# H2 — Federated AML Detection Under Label Scarcity

**Owner:** Indrakshi

**Exact hypothesis (original proposal):** A blockchain-orchestrated Federated Learning framework trained across simulated multi-institution data silos will achieve a statistically significant reduction in false-positive AML flags (target: ≥20 percent) relative to a centralized baseline trained on the same label-scarce distribution (e.g., the Elliptic dataset's 2 percent illicit label rate), while formally bounding PII leakage via differential privacy guarantees (target ε).

**Refined hypothesis (proposed by Indrakshi, pending team sign-off):** Federated cross-institutional AML detection performance degrades disproportionately as per-institution labeled illicit examples become scarce, and this degradation can be partially mitigated — without weakening privacy guarantees — by leveraging the existing boundary-embedding exchange channel for label-free signal propagation across institutional boundaries, rather than relying solely on each bank's local supervised loss.

**In simple words:** Banks want to catch fraud together without sharing customer data. The question is whether they can also use the “metadata” they already exchange to make up for the fact that each bank individually has very few labeled fraud examples.

**Target:** ≥20% fewer false-positive fraud flags vs a single bank training alone.

**Status:** Literature review done (Weber 2019, Bellei 2024, Commey 2026). Implementation not started.

## What goes here

- Elliptic dataset loading + centralized baseline model
- Simulated multi-institution split (3+ banks)
- Federated learning pipeline (e.g. Flower) + differential privacy (e.g. Opacus)
- Comparison of false-positive rate: federated vs centralized
