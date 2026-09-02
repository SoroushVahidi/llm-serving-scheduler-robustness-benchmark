"""Independent completed-matrix validator tests. Builds a full-scale
(18,720-cell-shaped) but entirely FABRICATED matrix -- real frozen
dimension constants (3 sources x 40 windows x 6 regions x 13 policies x
2 reps), synthetic window IDs and metric values, zero connection to any
real scheduler execution."""
from __future__ import annotations

import copy

import pytest

from robustbench.ranking_portability.analysis.matrix_validator import (
    IMMUTABLE_HASH_MANIFEST_KEYS,
    validate_completed_campaign,
)
from robustbench.ranking_portability.phase12_campaign import (
    CAMPAIGN_POLICIES,
    CAMPAIGN_REGIONS,
    CAMPAIGN_REPETITIONS,
    CAMPAIGN_SOURCES,
    WINDOWS_PER_SOURCE,
    generate_campaign_cell_specs,
)
from ranking_portability_analysis_fixtures import make_cell_row

FIXED_HASHES = {k: f"fixture-{k}" for k in IMMUTABLE_HASH_MANIFEST_KEYS}


def _build_full_fixture():
    window_ids_by_source = {
        s: [f"{s}_w{i:03d}" for i in range(WINDOWS_PER_SOURCE)] for s in CAMPAIGN_SOURCES
    }
    specs = generate_campaign_cell_specs(window_ids_by_source)
    consolidated_rows = {}
    assignment_index = {}
    for s in CAMPAIGN_SOURCES:
        for w in window_ids_by_source[s]:
            for r in CAMPAIGN_REGIONS:
                assignment_index[f"{s}::{w}::{r}"] = {
                    "lambda_ref": 1.0, "selected_load_factor": 1.0, "absolute_load_factor": 1.0,
                }
    for spec in specs:
        consolidated_rows[spec.cell_id] = make_cell_row(
            source_family=spec.source_family, window_id=spec.window_id,
            load_region=spec.load_region, policy_id=spec.policy_id,
            repetition=spec.repetition, synthesis_seed=7, load_factor=1.0,
        )
    manifest = {"region_assignment_index": assignment_index, **FIXED_HASHES}
    return manifest, consolidated_rows, window_ids_by_source


def test_full_fabricated_matrix_is_valid():
    manifest, rows, window_ids_by_source = _build_full_fixture()
    report = validate_completed_campaign(
        manifest=manifest, consolidated_rows=rows,
        window_ids_by_source=window_ids_by_source,
        expected_immutable_hashes=FIXED_HASHES,
    )
    assert report.valid, report.problems
    assert report.n_actual_valid_cells == 18720
    assert report.n_windows == 120
    assert all(n == WINDOWS_PER_SOURCE for n in report.n_windows_per_source.values())
    assert report.n_regions == 6
    assert report.n_policies == 13
    assert report.n_reps == 2
    assert report.n_assignment_keys_represented == 720
    assert report.n_rep_input_mismatches == 0
    assert report.secondary_stratum_leakage == []


def test_missing_cells_detected():
    manifest, rows, window_ids_by_source = _build_full_fixture()
    some_key = next(iter(rows))
    del rows[some_key]
    report = validate_completed_campaign(
        manifest=manifest, consolidated_rows=rows,
        window_ids_by_source=window_ids_by_source,
        expected_immutable_hashes=FIXED_HASHES,
    )
    assert not report.valid
    assert any("missing from consolidated matrix" in p for p in report.problems)


def test_secondary_stratum_leakage_detected():
    manifest, rows, window_ids_by_source = _build_full_fixture()
    some_key = next(iter(rows))
    rows[some_key]["policy_id"] = "not_a_real_panel_policy"
    report = validate_completed_campaign(
        manifest=manifest, consolidated_rows=rows,
        window_ids_by_source=window_ids_by_source,
        expected_immutable_hashes=FIXED_HASHES,
    )
    assert not report.valid
    assert "not_a_real_panel_policy" in report.secondary_stratum_leakage


def test_immutable_hash_drift_detected():
    manifest, rows, window_ids_by_source = _build_full_fixture()
    manifest["phase10_window_hash"] = "drifted-hash"
    report = validate_completed_campaign(
        manifest=manifest, consolidated_rows=rows,
        window_ids_by_source=window_ids_by_source,
        expected_immutable_hashes=FIXED_HASHES,
    )
    assert not report.valid
    assert any("immutable hash drift" in p for p in report.problems)


def test_rep_input_mismatch_detected():
    manifest, rows, window_ids_by_source = _build_full_fixture()
    # Find a rep0/rep1 pair and desync their synthesis_seed.
    for cid, row in rows.items():
        if row["repetition"] == 1:
            row["synthesis_seed"] = 999
            break
    report = validate_completed_campaign(
        manifest=manifest, consolidated_rows=rows,
        window_ids_by_source=window_ids_by_source,
        expected_immutable_hashes=FIXED_HASHES,
    )
    assert not report.valid
    assert report.n_rep_input_mismatches >= 1


def test_wrong_window_count_per_source_detected():
    manifest, rows, window_ids_by_source = _build_full_fixture()
    window_ids_by_source = copy.deepcopy(window_ids_by_source)
    window_ids_by_source[CAMPAIGN_SOURCES[0]] = window_ids_by_source[CAMPAIGN_SOURCES[0]][:-1]
    report = validate_completed_campaign(
        manifest=manifest, consolidated_rows=rows,
        window_ids_by_source=window_ids_by_source,
        expected_immutable_hashes=FIXED_HASHES,
    )
    assert not report.valid
    assert any("expected" in p and "windows" in p for p in report.problems)
