"""Control vs treatment comparison.

Reuses the unstaked baseline and staked treatment runners. Both groups
use the same policy, `choose_action`, seed, and opportunity generator.
Detection uses a separate RNG inside the treatment runner.

This module does not implement a Sybil test and does not claim H3 is proven.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from h3_abt.metrics import absolute_difference, relative_reduction
from h3_abt.simulation import run_unstaked_baseline
from h3_abt.stats import ALPHA, format_p_value, h3_verdict, two_proportion_z_test
from h3_abt.treatment import run_staked_treatment
from h3_abt.types import (
    ExperimentObservation,
    ExperimentResult,
    GroupCounts,
    SimulationConfig,
    StepRecord,
)


EXPERIMENT_LABEL = "CONTROL VS TREATMENT"


def treatment_violation_feasible(config: SimulationConfig) -> bool:
    """True if some violating offer can still beat expected slash.

    This is a parameter-box check, not an experimental result.
    """
    expected_slash = config.detection_probability * min(
        config.slash_amount, config.stake_amount
    )
    return (
        config.violation_payoff_max - expected_slash
        > config.compliant_payoff_min
    )


def _observations(
    group: str, records: tuple[StepRecord, ...]
) -> list[ExperimentObservation]:
    return [
        ExperimentObservation(
            group=group,
            agent_id=record.agent_id,
            step=record.step,
            action=record.action.value,
            is_violation=record.is_violation,
            stake_before=record.stake_before,
            stake_after=record.stake_remaining,
            amount_slashed=record.slashed_amount,
        )
        for record in records
    ]


def run_comparison(config: SimulationConfig) -> ExperimentResult:
    """Run control and treatment, then the pre-registered z-test."""
    control_run = run_unstaked_baseline(config)
    treatment_run = run_staked_treatment(config)
    control = GroupCounts(
        group="control",
        n_agents=control_run.n_agents,
        total_actions=control_run.total_actions,
        total_violations=control_run.total_violations,
        violation_rate=control_run.violation_rate,
    )
    treatment = GroupCounts(
        group="treatment",
        n_agents=treatment_run.n_agents,
        total_actions=treatment_run.total_actions,
        total_violations=treatment_run.total_violations,
        violation_rate=treatment_run.violation_rate,
    )
    z_test = two_proportion_z_test(
        treatment.total_violations,
        treatment.total_actions,
        control.total_violations,
        control.total_actions,
        alpha=ALPHA,
    )
    rate_lower, significant, verdict = h3_verdict(
        treatment.violation_rate, control.violation_rate, z_test
    )
    observations = tuple(
        _observations("control", control_run.records)
        + _observations("treatment", treatment_run.records)
    )
    return ExperimentResult(
        label=EXPERIMENT_LABEL,
        experiment_role=config.experiment_role,
        seed=config.seed,
        n_steps=config.n_steps,
        alpha=ALPHA,
        control=control,
        treatment=treatment,
        absolute_difference=absolute_difference(
            treatment.violation_rate, control.violation_rate
        ),
        relative_reduction=relative_reduction(
            treatment.violation_rate, control.violation_rate
        ),
        z_test=z_test,
        treatment_rate_lower=rate_lower,
        statistically_significant_lower=significant,
        verdict=verdict,
        treatment_violation_feasible=treatment_violation_feasible(config),
        observations=observations,
    )


def result_to_dict(result: ExperimentResult) -> dict:
    return {
        "label": result.label,
        "experiment_role": result.experiment_role,
        "smoke_test": result.experiment_role == "smoke_test",
        "confirmatory": result.experiment_role == "confirmatory",
        "disclaimer": (
            "SUPPORTED means the predefined criterion was met under this "
            "configuration (treatment violation rate < control violation "
            "rate and one-sided two-proportion z-test p < 0.05). It does "
            "not mean H3 has been universally proven."
        ),
        "seed": result.seed,
        "n_steps": result.n_steps,
        "alpha": result.alpha,
        "control": {
            "group": result.control.group,
            "n_agents": result.control.n_agents,
            "total_actions": result.control.total_actions,
            "total_violations": result.control.total_violations,
            "violation_rate": result.control.violation_rate,
        },
        "treatment": {
            "group": result.treatment.group,
            "n_agents": result.treatment.n_agents,
            "total_actions": result.treatment.total_actions,
            "total_violations": result.treatment.total_violations,
            "violation_rate": result.treatment.violation_rate,
        },
        "absolute_difference": result.absolute_difference,
        "relative_reduction": result.relative_reduction,
        "z_test": {
            "z_statistic": result.z_test.z_statistic,
            "p_value": result.z_test.p_value,
            "p_value_display": format_p_value(result.z_test.p_value),
            "standard_error": result.z_test.standard_error,
            "pooled_proportion": result.z_test.pooled_proportion,
            "alpha": result.z_test.alpha,
            "defined": result.z_test.defined,
            "note": result.z_test.note,
        },
        "treatment_rate_lower": result.treatment_rate_lower,
        "statistically_significant_lower": (
            result.statistically_significant_lower
        ),
        "verdict": result.verdict,
        "treatment_violation_feasible": result.treatment_violation_feasible,
        "observations": [
            {
                "group": row.group,
                "agent_id": row.agent_id,
                "step": row.step,
                "action": row.action,
                "is_violation": row.is_violation,
                "stake_before": row.stake_before,
                "stake_after": row.stake_after,
                "amount_slashed": row.amount_slashed,
            }
            for row in result.observations
        ],
    }


def save_results(result: ExperimentResult, output_dir: Path) -> tuple[Path, Path]:
    """Write JSON and CSV. Returns (json_path, csv_path)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{result.experiment_role}_seed{result.seed}"
    json_path = output_dir / f"{stem}.json"
    csv_path = output_dir / f"{stem}.csv"
    json_path.write_text(
        json.dumps(result_to_dict(result), indent=2), encoding="utf-8"
    )
    fieldnames = [
        "group",
        "agent_id",
        "step",
        "action",
        "is_violation",
        "stake_before",
        "stake_after",
        "amount_slashed",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in result.observations:
            writer.writerow(
                {
                    "group": row.group,
                    "agent_id": row.agent_id,
                    "step": row.step,
                    "action": row.action,
                    "is_violation": row.is_violation,
                    "stake_before": row.stake_before,
                    "stake_after": row.stake_after,
                    "amount_slashed": row.amount_slashed,
                }
            )
    return json_path, csv_path
