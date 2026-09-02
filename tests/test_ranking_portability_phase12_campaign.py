"""Targeted tests for the Phase-12B campaign matrix contract
(robustbench.ranking_portability.phase12_campaign). Uses the real, frozen
compact window index -- no scientific execution, no synthesized data.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from robustbench.policies.registry import make_policy_any
from robustbench.ranking_portability.calibration import REGION_SEQUENCE
from robustbench.ranking_portability.phase12_campaign import (
    CAMPAIGN_POLICIES,
    CAMPAIGN_REGIONS,
    CAMPAIGN_REPETITIONS,
    CAMPAIGN_SOURCES,
    CELLS_PER_ASSIGNMENT_KEY,
    EXPECTED_ASSIGNMENT_KEY_COUNT,
    EXPECTED_CAMPAIGN_CELL_COUNT,
    SCIENTIFIC_STATUS_PILOT_V2_SCIENTIFIC,
    WINDOWS_PER_SOURCE,
    compute_campaign_freeze_identity,
    generate_campaign_cell_specs,
    load_campaign_window_ids,
)
from robustbench.ranking_portability.phase12_smoke import SMOKE_POLICIES

REPO_ROOT = Path(__file__).resolve().parents[1]
COMPACT_INDEX_PATH = REPO_ROOT / "artifacts" / "manifests" / "ranking_portability_pilot_v2_windows_index.json"
ASSIGNMENTS_PATH = REPO_ROOT / "artifacts" / "manifests" / "ranking_portability_phase11_region_assignments.json"


@pytest.fixture(scope="module")
def compact_index() -> dict:
    with open(COMPACT_INDEX_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def window_ids_by_source(compact_index) -> dict:
    return load_campaign_window_ids(compact_index)


def test_expected_cell_count_is_18720():
    assert EXPECTED_CAMPAIGN_CELL_COUNT == 3 * 40 * 6 * 13 * 2 == 18720


def test_expected_assignment_key_count_is_720():
    assert EXPECTED_ASSIGNMENT_KEY_COUNT == 120 * 6 == 720
    assert CELLS_PER_ASSIGNMENT_KEY == 13 * 2 == 26
    assert EXPECTED_ASSIGNMENT_KEY_COUNT * CELLS_PER_ASSIGNMENT_KEY == EXPECTED_CAMPAIGN_CELL_COUNT


def test_scientific_status_distinct_from_smoke_status():
    assert SCIENTIFIC_STATUS_PILOT_V2_SCIENTIFIC == "PILOT_V2_SCIENTIFIC"
    from robustbench.ranking_portability.phase12_smoke import SCIENTIFIC_STATUS_ENGINEERING_SMOKE
    assert SCIENTIFIC_STATUS_PILOT_V2_SCIENTIFIC != SCIENTIFIC_STATUS_ENGINEERING_SMOKE


def test_three_primary_sources_six_regions_thirteen_policies_two_reps():
    assert set(CAMPAIGN_SOURCES) == {"burstgpt", "azure_llm_2024", "bailian_qwen"}
    assert tuple(CAMPAIGN_REGIONS) == tuple(REGION_SEQUENCE)
    assert len(CAMPAIGN_POLICIES) == 13
    assert tuple(CAMPAIGN_POLICIES) == tuple(SMOKE_POLICIES)  # identical panel/order to the smoke
    assert set(CAMPAIGN_REPETITIONS) == {0, 1}
    for excluded in ("distserve_faithful", "llumnix_faithful", "apt_serve_faithful"):
        assert excluded not in CAMPAIGN_POLICIES


def test_every_campaign_policy_resolves_via_registry():
    for name in CAMPAIGN_POLICIES:
        assert make_policy_any(name) is not None


def test_load_campaign_window_ids_from_real_compact_index(window_ids_by_source):
    assert set(window_ids_by_source.keys()) == set(CAMPAIGN_SOURCES)
    for source in CAMPAIGN_SOURCES:
        ids = window_ids_by_source[source]
        assert len(ids) == WINDOWS_PER_SOURCE == 40
        assert len(set(ids)) == 40  # no duplicates
        assert all(wid.startswith(source) for wid in ids)


def test_load_campaign_window_ids_rejects_wrong_count():
    fake_index = {"windows": [{"source_family": "burstgpt", "window_id": "burstgpt_w0"}]}
    with pytest.raises(ValueError):
        load_campaign_window_ids(fake_index)


def test_cell_matrix_has_expected_count_and_no_duplicates(window_ids_by_source):
    specs = generate_campaign_cell_specs(window_ids_by_source)
    assert len(specs) == EXPECTED_CAMPAIGN_CELL_COUNT
    ids = [s.cell_id for s in specs]
    assert len(ids) == len(set(ids))


def test_cell_matrix_is_exact_cartesian_coverage(window_ids_by_source):
    specs = generate_campaign_cell_specs(window_ids_by_source)
    seen = {(s.source_family, s.window_id, s.load_region, s.policy_id, s.repetition) for s in specs}
    expected = set()
    for source in CAMPAIGN_SOURCES:
        for window_id in window_ids_by_source[source]:
            for region in CAMPAIGN_REGIONS:
                for policy in CAMPAIGN_POLICIES:
                    for rep in CAMPAIGN_REPETITIONS:
                        expected.add((source, window_id, region, policy, rep))
    assert seen == expected


def test_every_window_has_all_regions_policies_reps(window_ids_by_source):
    specs = generate_campaign_cell_specs(window_ids_by_source)
    for source in CAMPAIGN_SOURCES:
        for window_id in window_ids_by_source[source]:
            subset = [s for s in specs if s.source_family == source and s.window_id == window_id]
            assert len(subset) == len(CAMPAIGN_REGIONS) * len(CAMPAIGN_POLICIES) * len(CAMPAIGN_REPETITIONS)


def test_real_frozen_assignments_cover_every_campaign_key_exactly_once():
    with open(ASSIGNMENTS_PATH) as f:
        assign_doc = json.load(f)
    keys = [(a["source"], a["window_id"], a["region"]) for a in assign_doc["assignments"]]
    assert len(keys) == EXPECTED_ASSIGNMENT_KEY_COUNT == 720
    assert len(set(keys)) == 720  # no duplicates

    with open(COMPACT_INDEX_PATH) as f:
        compact_index = json.load(f)
    window_ids_by_source_ = load_campaign_window_ids(compact_index)
    expected_keys = {
        (source, window_id, region)
        for source in CAMPAIGN_SOURCES
        for window_id in window_ids_by_source_[source]
        for region in CAMPAIGN_REGIONS
    }
    assert set(keys) == expected_keys


def test_campaign_freeze_identity_deterministic():
    kwargs = dict(
        parent_smoke_branch_sha="a" * 40,
        telemetry_amendment_sha256="b" * 64,
        phase10_window_hash="c" * 64,
        phase11_prelaunch_hash="d" * 64,
        phase11_raw_fifo_hash="e" * 64,
        phase11_region_assignment_hash="f" * 64,
        window_ids_by_source={"burstgpt": ["w0", "w1"]},
        execution_file_hashes={"x.py": "1" * 64},
        full_matrix_hash="9" * 64,
    )
    r1 = compute_campaign_freeze_identity(**kwargs)
    r2 = compute_campaign_freeze_identity(**kwargs)
    assert r1["campaign_freeze_sha256"] == r2["campaign_freeze_sha256"]
    assert len(r1["campaign_freeze_sha256"]) == 64
