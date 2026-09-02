"""Independent completed-campaign-matrix validator. Deliberately does NOT
import or trust `consolidation.py`'s bookkeeping (mirrors
`scripts/ranking_portability/validate_phase12_campaign_freeze.py`'s
"independently re-derive, then diff" pattern for the pre-launch freeze) --
it re-derives the expected 18,720-cell Cartesian product itself from the
same frozen contract module the campaign-freeze builder uses, and checks
the actual consolidated matrix against that independently-reconstructed
expectation.

This module never executes a cell and never reads scheduler-outcome
values beyond their presence/schema-validity -- it answers "is the matrix
complete and structurally valid", not "who won".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Sequence

from ..calibration import REGION_SEQUENCE
from ..phase12_campaign import (
    CAMPAIGN_POLICIES,
    CAMPAIGN_REGIONS,
    CAMPAIGN_REPETITIONS,
    CAMPAIGN_SOURCES,
    EXPECTED_ASSIGNMENT_KEY_COUNT,
    EXPECTED_CAMPAIGN_CELL_COUNT,
    WINDOWS_PER_SOURCE,
    generate_campaign_cell_specs,
)
from .contract import PRIMARY_POLICIES, STYLE_APPROXIMATION_POLICIES

# The five immutable Phase-10/11 scientific hashes this validator must
# see preserved unchanged in the manifest (docs/PROJECT_STATUS.md §4).
IMMUTABLE_HASH_MANIFEST_KEYS = (
    "phase10_window_hash",
    "phase10_compact_index_hash",
    "phase11_prelaunch_hash",
    "phase11_raw_fifo_hash",
    "phase11_region_assignment_hash",
)


@dataclass
class MatrixValidationReport:
    problems: List[str] = field(default_factory=list)
    n_expected_cells: int = 0
    n_actual_valid_cells: int = 0
    n_windows: int = 0
    n_windows_per_source: Dict[str, int] = field(default_factory=dict)
    n_regions: int = 0
    n_policies: int = 0
    n_reps: int = 0
    n_assignment_keys_represented: int = 0
    n_rep_input_mismatches: int = 0
    n_rep_output_metric_diagnostic_mismatches: int = 0
    secondary_stratum_leakage: List[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.problems


def validate_completed_campaign(
    *,
    manifest: dict,
    consolidated_rows: Mapping[str, dict],
    window_ids_by_source: Mapping[str, Sequence[str]],
    expected_immutable_hashes: Mapping[str, str],
) -> MatrixValidationReport:
    problems: List[str] = []

    # --- Independently reconstruct the expected cell-identity set ---
    if EXPECTED_CAMPAIGN_CELL_COUNT != 18720:
        problems.append(f"contract module's own expected cell count changed: {EXPECTED_CAMPAIGN_CELL_COUNT}")
    expected_specs = generate_campaign_cell_specs(dict(window_ids_by_source))
    expected_cell_ids = {s.cell_id for s in expected_specs}
    if len(expected_cell_ids) != EXPECTED_CAMPAIGN_CELL_COUNT:
        problems.append(
            f"independently reconstructed {len(expected_cell_ids)} unique cell IDs, "
            f"expected {EXPECTED_CAMPAIGN_CELL_COUNT}"
        )

    actual_ids = set(consolidated_rows.keys())
    missing = expected_cell_ids - actual_ids
    unexpected = actual_ids - expected_cell_ids
    if missing:
        problems.append(f"{len(missing)} expected cell(s) missing from consolidated matrix, e.g. {sorted(missing)[:3]}")
    if unexpected:
        problems.append(f"{len(unexpected)} unexpected cell(s) in consolidated matrix, e.g. {sorted(unexpected)[:3]}")

    # --- Structural counts ---
    n_windows_by_source = {s: len(set(window_ids_by_source.get(s, []))) for s in CAMPAIGN_SOURCES}
    for s in CAMPAIGN_SOURCES:
        if n_windows_by_source[s] != WINDOWS_PER_SOURCE:
            problems.append(f"source {s!r} has {n_windows_by_source[s]} windows, expected {WINDOWS_PER_SOURCE}")
    n_windows_total = sum(n_windows_by_source.values())
    if n_windows_total != 120:
        problems.append(f"total windows = {n_windows_total}, expected 120")

    if set(CAMPAIGN_REGIONS) != set(REGION_SEQUENCE) or len(CAMPAIGN_REGIONS) != 6:
        problems.append(f"campaign regions changed from frozen 6-region grid: {CAMPAIGN_REGIONS}")

    expected_policy_set = set(PRIMARY_POLICIES) | set(STYLE_APPROXIMATION_POLICIES)
    if set(CAMPAIGN_POLICIES) != expected_policy_set or len(CAMPAIGN_POLICIES) != 13:
        problems.append(f"campaign policy panel changed from frozen 13-policy set: {set(CAMPAIGN_POLICIES) ^ expected_policy_set}")

    if set(CAMPAIGN_REPETITIONS) != {0, 1}:
        problems.append(f"repetitions changed from frozen {{0,1}}: {CAMPAIGN_REPETITIONS}")

    # --- Secondary-stratum leakage: no cell may use a policy outside the
    # frozen 13-policy panel, and STYLE_APPROXIMATION policies may never
    # be silently treated as PRIMARY downstream (checked again here, not
    # just trusted from contract.py, in case a row's own policy_id drifted). ---
    leakage = sorted({
        row["policy_id"] for row in consolidated_rows.values()
        if row["policy_id"] not in expected_policy_set
    })
    if leakage:
        problems.append(f"secondary-stratum leakage: policy_id(s) outside frozen panel: {leakage}")

    # --- Phase-11 assignment coverage ---
    assignment_index = manifest.get("region_assignment_index", {})
    if len(assignment_index) != EXPECTED_ASSIGNMENT_KEY_COUNT:
        problems.append(
            f"region_assignment_index has {len(assignment_index)} keys, expected {EXPECTED_ASSIGNMENT_KEY_COUNT}"
        )
    used_assignment_keys = {
        f"{row['source_family']}::{row['window_id']}::{row['load_region']}"
        for row in consolidated_rows.values()
    }
    unused = set(assignment_index.keys()) - used_assignment_keys
    if unused:
        problems.append(f"{len(unused)} Phase-11 assignment key(s) never used by any cell, e.g. {sorted(unused)[:3]}")

    # --- Immutable hash preservation ---
    for key in IMMUTABLE_HASH_MANIFEST_KEYS:
        expected = expected_immutable_hashes.get(key)
        actual = manifest.get(key)
        if expected is not None and actual != expected:
            problems.append(f"immutable hash drift on {key}: expected {expected!r}, manifest has {actual!r}")

    # --- Deterministic repetition agreement (§ input identity, the
    # frozen contract's actual claim -- "rep0/rep1 share identical
    # seed/input", never a claim about output-metric equality) ---
    by_quad: Dict[tuple, Dict[int, dict]] = {}
    for row in consolidated_rows.values():
        quad = (row["source_family"], row["window_id"], row["load_region"], row["policy_id"])
        by_quad.setdefault(quad, {})[row["repetition"]] = row
    n_input_mismatch = 0
    n_output_diag_mismatch = 0
    for by_rep in by_quad.values():
        if 0 in by_rep and 1 in by_rep:
            r0, r1 = by_rep[0], by_rep[1]
            if r0["synthesis_seed"] != r1["synthesis_seed"] or abs(r0["load_factor"] - r1["load_factor"]) > 1e-9:
                n_input_mismatch += 1
            # Diagnostic only (not part of the frozen invalidity gate):
            # since the simulator is deterministic given identical inputs,
            # an ANWG mismatch despite identical inputs signals an
            # engineering bug worth surfacing, but the protocol does not
            # declare it scientifically invalidating on its own.
            if r0.get("success") and r1.get("success"):
                a0 = r0.get("arrival_normalized_weighted_goodput")
                a1 = r1.get("arrival_normalized_weighted_goodput")
                if a0 is not None and a1 is not None and a0 == a0 and a1 == a1 and abs(a0 - a1) > 1e-9:
                    n_output_diag_mismatch += 1
    if n_input_mismatch:
        problems.append(f"{n_input_mismatch} (source,window,region,policy) pair(s) have rep0/rep1 input (seed/load_factor) mismatch")

    n_assignment_keys_represented = len(used_assignment_keys & set(assignment_index.keys()))

    return MatrixValidationReport(
        problems=problems,
        n_expected_cells=EXPECTED_CAMPAIGN_CELL_COUNT,
        n_actual_valid_cells=len(consolidated_rows),
        n_windows=n_windows_total,
        n_windows_per_source=n_windows_by_source,
        n_regions=len(CAMPAIGN_REGIONS),
        n_policies=len(CAMPAIGN_POLICIES),
        n_reps=len(CAMPAIGN_REPETITIONS),
        n_assignment_keys_represented=n_assignment_keys_represented,
        n_rep_input_mismatches=n_input_mismatch,
        n_rep_output_metric_diagnostic_mismatches=n_output_diag_mismatch,
        secondary_stratum_leakage=leakage,
    )
