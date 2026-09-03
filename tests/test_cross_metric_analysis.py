"""Fabricated-fixture tests for the post-Phase12 cross-metric portability
analysis extension (POST_PHASE12_RESULT_INDEPENDENT_ANALYSIS_EXTENSION).

No real Phase-12 row is used anywhere in this file, per the same
result-blindness discipline as the sealed analysis package's own test
suite. See docs/CROSS_METRIC_ANALYSIS_PROTOCOL_20260903.md.
"""
from __future__ import annotations

import pytest

from robustbench.analysis.cross_metric import (
    MIN_COMMON_POLICIES,
    CrossMetricDisagreementClass,
    all_metric_pairs,
    build_metric_eligibility_table,
    classify_pairwise_disagreement,
    compare_metrics_for_condition,
    eligible_metric_names,
    source_region_conditions,
)


def _row(window_id, policy_id, **metrics):
    row = {
        "window_id": window_id, "policy_id": policy_id,
        "source_family": "fake_source", "load_region": "FAKE_REGION",
    }
    row.update(metrics)
    return row


def _rows(window_ids, policy_values_by_metric):
    """policy_values_by_metric: {metric: {policy: [per-window values]}}"""
    rows = []
    all_policies = set()
    for by_policy in policy_values_by_metric.values():
        all_policies |= set(by_policy.keys())
    for wi, w in enumerate(window_ids):
        for p in sorted(all_policies):
            cell = {}
            for metric, by_policy in policy_values_by_metric.items():
                if p in by_policy:
                    cell[metric] = by_policy[p][wi]
            rows.append(_row(w, p, **cell))
    return rows


WINDOWS_4 = ["w0", "w1", "w2", "w3"]


# ---------------------------------------------------------------------------
# 1. Identical rankings -> tau = 1
# ---------------------------------------------------------------------------

def test_identical_rankings_tau_equals_one():
    policies = ["A", "B", "C", "D"]
    # Same values on both metrics (both HIGHER_BETTER real metric names).
    values = {p: [10.0 + i, 20.0 + i, 30.0 + i, 40.0 + i] for i, p in enumerate(policies)}
    rows = _rows(WINDOWS_4, {
        "completion_fraction": values,
        "weighted_completion_fraction": values,
    })
    res = compare_metrics_for_condition(
        rows, source="s", region="r",
        metric_a="completion_fraction", metric_b="weighted_completion_fraction",
        all_policies=policies,
    )
    assert res.status == "OK"
    assert res.kendall_tau_b == pytest.approx(1.0)
    assert res.spearman_rho == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# 2. Exactly reversed rankings -> tau = -1
# ---------------------------------------------------------------------------

def test_exactly_reversed_rankings_tau_equals_minus_one():
    policies = ["A", "B", "C", "D"]
    values_a = {p: [10.0 + 5 * i] * 4 for i, p in enumerate(policies)}
    values_b = {p: [-(10.0 + 5 * i)] * 4 for i, p in enumerate(policies)}
    rows = _rows(WINDOWS_4, {
        "completion_fraction": values_a,
        "weighted_completion_fraction": values_b,
    })
    res = compare_metrics_for_condition(
        rows, source="s", region="r",
        metric_a="completion_fraction", metric_b="weighted_completion_fraction",
        all_policies=policies,
    )
    assert res.kendall_tau_b == pytest.approx(-1.0)
    assert res.spearman_rho == pytest.approx(-1.0)


# ---------------------------------------------------------------------------
# 3. Mixed / tied rankings
# ---------------------------------------------------------------------------

def test_mixed_tied_rankings_does_not_crash_and_bounded():
    policies = ["A", "B", "C", "D"]
    values_a = {"A": [1.0] * 4, "B": [1.0] * 4, "C": [2.0] * 4, "D": [3.0] * 4}
    values_b = {"A": [5.0] * 4, "B": [1.0] * 4, "C": [1.0] * 4, "D": [9.0] * 4}
    rows = _rows(WINDOWS_4, {
        "completion_fraction": values_a,
        "weighted_completion_fraction": values_b,
    })
    res = compare_metrics_for_condition(
        rows, source="s", region="r",
        metric_a="completion_fraction", metric_b="weighted_completion_fraction",
        all_policies=policies,
    )
    assert res.status == "OK"
    assert -1.0 <= res.kendall_tau_b <= 1.0
    assert -1.0 <= res.spearman_rho <= 1.0


# ---------------------------------------------------------------------------
# 4. Higher-is-better vs lower-is-better normalization
# ---------------------------------------------------------------------------

