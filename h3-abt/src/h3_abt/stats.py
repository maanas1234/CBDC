"""Two-proportion z-test for H3.

One-sided test of H1: p_treatment < p_control, alpha = 0.05.
This module does not claim H3 is proven.
"""

from __future__ import annotations

import math

from h3_abt.types import TwoProportionZTest

ALPHA = 0.05
SUPPORTED = "SUPPORTED"
NOT_SUPPORTED = "NOT SUPPORTED BY THIS EXPERIMENT"


def standard_normal_cdf(z: float) -> float:
    """Φ(z) = P(Z <= z).

    Uses erfc so the left tail is not flushed to 0 by ``1 + erf``.
    For extreme negative z, where erfc underflows, uses a Mills-ratio
    asymptotic so the value is not reported as a literal zero when a
    positive approximation still fits in float64.
    """
    x = -z / math.sqrt(2.0)
    tail = 0.5 * math.erfc(x)
    if tail > 0.0:
        return tail
    if z >= 0.0:
        return 1.0
    return _left_tail_asymptotic(z)


def _left_tail_asymptotic(z: float) -> float:
    """Φ(z) ~ φ(z)/|z| * (1 - 1/z^2 + 3/z^4) for z → -∞."""
    abs_z = -z
    inv_z2 = 1.0 / (z * z)
    mill = 1.0 - inv_z2 + 3.0 * inv_z2 * inv_z2
    log_p = (
        -0.5 * z * z
        - 0.5 * math.log(2.0 * math.pi)
        - math.log(abs_z)
        + math.log(mill)
    )
    return math.exp(log_p)


def format_p_value(p_value: float | None) -> str:
    """Human-readable p-value. Never prints a tiny tail as 0.000000."""
    if p_value is None:
        return "undefined"
    if p_value <= 0.0:
        return "< 1e-300"
    if p_value >= 1e-4:
        return f"{p_value:.6f}"
    return f"{p_value:.6e}"


def two_proportion_z_test(
    violations_treatment: int,
    actions_treatment: int,
    violations_control: int,
    actions_control: int,
    alpha: float = ALPHA,
) -> TwoProportionZTest:
    """Compare two independent Bernoulli samples.

    z = (p_treatment - p_control) / SE, with pooled SE under H0.
    One-sided p-value = Phi(z) for H1: p_treatment < p_control.
    """
    if actions_treatment <= 0 or actions_control <= 0:
        return TwoProportionZTest(
            z_statistic=None,
            p_value=None,
            standard_error=None,
            pooled_proportion=None,
            alpha=alpha,
            defined=False,
            note="z-test undefined: a group has zero actions",
        )
    pooled = (violations_treatment + violations_control) / (
        actions_treatment + actions_control
    )
    se = math.sqrt(
        pooled
        * (1.0 - pooled)
        * (1.0 / actions_treatment + 1.0 / actions_control)
    )
    if se == 0.0:
        return TwoProportionZTest(
            z_statistic=None,
            p_value=None,
            standard_error=0.0,
            pooled_proportion=pooled,
            alpha=alpha,
            defined=False,
            note="z-test undefined: pooled variance is zero",
        )
    p_t = violations_treatment / actions_treatment
    p_c = violations_control / actions_control
    z = (p_t - p_c) / se
    p_value = standard_normal_cdf(z)
    return TwoProportionZTest(
        z_statistic=z,
        p_value=p_value,
        standard_error=se,
        pooled_proportion=pooled,
        alpha=alpha,
        defined=True,
        note="one-sided two-proportion z-test, H1: p_treatment < p_control",
    )


def h3_verdict(
    treatment_rate: float,
    control_rate: float,
    z_test: TwoProportionZTest,
) -> tuple[bool, bool, str]:
    """Return (rate_lower, significant_lower, verdict string).

    SUPPORTED means the predefined criterion was met under the specified
    configuration (treatment rate < control rate and p < alpha). It does
    not mean H3 is universally proven.
    """
    rate_lower = treatment_rate < control_rate
    significant = (
        rate_lower
        and z_test.defined
        and z_test.p_value is not None
        and z_test.p_value < z_test.alpha
    )
    if significant:
        return rate_lower, True, SUPPORTED
    return rate_lower, False, NOT_SUPPORTED
