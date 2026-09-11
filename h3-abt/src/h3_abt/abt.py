"""In-simulation AgentBound Token registry.

This is the liability *mechanism* (identity, stake, non-transfer,
reportViolation → slash). It is not an on-chain contract and not an
H3 experimental result.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from h3_abt.protocol import is_violation
from h3_abt.types import (
    AgentBoundToken,
    AgentState,
    SimulationConfig,
    Transfer,
    ViolationEvent,
)


class ABTError(Exception):
    """Base error for the ABT registry."""


class ABTTransferError(ABTError):
    """AgentBound Tokens cannot be transferred."""


class ABTRegistryError(ABTError):
    """Invalid registry operation."""


@dataclass
class _Account:
    token: AgentBoundToken
    stake_remaining: float = 0.0
    history: list[ViolationEvent] = field(default_factory=list)


class ABTRegistry:
    """Identity-bound stake ledger with automatic slashing on report."""

    def __init__(self) -> None:
        self._accounts: dict[str, _Account] = {}

    def register(self, agent_id: str) -> AgentBoundToken:
        """Issue a non-transferable ABT bound to `agent_id`."""
        if not agent_id:
            raise ABTRegistryError("agent_id must be non-empty")
        if agent_id in self._accounts:
            raise ABTRegistryError(f"agent already registered: {agent_id}")
        token = AgentBoundToken(token_id=f"abt_{agent_id}", owner_id=agent_id)
        self._accounts[agent_id] = _Account(token=token)
        return token

    def stake(self, agent_id: str, amount: float) -> float:
        """Post collateral. Returns remaining stake after the deposit."""
        account = self._require(agent_id)
        if amount <= 0:
            raise ABTRegistryError("stake amount must be > 0")
        account.stake_remaining += amount
        return account.stake_remaining

    def register_and_stake(
        self, agent_id: str, amount: float
    ) -> AgentBoundToken:
        token = self.register(agent_id)
        self.stake(agent_id, amount)
        return token

    def transfer(self, from_agent_id: str, to_agent_id: str) -> None:
        """Always rejected. ABTs are non-transferable."""
        self._require(from_agent_id)
        raise ABTTransferError(
            f"ABT cannot be transferred from {from_agent_id} to {to_agent_id}"
        )

    def token(self, agent_id: str) -> AgentBoundToken:
        return self._require(agent_id).token

    def remaining_stake(self, agent_id: str) -> float:
        return self._require(agent_id).stake_remaining

    def history(self, agent_id: str) -> tuple[ViolationEvent, ...]:
        return tuple(self._require(agent_id).history)

    def agent_state(self, agent_id: str) -> AgentState:
        account = self._require(agent_id)
        return AgentState(
            agent_id=agent_id,
            is_staked=True,
            stake_remaining=account.stake_remaining,
        )

    def report_violation(
        self,
        agent_id: str,
        transfer: Transfer,
        config: SimulationConfig,
        step: int,
    ) -> ViolationEvent:
        """Verify a policy violation, slash, and append history.

        Slash is `min(slash_amount, stake_remaining)` so remaining stake
        never goes negative. A fully slashed agent stays registered.
        """
        account = self._require(agent_id)
        if not is_violation(transfer, config):
            raise ABTRegistryError(
                "report_violation requires a policy-violating transfer"
            )
        slashed = min(config.slash_amount, account.stake_remaining)
        account.stake_remaining -= slashed
        if account.stake_remaining < 0:
            account.stake_remaining = 0.0
        event = ViolationEvent(
            step=step,
            agent_id=agent_id,
            token_id=account.token.token_id,
            amount=transfer.amount,
            destination=transfer.destination,
            slashed_amount=slashed,
            stake_remaining=account.stake_remaining,
        )
        account.history.append(event)
        return event

    def _require(self, agent_id: str) -> _Account:
        if agent_id not in self._accounts:
            raise ABTRegistryError(f"unknown agent: {agent_id}")
        return self._accounts[agent_id]
