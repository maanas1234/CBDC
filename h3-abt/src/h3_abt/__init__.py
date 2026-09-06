"""H3 protocol scaffold. No simulation runner and no experimental results."""

from h3_abt.config import ConfigError, load_config, parse_config
from h3_abt.protocol import (
    choose_action,
    expected_payoff_execute,
    expected_payoff_refuse,
    expected_slash,
    is_violation,
    make_staked_agent,
    make_unstaked_agent,
)
from h3_abt.types import (
    Action,
    AgentState,
    Opportunity,
    SimulationConfig,
    TieBreak,
    Transfer,
)

__all__ = [
    "Action",
    "AgentState",
    "ConfigError",
    "Opportunity",
    "SimulationConfig",
    "TieBreak",
    "Transfer",
    "choose_action",
    "expected_payoff_execute",
    "expected_payoff_refuse",
    "expected_slash",
    "is_violation",
    "load_config",
    "make_staked_agent",
    "make_unstaked_agent",
    "parse_config",
]
