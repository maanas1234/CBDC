"""Protocol unit tests. Constructed examples, not an H3 experiment."""

from __future__ import annotations

from h3_abt.config import load_config
from h3_abt.protocol import (
    choose_action,
    expected_payoff_execute,
    expected_slash,
    is_violation,
    make_staked_agent,
    make_unstaked_agent,
)
from h3_abt.types import Action, Opportunity, TieBreak, Transfer


def _config(**overrides):
    data = load_config()
    if not overrides:
        return data
    return data.__class__(**{**data.__dict__, **overrides})


def test_over_limit_amount_is_a_violation() -> None:
    config = _config()
    transfer = Transfer(amount=50.01, destination="merchant_a")
    assert is_violation(transfer, config) is True


def test_sanctioned_destination_is_a_violation() -> None:
    config = _config()
    transfer = Transfer(amount=1.0, destination="sanctioned_0")
    assert is_violation(transfer, config) is True


def test_compliant_transfer_is_not_a_violation() -> None:
    config = _config()
    transfer = Transfer(amount=50.0, destination="merchant_a")
    assert is_violation(transfer, config) is False


def test_unstaked_expected_slash_is_zero() -> None:
    agent = make_unstaked_agent("control_0")
    assert expected_slash(agent, slash_amount=100.0, detection_probability=1.0) == 0.0


def test_staked_expected_slash_uses_remaining_stake() -> None:
    config = _config(stake_amount=40.0)
    agent = make_staked_agent("treat_0", config)
    assert expected_slash(agent, slash_amount=100.0, detection_probability=1.0) == 40.0


def test_zero_remaining_stake_removes_deterrent() -> None:
    config = _config(stake_amount=0.0)
    agent = make_staked_agent("treat_empty", config)
    assert expected_slash(agent, slash_amount=100.0, detection_probability=1.0) == 0.0


def test_compliant_execute_ignores_slash() -> None:
    config = _config()
    opportunity = Opportunity(
        transfer=Transfer(amount=10.0, destination="merchant_a"),
        compliant_payoff=5.0,
        violation_payoff=99.0,
        detection_probability=1.0,
    )
    staked = make_staked_agent("treat_0", config)
    unstaked = make_unstaked_agent("control_0")
    assert expected_payoff_execute(opportunity, staked, config) == 5.0
    assert expected_payoff_execute(opportunity, unstaked, config) == 5.0


def test_same_opportunity_stake_can_change_choice() -> None:
    """Incentive-responsiveness of the decision rule, not an experiment.

    Constructed payoffs: private gain from violating is 30; slash is 100
    with certain detection. Unstaked expected payoff is 30; staked is -70.
    Compliant/refuse payoff is 1. The same function must then refuse for
    the staked agent and execute for the unstaked agent.
    """
    config = _config(slash_amount=100.0, detection_probability=1.0)
    opportunity = Opportunity(
        transfer=Transfer(amount=80.0, destination="merchant_a"),
        compliant_payoff=1.0,
        violation_payoff=30.0,
        detection_probability=1.0,
    )
    staked = make_staked_agent("treat_0", config)
    unstaked = make_unstaked_agent("control_0")

    assert choose_action(opportunity, staked, config) is Action.REFUSE
    assert choose_action(opportunity, unstaked, config) is Action.EXECUTE


def test_tie_defaults_to_refuse() -> None:
    config = _config(slash_amount=0.0, tie_break=TieBreak.REFUSE)
    opportunity = Opportunity(
        transfer=Transfer(amount=80.0, destination="merchant_a"),
        compliant_payoff=10.0,
        violation_payoff=10.0,
        detection_probability=1.0,
    )
    agent = make_unstaked_agent("control_0")
    assert choose_action(opportunity, agent, config) is Action.REFUSE


def test_tie_can_be_configured_to_execute() -> None:
    config = _config(slash_amount=0.0, tie_break=TieBreak.EXECUTE)
    opportunity = Opportunity(
        transfer=Transfer(amount=80.0, destination="merchant_a"),
        compliant_payoff=10.0,
        violation_payoff=10.0,
        detection_probability=1.0,
    )
    agent = make_unstaked_agent("control_0")
    assert choose_action(opportunity, agent, config) is Action.EXECUTE
