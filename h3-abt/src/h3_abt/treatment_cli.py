"""CLI for the staked treatment simulation.

Smoke-test output is not a confirmatory H3 result.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from h3_abt.config import DEFAULT_CONFIG_PATH, load_config
from h3_abt.treatment import run_staked_treatment
from h3_abt.types import TreatmentResult


def format_treatment_report(result: TreatmentResult) -> str:
    rate_pct = 100.0 * result.violation_rate
    return "\n".join(
        [
            "=== STAKED TREATMENT (SMOKE TEST) ===",
            "This run is a wiring smoke test, not a confirmatory H3 experiment.",
            "Do not treat these numbers as hypothesis pass/fail evidence.",
            "Protocol correctness (ABT/slash) is tested separately in pytest.",
            f"label: {result.label}",
            f"seed: {result.seed}",
            f"n_agents (staked only): {result.n_agents}",
            f"n_steps: {result.n_steps}",
            f"total_actions: {result.total_actions}",
            f"total_violations: {result.total_violations}",
            f"total_slashed: {result.total_slashed:.6f}",
            f"violation_rate: {result.violation_rate:.6f} ({rate_pct:.2f}%)",
        ]
    )


def result_to_dict(result: TreatmentResult) -> dict:
    return {
        "label": result.label,
        "smoke_test": True,
        "confirmatory": False,
        "n_agents": result.n_agents,
        "n_steps": result.n_steps,
        "seed": result.seed,
        "total_actions": result.total_actions,
        "total_violations": result.total_violations,
        "total_slashed": result.total_slashed,
        "violation_rate": result.violation_rate,
        "records": [
            {
                "seed": record.seed,
                "step": record.step,
                "agent_id": record.agent_id,
                "is_staked": record.is_staked,
                "abt_id": record.abt_id,
                "amount": record.amount,
                "destination": record.destination,
                "offer_is_policy_violation": record.offer_is_policy_violation,
                "action": record.action.value,
                "is_violation": record.is_violation,
                "detected": record.detected,
                "slashed_amount": record.slashed_amount,
                "stake_before": record.stake_before,
                "stake_remaining": record.stake_remaining,
            }
            for record in result.records
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the STAKED TREATMENT simulation. "
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
    result = run_staked_treatment(config)
    sys.stdout.write(format_treatment_report(result) + "\n")
    if args.json:
        sys.stdout.write(json.dumps(result_to_dict(result), indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