def test_direction_normalization_higher_vs_lower_is_better():
    policies = ["A", "B", "C", "D"]
    # completion_fraction (HIGHER_BETTER): increasing with policy index
    # (D is genuinely best). mean_latency (LOWER_BETTER): DECREASING raw
    # value with policy index (D has the lowest/best raw latency too) --
    # i.e. D is genuinely best on both metrics, A genuinely worst on
    # both. After direction normalization (negate latency so higher is
    # better), both normalized rankings agree: tau = +1. Comparing the
    # RAW (un-normalized) values directly would wrongly show tau = -1.
    values_cf = {p: [10.0 + i] * 4 for i, p in enumerate(policies)}
    values_lat = {p: [10.0 - i] * 4 for i, p in enumerate(policies)}
    rows = _rows(WINDOWS_4, {
        "completion_fraction": values_cf,
        "mean_latency": values_lat,
    })
    res = compare_metrics_for_condition(
        rows, source="s", region="r",
        metric_a="completion_fraction", metric_b="mean_latency",
        all_policies=policies,
    )
    assert res.kendall_tau_b == pytest.approx(1.0)
    assert res.spearman_rho == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# 5. Top-1 agreement
# ---------------------------------------------------------------------------

def test_top1_agreement_disagrees_when_best_policy_differs():
    policies = ["A", "B", "C", "D"]
    values_a = {"A": [4.0] * 4, "B": [3.0] * 4, "C": [2.0] * 4, "D": [1.0] * 4}  # best=A
    values_b = {"A": [1.0] * 4, "B": [2.0] * 4, "C": [3.0] * 4, "D": [4.0] * 4}  # best=D
    rows = _rows(WINDOWS_4, {
        "completion_fraction": values_a,
        "weighted_completion_fraction": values_b,
    })
    res = compare_metrics_for_condition(
        rows, source="s", region="r",
        metric_a="completion_fraction", metric_b="weighted_completion_fraction",
        all_policies=policies,
    )
    assert res.top1_agreement == pytest.approx(0.0)


def test_top1_agreement_agrees_when_best_policy_same():
    policies = ["A", "B", "C", "D"]
    values_a = {"A": [4.0] * 4, "B": [3.0] * 4, "C": [2.0] * 4, "D": [1.0] * 4}  # best=A
    values_b = {"A": [9.0] * 4, "B": [1.0] * 4, "C": [2.0] * 4, "D": [3.0] * 4}  # best=A
    rows = _rows(WINDOWS_4, {
        "completion_fraction": values_a,
        "weighted_completion_fraction": values_b,
    })
    res = compare_metrics_for_condition(
        rows, source="s", region="r",
        metric_a="completion_fraction", metric_b="weighted_completion_fraction",
        all_policies=policies,
    )
    assert res.top1_agreement == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# 6. Top-3 overlap
# ---------------------------------------------------------------------------

def test_top3_overlap_partial():
    policies = ["A", "B", "C", "D", "E"]
    # metric_a top-3 = {A, B, C}; metric_b top-3 = {A, B, D} -> overlap 2/3
    values_a = {"A": [5.0] * 4, "B": [4.0] * 4, "C": [3.0] * 4, "D": [2.0] * 4, "E": [1.0] * 4}
    values_b = {"A": [5.0] * 4, "B": [4.0] * 4, "C": [1.0] * 4, "D": [3.0] * 4, "E": [2.0] * 4}
    rows = _rows(WINDOWS_4, {
        "completion_fraction": values_a,
        "weighted_completion_fraction": values_b,
    })
    res = compare_metrics_for_condition(
        rows, source="s", region="r",
        metric_a="completion_fraction", metric_b="weighted_completion_fraction",
        all_policies=policies,
    )
    assert res.top3_overlap == pytest.approx(2.0 / 3.0)


# ---------------------------------------------------------------------------
# 7. Common-policy intersection
# ---------------------------------------------------------------------------

def test_common_policy_intersection_excludes_metric_specific_missing_policy():
    policies = ["A", "B", "C", "D"]
    values_a = {"A": [1.0] * 4, "B": [2.0] * 4, "C": [3.0] * 4, "D": [4.0] * 4}
    values_b = {"A": [4.0] * 4, "B": [3.0] * 4, "C": [2.0] * 4}  # D undefined for metric_b
    rows = _rows(WINDOWS_4, {
        "completion_fraction": values_a,
        "weighted_completion_fraction": values_b,
    })
    res = compare_metrics_for_condition(
        rows, source="s", region="r",
        metric_a="completion_fraction", metric_b="weighted_completion_fraction",
        all_policies=policies,
    )
    assert res.effective_policy_count == 3


# ---------------------------------------------------------------------------
# 8. Undefined values -- never zero-imputed
# ---------------------------------------------------------------------------

