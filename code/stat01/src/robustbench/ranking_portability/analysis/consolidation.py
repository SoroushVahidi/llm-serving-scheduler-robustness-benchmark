"""Deterministic, idempotent consolidator for the (future) 64 Phase-12
campaign-shard outputs into one canonical matrix, plus a logically
separate independent completed-matrix validator that never trusts the
consolidator's own bookkeeping.

Both operate purely on in-memory dicts (manifest, shard outputs) so tests
can exercise every rule with small fabricated fixtures -- neither
function here ever guesses a default path to a real results directory
(see `result_blindness.py` for the guard enforcing that at the CLI layer).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from ..schema import validate_cell_result
from ..phase12_campaign import SCIENTIFIC_STATUS_PILOT_V2_SCIENTIFIC
from ...simulator.telemetry import TelemetrySummary, validate_telemetry

IDENTITY_FIELDS = ("source_family", "window_id", "load_region", "policy_id", "repetition")


def _row_problems(manifest_cell: dict, row: dict, region_assignment_index: dict) -> List[str]:
    problems: List[str] = []
    for f in IDENTITY_FIELDS:
        if row.get(f) != manifest_cell.get(f):
            problems.append(f"identity mismatch on {f}: manifest={manifest_cell.get(f)!r} row={row.get(f)!r}")
    if row.get("synthesis_seed") != manifest_cell.get("synthesis_seed"):
        problems.append(
            f"synthesis_seed mismatch: manifest={manifest_cell.get('synthesis_seed')!r} row={row.get('synthesis_seed')!r}"
        )
    if row.get("scientific_status") != SCIENTIFIC_STATUS_PILOT_V2_SCIENTIFIC:
        problems.append(
            f"scientific_status must be {SCIENTIFIC_STATUS_PILOT_V2_SCIENTIFIC!r}, got {row.get('scientific_status')!r}"
        )

    assignment = region_assignment_index.get(manifest_cell.get("region_assignment_key"))
    if assignment is None:
        problems.append(f"region_assignment_key {manifest_cell.get('region_assignment_key')!r} not found")
    else:
        expected_lf = assignment["absolute_load_factor"]
        row_lf = row.get("load_factor")
        if row_lf is None or abs(float(row_lf) - float(expected_lf)) > 1e-9:
            problems.append(f"load_factor mismatch: expected {expected_lf!r} (Phase-11 assignment), row={row_lf!r}")

    if row.get("success") is True:
        problems.extend(validate_cell_result(row))
        telemetry = row.get("telemetry")
        if isinstance(telemetry, dict):
            try:
                t = TelemetrySummary(**telemetry)
            except TypeError as e:
                problems.append(f"telemetry does not match TelemetrySummary: {e}")
            else:
                problems.extend(f"telemetry.{p}" for p in validate_telemetry(t))
    elif row.get("success") is False:
        pass  # a recorded failure is a valid row shape; just not a "complete" cell
    else:
        problems.append(f"row.success must be True or False, got {row.get('success')!r}")

    return problems


@dataclass
class ConsolidationReport:
    campaign_freeze_sha256: str
    n_expected_cells: int
    n_consolidated_valid: int
    n_missing: int
    n_failed: int
    n_invalid: int
    n_duplicate_cross_shard: int
    n_unknown_cell_ids: int
    n_wrong_provenance_shards: int
    missing_cell_ids: List[str] = field(default_factory=list)
    failed_cell_ids: List[str] = field(default_factory=list)
    invalid_cell_ids: List[str] = field(default_factory=list)
    duplicate_cell_ids: List[str] = field(default_factory=list)
    unknown_cell_ids: List[str] = field(default_factory=list)
    rep_mismatch_pairs: List[str] = field(default_factory=list)
    is_complete_and_valid: bool = False
    consolidated_rows: Dict[str, dict] = field(default_factory=dict)


def consolidate(
    *,
    manifest: dict,
    shard_outputs: Mapping[int, Tuple[str, Dict[str, dict]]],
    expected_campaign_freeze_sha256: str,
) -> ConsolidationReport:
    """`shard_outputs`: {shard_id: (claimed_campaign_freeze_prefix, {cell_id: row})}
    -- the caller (the CLI script, in production) is responsible for
    reading each shard file from its campaign-freeze-namespaced directory
    and passing along the directory-name prefix it actually read the file
    from, so provenance can be checked against where the bytes came from,
    not just against a field inside the JSON."""
    if manifest.get("campaign_freeze_sha256") != expected_campaign_freeze_sha256:
        raise ValueError(
            "Manifest campaign_freeze_sha256 "
            f"{manifest.get('campaign_freeze_sha256')!r} does not match the "
            f"expected identity {expected_campaign_freeze_sha256!r}. STOPPING."
        )
    expected_prefix = expected_campaign_freeze_sha256[:16]

    manifest_cells = {c["cell_id"]: c for c in manifest["cells"]}
    region_assignment_index = manifest["region_assignment_index"]
    n_expected = len(manifest_cells)

    consolidated: Dict[str, dict] = {}
    duplicate_ids: List[str] = []
    unknown_ids: List[str] = []
    invalid_ids: List[str] = []
    failed_ids: List[str] = []
    wrong_provenance_shards = 0

    for shard_id, (claimed_prefix, rows) in shard_outputs.items():
        if claimed_prefix != expected_prefix:
            wrong_provenance_shards += 1
            continue  # reject the whole shard's output -- wrong campaign lineage
        for cell_id, row in rows.items():
            if cell_id != row.get("cell_id"):
                invalid_ids.append(cell_id)
                continue
            manifest_cell = manifest_cells.get(cell_id)
            if manifest_cell is None:
                unknown_ids.append(cell_id)
                continue
            if cell_id in consolidated:
                duplicate_ids.append(cell_id)
                continue

            problems = _row_problems(manifest_cell, row, region_assignment_index)
            if problems:
                invalid_ids.append(cell_id)
                continue
            if row.get("success") is False:
                failed_ids.append(cell_id)
                continue
            consolidated[cell_id] = row

    missing_ids = sorted(set(manifest_cells) - set(consolidated) - set(failed_ids) - set(invalid_ids))

    # rep0/rep1 identical scientific-input check (§14): same
    # (source,window,region,policy) pair, both reps present and valid,
    # must share synthesis_seed and load_factor (they always do by
    # manifest construction, but this independently re-checks the
    # ACTUAL rows, not just the manifest's intent).
    by_quad: Dict[Tuple, Dict[int, dict]] = {}
    for cell_id, row in consolidated.items():
        quad = (row["source_family"], row["window_id"], row["load_region"], row["policy_id"])
        by_quad.setdefault(quad, {})[row["repetition"]] = row
    rep_mismatches: List[str] = []
    for quad, by_rep in by_quad.items():
        if 0 in by_rep and 1 in by_rep:
            r0, r1 = by_rep[0], by_rep[1]
            if r0["synthesis_seed"] != r1["synthesis_seed"] or abs(r0["load_factor"] - r1["load_factor"]) > 1e-9:
                rep_mismatches.append("::".join(map(str, quad)))

    n_valid = len(consolidated)
    is_complete = (
        n_valid == n_expected
        and not missing_ids and not failed_ids and not invalid_ids
        and not duplicate_ids and not unknown_ids
        and not wrong_provenance_shards and not rep_mismatches
    )

    return ConsolidationReport(
        campaign_freeze_sha256=expected_campaign_freeze_sha256,
        n_expected_cells=n_expected,
        n_consolidated_valid=n_valid,
        n_missing=len(missing_ids),
        n_failed=len(failed_ids),
        n_invalid=len(invalid_ids),
        n_duplicate_cross_shard=len(duplicate_ids),
        n_unknown_cell_ids=len(unknown_ids),
        n_wrong_provenance_shards=wrong_provenance_shards,
        missing_cell_ids=missing_ids,
        failed_cell_ids=sorted(failed_ids),
        invalid_cell_ids=sorted(invalid_ids),
        duplicate_cell_ids=sorted(duplicate_ids),
        unknown_cell_ids=sorted(unknown_ids),
        rep_mismatch_pairs=sorted(rep_mismatches),
        is_complete_and_valid=is_complete,
        consolidated_rows=consolidated if is_complete else {},
    )
