"""Targeted tests for the Phase-12A engineering-smoke selection contract
(robustbench.ranking_portability.phase12_smoke). No real workload data or
simulator execution is needed -- these tests only check the deterministic,
outcome-blind matrix-construction logic itself.
"""
from __future__ import annotations

from robustbench.policies.registry import make_policy_any
from robustbench.ranking_portability.calibration import REGION_SEQUENCE
from robustbench.ranking_portability.phase12_smoke import (
    EXPECTED_SMOKE_CELL_COUNT,
    SCIENTIFIC_STATUS_ENGINEERING_SMOKE,
    SMOKE_POLICIES,
    SMOKE_REGIONS,
    SMOKE_REPETITIONS,
    SMOKE_SOURCES,
    SMOKE_WINDOW_IDS,
    compute_smoke_freeze_identity,
    generate_smoke_cell_specs,
    synthesis_seed_for_window,
)


def test_expected_cell_count_is_468():
    assert EXPECTED_SMOKE_CELL_COUNT == 3 * 1 * 6 * 13 * 2 == 468


def test_scientific_status_marker_is_smoke_not_confused_with_real_evidence():
    assert SCIENTIFIC_STATUS_ENGINEERING_SMOKE == "ENGINEERING_SMOKE"
    assert SCIENTIFIC_STATUS_ENGINEERING_SMOKE != "FIXTURE_ONLY_DO_NOT_ANALYZE"


def test_three_primary_sources_only():
    assert set(SMOKE_SOURCES) == {"burstgpt", "azure_llm_2024", "bailian_qwen"}
    assert len(SMOKE_SOURCES) == 3


def test_one_window_per_source_selected_by_canonical_first_position():
    assert len(SMOKE_WINDOW_IDS) == 3
    for source in SMOKE_SOURCES:
        # Canonical manifest ordering: source's first frozen window is its
        # Stage-0-reused w00 (never chosen by inspecting outcome/content).
        assert SMOKE_WINDOW_IDS[source] == f"{source}_stage0_w00"


def test_all_six_frozen_regions_included_in_frozen_order():
    assert tuple(SMOKE_REGIONS) == tuple(REGION_SEQUENCE)
    assert list(SMOKE_REGIONS) == [
        "LOW", "PRE_KNEE", "KNEE", "POST_KNEE", "OVERLOAD", "HIGH_PRESSURE",
    ]


def test_thirteen_primary_policies_no_secondary_stratum_policies():
    assert len(SMOKE_POLICIES) == 13
    assert len(set(SMOKE_POLICIES)) == 13  # no duplicates
    assert "distserve_faithful" not in SMOKE_POLICIES
    assert "llumnix_faithful" not in SMOKE_POLICIES
    assert "apt_serve_faithful" not in SMOKE_POLICIES


def test_every_smoke_policy_name_resolves_via_registry():
    """Fails fast, before any real execution, if a policy name typo or a
    registry gap exists (the exact class of bug
    docs/RANKING_PORTABILITY_TELEMETRY_IMPLEMENTATION.md's registry-gap fix
    was written to close)."""
    for name in SMOKE_POLICIES:
        policy = make_policy_any(name)
        assert policy is not None


def test_two_repetitions_rep0_rep1_only():
    assert tuple(SMOKE_REPETITIONS) == (0, 1)


def test_cell_matrix_has_expected_count_and_no_duplicates():
    specs = generate_smoke_cell_specs()
    assert len(specs) == EXPECTED_SMOKE_CELL_COUNT
    ids = [s.cell_id for s in specs]
    assert len(ids) == len(set(ids)), "duplicate cell_id detected in smoke matrix"


def test_cell_matrix_is_exact_cartesian_coverage():
    specs = generate_smoke_cell_specs()
    seen = {
        (s.source_family, s.window_id, s.load_region, s.policy_id, s.repetition)
        for s in specs
    }
    expected = set()
    for source in SMOKE_SOURCES:
        window_id = SMOKE_WINDOW_IDS[source]
        for region in SMOKE_REGIONS:
            for policy in SMOKE_POLICIES:
                for rep in SMOKE_REPETITIONS:
                    expected.add((source, window_id, region, policy, rep))
    assert seen == expected


def test_cell_matrix_every_source_window_has_all_policies_and_reps():
    specs = generate_smoke_cell_specs()
    for source in SMOKE_SOURCES:
        window_id = SMOKE_WINDOW_IDS[source]
        subset = [s for s in specs if s.source_family == source and s.window_id == window_id]
        assert len(subset) == len(SMOKE_REGIONS) * len(SMOKE_POLICIES) * len(SMOKE_REPETITIONS)
        for region in SMOKE_REGIONS:
            region_subset = [s for s in subset if s.load_region == region]
            assert len(region_subset) == len(SMOKE_POLICIES) * len(SMOKE_REPETITIONS)
            policies_seen = {s.policy_id for s in region_subset}
            assert policies_seen == set(SMOKE_POLICIES)
            for policy in SMOKE_POLICIES:
                reps_seen = {s.repetition for s in region_subset if s.policy_id == policy}
                assert reps_seen == {0, 1}


def test_synthesis_seed_matches_phase11_convention():
    # Identical to build_phase11_calibration.py's `900000 + int(window_id...)`.
    assert synthesis_seed_for_window("burstgpt_stage0_w00") == 900000
    assert synthesis_seed_for_window("azure_llm_2024_stage0_w00") == 900000
    assert synthesis_seed_for_window("bailian_qwen_pilot_v2_w15") == 900015


def test_rep0_and_rep1_use_identical_synthesis_seed_for_same_window():
    specs = generate_smoke_cell_specs()
    seeds = {synthesis_seed_for_window(s.window_id) for s in specs if s.source_family == "burstgpt"}
    assert seeds == {900000}


def test_smoke_freeze_identity_is_deterministic_and_order_independent_of_call():
    kwargs = dict(
        parent_branch_sha="a" * 40,
        phase10_window_hash="b" * 64,
        phase11_prelaunch_hash="c" * 64,
        phase11_raw_fifo_hash="d" * 64,
        phase11_region_assignment_hash="e" * 64,
        execution_file_hashes={"x.py": "1" * 64, "y.py": "2" * 64},
    )
    r1 = compute_smoke_freeze_identity(**kwargs)
    r2 = compute_smoke_freeze_identity(**kwargs)
    assert r1["smoke_freeze_sha256"] == r2["smoke_freeze_sha256"]
    assert len(r1["smoke_freeze_sha256"]) == 64


def test_smoke_freeze_identity_changes_if_any_input_changes():
    kwargs = dict(
        parent_branch_sha="a" * 40,
        phase10_window_hash="b" * 64,
        phase11_prelaunch_hash="c" * 64,
        phase11_raw_fifo_hash="d" * 64,
        phase11_region_assignment_hash="e" * 64,
        execution_file_hashes={"x.py": "1" * 64},
    )
    r1 = compute_smoke_freeze_identity(**kwargs)
    kwargs["parent_branch_sha"] = "f" * 40
    r2 = compute_smoke_freeze_identity(**kwargs)
    assert r1["smoke_freeze_sha256"] != r2["smoke_freeze_sha256"]
