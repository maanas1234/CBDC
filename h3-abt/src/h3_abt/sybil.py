"""Sybil / identity-reset probe of the in-simulation ABT registry.

The registry binds ABT, stake, and violation history to an `agent_id`
string only. It has no logical-operator, hardware, or real-world identity
link. This module tests that actual mechanism. It does not invent an
on-chain identity graph and does not change the control-vs-treatment
z-test.
"""

from __future__ import annotations

from h3_abt.abt import ABTRegistry
from h3_abt.protocol import is_violation
from h3_abt.types import (
    SimulationConfig,
    SybilOutcome,
    SybilResult,
    Transfer,
)

SYBIL_LABEL = "SYBIL IDENTITY-RESET"
ORIGINAL_IDENTITY = "logical_agent_0"
RESET_IDENTITY = "logical_agent_0_reset"

_INTERPRETATION = (
    "The in-simulation ABT registry keys accounts by agent_id string. "
    "Non-transferability blocks moving the original ABT to a new id, "
    "but a new string can register, receive a new ABT, post fresh stake, "
    "and start with empty history. Previous liability stays on the old "
    "id only. There is no logical-agent binding, so a penalized operator "
    "can reset identity. Outcome is SYBIL_SUCCEEDED. This result is "
    "independent of the control-vs-treatment statistical test and is "
    "not a claim that H3 is proven."
)


def _violating_transfer(config: SimulationConfig) -> Transfer:
    return Transfer(
        amount=config.max_compliant_amount + 1.0,
        destination="merchant_a",
    )


def run_sybil_identity_reset(config: SimulationConfig) -> SybilResult:
    """Run one deterministic identity-reset attempt against ABTRegistry."""
    registry = ABTRegistry()
    original_token = registry.register_and_stake(
        ORIGINAL_IDENTITY, config.stake_amount
    )
    stake_before = registry.remaining_stake(ORIGINAL_IDENTITY)
    transfer = _violating_transfer(config)
    if not is_violation(transfer, config):
        raise RuntimeError("Sybil fixture transfer must be a policy violation")
    registry.report_violation(ORIGINAL_IDENTITY, transfer, config, step=1)
    original_history = registry.history(ORIGINAL_IDENTITY)
    stake_after = registry.remaining_stake(ORIGINAL_IDENTITY)

    new_token = registry.register(RESET_IDENTITY)
    new_stake = registry.stake(RESET_IDENTITY, config.stake_amount)
    new_history = registry.history(RESET_IDENTITY)

    fresh_abt = new_token.token_id != original_token.token_id
    fresh_stake = new_stake == config.stake_amount
    bypassed = (
        len(new_history) == 0
        and fresh_abt
        and fresh_stake
        and len(original_history) >= 1
    )
    return SybilResult(
        label=SYBIL_LABEL,
        seed=config.seed,
        original_identity=ORIGINAL_IDENTITY,
        original_abt_id=original_token.token_id,
        original_stake_before=stake_before,
        slash_amount=min(config.slash_amount, stake_before),
        original_stake_after=stake_after,
        original_violation_count=len(original_history),
        original_history=original_history,
        new_identity=RESET_IDENTITY,
        new_registration_succeeded=True,
        fresh_abt_obtained=fresh_abt,
        new_abt_id=new_token.token_id,
        fresh_stake_obtained=fresh_stake,
        new_stake=new_stake,
        new_violation_count=len(new_history),
        previous_liability_bypassed=bypassed,
        logical_agent_binding_exists=False,
        outcome=(
            SybilOutcome.SYBIL_SUCCEEDED
            if bypassed
            else SybilOutcome.SYBIL_BLOCKED
        ),
        interpretation=_INTERPRETATION,
    )
