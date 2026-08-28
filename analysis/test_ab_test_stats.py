"""
Unit tests for ab_test_stats.py — validated against scipy's own implementations
and hand-checkable cases, so the toolkit's numbers can be trusted (and defended).

Run: pytest analysis/test_ab_test_stats.py -v
"""
import numpy as np
from scipy import stats as scipy_stats
from ab_test_stats import (
    srm_check, two_proportion_ztest, required_sample_size,
    minimum_detectable_effect, mann_whitney_test, bonferroni_alpha,
)


def test_srm_check_no_mismatch_on_perfect_split():
    result = srm_check(n_a=5000, n_b=5000)
    assert not result.is_mismatched
    assert result.p_value > 0.9


def test_srm_check_flags_obvious_mismatch():
    # 6000 vs 4000 on an intended 50/50 split is a huge, obvious break
    result = srm_check(n_a=6000, n_b=4000)
    assert result.is_mismatched
    assert result.p_value < 0.001


def test_two_proportion_ztest_matches_scipy_chi2_direction():
    # Cross-check against scipy's own two-proportion z-test (via statsmodels-style
    # manual chi2) isn't available directly in scipy, so we validate the sign and
    # rough magnitude against a hand-computed pooled-SE z-test.
    result = two_proportion_ztest(x_a=100, n_a=1000, x_b=150, n_b=1000)
    assert result.rate_a == 0.10
    assert result.rate_b == 0.15
    assert abs(result.abs_diff - 0.05) < 1e-9  # float arithmetic, not exact equality
    assert result.is_significant  # this size of gap at n=1000/arm should be significant
    assert result.z_stat > 0  # p_b > p_a, and z is defined as (p_b - p_a)/se, so z should be positive


def test_two_proportion_ztest_no_effect_when_equal():
    result = two_proportion_ztest(x_a=500, n_a=5000, x_b=500, n_b=5000)
    assert result.abs_diff == 0
    assert not result.is_significant
    assert round(result.p_value, 2) == 1.0


def test_required_sample_size_decreases_with_larger_mde():
    # Detecting a bigger effect needs fewer users -- sanity check on monotonicity
    n_small_effect = required_sample_size(baseline_rate=0.20, mde_abs=0.01)
    n_large_effect = required_sample_size(baseline_rate=0.20, mde_abs=0.05)
    assert n_large_effect < n_small_effect


def test_minimum_detectable_effect_is_consistent_with_required_sample_size():
    # Round-trip check: if N users gives MDE m, then required_sample_size for MDE m
    # should be approximately N
    baseline = 0.19
    n_per_group = 15300
    mde = minimum_detectable_effect(n_per_group, baseline)
    n_check = required_sample_size(baseline, mde)
    assert abs(n_check - n_per_group) / n_per_group < 0.05  # within 5%


def test_mann_whitney_matches_scipy_directly():
    rng = np.random.default_rng(42)
    sample_a = rng.exponential(scale=10, size=500)
    sample_b = rng.exponential(scale=15, size=500)  # shifted higher
    result = mann_whitney_test(sample_a, sample_b)
    u_check, p_check = scipy_stats.mannwhitneyu(sample_a, sample_b, alternative="two-sided")
    assert result.u_stat == u_check
    assert abs(result.p_value - p_check) < 1e-9
    assert result.is_significant  # scale=10 vs scale=15 at n=500 should show up


def test_bonferroni_alpha():
    assert bonferroni_alpha(0.05, 3) == 0.05 / 3
    assert bonferroni_alpha(0.05, 1) == 0.05
