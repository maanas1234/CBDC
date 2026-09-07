"""H3 experimental protocol primitives.

This module defines:
1. A machine-checkable violation rule.
2. An expected-payoff decision rule that includes stake/slash.
3. One code path for treatment and control; only `is_staked` changes
   the slash term.

It does not run a multi-agent experiment and does not produce H3 results.
"""

from __future__ import annotations

from h3_abt.types import (
    Action,
    AgentState,
    Opportunity,
    SimulationConfig,
    TieBreak,
    Transfer,
)


def is_violation(transfer: Transfer, config: SimulationConfig) -> bool:
    """Return True iff executing `transfer` breaks the coded policy.

    A transfer is a violation if either:
    - `transfer.amount` is greater than `config.max_compliant_amount`, or
    - `transfer.destination` is in `config.sanctioned_destinations`.

    The check is deterministic. No human oracle is required.
    """
    if transfer.amount > config.max_compliant_amount:
        return True
    return transfer.destination in config.sanctioned_destinations


def expected_slash(
    agent: AgentState,
    slash_amount: float,
    detection_probability: float,
) -> float:
    """Expected slash if the agent executes a detected violation.

    Control (unstaked) agents always get 0. Treatment agents get
    `detection_probability * min(slash_amount, stake_remaining)`.
    A fully slashed staked agent therefore has no remaining deterrent
    until they re-stake (later work).
    """
    if not agent.is_staked:
        return 0.0
    if agent.stake_remaining <= 0:
        return 0.0
    return detection_probability * min(slash_amount, agent.stake_remaining)


def expected_payoff_execute(
    opportunity: Opportunity,
    agent: AgentState,
    config: SimulationConfig,
) -> float:
    """Expected payoff of executing the offered transfer."""
    if not is_violation(opportunity.transfer, config):
        return opportunity.compliant_payoff
    return opportunity.violation_payoff - expected_slash(
        agent,
        config.slash_amount,
        opportunity.detection_probability,
    )


def expected_payoff_refuse(opportunity: Opportunity) -> float:
    """Expected payoff of refusing the offered transfer."""
    return opportunity.compliant_payoff


def choose_action(
    opportunity: Opportunity,
    agent: AgentState,
    config: SimulationConfig,
) -> Action:
    """Choose EXECUTE or REFUSE by comparing expected payoffs.

    Treatment and control call this same function. The only group
    difference is `agent.is_staked` (and the stake it implies).
    """
    execute_payoff = expected_payoff_execute(opportunity, agent, config)
    refuse_payoff = expected_payoff_refuse(opportunity)
    if execute_payoff > refuse_payoff:
        return Action.EXECUTE
    if refuse_payoff > execute_payoff:
        return Action.REFUSE
    if config.tie_break is TieBreak.EXECUTE:
        return Action.EXECUTE
    return Action.REFUSE


def make_staked_agent(agent_id: str, config: SimulationConfig) -> AgentState:
    """Treatment-group agent: same logic, stake posted."""
    return AgentState(
        agent_id=agent_id,
        is_staked=True,
        stake_remaining=config.stake_amount,
    )


def make_unstaked_agent(agent_id: str) -> AgentState:
    """Control-group agent: same logic, no stake."""
    return AgentState(
        agent_id=agent_id,
        is_staked=False,
        stake_remaining=0.0,
    )
