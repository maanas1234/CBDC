"""Unstaked control/baseline simulation.

Every agent is unstaked, faces the same environment generator, and uses
the PR 1 `choose_action` decision rule. This module does not create
staked agents, apply slashing, run a statistical test, or claim H3
pass/fail.
"""

from __future__ import annotations

from random import Random

from h3_abt.environment import iter_agent_opportunities
from h3_abt.protocol import choose_action, is_violation, make_unstaked_agent
from h3_abt.types import (
    Action,
    BaselineResult,
    SimulationConfig,
    StepRecord,
)

UNSTAKED_BASELINE_LABEL = "UNSTAKED CONTROL/BASELINE"


def _violation_rate(total_violations: int, total_actions: int) -> float:
    if total_actions == 0:
        return 0.0
    return total_violations / total_actions


def run_unstaked_baseline(config: SimulationConfig) -> BaselineResult:
    """Run the unstaked control/baseline for `config.n_steps` rounds.

    `config.n_staked` is ignored. Agents are created only with
    `make_unstaked_agent`.
    """
    rng = Random(config.seed)
    agents = [
        make_unstaked_agent(f"unstaked_{index}")
        for index in range(config.n_unstaked)
    ]
    records: list[StepRecord] = []

    for step, agent_index, opportunity in iter_agent_opportunities(
        config, len(agents), rng
    ):
        agent = agents[agent_index]
        action = choose_action(opportunity, agent, config)
        offer_violates = is_violation(opportunity.transfer, config)
        committed = action is Action.EXECUTE and offer_violates
        records.append(
            StepRecord(
                seed=config.seed,
                step=step,
                agent_id=agent.agent_id,
                is_staked=agent.is_staked,
                amount=opportunity.transfer.amount,
                destination=opportunity.transfer.destination,
                offer_is_policy_violation=offer_violates,
                compliant_payoff=opportunity.compliant_payoff,
                violation_payoff=opportunity.violation_payoff,
                detection_probability=opportunity.detection_probability,
                action=action,
                is_violation=committed,
                abt_id=None,
                detected=False,
                slashed_amount=0.0,
                stake_before=0.0,
                stake_remaining=0.0,
            )
        )

    total_actions = len(records)
    total_violations = sum(1 for record in records if record.is_violation)
    return BaselineResult(
        label=UNSTAKED_BASELINE_LABEL,
        n_agents=len(agents),
        n_steps=config.n_steps,
        seed=config.seed,
        total_actions=total_actions,
        total_violations=total_violations,
        violation_rate=_violation_rate(total_violations, total_actions),
        records=tuple(records),
    )
