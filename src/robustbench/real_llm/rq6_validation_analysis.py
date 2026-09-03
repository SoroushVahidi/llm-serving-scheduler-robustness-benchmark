"""RQ6 result-blind analysis contract: sign agreement, Kendall's tau, and
reversal agreement for the frozen reversal case and stable control, per
docs/RQ6_REAL_VLLM_SCIENTIFIC_PROTOCOL_20260902.md's "Statistics" section.

Reuses, never reimplements, the Phase-12 statistics primitives:
`robustbench.ranking_portability.analysis.stats.block_bootstrap_ci` (window-
level bootstrap, >=2000 resamples) and `.benjamini_hochberg` (FDR q=0.05
over the 4-test family: 2 reversal-condition + 2 stable-control-condition
tests, matching docs/STATISTICAL_ANALYSIS_PLAN.md's per-family convention).
`.compare_rankings` (Kendall's tau-b) is reused too, for the
"Kendall's tau" quantity the task's own report template names explicitly --
disclosed limitation: with exactly 2 real execution paths
(slai_faithful, vllm_faithful) per condition, a rank correlation over 2
items is degenerate (+-1 whenever the two policies are not exactly tied,
undefined on an exact tie) -- it is reported for framework consistency with
Phase-12's many-policy comparisons, not because it is an informative
quantity in its own right for a 2-policy comparison. The scientifically
load-bearing quantity for RQ6 is the SLAI-minus-vLLM effect size and its
sign, computed directly below (`condition_effect`), matching the frozen
protocol's own "SLAI-minus-vLLM ANWG effect and its 95% bootstrap CI, per
condition" / "Winner sign per condition" / "Whether the sign flips" /
"reversal agreement" language.

This module never reads or embeds any real RQ6 result. All examples/tests
using literal numbers must be synthetic and stamped
SYNTHETIC_FIXTURE_NOT_SCIENTIFIC_EVIDENCE (see tests/test_rq6_validation_
analysis.py), never presented as scientific evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Sequence

import numpy as np

from robustbench.ranking_portability.analysis.stats import (
    PairedRankingComparison,
    benjamini_hochberg,
    block_bootstrap_ci,
    compare_rankings,
)

BOOTSTRAP_RESAMPLES = 2000
CI_LEVEL = 0.95
FDR_Q = 0.05


@dataclass
class ConditionEffect:
    """SLAI-minus-vLLM ANWG effect for one condition (one source::region),
    bootstrapped over that source's 40 windows."""

    condition_label: str
    n_windows: int
    point_estimate: float
    ci_lo: float
    ci_hi: float
    p_value_two_sided: float
    excludes_zero: bool
    winner: Optional[str]  # "slai_faithful" | "vllm_faithful" | None (CI includes zero)


def condition_effect(
    per_window_diff: Mapping[str, float], *, condition_label: str,
    n_resamples: int = BOOTSTRAP_RESAMPLES, ci_level: float = CI_LEVEL,
    rng: Optional[np.random.Generator] = None,
) -> ConditionEffect:
    """`per_window_diff`: {window_id: ANWG(slai) - ANWG(vllm)} for every
    window in this condition (all 40, unless a cell is a validator-flagged
    failure -- see validate_rq6_validation_outputs.py, which is responsible
    for refusing to hand incomplete conditions to this function silently).
    """
    if rng is None:
        rng = np.random.default_rng(0)
    values = list(per_window_diff.values())
    point, lo, hi = block_bootstrap_ci(
        values, np.mean, n_resamples=n_resamples, ci_level=ci_level, rng=rng,
    )
    # Bootstrap p-value (two-sided) for "does the effect differ from 0":
    # fraction of resamples on the side of 0 opposite the point estimate,
    # doubled and clamped to [0, 1] -- standard percentile-bootstrap p-value
    # construction, computed here (not inside the reused block_bootstrap_ci,
    # which only returns a CI) since only this caller needs a p-value for
    # the downstream BH-FDR step.
    resampled = np.empty(n_resamples)
    arr = np.asarray(values, dtype=float)
    for i in range(n_resamples):
        idx = rng.integers(0, len(arr), size=len(arr))
        resampled[i] = np.mean(arr[idx])
    if point >= 0:
        p = 2.0 * min(1.0, np.mean(resampled <= 0) + 1.0 / n_resamples)
    else:
        p = 2.0 * min(1.0, np.mean(resampled >= 0) + 1.0 / n_resamples)
    p = float(min(p, 1.0))
    excludes_zero = not (lo <= 0.0 <= hi)
    winner = None
    if excludes_zero:
        winner = "slai_faithful" if point > 0 else "vllm_faithful"
    return ConditionEffect(
        condition_label=condition_label, n_windows=len(values),
        point_estimate=point, ci_lo=lo, ci_hi=hi,
        p_value_two_sided=p, excludes_zero=excludes_zero, winner=winner,
    )


