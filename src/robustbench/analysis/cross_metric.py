"""Post-Phase12 cross-metric portability analysis.

POST_PHASE12_RESULT_INDEPENDENT_ANALYSIS_EXTENSION: this module was
NOT part of the sealed Phase-12 analysis package
(`robustbench.ranking_portability.analysis`, frozen at
eb574a8ce5c34a80fddbcfd4417f6626fbdddfd1, docs/RANKING_PORTABILITY_
PHASE12_ANALYSIS_PREFREEZE.md). It answers a different question the
sealed package never asked: for the SAME source and load region, how
portable is a scheduler ranking across DIFFERENT metrics (e.g. does the
policy ranking under `mean_latency` agree with the ranking under
`slo_violation_rate`)? The sealed package only ever compares one fixed
metric across different conditions (sources, regions, temporal splits).

This module never modifies, re-runs, or re-derives the six sealed
canonical Phase-12 outputs; it reuses their statistical primitives as a
library (`stats.compare_rankings`, `ranking_analysis.per_window_policy_
values`/`aggregate_condition_ranking`, `reversal_analysis._diff_and_
margin`/`_bootstrap_diff_ci`) and writes into a wholly separate output
namespace (`artifacts/analysis/cross_metric_extension/<contract_hash>/`).

See docs/CROSS_METRIC_ANALYSIS_PROTOCOL_20260903.md and
configs/analysis/cross_metric_analysis_20260903.json for the frozen
contract this module implements; no threshold, metric-pair selection,
or seed here was chosen after inspecting any real Phase-12 outcome.
"""
from __future__ import annotations

import math
import zlib
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from robustbench.ranking_portability.analysis.contract import (
    ALL_RANKING_METRICS,
    ALWAYS_DEFINED_METRICS,
    CAMPAIGN_SOURCES,
    CONDITIONAL_ON_COMPLETION_METRICS,
    CONDITIONAL_ON_OTHER_PRECONDITION_METRICS,
    PRIMARY_POLICIES,
    SIX_REGION_GRID,
)
from robustbench.ranking_portability.analysis.ranking_analysis import (
    aggregate_condition_ranking,
    per_window_policy_values,
)
from robustbench.ranking_portability.analysis.reversal_analysis import (
    _bootstrap_diff_ci,
    _diff_and_margin,
)
from robustbench.ranking_portability.analysis.stats import (
    PairedRankingComparison,
    benjamini_hochberg,
    compare_rankings,
)

CROSS_METRIC_CONTRACT_VERSION = "cross_metric_analysis_v1"
SCIENTIFIC_STATUS_LABEL = "POST_PHASE12_RESULT_INDEPENDENT_ANALYSIS_EXTENSION"

TOP_K_VALUES = (1, 3)
N_BOOTSTRAP = 2000
BOOTSTRAP_CI_LEVEL = 0.95

# Frozen BEFORE execution, based on statistical validity, not outcomes:
# at n=2 common policies, Kendall tau-b is degenerate (only +1/-1 are
# possible, with no real distribution to estimate), so it carries no
# information beyond the raw sign. n=3 is the smallest common-policy
# count at which tau-b is a non-degenerate statistic.
MIN_COMMON_POLICIES = 3

# Reused as-is from the sealed reversal contract
# (docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md §A): a winning margin must
# exceed 10% of the LOSING POLICY'S OWN VALUE ON THAT SAME METRIC. This
# threshold is dimensionless BY CONSTRUCTION -- it is a self-relative
# ratio computed independently within each metric's own units, never a
# cross-metric unit comparison -- so it remains meaningful when metric_a
# and metric_b have heterogeneous units (e.g. seconds vs a violation
# fraction vs requests/second): each side of the intersection-union test
# only ever compares a metric to itself.
DISAGREEMENT_PRACTICAL_MARGIN_FRACTION = 0.10
DISAGREEMENT_CI_LEVEL = 0.95
DISAGREEMENT_FDR_Q = 0.05


def _is_defined(v) -> bool:
    return v is not None and not (isinstance(v, float) and math.isnan(v))


