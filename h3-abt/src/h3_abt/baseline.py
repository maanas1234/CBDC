"""CLI for the unstaked control/baseline simulation.

Smoke-test output is not a confirmatory H3 result.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from h3_abt.config import DEFAULT_CONFIG_PATH, load_config
from h3_abt.simulation import run_unstaked_baseline
from h3_abt.types import BaselineResult


def format_baseline_report(result: BaselineResult) -> str:
    rate_pct = 100.0 * result.violation_rate
    return "\n".join(
        [
            "=== UNSTAKED CONTROL/BASELINE (SMOKE TEST) ===",
            "This run is a wiring smoke test, not a confirmatory H3 experiment.",
            "Do not treat these numbers as hypothesis pass/fail evidence.",
            f"label: {result.label}",
            f"seed: {result.seed}",
            f"n_agents (unstaked only): {result.n_agents}",
            f"n_steps: {result.n_steps}",
            f"total_actions: {result.total_actions}",
            f"total_violations: {result.total_violations}",
            f"violation_rate: {result.violation_rate:.6f} ({rate_pct:.2f}%)",
        ]
    )


def result_to_dict(result: BaselineResult) -> dict:
    return {
        "label": result.label,
        "smoke_test": True,
        "confirmatory": False,
        "n_agents": result.n_agents,
        "n_steps": result.n_steps,
        "seed": result.seed,
        "total_actions": result.total_actions,
        "total_violations": result.total_violations,
        "violation_rate": result.violation_rate,
        "records": [
            {
                "seed": record.seed,
                "step": record.step,
                "agent_id": record.agent_id,
                "is_staked": record.is_staked,
                "amount": record.amount,
                "destination": record.destination,
                "offer_is_policy_violation": record.offer_is_policy_violation,
                "action": record.action.value,
                "is_violation": record.is_violation,
            }
            for record in result.records
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the UNSTAKED CONTROL/BASELINE simulation. "
            "Smoke-test output is not a confirmatory H3 result."
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="YAML config path (default: configs/default.yaml)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Also print a JSON record dump after the text summary.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    result = run_unstaked_baseline(config)
    sys.stdout.write(format_baseline_report(result) + "\n")
    if args.json:
        sys.stdout.write(json.dumps(result_to_dict(result), indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
