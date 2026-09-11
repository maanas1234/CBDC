"""Rate formula tests. Not H3 experimental results."""

from h3_abt.metrics import (
    absolute_difference,
    relative_reduction,
    violation_rate,
)


def test_violation_rate_known_fraction() -> None:
    assert violation_rate(2, 10) == 0.2
    assert violation_rate(0, 10) == 0.0
    assert violation_rate(10, 10) == 1.0


def test_violation_rate_zero_actions() -> None:
    assert violation_rate(0, 0) == 0.0


def test_absolute_difference_treatment_minus_control() -> None:
    assert absolute_difference(0.2, 0.5) == -0.3
    assert absolute_difference(0.5, 0.2) == 0.3


def test_relative_reduction_undefined_when_control_is_zero() -> None:
    assert relative_reduction(0.0, 0.0) is None
    assert relative_reduction(0.1, 0.0) is None
    assert relative_reduction(0.2, 0.5) == 0.6
