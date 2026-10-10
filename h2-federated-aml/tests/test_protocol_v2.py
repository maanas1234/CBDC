import math

import pandas as pd

from dp_accounting import epsilon_for
from protocol_v2 import _holm, _row, aggregate


def test_epsilon_matches_closed_form_optimum():
    # min_a T*a/(2z^2) + L/(a-1) has optimum T/(2z^2) + sqrt(2TL)/z.
    t, z, delta = 40, 2.0, 1e-5
    big_l = math.log(1 / delta)
    closed = t / (2 * z * z) + math.sqrt(2 * t * big_l) / z
    assert abs(epsilon_for(t, z, delta) - closed) < 0.01


def test_epsilon_edge_cases_and_monotonicity():
    assert epsilon_for(0, 1.0) == 0.0
    assert epsilon_for(5, 0.0) == math.inf
    assert epsilon_for(40, 2.0) < epsilon_for(40, 1.0)
    assert epsilon_for(80, 1.0) > epsilon_for(40, 1.0)


def test_holm_is_monotone_and_capped():
    adjusted = _holm([0.01, 0.04, 0.03, 0.5])
    assert adjusted[0] == 0.04
    assert all(0 <= p <= 1 for p in adjusted)
    assert adjusted[3] == 1.0 or adjusted[3] >= max(adjusted[:3])


def test_row_extracts_confusion_counts():
    row = _row({"f1": 0.5, "confusion_matrix": [[90, 10], [5, 15]]}, method="fedavg")
    assert (row["true_negatives"], row["false_positives"], row["false_negatives"], row["true_positives"]) == (90, 10, 5, 15)
    assert "confusion_matrix" not in row


def _seed_rows(seed, fp_central, fp_fed):
    rows = []
    for scarcity in (1.0, 0.5):
        for method, fp in (("centralized", fp_central), ("local_only", fp_central), ("fedavg", fp_fed), ("fedavg_boundary", fp_fed)):
            rows.append({"experiment": "main_scarcity", "method": method, "scarcity": scarcity, "seed": seed, "institutions": 3, "boundary_lambda": 0.0,
                         "f1": 0.5, "pr_auc": 0.5, "roc_auc": 0.5, "precision": 0.5, "recall": 0.5, "false_positives": fp, "false_negatives": 1})
    return rows


def test_primary_criterion_detects_clear_fp_reduction(tmp_path):
    for seed in range(10):
        pd.DataFrame(_seed_rows(seed, fp_central=100 + seed, fp_fed=50 + seed)).to_csv(tmp_path / f"seed_{seed}.csv", index=False)
    cfg = {"scarcity_levels": [1.0, 0.5], "criterion": {"min_fp_reduction": 0.2, "alpha": 0.05}}
    report = aggregate(cfg, tmp_path)
    assert all(row["criterion_met"] for row in report["primary"])
    assert all(row["fp_reduction"] > 0.4 for row in report["primary"])


def test_primary_criterion_rejects_when_federated_is_worse(tmp_path):
    for seed in range(10):
        pd.DataFrame(_seed_rows(seed, fp_central=50 + seed, fp_fed=100 + seed)).to_csv(tmp_path / f"seed_{seed}.csv", index=False)
    cfg = {"scarcity_levels": [1.0, 0.5], "criterion": {"min_fp_reduction": 0.2, "alpha": 0.05}}
    report = aggregate(cfg, tmp_path)
    assert not any(row["criterion_met"] for row in report["primary"])
