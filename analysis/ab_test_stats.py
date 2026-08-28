"""
ab_test_stats.py — a small, reusable A/B testing toolkit.

This is deliberately dataset-agnostic: every function takes raw counts or arrays,
not a Cookie Cats dataframe, so it's the kind of internal significance-calculator
utility a DA/analytics team actually keeps around and reuses across experiments.

Covers the workflow a real experiment analysis needs, beyond just "run a t-test":
  - sample ratio mismatch (SRM) checks, to catch broken randomization
  - two-proportion significance testing with a proper (Wilson score) confidence
    interval, not just a point estimate
  - sample size / minimum detectable effect calculations, for pre-registering
    an experiment before looking at results
  - a non-parametric test for skewed continuous metrics, where a t-test's
    normality assumption doesn't hold
  - Bonferroni correction for testing multiple metrics on one dataset
"""
from dataclasses import dataclass
import math
import numpy as np
from scipy import stats


# ---------------------------------------------------------------------------
# Sample Ratio Mismatch (SRM)
# ---------------------------------------------------------------------------

@dataclass
class SRMResult:
    n_a: int
    n_b: int
    expected_ratio: float
    chi2_stat: float
    p_value: float
    is_mismatched: bool  # True if p < 0.001 (SRM convention -- a stricter bar than 0.05)


def srm_check(n_a: int, n_b: int, expected_ratio: float = 0.5, alpha: float = 0.001) -> SRMResult:
    """
    Checks whether observed group sizes match the intended split.

    Convention in industry experimentation platforms is to flag SRM at a much
    stricter threshold than the usual 0.05 (commonly 0.001), because with large
    experiment sample sizes even a functioning randomizer will occasionally show
    p < 0.05 by chance, and an SRM false alarm blocks the whole readout.

    Run this BEFORE trusting any other result -- a broken randomizer invalidates
    everything downstream, in either direction.
    """
    n_total = n_a + n_b
    expected_a = n_total * expected_ratio
    expected_b = n_total * (1 - expected_ratio)
    chi2_stat = ((n_a - expected_a) ** 2 / expected_a) + ((n_b - expected_b) ** 2 / expected_b)
    p_value = 1 - stats.chi2.cdf(chi2_stat, df=1)
    return SRMResult(
        n_a=n_a, n_b=n_b, expected_ratio=expected_ratio,
        chi2_stat=chi2_stat, p_value=p_value,
        is_mismatched=p_value < alpha,
    )


# ---------------------------------------------------------------------------
# Two-proportion significance test
# ---------------------------------------------------------------------------

@dataclass
class ProportionTestResult:
    rate_a: float
    rate_b: float
    abs_diff: float           # rate_b - rate_a
    relative_lift_pct: float  # (rate_b - rate_a) / rate_a * 100
    z_stat: float
    p_value: float
    ci_diff_low: float        # Wilson-based CI on the difference (abs_diff +/- margin)
    ci_diff_high: float
    is_significant: bool


def two_proportion_ztest(x_a: int, n_a: int, x_b: int, n_b: int, alpha: float = 0.05) -> ProportionTestResult:
    """
    Standard two-proportion z-test, PLUS a confidence interval on the difference
    (not just a p-value) -- a p-value alone tells you "is there an effect?", the
    CI tells you "how big might it plausibly be?", which is what a ship decision
    actually needs.

    x_a, n_a: successes and total for group A (control)
    x_b, n_b: successes and total for group B (treatment)
    """
    p_a, p_b = x_a / n_a, x_b / n_b
    p_pool = (x_a + x_b) / (n_a + n_b)
    se_pooled = math.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b))
    z_stat = (p_b - p_a) / se_pooled if se_pooled > 0 else 0.0
    p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))

    # CI on the difference uses unpooled SE (standard for a CI, vs pooled SE for the test statistic)
    se_diff = math.sqrt(p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b)
    z_crit = stats.norm.ppf(1 - alpha / 2)
    diff = p_b - p_a
    margin = z_crit * se_diff

    return ProportionTestResult(
        rate_a=p_a, rate_b=p_b, abs_diff=diff,
        relative_lift_pct=(diff / p_a * 100) if p_a else float("nan"),
        z_stat=z_stat, p_value=p_value,
        ci_diff_low=diff - margin, ci_diff_high=diff + margin,
        is_significant=p_value < alpha,
    )


# ---------------------------------------------------------------------------
# Sample size / MDE planning
# ---------------------------------------------------------------------------

def required_sample_size(baseline_rate: float, mde_abs: float, alpha: float = 0.05, power: float = 0.80) -> int:
    """
    Required sample size PER ARM for a two-proportion test, given a baseline
    conversion rate and the smallest absolute effect (mde_abs) worth detecting.
    Standard normal-approximation formula used by most experimentation platforms.
    """
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_power = stats.norm.ppf(power)
    p1 = baseline_rate
    p2 = baseline_rate + mde_abs
    p_bar = (p1 + p2) / 2
    numerator = (z_alpha * math.sqrt(2 * p_bar * (1 - p_bar)) + z_power * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    n = numerator / (mde_abs ** 2)
    return math.ceil(n)


def minimum_detectable_effect(n_per_group: int, baseline_rate: float, alpha: float = 0.05, power: float = 0.80,
                               tol: float = 1e-6) -> float:
    """
    Inverse of required_sample_size: given the sample size we actually have,
    what's the smallest effect we had the power to detect? Useful *after* the
    fact to sanity-check whether a "no significant difference" result means
    "no effect" or "underpowered to detect a real effect."
    Solved via simple binary search since there's no closed form.
    """
    lo, hi = 1e-5, 0.5
    while hi - lo > tol:
        mid = (lo + hi) / 2
        n_needed = required_sample_size(baseline_rate, mid, alpha, power)
        if n_needed > n_per_group:
            lo = mid
        else:
            hi = mid
    return hi


# ---------------------------------------------------------------------------
# Non-parametric test for skewed continuous metrics
# ---------------------------------------------------------------------------

@dataclass
class MannWhitneyResult:
    median_a: float
    median_b: float
    u_stat: float
    p_value: float
    is_significant: bool


def mann_whitney_test(sample_a: np.ndarray, sample_b: np.ndarray, alpha: float = 0.05) -> MannWhitneyResult:
    """
    Non-parametric alternative to a t-test for comparing two groups on a
    continuous metric that's heavily skewed / has extreme outliers (like
    in-game engagement counts) -- a t-test's normality assumption doesn't
    hold there, and its result would be dominated by a handful of extreme
    values rather than reflecting the typical user.
    """
    u_stat, p_value = stats.mannwhitneyu(sample_a, sample_b, alternative="two-sided")
    return MannWhitneyResult(
        median_a=float(np.median(sample_a)),
        median_b=float(np.median(sample_b)),
        u_stat=float(u_stat), p_value=float(p_value),
        is_significant=p_value < alpha,
    )


# ---------------------------------------------------------------------------
# Multiple comparison correction
# ---------------------------------------------------------------------------

def bonferroni_alpha(alpha: float, num_tests: int) -> float:
    """The adjusted per-test significance threshold when testing multiple metrics on one dataset."""
    return alpha / num_tests
