# H2 protocol v2 — pre-registration

Committed before any v2 run. Config: `configs/protocol_v2.yaml`. Code: `src/protocol_v2.py`.

## Why v2

The v1 sweep (5 seeds, `results/scarcity_*.csv`) has three problems:

1. **No significance was possible.** A paired two-sided Wilcoxon test with 5 seeds has a minimum p-value of 2/2⁵ = 0.0625 > 0.05. "Nothing significant" in v1 is a design limit, not evidence of no effect.
2. **Unequal training.** Centralized trained 100 epochs with best-validation selection. FedAvg trained 10 rounds × 1 local epoch with no selection, and was still improving at 80 rounds (val F1 0.40 → 0.51 for seed 42). Local-only had no selection either.
3. **Wrong comparator.** The original H2 criterion compares federated against a centralized baseline under scarcity. v1 compares against local-only, and centralized exists only at full labels for one seed.

## Protocol

- 10 seeds (42–51). Minimum two-sided paired Wilcoxon p ≈ 0.002.
- Same GCN for all methods. Budget 200 epochs each: FedAvg 40 rounds × 5 local epochs, local-only 200 epochs per institution, centralized 200 epochs.
- Every method keeps its best checkpoint by validation F1 (global validation split; local-only uses each institution's validation nodes). Test set is touched once, after selection.
- **Centralized baseline = pooled training on the exact scarce label mask the federated run uses** (same partition, same per-institution scarcity sampling). The only difference is the data boundary.
- Decision threshold 0.5 for all methods.

## Primary test (original H2)

At each scarcity level s ∈ {1.0, 0.5, 0.2, 0.1, 0.05, 0.01}:
- Outcome: test-set false positives (licit transactions flagged illicit).
- FP reduction = (mean FP_centralized − mean FP_fedavg) / mean FP_centralized.
- Test: one-sided paired Wilcoxon over seeds, H1: FP_fedavg < FP_centralized. Holm correction across the 6 levels.
- **Criterion met at level s** iff FP reduction ≥ 20% **and** Holm-adjusted p < 0.05.
- H2 (original) is supported if the criterion is met at one or more scarcity levels below 1.0. It is reported per level either way.

## Secondary and refined (exploratory, no correction)

- Two-sided paired Wilcoxon on F1, PR-AUC, and false positives: fedavg vs centralized, fedavg vs local-only, fedavg_boundary vs fedavg.
- Refined H2 (boundary channel mitigates scarcity): F1 degradation from s = 1.0, boundary vs fedavg, one-sided.
- Lambda ablation and institution-count ablation at s = 0.1, for description only.

## Privacy

- Mechanism: `src/privacy.py`, institution-level. Clip each institution's update to C = 1.5 (about the observed median update norm of 1.6 under this budget, measured on training only), then add N(0, (zC)²) per institution per round.
- z ∈ {0.001, 0.01, 0.1, 1.0}, at s = 1.0, boundary channel off (λ = 0).
- ε from RDP composition over 40 rounds, δ = 1e-5 (`src/dp_accounting.py`).
- The guarantee is institution-level, model-update channel only, full participation. It does not cover per-transaction privacy, boundary embeddings, or the FedAvg sample-count weights. Round selection uses the server-held validation split.
- Reported as a privacy–utility curve. No pass/fail threshold on ε is pre-set, because the original hypothesis named a target ε without a value.
