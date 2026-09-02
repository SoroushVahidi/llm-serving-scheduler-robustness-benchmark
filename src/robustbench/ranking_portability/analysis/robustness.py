"""Robustness-subset selectors (docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md
§F). Every function here is a pure ROW FILTER over an already-consolidated,
already-validated row set -- none of them execute a cell, and none of
them are used to pick which headline finding to report (they run
alongside every RQ1/RQ2/RQ5 headline finding, not instead of it).

Two robustness items from the plan are classified explicitly rather
than implemented as postprocessing, per the task's instruction that
anything requiring new scheduler outcomes must never be disguised as a
row filter:

- SLO-definition sensitivity: the alternative SLO-synthesis rule
  (`docs/DATA_FIELD_PROVENANCE.md` item 3, `docs/EXPERIMENT_CAMPAIGN_PLAN.md`
  Stage 5) changes how requests are LABELED AT SYNTHESIS TIME, which
  requires resimulating with the alternative SLO rule -- it cannot be
  recovered from the frozen campaign's existing metric columns.
- Seed sensitivity: not applicable at all (deterministic simulator).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Sequence

from .contract import (
    FOUR_REGION_SUBSET,
    POLICY_FAMILY,
    PRIMARY_POLICIES,
    SEED_SENSITIVITY_APPLICABLE,
    SIX_REGION_GRID,
)


def filter_primary_only(rows: Sequence[Mapping]) -> List[Mapping]:
    primary = set(PRIMARY_POLICIES)
    return [r for r in rows if r["policy_id"] in primary]


def filter_leave_one_source_out(rows: Sequence[Mapping], excluded_source: str) -> List[Mapping]:
    return [r for r in rows if r["source_family"] != excluded_source]


def filter_leave_one_policy_family_out(rows: Sequence[Mapping], excluded_family: str) -> List[Mapping]:
    return [r for r in rows if POLICY_FAMILY.get(r["policy_id"]) != excluded_family]


def filter_four_region_subset(rows: Sequence[Mapping]) -> List[Mapping]:
    allowed = set(FOUR_REGION_SUBSET)
    return [r for r in rows if r["load_region"] in allowed]


def all_policy_families() -> List[str]:
    return sorted(set(POLICY_FAMILY.values()))


@dataclass
class RobustnessComponentStatus:
    component: str
    implemented_as_postprocessing: bool
    new_execution_required_for_this_sensitivity: bool
    note: str


ROBUSTNESS_COMPONENT_STATUS: Dict[str, RobustnessComponentStatus] = {
    "PRIMARY_ONLY": RobustnessComponentStatus(
        "PRIMARY_ONLY", True, False,
        "Row filter over the existing 13-policy panel's 11 PRIMARY members; "
        "no resimulation.",
    ),
    "LEAVE_ONE_SOURCE_OUT": RobustnessComponentStatus(
        "LEAVE_ONE_SOURCE_OUT", True, False,
        "Row filter excluding one of the 3 frozen sources; no resimulation.",
    ),
    "WINDOW_SIZE_SENSITIVITY": RobustnessComponentStatus(
        "WINDOW_SIZE_SENSITIVITY", True, False,
        "= the sample-complexity subsampling ladder (sample_complexity.py); "
        "row selection over already-executed windows, no resimulation.",
    ),
    "METRIC_DEFINITION_SENSITIVITY": RobustnessComponentStatus(
        "METRIC_DEFINITION_SENSITIVITY", True, False,
        "Compares the frozen per-policy exclusion rule "
        "(docs/RANKING_PORTABILITY_METRIC_DEFINITIONS.md) against a "
        "same-family 'drop the whole condition' alternative, computed purely "
        "from the existing consolidated metric columns; no resimulation.",
    ),
    "LOAD_CALIBRATION_SENSITIVITY": RobustnessComponentStatus(
        "LOAD_CALIBRATION_SENSITIVITY", True, False,
        "Row filter to the 4-region subset of the already-executed 6-region "
        "grid; no resimulation.",
    ),
    "TEMPORAL_SPLIT_SENSITIVITY": RobustnessComponentStatus(
        "TEMPORAL_SPLIT_SENSITIVITY", True, False,
        "Bisect vs. tercile split of the same already-executed BurstGPT "
        "windows (temporal_analysis.py); no resimulation.",
    ),
    "LEAVE_ONE_POLICY_FAMILY_OUT": RobustnessComponentStatus(
        "LEAVE_ONE_POLICY_FAMILY_OUT", True, False,
        "Row filter excluding one mechanism family at a time; no resimulation.",
    ),
    "SLO_DEFINITION_SENSITIVITY": RobustnessComponentStatus(
        "SLO_DEFINITION_SENSITIVITY", False, True,
        "The alternative SLO-synthesis rule "
        "(docs/DATA_FIELD_PROVENANCE.md item 3, "
        "docs/EXPERIMENT_CAMPAIGN_PLAN.md Stage 5) changes request-level "
        "SLO labels at synthesis time, which the frozen campaign's existing "
        "cell columns cannot reconstruct after the fact -- flagged as "
        "NEW_EXECUTION_REQUIRED_FOR_THIS_SENSITIVITY = YES, not implemented "
        "as a row filter or metric recomputation.",
    ),
}


def seed_sensitivity_applicable() -> bool:
    return SEED_SENSITIVITY_APPLICABLE  # False: deterministic simulator, no seed axis exists
