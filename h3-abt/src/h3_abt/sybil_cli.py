"""CLI for the Sybil / identity-reset test.

This result is separate from the control-vs-treatment z-test.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from h3_abt.config import DEFAULT_CONFIG_PATH, load_config
from h3_abt.sybil import run_sybil_identity_reset
from h3_abt.types import SybilResult


def format_sybil_report(result: SybilResult) -> str:
    return "\n".join(
        [
            "=== SYBIL / IDENTITY-RESET TEST ===",
            "This is a separate evaluation from the H3 z-test.",
            "Do not blend this outcome into the treatment/control verdict.",
            "Do not treat this as a proof of H3.",
            f"label: {result.label}",
            f"seed: {result.seed}",
            f"original_identity: {result.original_identity}",
            f"original_abt_id: {result.original_abt_id}",
            f"original_stake_before: {result.original_stake_before:.6f}",
            f"slash_amount: {result.slash_amount:.6f}",
            f"remaining_stake: {result.original_stake_after:.6f}",
            f"original_violation_count: {result.original_violation_count}",
            f"new_identity: {result.new_identity}",
            f"new_registration_succeeded: {result.new_registration_succeeded}",
            f"fresh_abt_obtained: {result.fresh_abt_obtained}",
            f"new_abt_id: {result.new_abt_id}",
            f"fresh_stake_obtained: {result.fresh_stake_obtained}",
            f"new_stake: {result.new_stake:.6f}",
            f"new_violation_count: {result.new_violation_count}",
            f"previous_liability_bypassed: {result.previous_liability_bypassed}",
            f"logical_agent_binding_exists: {result.logical_agent_binding_exists}",
            f"outcome: {result.outcome.value}",
            f"interpretation: {result.interpretation}",
        ]
    )


def result_to_dict(result: SybilResult) -> dict:
    return {
        "label": result.label,
        "separate_from_h3_z_test": True,
        "seed": result.seed,
        "original_identity": result.original_identity,
        "original_abt_id": result.original_abt_id,
        "original_stake_before": result.original_stake_before,
        "slash_amount": result.slash_amount,
        "remaining_stake": result.original_stake_after,
        "original_violation_count": result.original_violation_count,
        "original_violation_history": [
            {
                "step": event.step,
                "agent_id": event.agent_id,
                "token_id": event.token_id,
                "amount": event.amount,
                "destination": event.destination,
                "slashed_amount": event.slashed_amount,
                "stake_remaining": event.stake_remaining,
            }
            for event in result.original_history
        ],
        "new_identity": result.new_identity,
        "new_registration_succeeded": result.new_registration_succeeded,
        "fresh_abt_obtained": result.fresh_abt_obtained,
        "new_abt_id": result.new_abt_id,
        "fresh_stake_obtained": result.fresh_stake_obtained,
        "new_stake": result.new_stake,
        "new_violation_count": result.new_violation_count,
        "previous_liability_bypassed": result.previous_liability_bypassed,
        "logical_agent_binding_exists": result.logical_agent_binding_exists,
        "outcome": result.outcome.value,
        "interpretation": result.interpretation,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the Sybil/identity-reset test against the in-sim ABT "
            "registry. Separate from the H3 statistical comparison."
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
        help="Also print a JSON dump after the text summary.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    result = run_sybil_identity_reset(config)
    sys.stdout.write(format_sybil_report(result) + "\n")
    if args.json:
        sys.stdout.write(json.dumps(result_to_dict(result), indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
