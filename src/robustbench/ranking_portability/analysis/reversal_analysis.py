"""Pairwise rank-reversal classification
(docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md §A). A reversal between two
conditions (e.g. two sources, or two load regions) for a policy pair
(A, B) is counted as **practically meaningful** only if, in BOTH
directions: the winning margin exceeds 10% of the losing policy's value,
and the block-bootstrap CI on the sign of the difference excludes zero
at 95%. Anything else that still shows a sign flip is recorded
separately, never pooled into a headline reversal count
(docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md §A).

This module classifies only -- it never decides "who should win"; it is
symmetric in (A, B) and safe to run on fabricated fixtures with no
scientific content.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Optional, Sequence

import numpy as np

from .contract import REVERSAL_CI_LEVEL, REVERSAL_PRACTICAL_MARGIN_FRACTION
from .ranking_analysis import aggregate_condition_ranking, per_window_policy_values


class ReversalClass(str, Enum):
    UNDEFINED_UNESTIMABLE = "UNDEFINED_UNESTIMABLE"
    STABLE_NO_SIGN_CHANGE = "STABLE_NO_SIGN_CHANGE"
    SUPPORTED_PRACTICAL_REVERSAL = "SUPPORTED_PRACTICAL_REVERSAL"
    MICROSCOPIC_SIGN_CHANGE = "MICROSCOPIC_SIGN_CHANGE"
    UNSUPPORTED_SIGN_CHANGE_WIDE_CI = "UNSUPPORTED_SIGN_CHANGE_WIDE_CI"


@dataclass
class PairwiseReversalResult:
    classification: ReversalClass
    diff_x: Optional[float]
    diff_y: Optional[float]
    margin_x: Optional[float]
    margin_y: Optional[float]
    ci_x: Optional[tuple]
    ci_y: Optional[tuple]
    detail: str
    # Two-sided block-bootstrap sign-test p-values, computed from the SAME
    # resamples as ci_x/ci_y (p = 2*min(P(mean diff <= 0), P(mean diff >= 0))
    # over the resampled mean per-window differences). These are the
    # pre-specified test statistic the frozen multiple-testing plan applies
    # Benjamini-Hochberg FDR to within each (metric, load-region) reversal
    # family (docs/STATISTICAL_ANALYSIS_PLAN.md "Multiple-testing
    # correction": "e.g. all pairwise reversal tests within one load
    # level"). None when the CI stage was not reached.
    p_x: Optional[float] = None
    p_y: Optional[float] = None


def _diff_and_margin(value_a: Optional[float], value_b: Optional[float]) -> tuple:
    """Returns (diff = a-b, margin = winning_margin / losing_value), or
    (None, None) if either is undefined or the loser's value is zero
    (margin undefined by a zero denominator, treated as unestimable, not
    as an automatic pass)."""
    if value_a is None or value_b is None:
        return None, None
    diff = value_a - value_b
    if diff == 0:
        return 0.0, 0.0
    loser_value = value_b if diff > 0 else value_a
    if loser_value == 0:
        return diff, None
    margin = abs(diff) / abs(loser_value)
    return diff, margin


def _bootstrap_diff_ci(
    per_window: Mapping[str, Mapping[str, float]],
    policy_a: str,
    policy_b: str,
    *,
    n_resamples: int,
    ci_level: float,
    rng: np.random.Generator,
) -> Optional[tuple]:
    """Returns (ci_lo, ci_hi, p_two_sided) from ONE shared set of
    block-bootstrap resamples of the mean per-window (policy_a - policy_b)
    difference: the percentile CI at `ci_level` plus the two-sided
    sign-test p-value 2*min(P(resampled <= 0), P(resampled >= 0)). The
    p-value is not a new inferential procedure -- it is read off the same
    frozen resampling distribution that backs the preregistered CI rule,
    and exists so the frozen per-family Benjamini-Hochberg correction has
    its pre-specified p-value to adjust."""
    windows = [
        w for w, pw in per_window.items() if policy_a in pw and policy_b in pw
    ]
    if not windows:
        return None
    diffs = np.array([per_window[w][policy_a] - per_window[w][policy_b] for w in windows])
    resampled = np.empty(n_resamples)
    for i in range(n_resamples):
        idx = rng.integers(0, len(diffs), size=len(diffs))
        resampled[i] = diffs[idx].mean()
    alpha = 1.0 - ci_level
    lo, hi = np.quantile(resampled, [alpha / 2, 1 - alpha / 2])
    p_two_sided = float(2.0 * min(
        np.mean(resampled <= 0.0), np.mean(resampled >= 0.0)
    ))
    return float(lo), float(hi), min(1.0, p_two_sided)


def classify_pairwise_reversal(
    rows_x: Sequence[Mapping],
    rows_y: Sequence[Mapping],
    *,
    policy_a: str,
    policy_b: str,
    metric: str,
    margin_fraction: float = REVERSAL_PRACTICAL_MARGIN_FRACTION,
    ci_level: float = REVERSAL_CI_LEVEL,
    n_resamples: int = 2000,
    rng: Optional[np.random.Generator] = None,
) -> PairwiseReversalResult:
    if rng is None:
        rng = np.random.default_rng(0)

    pw_x = per_window_policy_values(rows_x, metric)
    pw_y = per_window_policy_values(rows_y, metric)
    rank_x = aggregate_condition_ranking(pw_x, all_policies=[policy_a, policy_b])
    rank_y = aggregate_condition_ranking(pw_y, all_policies=[policy_a, policy_b])

    va_x, vb_x = rank_x.values[policy_a], rank_x.values[policy_b]
    va_y, vb_y = rank_y.values[policy_a], rank_y.values[policy_b]

    diff_x, margin_x = _diff_and_margin(va_x, vb_x)
    diff_y, margin_y = _diff_and_margin(va_y, vb_y)

    if diff_x is None or diff_y is None or margin_x is None or margin_y is None:
        return PairwiseReversalResult(
            classification=ReversalClass.UNDEFINED_UNESTIMABLE,
            diff_x=diff_x, diff_y=diff_y, margin_x=margin_x, margin_y=margin_y,
            ci_x=None, ci_y=None,
            detail="one or both conditions have an undefined value for policy_a/policy_b, "
                   "or a zero-valued loser makes the margin unestimable",
        )

    sign_x = 0 if diff_x == 0 else (1 if diff_x > 0 else -1)
    sign_y = 0 if diff_y == 0 else (1 if diff_y > 0 else -1)
    sign_changed = sign_x != 0 and sign_y != 0 and sign_x != sign_y

    if not sign_changed:
        return PairwiseReversalResult(
            classification=ReversalClass.STABLE_NO_SIGN_CHANGE,
            diff_x=diff_x, diff_y=diff_y, margin_x=margin_x, margin_y=margin_y,
            ci_x=None, ci_y=None,
            detail="no sign change between conditions (includes exact ties)",
        )

    both_margins_pass = margin_x > margin_fraction and margin_y > margin_fraction
    if not both_margins_pass:
        return PairwiseReversalResult(
            classification=ReversalClass.MICROSCOPIC_SIGN_CHANGE,
            diff_x=diff_x, diff_y=diff_y, margin_x=margin_x, margin_y=margin_y,
            ci_x=None, ci_y=None,
            detail=f"sign changed but margin_x={margin_x:.4f} or margin_y={margin_y:.4f} "
                   f"<= practical threshold {margin_fraction}",
        )

    boot_x = _bootstrap_diff_ci(pw_x, policy_a, policy_b, n_resamples=n_resamples, ci_level=ci_level, rng=rng)
    boot_y = _bootstrap_diff_ci(pw_y, policy_a, policy_b, n_resamples=n_resamples, ci_level=ci_level, rng=rng)
    ci_x = (boot_x[0], boot_x[1]) if boot_x is not None else None
    ci_y = (boot_y[0], boot_y[1]) if boot_y is not None else None
    p_x = boot_x[2] if boot_x is not None else None
    p_y = boot_y[2] if boot_y is not None else None
    ci_x_excludes_zero = ci_x is not None and not (ci_x[0] <= 0 <= ci_x[1])
    ci_y_excludes_zero = ci_y is not None and not (ci_y[0] <= 0 <= ci_y[1])

    if ci_x_excludes_zero and ci_y_excludes_zero:
        return PairwiseReversalResult(
            classification=ReversalClass.SUPPORTED_PRACTICAL_REVERSAL,
            diff_x=diff_x, diff_y=diff_y, margin_x=margin_x, margin_y=margin_y,
            ci_x=ci_x, ci_y=ci_y, p_x=p_x, p_y=p_y,
            detail="sign change, both margins > threshold, both bootstrap CIs exclude zero",
        )

    return PairwiseReversalResult(
        classification=ReversalClass.UNSUPPORTED_SIGN_CHANGE_WIDE_CI,
        diff_x=diff_x, diff_y=diff_y, margin_x=margin_x, margin_y=margin_y,
        ci_x=ci_x, ci_y=ci_y, p_x=p_x, p_y=p_y,
        detail="sign change with sufficient margin, but at least one condition's "
               "bootstrap CI on the sign of the difference does not exclude zero",
    )
