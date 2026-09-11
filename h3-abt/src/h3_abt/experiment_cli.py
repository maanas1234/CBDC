"""CLI for control vs treatment comparison.

Smoke-test output is not a confirmatory H3 result.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from h3_abt.config import DEFAULT_CONFIG_PATH, load_config
from h3_abt.experiment import run_comparison, save_results, result_to_dict
from h3_abt.stats import format_p_value
from h3_abt.types import ExperimentResult

DEFAULT_OUTPUT_DIR = (
    Path(__file__).resolve().parents[2] / "results"
)


def _role_banner(role: str) -> str:
    if role == "confirmatory":
        return "=== CONTROL VS TREATMENT (CONFIRMATORY CONFIG) ==="
    return "=== CONTROL VS TREATMENT (SMOKE TEST) ==="


def format_experiment_report(result: ExperimentResult) -> str:
    rel = (
        "undefined (control rate is 0)"
        if result.relative_reduction is None
        else f"{result.relative_reduction:.6f}"
    )
    z = result.z_test.z_statistic
    p_text = format_p_value(result.z_test.p_value)
    z_text = "undefined" if z is None else f"{z:.6f}"
    return "\n".join(
        [
            _role_banner(result.experiment_role),
            "Do not treat this as a proof of H3.",
            "SUPPORTED means the predefined criterion was met under this",
            "configuration (treatment rate < control rate and p < 0.05),",
            "not that H3 has been universally proven.",
            f"experiment_role: {result.experiment_role}",
            f"seed: {result.seed}",
            f"n_steps: {result.n_steps}",
            f"control n_agents: {result.control.n_agents}",
            f"control total_actions: {result.control.total_actions}",
            f"control violations: {result.control.total_violations}",
            f"control violation_rate: {result.control.violation_rate:.6f}",
            f"treatment n_agents: {result.treatment.n_agents}",
            f"treatment total_actions: {result.treatment.total_actions}",
            f"treatment violations: {result.treatment.total_violations}",
            f"treatment violation_rate: {result.treatment.violation_rate:.6f}",
            f"absolute_difference (treatment - control): {result.absolute_difference:.6f}",
            f"relative_reduction: {rel}",
            f"z_statistic: {z_text}",
            f"p_value (one-sided, H1: p_t < p_c): {p_text}",
            f"alpha: {result.alpha}",
            f"treatment_rate_lower: {result.treatment_rate_lower}",
            f"statistically_significant_lower: {result.statistically_significant_lower}",
            f"treatment_violation_feasible (parameter box): {result.treatment_violation_feasible}",
            f"verdict: {result.verdict}",
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare unstaked control vs staked treatment. "
            "Smoke-test configs are not confirmatory H3 evidence."
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="YAML config path (default: configs/default.yaml smoke test)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for JSON/CSV output (default: results/)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Also print the JSON payload after the text summary.",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Do not write JSON/CSV files.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    result = run_comparison(config)
    sys.stdout.write(format_experiment_report(result) + "\n")
    if not args.no_save:
        json_path, csv_path = save_results(result, args.output_dir)
        sys.stdout.write(f"wrote {json_path}\n")
        sys.stdout.write(f"wrote {csv_path}\n")
    if args.json:
        sys.stdout.write(json.dumps(result_to_dict(result), indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
