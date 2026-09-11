"""Unstaked baseline simulation tests. Not H3 experimental results."""

from __future__ import annotations

from h3_abt.config import load_config, parse_config
from h3_abt.protocol import choose_action, is_violation, make_unstaked_agent
from h3_abt.simulation import UNSTAKED_BASELINE_LABEL, run_unstaked_baseline
from h3_abt.types import Action, Opportunity, Transfer


def _raw(**overrides) -> dict:
    data = {
        "n_staked": 99,
        "n_unstaked": 2,
        "n_steps": 5,
        "stake_amount": 100.0,
        "slash_amount": 100.0,
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
    }
    data.update(overrides)
    return data


def _opportunity(record) -> Opportunity:
    return Opportunity(
        transfer=Transfer(amount=record.amount, destination=record.destination),
        compliant_payoff=record.compliant_payoff,
        violation_payoff=record.violation_payoff,
        detection_probability=record.detection_probability,
    )


def test_baseline_label_and_unstaked_only() -> None:
    result = run_unstaked_baseline(parse_config(_raw()))
    assert result.label == UNSTAKED_BASELINE_LABEL
    assert result.n_agents == 2
    assert result.n_steps == 5
    assert result.total_actions == 10
    assert all(record.is_staked is False for record in result.records)
    assert {record.agent_id for record in result.records} == {
        "unstaked_0",
        "unstaked_1",
    }


def test_n_staked_is_ignored() -> None:
    result = run_unstaked_baseline(parse_config(_raw(n_staked=99, n_unstaked=3)))
    assert result.n_agents == 3
    assert result.total_actions == 15


def test_same_seed_is_reproducible() -> None:
    config = parse_config(_raw(seed=42))
    first = run_unstaked_baseline(config)
    second = run_unstaked_baseline(config)
    assert first.records == second.records
    assert first.total_violations == second.total_violations
    assert first.violation_rate == second.violation_rate


def test_actions_come_from_choose_action() -> None:
    config = parse_config(_raw())
    result = run_unstaked_baseline(config)
    for record in result.records:
        agent = make_unstaked_agent(record.agent_id)
        expected = choose_action(_opportunity(record), agent, config)
        assert record.action is expected
        offer_violates = is_violation(
            Transfer(record.amount, record.destination), config
        )
        assert record.offer_is_policy_violation is offer_violates
        assert record.is_violation is (
            record.action is Action.EXECUTE and offer_violates
        )


def test_high_private_gain_on_violating_offers_is_executed() -> None:
    """Constructed economics, not an H3 result.

    Every offer is over-limit and violation_payoff > compliant_payoff.
    Unstaked expected slash is 0, so choose_action must EXECUTE.
    """
    config = parse_config(
        _raw(
            n_unstaked=3,
            n_steps=4,
            p_over_limit=1.0,
            p_sanctioned=0.0,
            compliant_payoff_min=1.0,
            compliant_payoff_max=1.0,
            violation_payoff_min=10.0,
            violation_payoff_max=10.0,
        )
    )
    result = run_unstaked_baseline(config)
    assert result.total_actions == 12
    assert result.total_violations == 12
    assert result.violation_rate == 1.0
    assert all(record.action is Action.EXECUTE for record in result.records)
    assert all(record.is_violation is True for record in result.records)


def test_low_private_gain_on_violating_offers_is_refused() -> None:
    """Constructed economics, not an H3 result.

    Every offer is over-limit but refusal pays more, so unstaked agents
    still refuse. Violations are not hard-coded by step index.
    """
    config = parse_config(
        _raw(
            n_unstaked=3,
            n_steps=4,
            p_over_limit=1.0,
            p_sanctioned=0.0,
            compliant_payoff_min=10.0,
            compliant_payoff_max=10.0,
            violation_payoff_min=1.0,
            violation_payoff_max=1.0,
        )
    )
    result = run_unstaked_baseline(config)
    assert result.total_actions == 12
    assert result.total_violations == 0
    assert result.violation_rate == 0.0
    assert all(record.action is Action.REFUSE for record in result.records)
    assert all(record.offer_is_policy_violation is True for record in result.records)


def test_violation_rate_formula() -> None:
    config = parse_config(_raw(n_unstaked=1, n_steps=8, seed=1))
    result = run_unstaked_baseline(config)
    counted = sum(1 for record in result.records if record.is_violation)
    assert result.total_violations == counted
    assert result.total_actions == 8
    assert result.violation_rate == counted / 8


def test_zero_agents_has_zero_rate() -> None:
    result = run_unstaked_baseline(parse_config(_raw(n_unstaked=0, n_steps=3)))
    assert result.total_actions == 0
    assert result.total_violations == 0
    assert result.violation_rate == 0.0
    assert result.records == ()


def test_default_smoke_config_runs_and_is_labeled() -> None:
    result = run_unstaked_baseline(load_config())
    assert result.label == UNSTAKED_BASELINE_LABEL
    assert result.n_agents == 3
    assert result.n_steps == 20
    assert result.total_actions == 60
    assert result.seed == 42
    assert 0.0 <= result.violation_rate <= 1.0


def test_cli_summary_is_labeled_smoke_test(capsys) -> None:
    from h3_abt.baseline import format_baseline_report, main
    from h3_abt.config import DEFAULT_CONFIG_PATH

    result = run_unstaked_baseline(parse_config(_raw(n_unstaked=1, n_steps=1)))
    text = format_baseline_report(result)
    assert "UNSTAKED CONTROL/BASELINE (SMOKE TEST)" in text
    assert "not a confirmatory H3 experiment" in text

    exit_code = main(["--config", str(DEFAULT_CONFIG_PATH)])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "UNSTAKED CONTROL/BASELINE (SMOKE TEST)" in captured.out
    assert "not a confirmatory H3 experiment" in captured.out
