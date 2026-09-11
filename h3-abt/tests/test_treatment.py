"""Staked treatment simulation tests. Not H3 experimental results."""

from __future__ import annotations

from h3_abt.config import load_config, parse_config
from h3_abt.protocol import choose_action, is_violation, make_staked_agent
from h3_abt.simulation import run_unstaked_baseline
from h3_abt.treatment import STAKED_TREATMENT_LABEL, run_staked_treatment
from h3_abt.types import Action, AgentState, Opportunity, Transfer


def _raw(**overrides) -> dict:
    data = {
        "n_staked": 2,
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


def test_treatment_label_and_staked_only() -> None:
    result = run_staked_treatment(parse_config(_raw()))
    assert result.label == STAKED_TREATMENT_LABEL
    assert result.n_agents == 2
    assert result.n_steps == 5
    assert result.total_actions == 10
    assert all(record.is_staked is True for record in result.records)
    assert {record.agent_id for record in result.records} == {
        "staked_0",
        "staked_1",
    }
    assert {record.abt_id for record in result.records} == {
        "abt_staked_0",
        "abt_staked_1",
    }


def test_n_unstaked_is_ignored() -> None:
    result = run_staked_treatment(parse_config(_raw(n_unstaked=99, n_staked=3)))
    assert result.n_agents == 3
    assert result.total_actions == 15


def test_same_seed_is_reproducible() -> None:
    config = parse_config(_raw(seed=42))
    first = run_staked_treatment(config)
    second = run_staked_treatment(config)
    assert first.records == second.records
    assert first.total_violations == second.total_violations
    assert first.total_slashed == second.total_slashed


def test_actions_come_from_choose_action_with_current_stake() -> None:
    config = parse_config(_raw())
    result = run_staked_treatment(config)
    for record in result.records:
        agent = AgentState(
            agent_id=record.agent_id,
            is_staked=True,
            stake_remaining=record.stake_before,
        )
        expected = choose_action(_opportunity(record), agent, config)
        assert record.action is expected
        offer_violates = is_violation(
            Transfer(record.amount, record.destination), config
        )
        assert record.offer_is_policy_violation is offer_violates
        assert record.is_violation is (
            record.action is Action.EXECUTE and offer_violates
        )


def test_large_slash_deters_violation_on_constructed_payoffs() -> None:
    """Constructed economics, not an H3 result.

    Every offer is over-limit, private gain is 30, refuse pays 1, slash
    is 100 with certain detection. choose_action must REFUSE.
    """
    config = parse_config(
        _raw(
            n_staked=3,
            n_steps=4,
            stake_amount=100.0,
            slash_amount=100.0,
            p_over_limit=1.0,
            p_sanctioned=0.0,
            compliant_payoff_min=1.0,
            compliant_payoff_max=1.0,
            violation_payoff_min=30.0,
            violation_payoff_max=30.0,
        )
    )
    result = run_staked_treatment(config)
    assert result.total_actions == 12
    assert result.total_violations == 0
    assert result.total_slashed == 0.0
    assert all(record.action is Action.REFUSE for record in result.records)
    assert all(record.stake_remaining == 100.0 for record in result.records)


def test_zero_slash_does_not_deter_on_constructed_payoffs() -> None:
    """Same offers as the deterrent case, but slash_amount=0.

    Staked agents still use choose_action; with no slash term they
    execute. Violations are not hard-coded by group label.
    """
    config = parse_config(
        _raw(
            n_staked=3,
            n_steps=4,
            stake_amount=100.0,
            slash_amount=0.0,
            p_over_limit=1.0,
            p_sanctioned=0.0,
            compliant_payoff_min=1.0,
            compliant_payoff_max=1.0,
            violation_payoff_min=30.0,
            violation_payoff_max=30.0,
        )
    )
    result = run_staked_treatment(config)
    assert result.total_violations == 12
    assert result.total_slashed == 0.0
    assert all(record.action is Action.EXECUTE for record in result.records)
    assert all(record.stake_remaining == 100.0 for record in result.records)


def test_detected_violation_slashes_and_caps_at_zero() -> None:
    config = parse_config(
        _raw(
            n_staked=1,
            n_steps=3,
            stake_amount=50.0,
            slash_amount=20.0,
            p_over_limit=1.0,
            p_sanctioned=0.0,
            detection_probability=1.0,
            compliant_payoff_min=1.0,
            compliant_payoff_max=1.0,
            violation_payoff_min=30.0,
            violation_payoff_max=30.0,
        )
    )
    result = run_staked_treatment(config)
    remaining = [record.stake_remaining for record in result.records]
    slashed = [record.slashed_amount for record in result.records]
    assert remaining[0] == 30.0
    assert remaining[1] == 10.0
    assert remaining[2] == 0.0
    assert slashed == [20.0, 20.0, 10.0]
    assert all(record.stake_remaining >= 0.0 for record in result.records)
    assert all(record.is_violation is True for record in result.records)
    assert all(record.detected is True for record in result.records)


def test_same_environment_stream_as_unstaked_baseline() -> None:
    config = parse_config(_raw(n_staked=3, n_unstaked=3, n_steps=5, seed=11))
    control = run_unstaked_baseline(config)
    treatment = run_staked_treatment(config)
    assert len(control.records) == len(treatment.records)
    for left, right in zip(control.records, treatment.records, strict=True):
        assert left.step == right.step
        assert left.amount == right.amount
        assert left.destination == right.destination
        assert left.compliant_payoff == right.compliant_payoff
        assert left.violation_payoff == right.violation_payoff
        assert left.offer_is_policy_violation == right.offer_is_policy_violation


def test_make_staked_agent_matches_initial_registry_state() -> None:
    config = parse_config(_raw(stake_amount=75.0, n_staked=1, n_steps=1))
    result = run_staked_treatment(config)
    agent = make_staked_agent("staked_0", config)
    assert result.records[0].stake_before == agent.stake_remaining
    assert agent.is_staked is True


def test_default_smoke_config_runs_and_is_labeled() -> None:
    result = run_staked_treatment(load_config())
    assert result.label == STAKED_TREATMENT_LABEL
    assert result.n_agents == 3
    assert result.n_steps == 20
    assert result.total_actions == 60
    assert result.seed == 42
    assert 0.0 <= result.violation_rate <= 1.0
    assert result.total_slashed >= 0.0


def test_cli_summary_is_labeled_smoke_test(capsys) -> None:
    from h3_abt.config import DEFAULT_CONFIG_PATH
    from h3_abt.treatment_cli import format_treatment_report, main

    result = run_staked_treatment(parse_config(_raw(n_staked=1, n_steps=1)))
    text = format_treatment_report(result)
    assert "STAKED TREATMENT (SMOKE TEST)" in text
    assert "not a confirmatory H3 experiment" in text

    exit_code = main(["--config", str(DEFAULT_CONFIG_PATH)])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "STAKED TREATMENT (SMOKE TEST)" in captured.out
    assert "not a confirmatory H3 experiment" in captured.out
