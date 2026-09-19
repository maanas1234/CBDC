"""Two-proportion z-test tests. Constructed examples, not H3 results."""

from __future__ import annotations

import math

from h3_abt.stats import (
    ALPHA,
    NOT_SUPPORTED,
    SUPPORTED,
    format_p_value,
    h3_verdict,
    standard_normal_cdf,
    two_proportion_z_test,
)


def test_known_two_proportion_example() -> None:
    """Control 30/100, treatment 10/100. One-sided H1: p_t < p_c."""
    result = two_proportion_z_test(10, 100, 30, 100)
    pooled = 40 / 200
    se = math.sqrt(pooled * (1.0 - pooled) * (0.01 + 0.01))
    expected_z = (0.1 - 0.3) / se
    assert result.defined is True
    assert result.alpha == ALPHA
    assert result.z_statistic == expected_z
    assert result.p_value is not None
    assert result.p_value == 0.5 * math.erfc(-expected_z / math.sqrt(2.0))
    assert result.p_value < 0.05
    assert result.z_statistic < 0


def test_zero_actions_undefined() -> None:
    result = two_proportion_z_test(0, 0, 5, 10)
    assert result.defined is False
    assert result.z_statistic is None
    assert result.p_value is None


def test_zero_variance_undefined() -> None:
    result = two_proportion_z_test(0, 10, 0, 10)
    assert result.defined is False
    assert result.p_value is None
    assert "variance is zero" in result.note


def test_verdict_requires_lower_rate_and_significance() -> None:
    significant = two_proportion_z_test(10, 100, 30, 100)
    rate_lower, flag, verdict = h3_verdict(0.1, 0.3, significant)
    assert rate_lower is True
    assert flag is True
    assert verdict == SUPPORTED

    not_lower = two_proportion_z_test(30, 100, 10, 100)
    rate_lower, flag, verdict = h3_verdict(0.3, 0.1, not_lower)
    assert rate_lower is False
    assert flag is False
    assert verdict == NOT_SUPPORTED


def test_verdict_not_supported_when_test_undefined() -> None:
    undefined = two_proportion_z_test(0, 0, 0, 0)
    _, flag, verdict = h3_verdict(0.0, 0.0, undefined)
    assert flag is False
    assert verdict == NOT_SUPPORTED


def test_large_negative_z_is_not_flushed_to_zero() -> None:
    """erfc tail for z ≈ -10.070625 is about 3.73e-24, not 0.0."""
    z = -10.070625
    p_value = standard_normal_cdf(z)
    assert p_value > 0.0
    assert 3.0e-24 < p_value < 4.5e-24
    rendered = format_p_value(p_value)
    assert rendered != "0.000000"
    assert "e-" in rendered.lower()


def test_format_p_value_uses_scientific_notation_for_tiny_tails() -> None:
    assert format_p_value(None) == "undefined"
    assert format_p_value(0.04) == "0.040000"
    assert "e-" in format_p_value(3.73e-24).lower()
    assert format_p_value(0.0) == "< 1e-300"