def test_undefined_values_never_zero_imputed():
    policies = ["A", "B", "C", "D", "E"]
    values_a = {"A": [1.0] * 4, "B": [2.0] * 4, "C": [3.0] * 4, "D": [4.0] * 4, "E": [5.0] * 4}
    # E's mean_latency is NaN for every window (e.g. never completed) --
    # must be excluded, never treated as 0.0 (which would make it the
    # "best" LOWER_BETTER value and corrupt the ranking).
    values_b = {"A": [8.0] * 4, "B": [6.0] * 4, "C": [4.0] * 4, "D": [2.0] * 4, "E": [float("nan")] * 4}
    rows = _rows(WINDOWS_4, {
        "completion_fraction": values_a,
        "mean_latency": values_b,
    })
    res = compare_metrics_for_condition(
        rows, source="s", region="r",
        metric_a="completion_fraction", metric_b="mean_latency",
        all_policies=policies,
    )
    # Only A, B, C, D compared -- E excluded, never imputed as 0.0 (which
    # would falsely make E the "best" LOWER_BETTER latency).
    assert res.effective_policy_count == 4
    # A..D: completion_fraction increases 1->4 (better); mean_latency
    # decreases 8->2 (also better, since lower is better) -- both
    # genuinely improve together, so after direction normalization tau=+1.
    assert res.kendall_tau_b == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# 9. Insufficient policies
# ---------------------------------------------------------------------------

def test_insufficient_common_policies_flagged_undefined():
    policies = ["A", "B"]
    values_a = {"A": [1.0] * 4, "B": [2.0] * 4}
    values_b = {"A": [4.0] * 4, "B": [3.0] * 4}
    rows = _rows(WINDOWS_4, {
        "completion_fraction": values_a,
        "weighted_completion_fraction": values_b,
    })
    res = compare_metrics_for_condition(
        rows, source="s", region="r",
        metric_a="completion_fraction", metric_b="weighted_completion_fraction",
        all_policies=policies,
    )
    assert res.status == "UNDEFINED_INSUFFICIENT_COMMON_POLICIES"
    assert res.kendall_tau_b is None
    assert res.kendall_ci is None
    assert res.effective_policy_count < MIN_COMMON_POLICIES


# ---------------------------------------------------------------------------
# 10. Deterministic bootstrap
# ---------------------------------------------------------------------------

def test_bootstrap_ci_deterministic_across_repeated_calls():
    policies = ["A", "B", "C", "D", "E"]
    values_a = {p: [1.0 + i + 0.1 * wi for wi in range(4)] for i, p in enumerate(policies)}
    values_b = {p: [5.0 - i + 0.2 * wi for wi in range(4)] for i, p in enumerate(policies)}
    rows = _rows(WINDOWS_4, {
        "completion_fraction": values_a,
        "weighted_completion_fraction": values_b,
    })
    kwargs = dict(
        rows=rows, source="fixed_source", region="fixed_region",
        metric_a="completion_fraction", metric_b="weighted_completion_fraction",
        all_policies=policies, n_resamples=200,
    )
    res1 = compare_metrics_for_condition(**kwargs)
    res2 = compare_metrics_for_condition(**kwargs)
    assert res1.kendall_ci == res2.kendall_ci
    assert res1.spearman_ci == res2.spearman_ci


# ---------------------------------------------------------------------------
# 11. Stable output ordering
# ---------------------------------------------------------------------------

def test_metric_pairs_stable_ordering_independent_of_input_order():
    metrics_a = ["z_metric", "a_metric", "m_metric"]
    metrics_b = ["m_metric", "z_metric", "a_metric"]
    assert all_metric_pairs(metrics_a) == all_metric_pairs(metrics_b)
    assert all_metric_pairs(metrics_a) == [
        ("a_metric", "m_metric"), ("a_metric", "z_metric"), ("m_metric", "z_metric"),
    ]


def test_source_region_conditions_deterministic_and_count_18():
    from robustbench.ranking_portability.analysis.contract import CAMPAIGN_SOURCES, SIX_REGION_GRID
    conditions = source_region_conditions()
    assert len(conditions) == 18
    assert len(set(conditions)) == 18
    # Sources are alphabetized; within each source, regions follow the
    # frozen operational SIX_REGION_GRID order (not lexicographic --
    # e.g. "HIGH_PRESSURE" sorts before "LOW" alphabetically but must
    # appear last, per the frozen contract grid ordering).
    assert conditions == [(s, r) for s in sorted(CAMPAIGN_SOURCES) for r in SIX_REGION_GRID]
    assert source_region_conditions() == conditions  # deterministic across calls


# ---------------------------------------------------------------------------
# 12. Duplicate-key prevention
# ---------------------------------------------------------------------------

def test_all_metric_pairs_no_duplicates():
    pairs = all_metric_pairs(list(eligible_metric_names()))
    assert len(pairs) == len(set(pairs))
    keys = [(p[0], p[1]) for p in pairs]
    assert len(keys) == len(set(keys))


