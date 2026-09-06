"""Load and validate H3 simulation config from YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from h3_abt.types import SimulationConfig, TieBreak

DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parents[2] / "configs" / "default.yaml"
)


class ConfigError(ValueError):
    """Invalid simulation configuration."""


def _require_int(data: dict[str, Any], key: str) -> int:
    if key not in data:
        raise ConfigError(f"missing required field: {key}")
    value = data[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"{key} must be an integer")
    return value


def _require_float(data: dict[str, Any], key: str) -> float:
    if key not in data:
        raise ConfigError(f"missing required field: {key}")
    value = data[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{key} must be a number")
    return float(value)


def _require_non_negative_int(data: dict[str, Any], key: str) -> int:
    value = _require_int(data, key)
    if value < 0:
        raise ConfigError(f"{key} must be >= 0")
    return value


def _require_positive_int(data: dict[str, Any], key: str) -> int:
    value = _require_int(data, key)
    if value < 1:
        raise ConfigError(f"{key} must be >= 1")
    return value


def _require_non_negative_float(data: dict[str, Any], key: str) -> float:
    value = _require_float(data, key)
    if value < 0:
        raise ConfigError(f"{key} must be >= 0")
    return value


def parse_config(data: dict[str, Any]) -> SimulationConfig:
    """Validate a raw mapping and return a SimulationConfig."""
    n_staked = _require_non_negative_int(data, "n_staked")
    n_unstaked = _require_non_negative_int(data, "n_unstaked")
    n_steps = _require_positive_int(data, "n_steps")
    stake_amount = _require_non_negative_float(data, "stake_amount")
    slash_amount = _require_non_negative_float(data, "slash_amount")
    max_compliant_amount = _require_non_negative_float(
        data, "max_compliant_amount"
    )
    detection_probability = _require_float(data, "detection_probability")
    if not 0.0 <= detection_probability <= 1.0:
        raise ConfigError("detection_probability must be in [0, 1]")
    seed = _require_int(data, "seed")

    raw_destinations = data.get("sanctioned_destinations", [])
    if not isinstance(raw_destinations, list) or not all(
        isinstance(item, str) for item in raw_destinations
    ):
        raise ConfigError("sanctioned_destinations must be a list of strings")
    sanctioned = frozenset(raw_destinations)

    raw_tie = data.get("tie_break", "refuse")
    try:
        tie_break = TieBreak(raw_tie)
    except ValueError as exc:
        raise ConfigError("tie_break must be 'refuse' or 'execute'") from exc

    return SimulationConfig(
        n_staked=n_staked,
        n_unstaked=n_unstaked,
        n_steps=n_steps,
        stake_amount=stake_amount,
        slash_amount=slash_amount,
        max_compliant_amount=max_compliant_amount,
        sanctioned_destinations=sanctioned,
        detection_probability=detection_probability,
        tie_break=tie_break,
        seed=seed,
    )


def load_config(path: Path | str | None = None) -> SimulationConfig:
    """Load YAML config from `path`, or the default file if omitted."""
    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    if not config_path.is_file():
        raise ConfigError(f"config file not found: {config_path}")
    with config_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if raw is None:
        raise ConfigError("config file is empty")
    if not isinstance(raw, dict):
        raise ConfigError("config file must be a YAML mapping")
    return parse_config(raw)
