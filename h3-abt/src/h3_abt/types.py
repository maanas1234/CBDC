"""Shared types for the H3 experimental protocol.

These types encode the research design. Treatment vs control is a single
flag (`is_staked`). Both groups use the same opportunity and the same
decision function.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Action(str, Enum):
    """Choice an agent makes when offered a candidate transfer."""

    EXECUTE = "execute"
    REFUSE = "refuse"


class TieBreak(str, Enum):
    """Documented tie-break when expected payoffs are equal."""

    REFUSE = "refuse"
    EXECUTE = "execute"


@dataclass(frozen=True)
class SimulationConfig:
    """Configurable knobs for a later multi-agent run.

    This PR loads and validates the config. It does not run an experiment.
    """

    n_staked: int
    n_unstaked: int
    n_steps: int
    stake_amount: float
    slash_amount: float
    max_compliant_amount: float
    sanctioned_destinations: frozenset[str]
    detection_probability: float
    tie_break: TieBreak
    seed: int


@dataclass(frozen=True)
class Transfer:
    """A candidate CBDC transfer. Policy compliance is machine-checkable."""

    amount: float
    destination: str


@dataclass(frozen=True)
class Opportunity:
    """One decision an agent faces.

    `compliant_payoff` is the payoff of refusing, or of executing a
    policy-compliant transfer.
    `violation_payoff` is the private gain of executing a policy-violating
    transfer, before any slash.
    """

    transfer: Transfer
    compliant_payoff: float
    violation_payoff: float
    detection_probability: float


@dataclass(frozen=True)
class AgentState:
    """Agent identity and stake. The only group difference is `is_staked`.

    Unstaked (control) agents must have `is_staked=False` and
    `stake_remaining=0`. Staked (treatment) agents start with
    `stake_remaining=stake_amount`.
    """

    agent_id: str
    is_staked: bool
    stake_remaining: float
