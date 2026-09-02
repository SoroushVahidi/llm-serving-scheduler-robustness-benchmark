"""Ranking-aggregation exclusion semantics: fixture cases 8 (zero-completion),
9 (undefined conditional metric), 10 (TTFT-specific undefined case),
11 (style-policy exclusion from PRIMARY)."""
from __future__ import annotations

from robustbench.ranking_portability.analysis.ranking_analysis import (
    aggregate_condition_ranking,
    compare_conditions,
    per_window_policy_values,
)
from robustbench.ranking_portability.analysis.robustness import filter_primary_only
from ranking_portability_analysis_fixtures import (
    make_cell_row,
    make_ttft_undefined_row,
    make_zero_completion_row,
)


def test_case8_9_zero_completion_excludes_conditional_metric_only():
    rows = [
        make_zero_completion_row(source_family="burstgpt", window_id="w0", load_region="KNEE", policy_id="fifo"),
        make_cell_row(source_family="burstgpt", window_id="w0", load_region="KNEE", policy_id="edf"),
    ]
    pw_anwg = per_window_policy_values(rows, "arrival_normalized_weighted_goodput")
    # ALWAYS_DEFINED metric: fifo still contributes a value even at zero completion.
    assert "fifo" in pw_anwg["w0"]

    pw_slo = per_window_policy_values(rows, "slo_violation_rate")
    # CONDITIONAL_ON_COMPLETION metric: fifo excluded, edf still present.
    assert "fifo" not in pw_slo["w0"]
    assert "edf" in pw_slo["w0"]


def test_case9_undefined_conditional_metric_excludes_policy_from_ranking_only():
    rows = [
        make_zero_completion_row(source_family="burstgpt", window_id="w0", load_region="KNEE", policy_id="fifo"),
        make_cell_row(source_family="burstgpt", window_id="w0", load_region="KNEE", policy_id="edf"),
    ]
    agg = aggregate_condition_ranking(
        per_window_policy_values(rows, "weighted_goodput"), all_policies=["fifo", "edf"],
    )
    assert agg.values["fifo"] is None
    assert agg.values["edf"] is not None
    assert "fifo" in agg.excluded_policies_no_defined_value


def test_case10_ttft_undefined_independent_of_completion_fraction():
    rows = [
        make_ttft_undefined_row(source_family="burstgpt", window_id="w0", load_region="KNEE", policy_id="fifo"),
        make_cell_row(source_family="burstgpt", window_id="w0", load_region="KNEE", policy_id="edf"),
    ]
    pw_ttft = per_window_policy_values(rows, "mean_ttft")
    pw_completion = per_window_policy_values(rows, "completion_fraction")
    # fifo has completion_fraction=1.0 (defined) but mean_ttft is still
    # excluded -- a stricter, independently-checked precondition.
    assert "fifo" in pw_completion["w0"]
    assert "fifo" not in pw_ttft["w0"]


def test_case11_style_approximation_excluded_from_primary_filter():
    rows = [
        make_cell_row(window_id="w0", policy_id="fifo"),
        make_cell_row(window_id="w0", policy_id="vllm_style_token_budget"),
        make_cell_row(window_id="w0", policy_id="scorpio_style_slo_guard"),
    ]
    primary_only = filter_primary_only(rows)
    policy_ids = {r["policy_id"] for r in primary_only}
    assert policy_ids == {"fifo"}


def test_n_conditions_excluded_reported_in_comparison():
    rows_x = [
        make_zero_completion_row(source_family="burstgpt", window_id="w0", load_region="KNEE", policy_id="fifo"),
        make_cell_row(source_family="burstgpt", window_id="w0", load_region="KNEE", policy_id="edf"),
    ]
    rows_y = [
        make_cell_row(source_family="azure_llm_2024", window_id="w1", load_region="KNEE", policy_id="fifo"),
        make_cell_row(source_family="azure_llm_2024", window_id="w1", load_region="KNEE", policy_id="edf"),
    ]
    result = compare_conditions(
        rows_x, rows_y, metric="slo_violation_rate", all_policies=["fifo", "edf"],
        condition_x_label="burstgpt", condition_y_label="azure_llm_2024",
        n_resamples=50,
    )
    assert result.n_conditions_excluded_for_undefined_metric >= 1
