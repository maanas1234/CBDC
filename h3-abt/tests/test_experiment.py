"""Control vs treatment experiment tests. Not confirmatory H3 results."""

from __future__ import annotations

from pathlib import Path

from h3_abt.config import load_config, parse_config
from h3_abt.experiment import run_comparison, save_results, treatment_violation_feasible
from h3_abt.stats import NOT_SUPPORTED


def _raw(**overrides) -> dict:
    data = {
        "n_staked": 2,
        "n_unstaked": 2,
        "n_steps": 5,
        "stake_amount": 100.0,
        "slash_amount": 15.0,
        "max_compliant_amount": 50.0,
        "sanctioned_destinations": ["sanctioned_0"],
        "detection_probability": 1.0,
        "tie_break": "refuse",
        "seed": 7,
        "p_over_limit": 0.5,
        "p_sanctioned": 0.2,
        "over_limit_extra": 50.0,
        "n_clean_destinations": 5,
        "compliant_payoff_min": 1.0,
        "compliant_payoff_max": 10.0,
        "violation_payoff_min": 1.0,
        "violation_payoff_max": 30.0,
        "experiment_role": "smoke_test",
    }
    data.update(overrides)
    return data


def test_control_and_treatment_wiring() -> None:
    result = run_comparison(parse_config(_raw()))
    assert result.control.group == "control"
    assert result.treatment.group == "treatment"
    assert result.control.n_agents == 2
    assert result.treatment.n_agents == 2
    assert result.control.total_actions == 10
    assert result.treatment.total_actions == 10
    groups = {row.group for row in result.observations}
    assert groups == {"control", "treatment"}
    control_ids = {
        row.agent_id for row in result.observations if row.group == "control"
    }
    treatment_ids = {
        row.agent_id for row in result.observations if row.group == "treatment"
    }
    assert control_ids == {"unstaked_0", "unstaked_1"}
    assert treatment_ids == {"staked_0", "staked_1"}


def test_raw_observations_have_required_fields() -> None:
    result = run_comparison(parse_config(_raw(n_steps=1, n_staked=1, n_unstaked=1)))
    assert len(result.observations) == 2
    for row in result.observations:
        assert row.agent_id
        assert row.step == 1
        assert row.action in {"execute", "refuse"}
        assert isinstance(row.is_violation, bool)
        assert row.stake_before >= 0.0
        assert row.stake_after >= 0.0
        assert row.amount_slashed >= 0.0


def test_same_seed_is_reproducible() -> None:
    config = parse_config(_raw(seed=42))
    first = run_comparison(config)
    second = run_comparison(config)
    assert first.observations == second.observations
    assert first.control.total_violations == second.control.total_violations
    assert first.treatment.total_violations == second.treatment.total_violations
    assert first.z_test.p_value == second.z_test.p_value
    assert first.verdict == second.verdict


def test_matched_opportunity_stream_when_counts_equal() -> None:
    result = run_comparison(parse_config(_raw(n_staked=3, n_unstaked=3, n_steps=4)))
    control = [row for row in result.observations if row.group == "control"]
    treatment = [row for row in result.observations if row.group == "treatment"]
    assert len(control) == len(treatment)
    # Same seed and equal n ⇒ same step order. Opportunity matching is
    # checked in test_treatment; here we only check parallel structure.
    assert [row.step for row in control] == [row.step for row in treatment]


def test_staked_agents_can_still_violate_when_gain_exceeds_slash() -> None:
    """Constructed economics, not an H3 result.

    Slash 20 vs gain 30 and refuse payoff 1. Treatment must be able to
    EXECUTE violating offers; this is not a hard ban.
    """
    config = parse_config(
        _raw(
            n_staked=1,
            n_unstaked=1,
            n_steps=3,
            slash_amount=20.0,
            p_over_limit=1.0,
            p_sanctioned=0.0,
            compliant_payoff_min=1.0,
            compliant_payoff_max=1.0,
            violation_payoff_min=30.0,
            violation_payoff_max=30.0,
        )
    )
    result = run_comparison(config)
    treatment_rows = [
        row for row in result.observations if row.group == "treatment"
    ]
    assert any(row.is_violation for row in treatment_rows)
    assert treatment_violation_feasible(config) is True


def test_smoke_slash_box_is_not_feasible() -> None:
    config = load_config()
    assert config.experiment_role == "smoke_test"
    assert treatment_violation_feasible(config) is False


def test_zero_observations_not_supported() -> None:
    result = run_comparison(
        parse_config(_raw(n_staked=0, n_unstaked=0, n_steps=1))
    )
    assert result.control.total_actions == 0
    assert result.treatment.total_actions == 0
    assert result.z_test.defined is False
    assert result.verdict == NOT_SUPPORTED


def test_constructed_rates_match_observation_counts() -> None:
    result = run_comparison(parse_config(_raw()))
    control_v = sum(
        1
        for row in result.observations
        if row.group == "control" and row.is_violation
    )
    treat_v = sum(
        1
        for row in result.observations
        if row.group == "treatment" and row.is_violation
    )
    assert result.control.total_violations == control_v
    assert result.treatment.total_violations == treat_v
    assert result.control.violation_rate == control_v / result.control.total_actions


def test_save_results_writes_json_and_csv(tmp_path: Path) -> None:
    result = run_comparison(parse_config(_raw(n_steps=1, n_staked=1, n_unstaked=1)))
    json_path, csv_path = save_results(result, tmp_path)
    assert json_path.is_file()
    assert csv_path.is_file()
    csv_text = csv_path.read_text(encoding="utf-8")
    assert "group,agent_id,step,action,is_violation" in csv_text
    assert "control" in csv_text
    assert "treatment" in csv_text


def test_cli_smoke_banner(capsys) -> None:
    from h3_abt.config import DEFAULT_CONFIG_PATH
    from h3_abt.experiment_cli import main

    exit_code = main(
        ["--config", str(DEFAULT_CONFIG_PATH), "--no-save"]
    )
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "SMOKE TEST" in captured.out
    assert "not that H3 has been universally proven" in captured.out
    assert "verdict:" in captured.out
    assert captured.out.count("SUPPORTED") >= 1
    p_lines = [
        line
        for line in captured.out.splitlines()
        if line.startswith("p_value")
    ]
    assert p_lines
    assert "0.000000" not in p_lines[0]
    assert "e-" in p_lines[0].lower()
