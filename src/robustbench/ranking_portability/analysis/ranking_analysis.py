"""Ranking-portability comparison (docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md
§A / docs/STATISTICAL_ANALYSIS_PLAN.md §A): compares the policy ranking
observed under one condition (e.g. a source, or a source+load-region) to
another, via Kendall tau-b, Spearman rho, and top-{1,3} overlap, with
block-bootstrap CIs resampled over WINDOWS (never requests, never
(policy,window) rows treated as independent).

Consumes ONLY a consolidated+validated row set (never raw shard files --
enforced by the caller, `input_manifest.py`'s gate). Every undefined
conditional metric is excluded from a policy's aggregate, never imputed
(docs/RANKING_PORTABILITY_METRIC_DEFINITIONS.md).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Sequence

import numpy as np

from .contract import BOOTSTRAP_CI_LEVEL, BOOTSTRAP_RESAMPLES, TOP_K_VALUES
from .stats import PairedRankingComparison, compare_rankings


def _is_defined(v) -> bool:
    return v is not None and not (isinstance(v, float) and math.isnan(v))


def per_window_policy_values(rows: Sequence[Mapping], metric: str) -> Dict[str, Dict[str, float]]:
    """rows: consolidated cell rows already filtered to one (source,
    load_region) condition, both repetitions included. Returns
    {window_id: {policy_id: value}}, averaging the (up to) two
    repetitions' defined values per (window, policy) -- identical by
    construction when both are defined (deterministic simulator, shared
    seed), so the average is a no-op in the well-formed case and a
    graceful degrade if exactly one rep is undefined."""
    by_window_policy: Dict[str, Dict[str, List[float]]] = {}
    for row in rows:
        v = row.get(metric)
        if not _is_defined(v):
            continue
        w = row["window_id"]
        p = row["policy_id"]
        by_window_policy.setdefault(w, {}).setdefault(p, []).append(float(v))
    return {
        w: {p: float(np.mean(vals)) for p, vals in policies.items()}
        for w, policies in by_window_policy.items()
    }


@dataclass
class ConditionRanking:
    """A policy->value aggregate ranking for one condition, plus the
    exclusion accounting the metric contract requires be reported."""
    values: Dict[str, Optional[float]]
    n_windows_used: int
    n_policy_window_observations_excluded_for_undefined_metric: int
    excluded_policies_no_defined_value: List[str] = field(default_factory=list)


def aggregate_condition_ranking(
    per_window: Mapping[str, Mapping[str, float]],
    *,
    all_policies: Sequence[str],
) -> ConditionRanking:
    n_windows = len(per_window)
    n_excluded_obs = 0
    values: Dict[str, Optional[float]] = {}
    for p in all_policies:
        obs = [pw[p] for pw in per_window.values() if p in pw]
        n_excluded_obs += n_windows - len(obs)
        values[p] = float(np.mean(obs)) if obs else None
    excluded_entirely = sorted(p for p, v in values.items() if v is None)
    return ConditionRanking(
        values=values,
        n_windows_used=n_windows,
        n_policy_window_observations_excluded_for_undefined_metric=n_excluded_obs,
        excluded_policies_no_defined_value=excluded_entirely,
    )


@dataclass
class RankingComparisonResult:
    metric: str
    condition_x_label: str
    condition_y_label: str
    point: PairedRankingComparison
    kendall_tau_ci: Optional[tuple]
    spearman_rho_ci: Optional[tuple]
    n_conditions_excluded_for_undefined_metric: int


def compare_conditions(
    rows_x: Sequence[Mapping],
    rows_y: Sequence[Mapping],
    *,
    metric: str,
    all_policies: Sequence[str],
    condition_x_label: str,
    condition_y_label: str,
    n_resamples: int = BOOTSTRAP_RESAMPLES,
    ci_level: float = BOOTSTRAP_CI_LEVEL,
    top_k_values: Sequence[int] = TOP_K_VALUES,
    rng: Optional[np.random.Generator] = None,
) -> RankingComparisonResult:
    if rng is None:
        rng = np.random.default_rng(0)

    pw_x = per_window_policy_values(rows_x, metric)
    pw_y = per_window_policy_values(rows_y, metric)
    rank_x = aggregate_condition_ranking(pw_x, all_policies=all_policies)
    rank_y = aggregate_condition_ranking(pw_y, all_policies=all_policies)

    point = compare_rankings(rank_x.values, rank_y.values, top_k_values=top_k_values)
    n_excluded = (
        rank_x.n_policy_window_observations_excluded_for_undefined_metric
        + rank_y.n_policy_window_observations_excluded_for_undefined_metric
    )

    tau_ci = None
    rho_ci = None
    if point.n_policies_compared >= 2 and pw_x and pw_y:
        windows_x = list(pw_x.keys())
        windows_y = list(pw_y.keys())
        taus, rhos = [], []
        for _ in range(n_resamples):
            rx = rng.choice(windows_x, size=len(windows_x), replace=True)
            ry = rng.choice(windows_y, size=len(windows_y), replace=True)
            resampled_x = {w: pw_x[w] for w in rx}
            # Rebuild as list-of-dicts semantics for aggregate helper: it
            # accepts any Mapping[str, Mapping[str, float]], duplicate
            # window-id keys collapse in a dict -- so key by synthetic
            # index instead to preserve resample multiplicities.
            resampled_x = {f"{w}#{i}": pw_x[w] for i, w in enumerate(rx)}
            resampled_y = {f"{w}#{i}": pw_y[w] for i, w in enumerate(ry)}
            agg_x = aggregate_condition_ranking(resampled_x, all_policies=all_policies)
            agg_y = aggregate_condition_ranking(resampled_y, all_policies=all_policies)
            cmp = compare_rankings(agg_x.values, agg_y.values, top_k_values=top_k_values)
            if cmp.kendall_tau is not None:
                taus.append(cmp.kendall_tau)
            if cmp.spearman_rho is not None:
                rhos.append(cmp.spearman_rho)
        alpha = 1.0 - ci_level
        if taus:
            tau_ci = tuple(np.quantile(taus, [alpha / 2, 1 - alpha / 2]))
        if rhos:
            rho_ci = tuple(np.quantile(rhos, [alpha / 2, 1 - alpha / 2]))

    return RankingComparisonResult(
        metric=metric,
        condition_x_label=condition_x_label,
        condition_y_label=condition_y_label,
        point=point,
        kendall_tau_ci=tau_ci,
        spearman_rho_ci=rho_ci,
        n_conditions_excluded_for_undefined_metric=n_excluded,
    )