# ---------------------------------------------------------------------------
# D. Metric eligibility table (frozen; no metric invented, all field names
# verified against src/robustbench/ranking_portability/schema.py and
# docs/RANKING_PORTABILITY_METRIC_DEFINITIONS.md)
# ---------------------------------------------------------------------------

_UNDEFINED_SEMANTICS = {
    "arrival_normalized_weighted_goodput": "Never NaN for a real window (ALWAYS_DEFINED).",
    "completion_fraction": "Never NaN for a real window (ALWAYS_DEFINED); num_total > 0 always.",
    "weighted_completion_fraction": "Never NaN for a real window (ALWAYS_DEFINED).",
    "slo_violation_rate": "NaN iff completion_fraction == 0.0.",
    "weighted_goodput": "NaN iff completion_fraction == 0.0.",
    "mean_latency": "NaN iff completion_fraction == 0.0.",
    "p95_latency": "NaN iff completion_fraction == 0.0.",
    "request_throughput": "NaN iff completion_fraction == 0.0 (given sim_duration > 0).",
    "token_throughput": "NaN iff completion_fraction == 0.0 (given sim_duration > 0).",
    "mean_ttft": "NaN iff no completed request recorded a first-token time "
                 "(independent precondition, may be undefined even when completion_fraction > 0).",
    "p95_ttft": "NaN iff no completed request recorded a first-token time "
                "(independent precondition, may be undefined even when completion_fraction > 0).",
}

_HIGHER_BETTER = {
    "arrival_normalized_weighted_goodput": True,
    "completion_fraction": True,
    "weighted_completion_fraction": True,
    "slo_violation_rate": False,
    "weighted_goodput": True,
    "mean_latency": False,
    "p95_latency": False,
    "request_throughput": True,
    "token_throughput": True,
    "mean_ttft": False,
    "p95_ttft": False,
}


def _conditioning_of(metric: str) -> str:
    if metric in ALWAYS_DEFINED_METRICS:
        return "ALL_REQUESTS"
    if metric in CONDITIONAL_ON_COMPLETION_METRICS:
        return "COMPLETED_ONLY"
    if metric in CONDITIONAL_ON_OTHER_PRECONDITION_METRICS:
        return "OTHER"
    raise KeyError(metric)


@dataclass(frozen=True)
class MetricEligibility:
    metric_name: str
    optimization_direction: str  # HIGHER_BETTER / LOWER_BETTER
    conditioning: str  # ALL_REQUESTS / COMPLETED_ONLY / OTHER
    undefined_semantics: str
    eligible_for_cross_metric: str  # YES / NO
    reason: str


def build_metric_eligibility_table() -> List[MetricEligibility]:
    """No metric invented: enumerates exactly `ALL_RANKING_METRICS` from
    the sealed contract module (already verified against the live schema
    and the structural-completion audit's `metrics_present` list -- both
    list exactly these 11 field names)."""
    out = []
    for metric in ALL_RANKING_METRICS:
        out.append(MetricEligibility(
            metric_name=metric,
            optimization_direction="HIGHER_BETTER" if _HIGHER_BETTER[metric] else "LOWER_BETTER",
            conditioning=_conditioning_of(metric),
            undefined_semantics=_UNDEFINED_SEMANTICS[metric],
            eligible_for_cross_metric="YES",
            reason="supports per-policy ranking under the frozen metric contract "
                   "(docs/RANKING_PORTABILITY_METRIC_DEFINITIONS.md) with a defined "
                   "optimization direction and a documented undefined-value rule; "
                   "no a priori exclusion applies.",
        ))
    return out


def eligible_metric_names() -> Tuple[str, ...]:
    return tuple(m.metric_name for m in build_metric_eligibility_table() if m.eligible_for_cross_metric == "YES")


def all_metric_pairs(metrics: Sequence[str]) -> List[Tuple[str, str]]:
    """All unordered pairs among eligible metrics, deterministically
    ordered (sorted metric list, then lexicographic pair order) -- pairs
    are never selected or filtered based on any observed statistic."""
    ordered = sorted(metrics)
    pairs = []
    for i, a in enumerate(ordered):
        for b in ordered[i + 1:]:
            pairs.append((a, b))
    return pairs


