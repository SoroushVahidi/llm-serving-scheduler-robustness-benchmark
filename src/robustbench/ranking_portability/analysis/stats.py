"""Generic, outcome-agnostic statistics primitives shared by every Phase-12
analysis component: Kendall's tau-b / Spearman's rho over partially-defined
rankings, top-k overlap with `k_reduced` flagging, block bootstrap over
windows, Benjamini-Hochberg FDR, and the Friedman omnibus test.

Nothing in this module knows about scheduler policies, campaigns, or
cell schemas -- it operates on plain (policy_id -> value) dicts and lists
of window-blocks, so it is trivially testable with fabricated fixtures
and reusable unchanged once real cells exist.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
from scipy import stats as scipy_stats


def _is_defined(v) -> bool:
    return v is not None and not (isinstance(v, float) and math.isnan(v))


@dataclass
class PairedRankingComparison:
    """Result of comparing two policy->value rankings, restricted to the
    policies defined in BOTH (docs/RANKING_PORTABILITY_METRIC_DEFINITIONS.md:
    "computed pairwise over the set of policies with a defined value in
    both rankings being compared")."""
    n_policies_compared: int
    n_policies_excluded_left: int
    n_policies_excluded_right: int
    kendall_tau: Optional[float]
    kendall_p: Optional[float]
    spearman_rho: Optional[float]
    spearman_p: Optional[float]
    topk_overlap: Dict[int, float] = field(default_factory=dict)
    topk_k_reduced: Dict[int, bool] = field(default_factory=dict)


def compare_rankings(
    left: Mapping[str, Optional[float]],
    right: Mapping[str, Optional[float]],
    *,
    top_k_values: Sequence[int],
    higher_is_better: bool = True,
) -> PairedRankingComparison:
    common = [
        p for p in left.keys() & right.keys()
        if _is_defined(left[p]) and _is_defined(right[p])
    ]
    n_excl_left = sum(1 for p in left if not _is_defined(left[p]))
    n_excl_right = sum(1 for p in right if not _is_defined(right[p]))

    if len(common) < 2:
        return PairedRankingComparison(
            n_policies_compared=len(common),
            n_policies_excluded_left=n_excl_left,
            n_policies_excluded_right=n_excl_right,
            kendall_tau=None, kendall_p=None,
            spearman_rho=None, spearman_p=None,
            topk_overlap={k: float("nan") for k in top_k_values},
            topk_k_reduced={k: True for k in top_k_values},
        )

    common_sorted = sorted(common)
    lv = np.array([left[p] for p in common_sorted], dtype=float)
    rv = np.array([right[p] for p in common_sorted], dtype=float)
    if not higher_is_better:
        lv, rv = -lv, -rv

    tau, tau_p = scipy_stats.kendalltau(lv, rv)
    rho, rho_p = scipy_stats.spearmanr(lv, rv)

    topk_overlap: Dict[int, float] = {}
    topk_reduced: Dict[int, bool] = {}
    ranked_left = [p for _, p in sorted(zip(-lv, common_sorted))]
    ranked_right = [p for _, p in sorted(zip(-rv, common_sorted))]
    for k in top_k_values:
        eff_k = min(k, len(common_sorted))
        topk_reduced[k] = eff_k < k
        set_l = set(ranked_left[:eff_k])
        set_r = set(ranked_right[:eff_k])
        topk_overlap[k] = (len(set_l & set_r) / eff_k) if eff_k > 0 else float("nan")

    return PairedRankingComparison(
        n_policies_compared=len(common_sorted),
        n_policies_excluded_left=n_excl_left,
        n_policies_excluded_right=n_excl_right,
        kendall_tau=float(tau) if tau == tau else None,
        kendall_p=float(tau_p) if tau_p == tau_p else None,
        spearman_rho=float(rho) if rho == rho else None,
        spearman_p=float(rho_p) if rho_p == rho_p else None,
        topk_overlap=topk_overlap,
        topk_k_reduced=topk_reduced,
    )


def block_bootstrap_ci(
    per_window_values: Sequence[float],
    statistic_fn,
    *,
    n_resamples: int,
    ci_level: float,
    rng: np.random.Generator,
) -> Tuple[float, float, float]:
    """Resamples `per_window_values` (one entry per window, WITH
    replacement, whole windows only -- never individual requests) and
    applies `statistic_fn` to each resample. Returns
    (point_estimate, ci_lo, ci_hi). Windows sharing a load region/policy
    are the correlated unit here; caller is responsible for ensuring
    `per_window_values` really is one row per window."""
    values = np.asarray(per_window_values, dtype=float)
    n = len(values)
    point = statistic_fn(values)
    if n == 0:
        return point, float("nan"), float("nan")
    resampled = np.empty(n_resamples)
    for i in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        resampled[i] = statistic_fn(values[idx])
    alpha = 1.0 - ci_level
    lo, hi = np.nanquantile(resampled, [alpha / 2, 1 - alpha / 2])
    return float(point), float(lo), float(hi)


def benjamini_hochberg(p_values: Sequence[float], *, q: float) -> List[bool]:
    """Returns a same-length list of booleans: True where the hypothesis
    is rejected under BH FDR control at level `q`. NaN p-values are never
    rejected and do not consume a rank slot ahead of real p-values."""
    indexed = [(p, i) for i, p in enumerate(p_values) if p == p]
    m = len(indexed)
    reject = [False] * len(p_values)
    if m == 0:
        return reject
    indexed.sort(key=lambda t: t[0])
    threshold_rank = 0
    for rank, (p, _orig_i) in enumerate(indexed, start=1):
        if p <= (rank / m) * q:
            threshold_rank = rank
    for rank, (p, orig_i) in enumerate(indexed, start=1):
        if rank <= threshold_rank:
            reject[orig_i] = True
    return reject


@dataclass
class FriedmanResult:
    statistic: Optional[float]
    p_value: Optional[float]
    n_blocks: int
    n_treatments: int
    excluded_policies: List[str]


def friedman_omnibus(
    block_treatment_values: Mapping[str, Mapping[str, float]],
) -> FriedmanResult:
    """`block_treatment_values`: {window_id: {policy_id: value}}. Only
    policies present with a defined value in EVERY block are included
    (Friedman requires a complete block design); excluded policies are
    reported, never imputed."""
    all_policies = set()
    for row in block_treatment_values.values():
        all_policies |= set(row.keys())

    complete_policies = sorted(
        p for p in all_policies
        if all(
            p in row and _is_defined(row[p])
            for row in block_treatment_values.values()
        )
    )
    excluded = sorted(all_policies - set(complete_policies))

    blocks = sorted(block_treatment_values.keys())
    if len(complete_policies) < 3 or len(blocks) < 2:
        return FriedmanResult(
            statistic=None, p_value=None,
            n_blocks=len(blocks), n_treatments=len(complete_policies),
            excluded_policies=excluded,
        )

    matrix = np.array(
        [[block_treatment_values[b][p] for p in complete_policies] for b in blocks],
        dtype=float,
    )
    columns = [matrix[:, j] for j in range(matrix.shape[1])]
    stat, p = scipy_stats.friedmanchisquare(*columns)
    return FriedmanResult(
        statistic=float(stat), p_value=float(p),
        n_blocks=len(blocks), n_treatments=len(complete_policies),
        excluded_policies=excluded,
    )
