"""Sybil / identity-reset tests. Not H3 statistical results."""

from __future__ import annotations

import pytest

from h3_abt.abt import ABTRegistry, ABTRegistryError, ABTTransferError
from h3_abt.config import load_config, parse_config
from h3_abt.sybil import (
    ORIGINAL_IDENTITY,
    RESET_IDENTITY,
    SYBIL_LABEL,
    run_sybil_identity_reset,
)
from h3_abt.sybil_cli import format_sybil_report, main
from h3_abt.types import SybilOutcome, Transfer


def _raw(**overrides) -> dict:
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
        "seed": 42,
    }
    data.update(overrides)
    return data


def test_original_identity_is_registered_and_staked() -> None:
    result = run_sybil_identity_reset(parse_config(_raw()))
    assert result.original_identity == ORIGINAL_IDENTITY
    assert result.original_abt_id == f"abt_{ORIGINAL_IDENTITY}"
    assert result.original_stake_before == 100.0


def test_violation_is_slashed_and_history_stays_on_original() -> None:
    result = run_sybil_identity_reset(parse_config(_raw(slash_amount=40.0)))
    assert result.slash_amount == 40.0
    assert result.original_stake_after == 60.0
    assert result.original_violation_count == 1
    assert len(result.original_history) == 1
    assert result.original_history[0].agent_id == ORIGINAL_IDENTITY
    assert result.original_history[0].token_id == result.original_abt_id


def test_same_string_cannot_re_register() -> None:
    registry = ABTRegistry()
    registry.register(ORIGINAL_IDENTITY)
    with pytest.raises(ABTRegistryError, match="already registered"):
        registry.register(ORIGINAL_IDENTITY)


def test_fresh_identity_registers_and_gets_new_abt_and_stake() -> None:
    result = run_sybil_identity_reset(parse_config(_raw()))
    assert result.new_identity == RESET_IDENTITY
    assert result.new_registration_succeeded is True
    assert result.fresh_abt_obtained is True
    assert result.new_abt_id == f"abt_{RESET_IDENTITY}"
    assert result.new_abt_id != result.original_abt_id
    assert result.fresh_stake_obtained is True
    assert result.new_stake == 100.0
    assert result.new_violation_count == 0


def test_previous_liability_does_not_follow_the_new_identity() -> None:
    result = run_sybil_identity_reset(parse_config(_raw()))
    assert result.previous_liability_bypassed is True
    assert result.logical_agent_binding_exists is False
    assert result.original_violation_count == 1
    assert result.new_violation_count == 0
    assert result.original_stake_after == 60.0
    assert result.new_stake == 100.0


def test_original_history_is_not_erased_by_the_reset() -> None:
    config = parse_config(_raw())
    result = run_sybil_identity_reset(config)
    registry = ABTRegistry()
    registry.register_and_stake(ORIGINAL_IDENTITY, 100.0)
    registry.report_violation(
        ORIGINAL_IDENTITY,
        Transfer(amount=51.0, destination="merchant_a"),
        config,
        step=1,
    )
    registry.register_and_stake(RESET_IDENTITY, 100.0)
    assert len(registry.history(ORIGINAL_IDENTITY)) == 1
    assert registry.history(RESET_IDENTITY) == ()
    assert result.original_history[0].agent_id == ORIGINAL_IDENTITY


def test_old_abt_still_cannot_be_transferred_to_the_new_id() -> None:
    registry = ABTRegistry()
    registry.register_and_stake(ORIGINAL_IDENTITY, 100.0)
    registry.register(RESET_IDENTITY)
    with pytest.raises(ABTTransferError):
        registry.transfer(ORIGINAL_IDENTITY, RESET_IDENTITY)


def test_outcome_is_sybil_succeeded_not_blocked() -> None:
    result = run_sybil_identity_reset(parse_config(_raw()))
    assert result.label == SYBIL_LABEL
    assert result.outcome is SybilOutcome.SYBIL_SUCCEEDED
    assert result.outcome is not SybilOutcome.SYBIL_BLOCKED


def test_sybil_run_is_deterministic() -> None:
    config = parse_config(_raw(seed=42))
    first = run_sybil_identity_reset(config)
    second = run_sybil_identity_reset(config)
    assert first == second


def test_full_slash_still_allows_fresh_identity() -> None:
    result = run_sybil_identity_reset(parse_config(_raw(slash_amount=100.0)))
    assert result.original_stake_after == 0.0
    assert result.new_registration_succeeded is True
    assert result.new_stake == 100.0
    assert result.outcome is SybilOutcome.SYBIL_SUCCEEDED


def test_cli_labels_result_as_separate_from_z_test(capsys) -> None:
    from h3_abt.config import DEFAULT_CONFIG_PATH

    result = run_sybil_identity_reset(load_config())
    text = format_sybil_report(result)
    assert "SYBIL / IDENTITY-RESET TEST" in text
    assert "separate evaluation from the H3 z-test" in text
    assert "SYBIL_SUCCEEDED" in text

    exit_code = main(["--config", str(DEFAULT_CONFIG_PATH)])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "SYBIL_SUCCEEDED" in captured.out
    assert "previous_liability_bypassed: True" in captured.out
