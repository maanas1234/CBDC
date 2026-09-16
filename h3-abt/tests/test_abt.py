"""ABT registry protocol tests. These are not H3 experimental results."""

from __future__ import annotations

import pytest

from h3_abt.abt import (
    ABTRegistry,
    ABTRegistryError,
    ABTTransferError,
)
from h3_abt.config import parse_config
from h3_abt.types import Transfer


def _config(**overrides):
    data = {
        "n_staked": 1,
        "n_unstaked": 1,
        "n_steps": 1,
        "stake_amount": 100.0,
        "slash_amount": 40.0,
        "max_compliant_amount": 50.0,
        "sanctioned_destinations": ["sanctioned_0"],
        "detection_probability": 1.0,
        "tie_break": "refuse",
        "seed": 0,
    }
    data.update(overrides)
    return parse_config(data)


def test_register_issues_abt_bound_to_agent() -> None:
    registry = ABTRegistry()
    token = registry.register("staked_0")
    assert token.owner_id == "staked_0"
    assert token.token_id == "abt_staked_0"
    assert registry.token("staked_0") == token
    assert registry.remaining_stake("staked_0") == 0.0


def test_duplicate_register_rejected() -> None:
    registry = ABTRegistry()
    registry.register("staked_0")
    with pytest.raises(ABTRegistryError, match="already registered"):
        registry.register("staked_0")


def test_successful_staking_tracks_remaining() -> None:
    registry = ABTRegistry()
    registry.register_and_stake("staked_0", 100.0)
    assert registry.remaining_stake("staked_0") == 100.0
    registry.stake("staked_0", 25.0)
    assert registry.remaining_stake("staked_0") == 125.0


def test_stake_requires_positive_amount() -> None:
    registry = ABTRegistry()
    registry.register("staked_0")
    with pytest.raises(ABTRegistryError, match="stake amount"):
        registry.stake("staked_0", 0.0)


def test_abt_is_non_transferable() -> None:
    registry = ABTRegistry()
    token = registry.register_and_stake("alice", 50.0)
    registry.register("bob")
    with pytest.raises(ABTTransferError, match="cannot be transferred"):
        registry.transfer("alice", "bob")
    assert registry.token("alice") == token
    assert registry.token("alice").owner_id == "alice"
    assert registry.remaining_stake("alice") == 50.0
    assert registry.remaining_stake("bob") == 0.0


def test_report_violation_slashes_and_records_history() -> None:
    config = _config(slash_amount=40.0)
    registry = ABTRegistry()
    registry.register_and_stake("staked_0", 100.0)
    transfer = Transfer(amount=80.0, destination="merchant_a")
    event = registry.report_violation("staked_0", transfer, config, step=1)
    assert event.slashed_amount == 40.0
    assert event.stake_remaining == 60.0
    assert event.token_id == "abt_staked_0"
    assert registry.remaining_stake("staked_0") == 60.0
    history = registry.history("staked_0")
    assert len(history) == 1
    assert history[0] == event


def test_slash_never_goes_negative() -> None:
    config = _config(slash_amount=100.0)
    registry = ABTRegistry()
    registry.register_and_stake("staked_0", 30.0)
    transfer = Transfer(amount=80.0, destination="merchant_a")
    event = registry.report_violation("staked_0", transfer, config, step=1)
    assert event.slashed_amount == 30.0
    assert event.stake_remaining == 0.0
    assert registry.remaining_stake("staked_0") == 0.0
    second = registry.report_violation("staked_0", transfer, config, step=2)
    assert second.slashed_amount == 0.0
    assert second.stake_remaining == 0.0
    assert len(registry.history("staked_0")) == 2


def test_report_rejects_compliant_transfer() -> None:
    config = _config()
    registry = ABTRegistry()
    registry.register_and_stake("staked_0", 100.0)
    transfer = Transfer(amount=10.0, destination="merchant_a")
    with pytest.raises(ABTRegistryError, match="policy-violating"):
        registry.report_violation("staked_0", transfer, config, step=1)
    assert registry.remaining_stake("staked_0") == 100.0
    assert registry.history("staked_0") == ()


def test_report_unknown_agent_rejected() -> None:
    config = _config()
    registry = ABTRegistry()
    transfer = Transfer(amount=80.0, destination="merchant_a")
    with pytest.raises(ABTRegistryError, match="unknown agent"):
        registry.report_violation("ghost", transfer, config, step=1)


def test_agent_state_snapshot_is_staked() -> None:
    registry = ABTRegistry()
    registry.register_and_stake("staked_0", 80.0)
    state = registry.agent_state("staked_0")
    assert state.agent_id == "staked_0"
    assert state.is_staked is True
    assert state.stake_remaining == 80.0
