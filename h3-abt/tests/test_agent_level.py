from h3_abt.agent_level import analyze, mann_whitney_less, per_agent_rates, permutation_less


def _rows(group, agent, violations, actions):
    return [{"group": group, "agent_id": agent, "is_violation": str(i < violations)} for i in range(actions)]


def test_per_agent_rates_counts_each_agent_once():
    rows = _rows("control", "a", 3, 10) + _rows("control", "b", 1, 10) + _rows("treatment", "c", 0, 5)
    rates = per_agent_rates(rows)
    assert sorted(rates["control"]) == [0.1, 0.3]
    assert rates["treatment"] == [0.0]


def test_mann_whitney_detects_clear_separation():
    u, z, p = mann_whitney_less([0.1, 0.2, 0.15, 0.05, 0.12], [0.6, 0.7, 0.65, 0.8, 0.75])
    assert u == 0
    assert p < 0.01


def test_mann_whitney_identical_groups_give_p_one_half():
    _, z, p = mann_whitney_less([0.3, 0.3, 0.3], [0.3, 0.3, 0.3])
    assert z == 0.0 and abs(p - 0.5) < 1e-9


def test_permutation_is_deterministic_and_bounded():
    a, b = [0.1, 0.2, 0.3], [0.7, 0.8, 0.9]
    p1 = permutation_less(a, b, 2000, seed=7)
    assert p1 == permutation_less(a, b, 2000, seed=7)
    assert 0 < p1 <= 1
    assert permutation_less(b, a, 2000, seed=7) > 0.9


def test_analyze_reports_majority_bar_per_group():
    rows = []
    for i in range(4):
        rows += _rows("treatment", f"t{i}", 1, 10)
        rows += _rows("control", f"c{i}", 8, 10)
    result = analyze(rows, permutations=500, seed=1)
    assert result.majority_bar_treatment == 4
    assert result.majority_bar_control == 0
    assert result.mean_difference < 0