@dataclass
class ReversalAnalysisResult:
    """Result of the frozen reversal-case test: does the SLAI-vs-vLLM
    ordering flip sign between condition_x and condition_y."""

    condition_x: ConditionEffect
    condition_y: ConditionEffect
    sign_flip_observed: bool
    both_conditions_supported: bool  # both CIs exclude zero
    agrees_with_simulator_selected_direction: Optional[bool]
    kendall_tau_x_vs_y: Optional[PairedRankingComparison]


def reversal_analysis(
    per_window_diff_x: Mapping[str, float], per_window_diff_y: Mapping[str, float], *,
    condition_x_label: str, condition_y_label: str,
    simulator_selected_x_winner: str, simulator_selected_y_winner: str,
    rng: Optional[np.random.Generator] = None,
) -> ReversalAnalysisResult:
    """`simulator_selected_x_winner`/`_y_winner`: the winner
    (slai_faithful|vllm_faithful) each condition was frozen as selecting in
    `artifacts/manifests/phase12_rq6_case_selection_20260902.json`
    (simulator-side), supplied by the caller from that manifest -- this
    function never re-derives or hardcodes it."""
    if rng is None:
        rng = np.random.default_rng(0)
    cx = condition_effect(per_window_diff_x, condition_label=condition_x_label, rng=rng)
    cy = condition_effect(per_window_diff_y, condition_label=condition_y_label, rng=rng)

    sign_flip = (cx.point_estimate >= 0) != (cy.point_estimate >= 0)
    both_supported = cx.excludes_zero and cy.excludes_zero

    agrees: Optional[bool] = None
    if both_supported:
        real_matches_simulator = (
            cx.winner == simulator_selected_x_winner and cy.winner == simulator_selected_y_winner
        )
        agrees = real_matches_simulator

    # Degenerate 2-policy Kendall's tau, reported per the task's report
    # template -- see module docstring's disclosed-limitation note.
    left = {"slai_faithful": sum(per_window_diff_x.values()), "vllm_faithful": 0.0}
    right = {"slai_faithful": sum(per_window_diff_y.values()), "vllm_faithful": 0.0}
    tau = compare_rankings(left, right, top_k_values=(1,))

    return ReversalAnalysisResult(
        condition_x=cx, condition_y=cy, sign_flip_observed=sign_flip,
        both_conditions_supported=both_supported,
        agrees_with_simulator_selected_direction=agrees,
        kendall_tau_x_vs_y=tau,
    )


@dataclass
class StableControlAnalysisResult:
    condition_x: ConditionEffect
    condition_y: ConditionEffect
    same_sign_both_conditions: bool


def stable_control_analysis(
    per_window_diff_x: Mapping[str, float], per_window_diff_y: Mapping[str, float], *,
    condition_x_label: str, condition_y_label: str,
    rng: Optional[np.random.Generator] = None,
) -> StableControlAnalysisResult:
    if rng is None:
        rng = np.random.default_rng(0)
    cx = condition_effect(per_window_diff_x, condition_label=condition_x_label, rng=rng)
    cy = condition_effect(per_window_diff_y, condition_label=condition_y_label, rng=rng)
    same_sign = (cx.point_estimate >= 0) == (cy.point_estimate >= 0)
    return StableControlAnalysisResult(condition_x=cx, condition_y=cy, same_sign_both_conditions=same_sign)


def apply_family_fdr(p_values: Sequence[float], *, q: float = FDR_Q) -> List[bool]:
    """BH-FDR over the frozen 4-test family (2 reversal-condition + 2
    stable-control-condition p-values), per
    docs/RQ6_REAL_VLLM_SCIENTIFIC_PROTOCOL_20260902.md's "Multiple-testing
    correction". Caller is responsible for assembling exactly this 4-element
    family in a fixed, documented order."""
    return benjamini_hochberg(p_values, q=q)
