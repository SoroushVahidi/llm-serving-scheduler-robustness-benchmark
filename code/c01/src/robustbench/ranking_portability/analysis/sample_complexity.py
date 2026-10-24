"""Benchmark sample-complexity analysis
(docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md §C /
docs/STATISTICAL_ANALYSIS_PLAN.md §F). Subsampling ladder n in
{5,10,20,30,40} (40 = full window count), >=500 draws per n without
replacement, recovery = probability of matching the full-window
reference ranking (exact and top-k), reported per source/metric, plus
the concentrated-vs-spread cross-source convergence comparison
(purely descriptive, no framing of either as "expected").

Deterministic: every draw uses an explicitly-seeded `numpy.random.Generator`
and the seed is recorded in the result so a resample is exactly
reproducible.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Sequence

import numpy as np

from .contract import (
    SAMPLE_COMPLEXITY_DRAWS_PER_N,
    SAMPLE_COMPLEXITY_N_VALUES,
    SAMPLE_COMPLEXITY_RECOVERY_THRESHOLD,
    TOP_K_VALUES,
)


def _ranking_order(values: Mapping[str, float]) -> tuple:
    return tuple(sorted(values.keys(), key=lambda p: (-values[p], p)))


def _topk_set(values: Mapping[str, float], k: int) -> frozenset:
    order = _ranking_order(values)
    return frozenset(order[:min(k, len(order))])


def _aggregate(per_window: Mapping[str, Mapping[str, float]], policies: Sequence[str]) -> Dict[str, float]:
    out = {}
    for p in policies:
        vals = [pw[p] for pw in per_window.values() if p in pw]
        if vals:
            out[p] = float(np.mean(vals))
    return out


@dataclass
class SampleComplexityPoint:
    n: int
    n_draws: int
    seed: int
    p_exact_recovery: float
    p_topk_recovery: Dict[int, float] = field(default_factory=dict)


@dataclass
class SampleComplexityResult:
    reference_ranking: tuple
    points: List[SampleComplexityPoint]
    first_n_meeting_exact_threshold: int | None
    first_n_meeting_topk_threshold: Dict[int, int | None]


def run_sample_complexity(
    per_window: Mapping[str, Mapping[str, float]],
    *,
    policies: Sequence[str],
    n_values: Sequence[int] = SAMPLE_COMPLEXITY_N_VALUES,
    draws_per_n: int = SAMPLE_COMPLEXITY_DRAWS_PER_N,
    recovery_threshold: float = SAMPLE_COMPLEXITY_RECOVERY_THRESHOLD,
    top_k_values: Sequence[int] = TOP_K_VALUES,
    base_seed: int = 12345,
) -> SampleComplexityResult:
    window_ids = list(per_window.keys())
    full_agg = _aggregate(per_window, policies)
    reference_order = _ranking_order(full_agg)
    reference_topk = {k: _topk_set(full_agg, k) for k in top_k_values}

    points: List[SampleComplexityPoint] = []
    for n in n_values:
        n_eff = min(n, len(window_ids))
        seed = base_seed + n
        rng = np.random.default_rng(seed)
        n_exact_match = 0
        n_topk_match = {k: 0 for k in top_k_values}
        for _ in range(draws_per_n):
            sample_idx = rng.choice(len(window_ids), size=n_eff, replace=False)
            sample_windows = {window_ids[i]: per_window[window_ids[i]] for i in sample_idx}
            agg = _aggregate(sample_windows, policies)
            if _ranking_order(agg) == reference_order:
                n_exact_match += 1
            for k in top_k_values:
                if _topk_set(agg, k) == reference_topk[k]:
                    n_topk_match[k] += 1
        points.append(SampleComplexityPoint(
            n=n, n_draws=draws_per_n, seed=seed,
            p_exact_recovery=n_exact_match / draws_per_n,
            p_topk_recovery={k: n_topk_match[k] / draws_per_n for k in top_k_values},
        ))

    first_exact = next((pt.n for pt in points if pt.p_exact_recovery >= recovery_threshold), None)
    first_topk = {
        k: next((pt.n for pt in points if pt.p_topk_recovery[k] >= recovery_threshold), None)
        for k in top_k_values
    }

    return SampleComplexityResult(
        reference_ranking=reference_order,
        points=points,
        first_n_meeting_exact_threshold=first_exact,
        first_n_meeting_topk_threshold=first_topk,
    )


@dataclass
class ConcentratedVsSpreadResult:
    n_total: int
    n_draws: int
    mean_tau_concentrated: float
    mean_tau_spread: float


def compare_concentrated_vs_spread(
    per_window_by_source: Mapping[str, Mapping[str, Mapping[str, float]]],
    *,
    policies: Sequence[str],
    n_total: int = 40,
    n_draws: int = SAMPLE_COMPLEXITY_DRAWS_PER_N,
    base_seed: int = 999,
) -> ConcentratedVsSpreadResult:
    """(i) n_total windows concentrated in one source vs. (ii) the same
    n_total budget split evenly across all sources -- both compared
    against the full 3xN cross-source reference ranking via Kendall tau
    (docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md §C). Purely descriptive."""
    from scipy import stats as scipy_stats

    sources = sorted(per_window_by_source.keys())
    full_pooled: Dict[str, Mapping[str, float]] = {}
    for s in sources:
        for w, pw in per_window_by_source[s].items():
            full_pooled[f"{s}::{w}"] = pw
    reference = _aggregate(full_pooled, policies)
    ref_order_vals = [reference[p] for p in policies]

    def tau_against_reference(agg: Mapping[str, float]) -> float:
        vals = [agg.get(p, float("nan")) for p in policies]
        if any(v != v for v in vals):
            return float("nan")
        tau, _ = scipy_stats.kendalltau(ref_order_vals, vals)
        return float(tau) if tau == tau else float("nan")

    rng = np.random.default_rng(base_seed)
    concentrated_taus, spread_taus = [], []
    per_source_budget = max(1, n_total // len(sources))

    for _ in range(n_draws):
        # (i) concentrated: n_total windows from one randomly chosen source
        src = sources[rng.integers(0, len(sources))]
        windows = list(per_window_by_source[src].keys())
        n_eff = min(n_total, len(windows))
        idx = rng.choice(len(windows), size=n_eff, replace=False)
        sample = {windows[i]: per_window_by_source[src][windows[i]] for i in idx}
        concentrated_taus.append(tau_against_reference(_aggregate(sample, policies)))

        # (ii) spread: per_source_budget windows from each source
        spread_sample: Dict[str, Mapping[str, float]] = {}
        for s in sources:
            windows_s = list(per_window_by_source[s].keys())
            n_eff_s = min(per_source_budget, len(windows_s))
            idx_s = rng.choice(len(windows_s), size=n_eff_s, replace=False)
            for i in idx_s:
                spread_sample[f"{s}::{windows_s[i]}"] = per_window_by_source[s][windows_s[i]]
        spread_taus.append(tau_against_reference(_aggregate(spread_sample, policies)))

    return ConcentratedVsSpreadResult(
        n_total=n_total,
        n_draws=n_draws,
        mean_tau_concentrated=float(np.nanmean(concentrated_taus)),
        mean_tau_spread=float(np.nanmean(spread_taus)),
    )