# ---------------------------------------------------------------------------
# 13 & 14. metric_a != metric_b; no same-metric comparisons
# ---------------------------------------------------------------------------

def test_same_metric_comparison_rejected():
    rows = _rows(WINDOWS_4, {"completion_fraction": {"A": [1.0] * 4, "B": [2.0] * 4}})
    with pytest.raises(ValueError):
        compare_metrics_for_condition(
            rows, source="s", region="r",
            metric_a="completion_fraction", metric_b="completion_fraction",
            all_policies=["A", "B"],
        )


def test_all_metric_pairs_never_contains_same_metric_twice():
    for a, b in all_metric_pairs(list(eligible_metric_names())):
        assert a != b


# ---------------------------------------------------------------------------
# Metric eligibility table structural checks
# ---------------------------------------------------------------------------

def test_metric_eligibility_table_covers_all_11_no_invention():
    table = build_metric_eligibility_table()
    names = {m.metric_name for m in table}
    assert len(names) == 11
    for m in table:
        assert m.optimization_direction in ("HIGHER_BETTER", "LOWER_BETTER")
        assert m.conditioning in ("ALL_REQUESTS", "COMPLETED_ONLY", "OTHER")
        assert m.eligible_for_cross_metric == "YES"
        assert m.undefined_semantics


def test_eligible_metric_names_matches_table():
    assert set(eligible_metric_names()) == {m.metric_name for m in build_metric_eligibility_table()}


# ---------------------------------------------------------------------------
# Pairwise disagreement classification (section G)
# ---------------------------------------------------------------------------

def test_disagreement_same_order_no_sign_change():
    windows = ["w0", "w1", "w2", "w3"]
    values_a = {"X": [10.0] * 4, "Y": [1.0] * 4}
    values_b = {"X": [20.0] * 4, "Y": [2.0] * 4}
    rows = _rows(windows, {"completion_fraction": values_a, "weighted_completion_fraction": values_b})
    res = classify_pairwise_disagreement(
        rows, source="s", region="r",
        metric_a="completion_fraction", metric_b="weighted_completion_fraction",
        policy_x="X", policy_y="Y",
    )
    assert res.classification == CrossMetricDisagreementClass.SAME_ORDER


def test_disagreement_undefined_when_policy_missing():
    windows = ["w0", "w1", "w2", "w3"]
    values_a = {"X": [10.0] * 4, "Y": [1.0] * 4}
    values_b = {"X": [20.0] * 4}  # Y undefined
    rows = _rows(windows, {"completion_fraction": values_a, "weighted_completion_fraction": values_b})
    res = classify_pairwise_disagreement(
        rows, source="s", region="r",
        metric_a="completion_fraction", metric_b="weighted_completion_fraction",
        policy_x="X", policy_y="Y",
    )
    assert res.classification == CrossMetricDisagreementClass.UNDEFINED


def test_disagreement_microscopic_sign_change_below_margin():
    windows = ["w0", "w1", "w2", "w3"]
    # metric_a: X slightly > Y (sign +); metric_b: X slightly < Y (sign -)
    # but margin well under the 10% practical threshold on both sides.
    values_a = {"X": [10.01] * 4, "Y": [10.0] * 4}
    values_b = {"X": [9.99] * 4, "Y": [10.0] * 4}
    rows = _rows(windows, {"completion_fraction": values_a, "weighted_completion_fraction": values_b})
    res = classify_pairwise_disagreement(
        rows, source="s", region="r",
        metric_a="completion_fraction", metric_b="weighted_completion_fraction",
        policy_x="X", policy_y="Y",
    )
    assert res.classification == CrossMetricDisagreementClass.SIGN_CHANGE_MICROSCOPIC


def test_disagreement_supported_practical_disagreement():
    windows = [f"w{i}" for i in range(20)]
    # metric_a: X consistently much better than Y (sign +, large margin).
    # metric_b (after direction normalization): Y consistently much
    # better than X (sign -, large margin), with tiny window-to-window
    # noise so the bootstrap CI is tight and excludes zero on both sides.
    values_a = {"X": [10.0 + 0.001 * i for i in range(20)], "Y": [1.0 + 0.001 * i for i in range(20)]}
    values_b = {"X": [10.0 + 0.001 * i for i in range(20)], "Y": [1.0 + 0.001 * i for i in range(20)]}
    rows = _rows(windows, {"completion_fraction": values_a, "mean_latency": values_b})
    res = classify_pairwise_disagreement(
        rows, source="s", region="r",
        metric_a="completion_fraction", metric_b="mean_latency",
        policy_x="X", policy_y="Y",
        n_resamples=500,
    )
    assert res.classification == CrossMetricDisagreementClass.SUPPORTED_PRACTICAL_DISAGREEMENT
    assert res.p_a is not None and res.p_b is not None
