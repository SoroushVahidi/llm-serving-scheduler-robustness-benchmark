"""Omnibus heterogeneity check + multiple-testing correction
(docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md §B,
docs/STATISTICAL_ANALYSIS_PLAN.md "Multiple-testing correction"):
Friedman rank-sum test (block=window, treatment=policy) as a
pre-registered, non-outcome-tuned omnibus check run BEFORE any pairwise
decomposition, per metric and load region; Benjamini-Hochberg FDR at
q=0.05 applied per family (e.g. all pairwise-reversal tests within one
load level), never globally across every section's tests at once.

No alternative omnibus test is implemented or selectable here -- adding
one only because it exists would violate "no result-dependent method
selection" (docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md §J of the task).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Sequence

from .contract import FDR_Q
from .ranking_analysis import per_window_policy_values
from .stats import FriedmanResult, benjamini_hochberg, friedman_omnibus


def friedman_for_condition(rows: Sequence[Mapping], *, metric: str) -> FriedmanResult:
    per_window = per_window_policy_values(rows, metric)
    return friedman_omnibus(per_window)


@dataclass
class FDRFamilyResult:
    family_label: str
    p_values: List[float]
    rejected: List[bool]
    q: float


def apply_fdr_family(family_label: str, p_values: Sequence[float], *, q: float = FDR_Q) -> FDRFamilyResult:
    rejected = benjamini_hochberg(list(p_values), q=q)
    return FDRFamilyResult(family_label=family_label, p_values=list(p_values), rejected=rejected, q=q)
