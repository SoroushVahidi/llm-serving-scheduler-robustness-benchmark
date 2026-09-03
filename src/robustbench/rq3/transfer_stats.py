"""RQ3 synthetic-to-real transfer statistics.

Reuses `robustbench.ranking_portability.analysis.stats.compare_rankings`
(Kendall tau-b, Spearman rho, top-k overlap) unchanged for the point
estimate on every resample. `compare_rankings` itself only accepts two
`{policy_id: value}` dicts, so the whole-window block bootstrap here is a
new, small wrapper (not a duplicate of `block_bootstrap_ci`, which
resamples a single scalar sequence) -- documented in
`docs/RQ3_SYNTHETIC_TO_REAL_PROTOCOL_20260903.md` section on why a custom
two-sided bootstrap was written instead of reusing that function directly.

Never zero-imputes: a policy missing a defined value in either side's
window set is simply excluded from that resample's ranking, exactly as
`compare_rankings` already does for its two inputs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Sequence

import numpy as np

from ..ranking_portability.analysis.stats import compare_rankings

N_BOOTSTRAP = 2000
CI_LEVEL = 0.95
TOP_K_VALUES = (1, 3)


def _mean_ranking(
    per_policy_per_window: Mapping[str, Sequence[Optional[float]]], idx: np.ndarray,
) -> Dict[str, Optional[float]]:
    out: Dict[str, Optional[float]] = {}
    for policy, values in per_policy_per_window.items():
        picked = [values[i] for i in idx if values[i] is not None]
        out[policy] = float(np.mean(picked)) if picked else None
    return out


@dataclass
class TransferResult:
    status: str  # "OK" or "UNDEFINED_INSUFFICIENT_COMMON_POLICIES"
    effective_policy_count: int
    policy_panel: List[str]
    kendall_tau_b: Optional[float] = None
    kendall_ci: Optional[List[float]] = None
    spearman_rho: Optional[float] = None
    spearman_ci: Optional[List[float]] = None
    top1_agreement: Optional[float] = None
    top3_overlap: Optional[float] = None
    bootstrap_count: int = 0
    sign_agreement_rate: Optional[float] = None
    n_sign_pairs: int = 0


def compute_transfer(
    synthetic_per_policy_per_window: Mapping[str, Sequence[float]],
    real_per_policy_per_window: Mapping[str, Sequence[float]],
    *,
    min_common_policies: int,
    n_bootstrap: int = N_BOOTSTRAP,
    ci_level: float = CI_LEVEL,
    rng: Optional[np.random.Generator] = None,
) -> TransferResult:
    """`*_per_policy_per_window`: {policy_id: [value_per_window, ...]}, one
    row per window on that side (synthetic seeds on the left, real frozen
    windows on the right) -- `arrival_normalized_weighted_goodput` is
    HIGHER_BETTER on both sides, no direction flip needed."""
    if rng is None:
        rng = np.random.default_rng(0)

    common_policies = sorted(
        set(synthetic_per_policy_per_window) & set(real_per_policy_per_window)
    )
    effective_n = len(common_policies)
    if effective_n < min_common_policies:
        return TransferResult(
            status="UNDEFINED_INSUFFICIENT_COMMON_POLICIES",
            effective_policy_count=effective_n, policy_panel=common_policies,
        )

    synth_map = {p: synthetic_per_policy_per_window[p] for p in common_policies}
    real_map = {p: real_per_policy_per_window[p] for p in common_policies}
    n_synth_windows = len(next(iter(synth_map.values())))
    n_real_windows = len(next(iter(real_map.values())))

    def _point(idx_s: np.ndarray, idx_r: np.ndarray):
        left = _mean_ranking(synth_map, idx_s)
        right = _mean_ranking(real_map, idx_r)
        cmp = compare_rankings(left, right, top_k_values=list(TOP_K_VALUES), higher_is_better=True)
        return cmp, left, right

    full_idx_s = np.arange(n_synth_windows)
    full_idx_r = np.arange(n_real_windows)
    point_cmp, point_left, point_right = _point(full_idx_s, full_idx_r)

    taus, rhos, top1s, top3s = [], [], [], []
    for _ in range(n_bootstrap):
        idx_s = rng.integers(0, n_synth_windows, size=n_synth_windows)
        idx_r = rng.integers(0, n_real_windows, size=n_real_windows)
        cmp, _, _ = _point(idx_s, idx_r)
        if cmp.kendall_tau is not None:
            taus.append(cmp.kendall_tau)
        if cmp.spearman_rho is not None:
            rhos.append(cmp.spearman_rho)
        if 1 in cmp.topk_overlap:
            top1s.append(cmp.topk_overlap[1])
        if 3 in cmp.topk_overlap:
            top3s.append(cmp.topk_overlap[3])

    alpha = 1.0 - ci_level

    def _ci(vals: List[float]) -> Optional[List[float]]:
        if not vals:
            return None
        lo, hi = np.nanquantile(np.asarray(vals), [alpha / 2, 1 - alpha / 2])
        return [float(lo), float(hi)]

    # Secondary: policy-pair sign agreement on the full-data point ranking
    # (same metric, same units, on both sides -- no cross-metric normalization
    # question applies here, unlike a cross-metric threshold).
    pairs = [(a, b) for i, a in enumerate(common_policies) for b in common_policies[i + 1:]]
    agree, total = 0, 0
    for a, b in pairs:
        la, lb = point_left.get(a), point_left.get(b)
        ra, rb = point_right.get(a), point_right.get(b)
        if la is None or lb is None or ra is None or rb is None or la == lb or ra == rb:
            continue
        total += 1
        if (la > lb) == (ra > rb):
            agree += 1

    return TransferResult(
        status="OK",
        effective_policy_count=effective_n,
        policy_panel=common_policies,
        kendall_tau_b=point_cmp.kendall_tau,
        kendall_ci=_ci(taus),
        spearman_rho=point_cmp.spearman_rho,
        spearman_ci=_ci(rhos),
        top1_agreement=point_cmp.topk_overlap.get(1),
        top3_overlap=point_cmp.topk_overlap.get(3),
        bootstrap_count=n_bootstrap,
        sign_agreement_rate=(agree / total) if total > 0 else None,
        n_sign_pairs=total,
    )
