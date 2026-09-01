from __future__ import annotations

import numpy as np

from robustbench.characterization.distances import (
    benjamini_hochberg,
    bootstrap_mean_ci,
    centroid_euclidean_distance,
    cohens_d,
    mahalanobis_centroid_distance,
    mann_whitney_with_effect_size,
    mmd_rbf_unbiased,
    univariate_pair_distance,
)


def test_bootstrap_mean_ci_contains_true_mean_for_normal_sample():
    rng = np.random.default_rng(0)
    v = rng.normal(loc=10.0, scale=1.0, size=500)
    lo, hi = bootstrap_mean_ci(v, n_boot=500, seed=1)
    assert lo is not None and hi is not None
    assert lo < 10.0 < hi


def test_bootstrap_mean_ci_none_for_single_value():
    assert bootstrap_mean_ci(np.array([5.0])) == (None, None)


def test_cohens_d_zero_for_identical_distributions():
    rng = np.random.default_rng(0)
    v = rng.normal(size=200)
    d = cohens_d(v, v.copy())
    assert d is not None
    assert abs(d) < 1e-9


def test_cohens_d_large_for_well_separated_distributions():
    rng = np.random.default_rng(0)
    a = rng.normal(loc=0.0, scale=1.0, size=200)
    b = rng.normal(loc=5.0, scale=1.0, size=200)
    d = cohens_d(a, b)
    assert d is not None
    assert abs(d) > 3.0


def test_univariate_pair_distance_ks_and_wasserstein_near_zero_for_same_distribution():
    rng = np.random.default_rng(0)
    a = rng.normal(size=300)
    b = rng.normal(size=300)
    res = univariate_pair_distance(a, b)
    assert res.ks_statistic is not None
    assert res.ks_statistic < 0.2  # loose bound, same distribution
    assert res.wasserstein < 0.3


def test_univariate_pair_distance_large_for_shifted_distribution():
    rng = np.random.default_rng(0)
    a = rng.normal(loc=0.0, size=300)
    b = rng.normal(loc=10.0, size=300)
    res = univariate_pair_distance(a, b)
    assert res.ks_statistic > 0.9
    assert res.wasserstein > 9.0
    assert res.ks_pvalue < 0.001


def test_benjamini_hochberg_monotonic_and_bounded():
    pvals = [0.001, 0.2, 0.01, None, 0.5, 0.03]
    adj = benjamini_hochberg(pvals)
    assert adj[3] is None
    non_none = [p for p in adj if p is not None]
    assert all(0.0 <= p <= 1.0 for p in non_none)
    # BH-adjusted p-values are always >= raw p-values.
    for raw, a in zip(pvals, adj):
        if raw is not None:
            assert a >= raw - 1e-9


def test_centroid_euclidean_distance_zero_for_identical_groups():
    X = np.array([[1.0, 2.0], [1.0, 2.0], [1.0, 2.0]])
    assert centroid_euclidean_distance(X, X) == 0.0


def test_centroid_euclidean_distance_positive_for_shifted_groups():
    rng = np.random.default_rng(0)
    X_a = rng.normal(loc=0.0, size=(50, 3))
    X_b = rng.normal(loc=5.0, size=(50, 3))
    dist = centroid_euclidean_distance(X_a, X_b)
    assert dist > 5.0


def test_mahalanobis_centroid_distance_scale_invariant_ish():
    rng = np.random.default_rng(0)
    X_a = rng.normal(loc=0.0, scale=3.0, size=(100, 2))
    X_b = rng.normal(loc=6.0, scale=3.0, size=(100, 2))
    dist = mahalanobis_centroid_distance(X_a, X_b)
    assert dist is not None
    assert dist > 0.5


def test_mmd_rbf_small_for_same_distribution_large_for_different():
    rng = np.random.default_rng(0)
    X_a = rng.normal(size=(100, 3))
    X_b_same = rng.normal(size=(100, 3))
    X_b_diff = rng.normal(loc=8.0, size=(100, 3))
    mmd_same = mmd_rbf_unbiased(X_a, X_b_same)
    mmd_diff = mmd_rbf_unbiased(X_a, X_b_diff)
    assert mmd_same is not None and mmd_diff is not None
    assert mmd_diff > mmd_same
    assert mmd_diff > 0.5


def test_mann_whitney_effect_size_large_for_separated_groups():
    rng = np.random.default_rng(0)
    a = rng.normal(loc=0.0, size=100)
    b = rng.normal(loc=10.0, size=100)
    res = mann_whitney_with_effect_size(a, b)
    assert res.pvalue is not None and res.pvalue < 0.001
    assert abs(res.rank_biserial) > 0.9