def source_region_conditions() -> List[Tuple[str, str]]:
    return [(s, r) for s in sorted(CAMPAIGN_SOURCES) for r in SIX_REGION_GRID]


def _seed_for(*parts: str) -> int:
    """Deterministic seed derived from a stable string key -- independent
    of iteration/enumeration order, so re-running the analysis (or
    running a subset of conditions) always reproduces the same seed for
    the same (source, region, metric_a, metric_b) tuple."""
    key = "|".join(parts).encode("utf-8")
    return zlib.crc32(key) & 0xFFFFFFFF


def _normalize_direction(
    per_window: Mapping[str, Mapping[str, float]], higher_is_better: bool,
) -> Dict[str, Dict[str, float]]:
    """Negates values so that, after this call, HIGHER is always better --
    matching section E's "normalize all metrics so the ranking order is
    consistently better-first" rule. A pure value transform; does not
    touch which (window, policy) observations are defined."""
    if higher_is_better:
        return {w: dict(pv) for w, pv in per_window.items()}
    return {w: {p: -v for p, v in pv.items()} for w, pv in per_window.items()}


# ---------------------------------------------------------------------------
# F. Cross-metric correlation + top-k, one (source, region, metric_a, metric_b)
# ---------------------------------------------------------------------------

@dataclass
class CrossMetricComparisonResult:
    source: str
    region: str
    metric_a: str
    metric_b: str
    effective_policy_count: int
    policy_panel: Tuple[str, ...]
    kendall_tau_b: Optional[float]
    kendall_ci: Optional[Tuple[float, float]]
    spearman_rho: Optional[float]
    spearman_ci: Optional[Tuple[float, float]]
    top1_agreement: Optional[float]
    top3_overlap: Optional[float]
    bootstrap_count: int
    status: str  # OK / UNDEFINED_INSUFFICIENT_COMMON_POLICIES


def compare_metrics_for_condition(
    rows: Sequence[Mapping],
    *,
    source: str,
    region: str,
    metric_a: str,
    metric_b: str,
    all_policies: Sequence[str] = PRIMARY_POLICIES,
    n_resamples: int = N_BOOTSTRAP,
    ci_level: float = BOOTSTRAP_CI_LEVEL,
    top_k_values: Sequence[int] = TOP_K_VALUES,
    min_common_policies: int = MIN_COMMON_POLICIES,
) -> CrossMetricComparisonResult:
    if metric_a == metric_b:
        raise ValueError("metric_a must differ from metric_b -- no same-metric cross-metric comparisons")

    pw_a_raw = per_window_policy_values(rows, metric_a)
    pw_b_raw = per_window_policy_values(rows, metric_b)
    pw_a = _normalize_direction(pw_a_raw, _HIGHER_BETTER[metric_a])
    pw_b = _normalize_direction(pw_b_raw, _HIGHER_BETTER[metric_b])

    rank_a = aggregate_condition_ranking(pw_a, all_policies=all_policies)
    rank_b = aggregate_condition_ranking(pw_b, all_policies=all_policies)

    point = compare_rankings(rank_a.values, rank_b.values, top_k_values=top_k_values, higher_is_better=True)

    if point.n_policies_compared < min_common_policies:
        return CrossMetricComparisonResult(
            source=source, region=region, metric_a=metric_a, metric_b=metric_b,
            effective_policy_count=point.n_policies_compared,
            policy_panel=tuple(sorted(all_policies)),
            kendall_tau_b=None, kendall_ci=None,
            spearman_rho=None, spearman_ci=None,
            top1_agreement=None, top3_overlap=None,
            bootstrap_count=0,
            status="UNDEFINED_INSUFFICIENT_COMMON_POLICIES",
        )

    # Paired bootstrap: metric_a and metric_b are computed from the SAME
    # physical windows (same rows), unlike the sealed cross-source
    # comparison (which correlates genuinely independent window
    # populations and so resamples each side independently). Drawing one
    # shared window resample per iteration and re-deriving both metrics'
    # aggregate rankings from it preserves the natural within-window
    # correlation between metric_a and metric_b.
    windows = sorted(set(pw_a.keys()) | set(pw_b.keys()))
    rng = np.random.default_rng(_seed_for(source, region, metric_a, metric_b))
    taus: List[float] = []
    rhos: List[float] = []
    if windows:
        for _ in range(n_resamples):
            draw = rng.choice(windows, size=len(windows), replace=True)
            resampled_a = {f"{w}#{i}": pw_a[w] for i, w in enumerate(draw) if w in pw_a}
            resampled_b = {f"{w}#{i}": pw_b[w] for i, w in enumerate(draw) if w in pw_b}
            agg_a = aggregate_condition_ranking(resampled_a, all_policies=all_policies)
            agg_b = aggregate_condition_ranking(resampled_b, all_policies=all_policies)
            cmp = compare_rankings(agg_a.values, agg_b.values, top_k_values=top_k_values, higher_is_better=True)
            if cmp.kendall_tau is not None:
                taus.append(cmp.kendall_tau)
            if cmp.spearman_rho is not None:
                rhos.append(cmp.spearman_rho)

    alpha = 1.0 - ci_level
    kendall_ci = tuple(np.quantile(taus, [alpha / 2, 1 - alpha / 2])) if taus else None
    spearman_ci = tuple(np.quantile(rhos, [alpha / 2, 1 - alpha / 2])) if rhos else None

    return CrossMetricComparisonResult(
        source=source, region=region, metric_a=metric_a, metric_b=metric_b,
        effective_policy_count=point.n_policies_compared,
        policy_panel=tuple(sorted(all_policies)),
        kendall_tau_b=point.kendall_tau,
        kendall_ci=kendall_ci,
        spearman_rho=point.spearman_rho,
        spearman_ci=spearman_ci,
        top1_agreement=point.topk_overlap.get(1),
        top3_overlap=point.topk_overlap.get(3),
        bootstrap_count=n_resamples if windows else 0,
        status="OK",
    )


