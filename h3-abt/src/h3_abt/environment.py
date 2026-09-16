"""Shared opportunity generator for the H3 testbed.

This module draws *candidate transfers and payoffs*. It does not decide
whether an agent violates. A violation is recorded only if `choose_action`
returns EXECUTE on a policy-violating transfer.
"""

from __future__ import annotations

from collections.abc import Iterator
from random import Random

from h3_abt.types import Opportunity, SimulationConfig, Transfer

_OVER_LIMIT_FLOOR = 0.01


def _draw_closed(rng: Random, low: float, high: float) -> float:
    if high < low:
        raise ValueError("high must be >= low")
    if high == low:
        return low
    return rng.uniform(low, high)


def sample_opportunity(rng: Random, config: SimulationConfig) -> Opportunity:
    """Draw one opportunity from the configured environment.

    All agents use this same generator. Randomness comes only from `rng`.
    """
    over_limit = rng.random() < config.p_over_limit
    sanctioned = rng.random() < config.p_sanctioned

    if over_limit:
        extra = max(config.over_limit_extra, _OVER_LIMIT_FLOOR)
        amount = config.max_compliant_amount + _draw_closed(
            rng, _OVER_LIMIT_FLOOR, extra
        )
    elif config.max_compliant_amount <= 0:
        amount = 0.0
    else:
        amount = _draw_closed(rng, 0.0, config.max_compliant_amount)

    if sanctioned and config.sanctioned_destinations:
        destination = rng.choice(sorted(config.sanctioned_destinations))
    else:
        index = rng.randrange(config.n_clean_destinations)
        destination = f"merchant_{index}"

    return Opportunity(
        transfer=Transfer(amount=amount, destination=destination),
        compliant_payoff=_draw_closed(
            rng, config.compliant_payoff_min, config.compliant_payoff_max
        ),
        violation_payoff=_draw_closed(
            rng, config.violation_payoff_min, config.violation_payoff_max
        ),
        detection_probability=config.detection_probability,
    )


def iter_agent_opportunities(
    config: SimulationConfig,
    n_agents: int,
    rng: Random,
) -> Iterator[tuple[int, int, Opportunity]]:
    """Yield `(step, agent_index, opportunity)` in a fixed order.

    Order is: for each step 1..n_steps, for each agent 0..n_agents-1.
    Unstaked and staked runners must use this so they share the same
    environment stream when `n_agents`, `n_steps`, and `seed` match.
    """
    for step in range(1, config.n_steps + 1):
        for agent_index in range(n_agents):
            yield step, agent_index, sample_opportunity(rng, config)

