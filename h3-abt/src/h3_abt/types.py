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
    """Configurable knobs for the simulation.

    The unstaked baseline uses `n_unstaked` and ignores `n_staked`.
    The staked treatment uses `n_staked` and ignores `n_unstaked`.
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
    p_over_limit: float
    p_sanctioned: float
    over_limit_extra: float
    n_clean_destinations: int
    compliant_payoff_min: float
    compliant_payoff_max: float
    violation_payoff_min: float
    violation_payoff_max: float


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


@dataclass(frozen=True)
class StepRecord:
    """One agent decision in one round.

    `is_violation` is whether the chosen action *committed* a policy
    violation (EXECUTE on a policy-violating transfer). Refusing a
    violating offer is not a violation.
    """

    seed: int
    step: int
    agent_id: str
    is_staked: bool
    amount: float
    destination: str
    offer_is_policy_violation: bool
    compliant_payoff: float
    violation_payoff: float
    detection_probability: float
    action: Action
    is_violation: bool
    abt_id: str | None = None
    detected: bool = False
    slashed_amount: float = 0.0
    stake_before: float = 0.0
    stake_remaining: float = 0.0


@dataclass(frozen=True)
class BaselineResult:
    """Outcome of the unstaked control/baseline run. Not an H3 pass/fail."""

    label: str
    n_agents: int
    n_steps: int
    seed: int
    total_actions: int
    total_violations: int
    violation_rate: float
    records: tuple[StepRecord, ...]


@dataclass(frozen=True)
class AgentBoundToken:
    """Non-transferable identity credential bound to one agent."""

    token_id: str
    owner_id: str


@dataclass(frozen=True)
class ViolationEvent:
    """One recorded, verified policy violation on an ABT identity."""

    step: int
    agent_id: str
    token_id: str
    amount: float
    destination: str
    slashed_amount: float
    stake_remaining: float


@dataclass(frozen=True)
class TreatmentResult:
    """Outcome of the staked treatment run. Not an H3 pass/fail."""

    label: str
    n_agents: int
    n_steps: int
    seed: int
    total_actions: int
    total_violations: int
    total_slashed: float
    violation_rate: float
    records: tuple[StepRecord, ...]