# ---------------------------------------------------------------------------
# G. Cross-metric pairwise policy disagreement classification
# ---------------------------------------------------------------------------

class CrossMetricDisagreementClass:
    UNDEFINED = "UNDEFINED"
    SAME_ORDER = "SAME_ORDER"
    SIGN_CHANGE_MICROSCOPIC = "SIGN_CHANGE_MICROSCOPIC"
    UNSUPPORTED_SIGN_CHANGE_WIDE_CI = "UNSUPPORTED_SIGN_CHANGE_WIDE_CI"
    SUPPORTED_PRACTICAL_DISAGREEMENT = "SUPPORTED_PRACTICAL_DISAGREEMENT"


@dataclass
class CrossMetricPairwiseDisagreement:
    source: str
    region: str
    metric_a: str
    metric_b: str
    policy_x: str
    policy_y: str
    classification: str
    diff_a: Optional[float]
    diff_b: Optional[float]
    margin_a: Optional[float]
    margin_b: Optional[float]
    ci_a: Optional[Tuple[float, float]]
    ci_b: Optional[Tuple[float, float]]
    p_a: Optional[float]
    p_b: Optional[float]


def classify_pairwise_disagreement(
    rows: Sequence[Mapping],
    *,
    source: str,
    region: str,
    metric_a: str,
    metric_b: str,
    policy_x: str,
    policy_y: str,
    margin_fraction: float = DISAGREEMENT_PRACTICAL_MARGIN_FRACTION,
    ci_level: float = DISAGREEMENT_CI_LEVEL,
    n_resamples: int = N_BOOTSTRAP,
) -> CrossMetricPairwiseDisagreement:
    """Same intersection-union logic as the sealed cross-condition
    reversal contract (reversal_analysis.classify_pairwise_reversal),
    adapted to compare two METRICS within the SAME (source, region)
    condition instead of one metric across two conditions. Reuses the
    sealed margin/bootstrap-CI primitives unchanged; direction-normalizes
    each metric independently before computing margins so a LOWER_BETTER
    metric's "winning" direction matches a HIGHER_BETTER metric's."""
    pw_a = _normalize_direction(per_window_policy_values(rows, metric_a), _HIGHER_BETTER[metric_a])
    pw_b = _normalize_direction(per_window_policy_values(rows, metric_b), _HIGHER_BETTER[metric_b])

    rank_a = aggregate_condition_ranking(pw_a, all_policies=[policy_x, policy_y])
    rank_b = aggregate_condition_ranking(pw_b, all_policies=[policy_x, policy_y])

    diff_a, margin_a = _diff_and_margin(rank_a.values[policy_x], rank_a.values[policy_y])
    diff_b, margin_b = _diff_and_margin(rank_b.values[policy_x], rank_b.values[policy_y])

    def _result(cls: str, ci_a=None, ci_b=None, p_a=None, p_b=None) -> CrossMetricPairwiseDisagreement:
        return CrossMetricPairwiseDisagreement(
            source=source, region=region, metric_a=metric_a, metric_b=metric_b,
            policy_x=policy_x, policy_y=policy_y, classification=cls,
            diff_a=diff_a, diff_b=diff_b, margin_a=margin_a, margin_b=margin_b,
            ci_a=ci_a, ci_b=ci_b, p_a=p_a, p_b=p_b,
        )

    if diff_a is None or diff_b is None or margin_a is None or margin_b is None:
        return _result(CrossMetricDisagreementClass.UNDEFINED)

    sign_a = 0 if diff_a == 0 else (1 if diff_a > 0 else -1)
    sign_b = 0 if diff_b == 0 else (1 if diff_b > 0 else -1)
    if sign_a == 0 or sign_b == 0 or sign_a == sign_b:
        return _result(CrossMetricDisagreementClass.SAME_ORDER)

    if not (margin_a > margin_fraction and margin_b > margin_fraction):
        return _result(CrossMetricDisagreementClass.SIGN_CHANGE_MICROSCOPIC)

    rng_a = np.random.default_rng(_seed_for(source, region, metric_a, metric_b, policy_x, policy_y, "a"))
    rng_b = np.random.default_rng(_seed_for(source, region, metric_a, metric_b, policy_x, policy_y, "b"))
    boot_a = _bootstrap_diff_ci(pw_a, policy_x, policy_y, n_resamples=n_resamples, ci_level=ci_level, rng=rng_a)
    boot_b = _bootstrap_diff_ci(pw_b, policy_x, policy_y, n_resamples=n_resamples, ci_level=ci_level, rng=rng_b)
    ci_a = (boot_a[0], boot_a[1]) if boot_a is not None else None
    ci_b = (boot_b[0], boot_b[1]) if boot_b is not None else None
    p_a = boot_a[2] if boot_a is not None else None
    p_b = boot_b[2] if boot_b is not None else None
    ci_a_excludes_zero = ci_a is not None and not (ci_a[0] <= 0 <= ci_a[1])
    ci_b_excludes_zero = ci_b is not None and not (ci_b[0] <= 0 <= ci_b[1])

    if ci_a_excludes_zero and ci_b_excludes_zero:
        return _result(CrossMetricDisagreementClass.SUPPORTED_PRACTICAL_DISAGREEMENT, ci_a, ci_b, p_a, p_b)
    return _result(CrossMetricDisagreementClass.UNSUPPORTED_SIGN_CHANGE_WIDE_CI, ci_a, ci_b, p_a, p_b)


def apply_bh_fdr_to_family(
    disagreements: Sequence[CrossMetricPairwiseDisagreement], *, q: float = DISAGREEMENT_FDR_Q,
) -> List[bool]:
    """BH-FDR family = all policy-pair disagreement tests that reached the
    statistical-support stage (i.e. carry both p_a and p_b) within ONE
    (source, region, metric_a, metric_b) condition -- mirroring the sealed
    reversal contract's family definition ("all pairwise reversal tests
    within one load level"), generalized to "within one metric-pair
    condition". The per-pair p-value is the intersection-union
    combination max(p_a, p_b), read off the same resamples as the CI
    rule -- no new inferential procedure."""
    family_idx = [
        i for i, d in enumerate(disagreements)
        if d.p_a is not None and d.p_b is not None
    ]
    p_values = [max(disagreements[i].p_a, disagreements[i].p_b) for i in family_idx]
    rejected = benjamini_hochberg(p_values, q=q)
    out = [False] * len(disagreements)
    for idx, rej in zip(family_idx, rejected):
        out[idx] = rej
    return out
