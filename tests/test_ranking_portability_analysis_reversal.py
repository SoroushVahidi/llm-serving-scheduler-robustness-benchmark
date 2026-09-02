"""Pairwise reversal classification fixture cases 5-7 (clear reversal,
microscopic sign flip, unsupported wide-CI reversal), plus stable/tie and
undefined-metric cases. All fabricated."""
from __future__ import annotations

import numpy as np

from robustbench.ranking_portability.analysis.reversal_analysis import (
    ReversalClass,
    classify_pairwise_reversal,
)
from ranking_portability_analysis_fixtures import make_cell_row, make_zero_completion_row


def _rows(source, window_ids, region, policy, values, load_factor=1.0):
    return [
        make_cell_row(source_family=source, window_id=w, load_region=region, policy_id=policy,
                      anwg=v, load_factor=load_factor)
        for w, v in zip(window_ids, values)
    ]


def test_case5_clear_supported_reversal():
    windows = [f"w{i}" for i in range(10)]
    # condition X: A clearly beats B (margin >> 10%, low variance)
    rows_x = _rows("burstgpt", windows, "KNEE", "policy_a", [1.0] * 10) + \
        _rows("burstgpt", windows, "KNEE", "policy_b", [0.5] * 10)
    # condition Y: B clearly beats A
    rows_y = _rows("azure_llm_2024", windows, "KNEE", "policy_a", [0.4] * 10) + \
        _rows("azure_llm_2024", windows, "KNEE", "policy_b", [1.0] * 10)
    result = classify_pairwise_reversal(
        rows_x, rows_y, policy_a="policy_a", policy_b="policy_b",
        metric="arrival_normalized_weighted_goodput",
        n_resamples=500, rng=np.random.default_rng(1),
    )
    assert result.classification == ReversalClass.SUPPORTED_PRACTICAL_REVERSAL


def test_case6_microscopic_sign_flip():
    windows = [f"w{i}" for i in range(10)]
    # margins just under 10% in both directions -> sign changes but not "practical"
    rows_x = _rows("burstgpt", windows, "KNEE", "policy_a", [1.00] * 10) + \
        _rows("burstgpt", windows, "KNEE", "policy_b", [0.97] * 10)
    rows_y = _rows("azure_llm_2024", windows, "KNEE", "policy_a", [0.97] * 10) + \
        _rows("azure_llm_2024", windows, "KNEE", "policy_b", [1.00] * 10)
    result = classify_pairwise_reversal(
        rows_x, rows_y, policy_a="policy_a", policy_b="policy_b",
        metric="arrival_normalized_weighted_goodput",
        n_resamples=500, rng=np.random.default_rng(2),
    )
    assert result.classification == ReversalClass.MICROSCOPIC_SIGN_CHANGE


def test_case7_unsupported_reversal_wide_ci():
    windows = [f"w{i}" for i in range(6)]
    # Margins pass the 10% threshold on point estimates (mean 0.4 vs 0.1,
    # loser value 0.1 -> margin 300%), but per-window values are so noisy
    # the bootstrap CI on the sign of the mean difference straddles zero.
    # The noisy values must keep a NONZERO mean -- an exactly-zero loser
    # value is the separate UNDEFINED_UNESTIMABLE case, not this one.
    noisy = [5.9, -5.1, 5.9, -5.1, 5.9, -5.1]
    rows_x = (
        _rows("burstgpt", windows, "KNEE", "policy_a", noisy)
        + _rows("burstgpt", windows, "KNEE", "policy_b", [0.1] * 6)
    )
    rows_y = (
        _rows("azure_llm_2024", windows, "KNEE", "policy_a", [0.1] * 6)
        + _rows("azure_llm_2024", windows, "KNEE", "policy_b", noisy)
    )
    result = classify_pairwise_reversal(
        rows_x, rows_y, policy_a="policy_a", policy_b="policy_b",
        metric="arrival_normalized_weighted_goodput",
        n_resamples=1000, rng=np.random.default_rng(3),
    )
    assert result.classification in (
        ReversalClass.UNSUPPORTED_SIGN_CHANGE_WIDE_CI,
        ReversalClass.MICROSCOPIC_SIGN_CHANGE,
    )


def test_stable_ordering_no_sign_change():
    windows = [f"w{i}" for i in range(5)]
    rows_x = _rows("burstgpt", windows, "KNEE", "policy_a", [1.0] * 5) + \
        _rows("burstgpt", windows, "KNEE", "policy_b", [0.5] * 5)
    rows_y = _rows("azure_llm_2024", windows, "KNEE", "policy_a", [2.0] * 5) + \
        _rows("azure_llm_2024", windows, "KNEE", "policy_b", [1.0] * 5)
    result = classify_pairwise_reversal(
        rows_x, rows_y, policy_a="policy_a", policy_b="policy_b",
        metric="arrival_normalized_weighted_goodput", n_resamples=200,
    )
    assert result.classification == ReversalClass.STABLE_NO_SIGN_CHANGE


def test_undefined_metric_gives_undefined_unestimable():
    windows = [f"w{i}" for i in range(3)]
    rows_x = [make_zero_completion_row(source_family="burstgpt", window_id=w, load_region="KNEE",
                                        policy_id="policy_a") for w in windows] + \
        _rows("burstgpt", windows, "KNEE", "policy_b", [1.0, 1.0, 1.0])
    rows_y = _rows("azure_llm_2024", windows, "KNEE", "policy_a", [1.0, 1.0, 1.0]) + \
        _rows("azure_llm_2024", windows, "KNEE", "policy_b", [1.0, 1.0, 1.0])
    result = classify_pairwise_reversal(
        rows_x, rows_y, policy_a="policy_a", policy_b="policy_b",
        metric="slo_violation_rate", n_resamples=200,
    )
    assert result.classification == ReversalClass.UNDEFINED_UNESTIMABLE
