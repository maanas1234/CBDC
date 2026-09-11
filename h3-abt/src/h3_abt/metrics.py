"""Shared rate formulas. These are not H3 experimental results."""

from __future__ import annotations


def violation_rate(total_violations: int, total_actions: int) -> float:
    if total_actions == 0:
        return 0.0
    return total_violations / total_actions


def absolute_difference(treatment_rate: float, control_rate: float) -> float:
    """Treatment minus control. Negative means treatment is lower."""
    return treatment_rate - control_rate


def relative_reduction(
    treatment_rate: float, control_rate: float
) -> float | None:
    """(control - treatment) / control. Undefined if control rate is 0."""
    if control_rate == 0.0:
        return None
    return (control_rate - treatment_rate) / control_rate
