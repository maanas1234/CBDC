"""H3 protocol scaffold plus unstaked baseline simulation.

The baseline is a control-group smoke test. It is not an H3 result.
"""

from h3_abt.baseline import format_baseline_report, main as baseline_main
from h3_abt.config import ConfigError, load_config, parse_config
from h3_abt.environment import sample_opportunity
from h3_abt.protocol import (
    choose_action,
    expected_payoff_execute,
    expected_payoff_refuse,
    expected_slash,
    is_violation,
    make_staked_agent,
    make_unstaked_agent,
)
from h3_abt.simulation import UNSTAKED_BASELINE_LABEL, run_unstaked_baseline
from h3_abt.types import (
    Action,
    AgentState,
    BaselineResult,
    Opportunity,
    SimulationConfig,
    StepRecord,
    TieBreak,
    Transfer,
)

__all__ = [
    "Action",
    "AgentState",
    "BaselineResult",
    "ConfigError",
    "Opportunity",
    "SimulationConfig",
    "StepRecord",
    "TieBreak",
    "Transfer",
    "UNSTAKED_BASELINE_LABEL",
    "baseline_main",
    "choose_action",
    "expected_payoff_execute",
    "expected_payoff_refuse",
    "expected_slash",
    "format_baseline_report",
    "is_violation",
    "load_config",
    "make_staked_agent",
    "make_unstaked_agent",
    "parse_config",
    "run_unstaked_baseline",
    "sample_opportunity",
]
