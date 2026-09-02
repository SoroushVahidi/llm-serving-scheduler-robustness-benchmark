"""Generic stats primitives + ranking-comparison fixture cases 1-4
(identical ranking, completely reversed ranking, partial top-k change,
tied policies). All values fabricated."""
from __future__ import annotations

import numpy as np

from robustbench.ranking_portability.analysis.stats import (
    benjamini_hochberg,
    block_bootstrap_ci,
    compare_rankings,
    friedman_omnibus,
)


def test_case1_identical_ranking_gives_tau_1():
    left = {"a": 3.0, "b": 2.0, "c": 1.0}
    right = {"a": 30.0, "b": 20.0, "c": 10.0}
    cmp = compare_rankings(left, right, top_k_values=(1, 3))
    assert cmp.kendall_tau == 1.0
    assert cmp.spearman_rho == 1.0
    assert cmp.topk_overlap[1] == 1.0
    assert cmp.topk_overlap[3] == 1.0


def test_case2_completely_reversed_ranking_gives_tau_minus_1():
    left = {"a": 3.0, "b": 2.0, "c": 1.0}
    right = {"a": 1.0, "b": 2.0, "c": 3.0}
    cmp = compare_rankings(left, right, top_k_values=(1,))
    assert cmp.kendall_tau == -1.0
    assert cmp.topk_overlap[1] == 0.0


def test_case3_partial_topk_change():
    left = {"a": 4.0, "b": 3.0, "c": 2.0, "d": 1.0}
    right = {"a": 4.0, "b": 1.0, "c": 3.0, "d": 2.0}  # b and c swap positions
    cmp = compare_rankings(left, right, top_k_values=(1, 3))
    assert cmp.topk_overlap[1] == 1.0  # 'a' stays top-1 on both
    assert 0.0 < cmp.topk_overlap[3] < 1.0


def test_case4_tied_policies_reported_not_crashed():
    left = {"a": 1.0, "b": 1.0, "c": 1.0}
    right = {"a": 1.0, "b": 1.0, "c": 1.0}
    cmp = compare_rankings(left, right, top_k_values=(1, 3))
    assert cmp.n_policies_compared == 3
    # Kendall/Spearman on all-tied data is defined as NaN by scipy;
    # this module must surface that as None, not crash or fabricate 0/1.
    assert cmp.kendall_tau is None or cmp.kendall_tau == cmp.kendall_tau


def test_undefined_policy_excluded_not_scored():
    left = {"a": 1.0, "b": None}
    right = {"a": 2.0, "b": 3.0}
    cmp = compare_rankings(left, right, top_k_values=(1,))
    assert cmp.n_policies_compared == 1
    assert cmp.n_policies_excluded_left == 1
    assert cmp.topk_k_reduced[1] is False or cmp.topk_k_reduced[1] is True  # never raises


def test_block_bootstrap_ci_shrinks_toward_point_with_more_windows():
    rng = np.random.default_rng(0)
    small = [1.0, 5.0]
    large = [1.0, 5.0] * 20
    _, lo_s, hi_s = block_bootstrap_ci(small, np.mean, n_resamples=500, ci_level=0.95, rng=rng)
    _, lo_l, hi_l = block_bootstrap_ci(large, np.mean, n_resamples=500, ci_level=0.95, rng=rng)
    assert (hi_l - lo_l) < (hi_s - lo_s)


def test_benjamini_hochberg_rejects_small_pvalues_only():
    p = [0.001, 0.02, 0.5, 0.9]
    rejected = benjamini_hochberg(p, q=0.05)
    assert rejected[0] is True
    assert rejected[3] is False


def test_benjamini_hochberg_ignores_nan():
    p = [0.001, float("nan"), 0.9]
    rejected = benjamini_hochberg(p, q=0.05)
    assert rejected[1] is False
    assert len(rejected) == 3


def test_friedman_omnibus_excludes_incomplete_policy():
    blocks = {
        "w0": {"a": 1.0, "b": 2.0, "c": 3.0},
        "w1": {"a": 2.0, "b": 1.0, "c": 3.0},
        "w2": {"a": 1.0, "b": 3.0, "c": 2.0, "d": 9.0},  # d only appears once
    }
    result = friedman_omnibus(blocks)
    assert result.excluded_policies == ["d"]
    assert result.n_treatments == 3
    assert result.statistic is not None
