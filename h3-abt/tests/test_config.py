"""Config loading and validation. These are not H3 experimental results."""

from __future__ import annotations

from pathlib import Path

import pytest

from h3_abt.config import ConfigError, load_config, parse_config
from h3_abt.types import TieBreak

DEFAULT_YAML = (
    Path(__file__).resolve().parents[1] / "configs" / "default.yaml"
)


def test_default_config_loads() -> None:
    config = load_config(DEFAULT_YAML)
    assert config.n_staked == 3
    assert config.n_unstaked == 3
    assert config.n_steps == 20
    assert config.stake_amount == 100.0
    assert config.slash_amount == 100.0
    assert config.max_compliant_amount == 50.0
    assert config.sanctioned_destinations == frozenset({"sanctioned_0"})
    assert config.detection_probability == 1.0
    assert config.tie_break is TieBreak.REFUSE
    assert config.seed == 42


def test_load_config_uses_package_default_when_path_omitted() -> None:
    config = load_config()
    assert config.seed == 42


def test_missing_file_raises() -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config(Path("does-not-exist.yaml"))


def test_detection_probability_out_of_range() -> None:
    raw = {
        "n_staked": 3,
        "n_unstaked": 3,
        "n_steps": 1,
        "stake_amount": 1.0,
        "slash_amount": 1.0,
        "max_compliant_amount": 1.0,
        "sanctioned_destinations": [],
        "detection_probability": 1.5,
        "tie_break": "refuse",
        "seed": 0,
    }
    with pytest.raises(ConfigError, match="detection_probability"):
        parse_config(raw)


def test_n_steps_must_be_positive() -> None:
    raw = {
        "n_staked": 0,
        "n_unstaked": 0,
        "n_steps": 0,
        "stake_amount": 0.0,
        "slash_amount": 0.0,
        "max_compliant_amount": 0.0,
        "sanctioned_destinations": [],
        "detection_probability": 0.0,
        "tie_break": "refuse",
        "seed": 0,
    }
    with pytest.raises(ConfigError, match="n_steps"):
        parse_config(raw)


def test_invalid_tie_break() -> None:
    raw = {
        "n_staked": 1,
        "n_unstaked": 1,
        "n_steps": 1,
        "stake_amount": 1.0,
        "slash_amount": 1.0,
        "max_compliant_amount": 1.0,
        "sanctioned_destinations": [],
        "detection_probability": 1.0,
        "tie_break": "random",
        "seed": 0,
    }
    with pytest.raises(ConfigError, match="tie_break"):
        parse_config(raw)
