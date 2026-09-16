"""Staked treatment simulation with ABT identity and automatic slashing.

Every agent is staked, faces the same opportunity generator as the
unstaked baseline, and uses the PR 1 `choose_action` rule. Detection
uses a separate RNG so it cannot shift the opportunity stream.

This module does not run a two-group comparison, a statistical test,
or a Sybil test, and it does not claim H3 pass/fail.
"""

from __future__ import annotations

from random import Random

from h3_abt.abt import ABTRegistry
from h3_abt.environment import iter_agent_opportunities
from h3_abt.protocol import choose_action, is_violation
from h3_abt.types import (
    Action,
    SimulationConfig,
    StepRecord,
    TreatmentResult,
)

STAKED_TREATMENT_LABEL = "STAKED TREATMENT"

# Separate from the opportunity seed so slashing draws cannot change
# the environment stream used by the unstaked baseline.
ENFORCEMENT_SEED_OFFSET = 1_000_003


def _violation_rate(total_violations: int, total_actions: int) -> float:
    if total_actions == 0:
        return 0.0
    return total_violations / total_actions


def run_staked_treatment(config: SimulationConfig) -> TreatmentResult:
    """Run the staked treatment for `config.n_steps` rounds.

    `config.n_unstaked` is ignored. Agents are registered with ABTs and
    posted `config.stake_amount` collateral.
    """
    registry = ABTRegistry()
    agent_ids = [f"staked_{index}" for index in range(config.n_staked)]
    for agent_id in agent_ids:
        registry.register(agent_id)
        if config.stake_amount > 0:
            registry.stake(agent_id, config.stake_amount)

    opportunity_rng = Random(config.seed)
    enforcement_rng = Random(config.seed + ENFORCEMENT_SEED_OFFSET)
    records: list[StepRecord] = []

    for step, agent_index, opportunity in iter_agent_opportunities(
        config, len(agent_ids), opportunity_rng
    ):
        agent_id = agent_ids[agent_index]
        state = registry.agent_state(agent_id)
        stake_before = state.stake_remaining
        action = choose_action(opportunity, state, config)
        offer_violates = is_violation(opportunity.transfer, config)
        committed = action is Action.EXECUTE and offer_violates
        detected = enforcement_rng.random() < opportunity.detection_probability
        slashed_amount = 0.0
        if committed and detected:
            event = registry.report_violation(
                agent_id,
                opportunity.transfer,
                config,
                step,
            )
            slashed_amount = event.slashed_amount

        records.append(
            StepRecord(
                seed=config.seed,
                step=step,
                agent_id=agent_id,
                is_staked=True,
                amount=opportunity.transfer.amount,
                destination=opportunity.transfer.destination,
                offer_is_policy_violation=offer_violates,
                compliant_payoff=opportunity.compliant_payoff,
                violation_payoff=opportunity.violation_payoff,
                detection_probability=opportunity.detection_probability,
                action=action,
                is_violation=committed,
                abt_id=registry.token(agent_id).token_id,
                detected=committed and detected,
                slashed_amount=slashed_amount,
                stake_before=stake_before,
                stake_remaining=registry.remaining_stake(agent_id),
            )
        )

    total_actions = len(records)
    total_violations = sum(1 for record in records if record.is_violation)
    total_slashed = sum(record.slashed_amount for record in records)
    return TreatmentResult(
        label=STAKED_TREATMENT_LABEL,
        n_agents=len(agent_ids),
        n_steps=config.n_steps,
        seed=config.seed,
        total_actions=total_actions,
        total_violations=total_violations,
        total_slashed=total_slashed,
        violation_rate=_violation_rate(total_violations, total_actions),
        records=tuple(records),
    )
