"""H3 protocol, baseline, treatment, and comparison experiment.

Smoke tests are not confirmatory H3 results.
"""

from h3_abt.abt import (
    ABTError,
    ABTRegistry,
    ABTRegistryError,
    ABTTransferError,
)
from h3_abt.baseline import format_baseline_report, main as baseline_main
from h3_abt.config import ConfigError, load_config, parse_config
from h3_abt.environment import iter_agent_opportunities, sample_opportunity
from h3_abt.experiment import run_comparison, save_results
from h3_abt.experiment_cli import (
    format_experiment_report,
    main as experiment_main,
)
from h3_abt.metrics import violation_rate
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
from h3_abt.stats import two_proportion_z_test
from h3_abt.treatment import STAKED_TREATMENT_LABEL, run_staked_treatment
from h3_abt.treatment_cli import (
    format_treatment_report,
    main as treatment_main,
)
from h3_abt.types import (
    Action,
    AgentBoundToken,
    AgentState,
    BaselineResult,
    ExperimentResult,
    Opportunity,
    SimulationConfig,
    StepRecord,
    TieBreak,
    Transfer,
    TreatmentResult,
    ViolationEvent,
)

__all__ = [
    "ABTError",
    "ABTRegistry",
    "ABTRegistryError",
    "ABTTransferError",
    "Action",
    "AgentBoundToken",
    "AgentState",
    "BaselineResult",
    "ConfigError",
    "ExperimentResult",
    "Opportunity",
    "SimulationConfig",
    "STAKED_TREATMENT_LABEL",
    "StepRecord",
    "TieBreak",
    "Transfer",
    "TreatmentResult",
    "UNSTAKED_BASELINE_LABEL",
    "ViolationEvent",
    "baseline_main",
    "choose_action",
    "expected_payoff_execute",
    "expected_payoff_refuse",
    "expected_slash",
    "experiment_main",
    "format_baseline_report",
    "format_experiment_report",
    "format_treatment_report",
    "is_violation",
    "iter_agent_opportunities",
    "load_config",
    "make_staked_agent",
    "make_unstaked_agent",
    "parse_config",
    "run_comparison",
    "run_staked_treatment",
    "run_unstaked_baseline",
    "sample_opportunity",
    "save_results",
    "treatment_main",
    "two_proportion_z_test",
    "violation_rate",
]
