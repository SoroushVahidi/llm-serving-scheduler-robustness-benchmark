"""Tests for the LSSP dataset-release contract/validator/builder
(docs/LSSP_DATASET_RELEASE_SCHEMA.md, docs/LSSP_DATASET_RELEASE_PREFREEZE.md).

Result-blindness guard for this test module itself: every fixture below is
hand-built with fabricated numeric values that have no connection to any
real Phase-12 scheduler outcome. The only *real* artifacts read here are
the frozen, non-scientific-outcome manifests already committed to this
repo (window/region-assignment/policy-panel identity) -- reading those is
explicitly permitted (they carry zero scheduler-performance content) and
is exercised in `TestStaticTablesAgainstRealFrozenManifests` to prove the
builder works against the actual frozen 18,720-cell identity, not just a
toy fixture.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from robustbench.dataset.lssp_release_contract import (
    LSSP_DATASET_RELEASE_VERSION,
    STATIC_TABLES_BUILDABLE_PREFREEZE,
    FieldCategory,
    FrozenCampaignIdentity,
    SCHEDULER_OUTCOMES_FIELD_CATEGORY,
    build_load_region_assignments_table,
    build_policy_registry_table,
    build_workload_descriptors_table,
    build_workload_windows_table,
    compute_aggregate_hash,
    load_frozen_campaign_identity,
    validate_scheduler_outcomes_row,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REAL_CAMPAIGN_MANIFEST = (
    REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_campaign_freeze.json"
)
REAL_WINDOWS_INDEX = (
    REPO_ROOT / "artifacts/manifests/ranking_portability_pilot_v2_windows_index.json"
)


# ---------------------------------------------------------------------------
# Fabricated fixtures -- no connection to any real scheduler outcome
# ---------------------------------------------------------------------------

FAKE_CELL_IDS = frozenset({
    "fakesource::fakewindow_w00::LOW::fake_policy_a::rep0",
    "fakesource::fakewindow_w00::LOW::fake_policy_a::rep1",
})

FAKE_IDENTITY = FrozenCampaignIdentity(
    campaign_freeze_sha256="fake_campaign_sha_0000000000000000000000000000000000000000000000000000",
    full_matrix_hash="fake_matrix_hash",
    expected_cell_count=2,
    cell_ids=FAKE_CELL_IDS,
    window_ids=frozenset({"fakewindow_w00"}),
    source_families=frozenset({"fakesource"}),
    load_regions=frozenset({"LOW"}),
    policy_ids=frozenset({"fake_policy_a"}),
    region_assignment_keys=frozenset({"fakesource::fakewindow_w00::LOW"}),
)


def _fake_telemetry() -> dict:
    """A structurally valid, fabricated telemetry block (values invented for
    test coverage only, not sampled from any simulator run). Field set kept
    in sync with `robustbench.simulator.telemetry.TelemetrySummary` --
    this fixture predates that schema's queue_depth/admission-control/
    preemption/n_steps fields; adding fabricated values for them here is a
    test-fixture-drift fix, not a change to any scientific semantics."""
    return {
        "schema_version": "telemetry_v1",
        "queue_depth_mean": 1.5,
        "queue_depth_max": 3,
        "kv_occupancy_mean": 0.42,
        "kv_occupancy_max": 0.51,
        "batch_saturation_mean": 0.3,
        "batch_saturation_max": 0.4,
        "prefill_decode_contention_fraction": 0.1,
        "admission_control_activations": 0,
        "preemption_or_reorder_events": 0,
        "token_budget_saturation_fraction": 0.2,
        "n_steps": 100,
    }


def _fake_row(**overrides) -> dict:
    row = {
        "schema_version": "ranking_portability_cell_result_v1",
        "cell_id": "fakesource::fakewindow_w00::LOW::fake_policy_a::rep0",
        "source_family": "fakesource",
        "window_id": "fakewindow_w00",
        "load_region": "LOW",
        "load_factor": 1.0,
        "policy_id": "fake_policy_a",
        "repetition": 0,
        "synthesis_seed": 12345,
        "success": True,
        "repo_sha": "deadbeef",
        "telemetry_schema_version": "telemetry_v1",
        "telemetry": _fake_telemetry(),
        "arrival_normalized_weighted_goodput": 0.77,
        "completion_fraction": 1.0,
        "weighted_completion_fraction": 1.0,
        "slo_violation_rate": 0.05,
        "weighted_goodput": 0.9,
        "mean_latency": 1.2,
        "p95_latency": 2.3,
        "mean_ttft": 0.1,
        "p95_ttft": 0.2,
        "request_throughput": 10.0,
        "token_throughput": 500.0,
        "scientific_status": "PILOT_V2_SCIENTIFIC",
        "dataset_release_version": LSSP_DATASET_RELEASE_VERSION,
        "campaign_freeze_sha256": FAKE_IDENTITY.campaign_freeze_sha256,
    }
    row.update(overrides)
    return row


# ---------------------------------------------------------------------------
# Contract self-consistency
# ---------------------------------------------------------------------------

class TestFieldClassificationCompleteness:
    def test_every_required_field_is_classified(self):
        assert set(SCHEDULER_OUTCOMES_FIELD_CATEGORY.values()) <= {
            FieldCategory.IDENTIFIER, FieldCategory.SCIENTIFIC_INPUT,
            FieldCategory.OUTCOME, FieldCategory.PROVENANCE_METADATA,
        }

    def test_identifiers_are_not_outcomes(self):
        assert SCHEDULER_OUTCOMES_FIELD_CATEGORY["cell_id"] == FieldCategory.IDENTIFIER
        assert SCHEDULER_OUTCOMES_FIELD_CATEGORY["arrival_normalized_weighted_goodput"] == (
            FieldCategory.OUTCOME
        )


# ---------------------------------------------------------------------------
# scheduler_outcomes row validation (fabricated fixtures only)
# ---------------------------------------------------------------------------

class TestValidateSchedulerOutcomesRow:
    def test_valid_row_passes(self):
        assert validate_scheduler_outcomes_row(_fake_row(), FAKE_IDENTITY) == []

    def test_wrong_campaign_hash_rejected(self):
        problems = validate_scheduler_outcomes_row(
            _fake_row(campaign_freeze_sha256="some_other_hash"), FAKE_IDENTITY
        )
        assert any("campaign_freeze_sha256 mismatch" in p for p in problems)

    def test_unknown_cell_id_rejected(self):
        problems = validate_scheduler_outcomes_row(
            _fake_row(cell_id="unknownsource::unknownwindow::LOW::x::rep0"), FAKE_IDENTITY
        )
        assert any("not one of the 18,720 frozen cell IDs" in p for p in problems)

    def test_non_pilot_v2_scientific_status_rejected(self):
        """A Stage-0 or Phase-12A-smoke row must never be silently promoted
        into the release's scheduler_outcomes table."""
        problems = validate_scheduler_outcomes_row(
            _fake_row(scientific_status="PHASE12A_SMOKE"), FAKE_IDENTITY
        )
        assert any("PILOT_V2_SCIENTIFIC" in p for p in problems)

    def test_missing_dataset_release_version_rejected(self):
        row = _fake_row()
        del row["dataset_release_version"]
        problems = validate_scheduler_outcomes_row(row, FAKE_IDENTITY)
        assert any("dataset_release_version" in p for p in problems)

    def test_zero_completion_undefined_metrics_accepted(self):
        """completion_fraction == 0.0 -> conditional metrics may be NaN;
        this must be schema-valid, not an error."""
        row = _fake_row(
            completion_fraction=0.0, weighted_completion_fraction=0.0,
            slo_violation_rate=float("nan"), weighted_goodput=float("nan"),
            mean_latency=float("nan"), p95_latency=float("nan"),
            request_throughput=float("nan"), token_throughput=float("nan"),
        )
        problems = validate_scheduler_outcomes_row(row, FAKE_IDENTITY)
        assert problems == []

    def test_nonzero_completion_but_undefined_conditional_metric_rejected(self):
        """completion_fraction > 0 but a CONDITIONAL_ON_COMPLETION metric is
        NaN anyway -- this must be a schema violation, not silently accepted
        or imputed."""
        row = _fake_row(completion_fraction=0.5, mean_latency=float("nan"))
        problems = validate_scheduler_outcomes_row(row, FAKE_IDENTITY)
        assert any("mean_latency is NaN despite completion_fraction != 0.0" in p for p in problems)

    def test_ttft_undefined_with_full_completion_accepted(self):
        """mean_ttft/p95_ttft have their own, stricter precondition
        (no completed request recorded a first-token time) -- may be NaN
        even when completion_fraction > 0, and must not be flagged."""
        row = _fake_row(completion_fraction=1.0, mean_ttft=float("nan"), p95_ttft=float("nan"))
        problems = validate_scheduler_outcomes_row(row, FAKE_IDENTITY)
        assert problems == []

    def test_always_defined_metric_nan_rejected(self):
        row = _fake_row(arrival_normalized_weighted_goodput=float("nan"))
        problems = validate_scheduler_outcomes_row(row, FAKE_IDENTITY)
        assert any("ALWAYS_DEFINED" in p for p in problems)

    def test_kv_occupancy_above_one_accepted_not_a_ceiling_violation(self):
        """docs/RANKING_PORTABILITY_PHASE12_TELEMETRY_SEMANTIC_AMENDMENT.md:
        kv_occupancy is normalized demand, no upper ceiling."""
        row = _fake_row()
        row["telemetry"] = dict(row["telemetry"], kv_occupancy_mean=1.4, kv_occupancy_max=1.9)
        assert validate_scheduler_outcomes_row(row, FAKE_IDENTITY) == []

    def test_kv_occupancy_max_below_mean_still_rejected(self):
        """The one telemetry invariant the amendment kept: max >= mean."""
        row = _fake_row()
        row["telemetry"] = dict(row["telemetry"], kv_occupancy_mean=0.9, kv_occupancy_max=0.1)
        problems = validate_scheduler_outcomes_row(row, FAKE_IDENTITY)
        assert any("telemetry" in p for p in problems)

    def test_missing_telemetry_rejected_on_success(self):
        row = _fake_row(telemetry={}, telemetry_schema_version="")
        problems = validate_scheduler_outcomes_row(row, FAKE_IDENTITY)
        assert any("telemetry" in p for p in problems)

    def test_repetition_must_be_0_or_1(self):
        row = _fake_row(repetition=2)
        problems = validate_scheduler_outcomes_row(row, FAKE_IDENTITY)
        assert any("repetition must be 0 or 1" in p for p in problems)


# ---------------------------------------------------------------------------
# compute_aggregate_hash determinism
# ---------------------------------------------------------------------------

class TestAggregateHash:
    def test_deterministic_and_key_order_independent(self):
        a = compute_aggregate_hash({"x": 1, "y": 2})
        b = compute_aggregate_hash({"y": 2, "x": 1})
        assert a == b

    def test_sensitive_to_content(self):
        a = compute_aggregate_hash({"x": 1})
        b = compute_aggregate_hash({"x": 2})
        assert a != b


# ---------------------------------------------------------------------------
# Static table builders -- tiny fabricated windows-index fixture
# ---------------------------------------------------------------------------

def _fake_windows_index() -> dict:
    return {
        "windows": [
            {
                "window_id": "fakewindow_w00",
                "source_family": "fakesource",
                "evidence_class": "STAGE0_WINDOW",
                "chronology_stratum": "EARLY",
                "request_count": 200,
                "arrival_time_s_min": 0.0,
                "arrival_time_s_max": 45.0,
                "source_file": "fake.csv",
                "source_file_sha256": "fakehash",
                "sampling_algorithm": "fake_v1",
                "sampling_seed": 1,
                "descriptor": {
                    "source_family": "fakesource", "window_id": "fakewindow_w00",
                    "time_bucket": None, "request_count": 200, "duration_s": 45.0,
                    "arrival_rate_rps": 4.4,
                },
            },
        ],
    }


def _fake_campaign_manifest() -> dict:
    return {
        "EXPECTED_PHASE12_CAMPAIGN_CELLS": 2,
        "campaign_freeze_sha256": FAKE_IDENTITY.campaign_freeze_sha256,
        "full_matrix_hash": "fake_matrix_hash",
        "phase11_region_assignment_hash": "fake_p11_hash",
        "region_assignment_index": {
            "fakesource::fakewindow_w00::LOW": {
                "lambda_ref": 10.0, "selected_load_factor": 1.0, "absolute_load_factor": 10.0,
            },
        },
        "cells": [
            {"cell_id": cid, "window_id": "fakewindow_w00", "source_family": "fakesource",
             "load_region": "LOW", "policy_id": "fake_policy_a"}
            for cid in FAKE_CELL_IDS
        ],
    }


class TestStaticTableBuildersFabricated:
    def test_workload_windows_table(self):
        rows = build_workload_windows_table(_fake_windows_index())
        assert len(rows) == 1
        assert rows[0]["workload_window_id"] == "fakewindow_w00"
        assert rows[0]["source_family"] == "fakesource"

    def test_workload_descriptors_table(self):
        rows = build_workload_descriptors_table(_fake_windows_index())
        assert rows[0]["workload_window_id"] == "fakewindow_w00"
        assert "window_id" not in rows[0]

    def test_load_region_assignments_table(self):
        rows = build_load_region_assignments_table(_fake_campaign_manifest())
        assert len(rows) == 1
        assert rows[0]["load_region"] == "LOW"
        assert rows[0]["lambda_ref"] == 10.0

    def test_policy_registry_table_passthrough(self):
        panel = [{"policy_id": "fake_policy_a", "fidelity_class": "X", "panel_status": "PRIMARY"}]
        assert build_policy_registry_table(panel) == panel

    def test_load_frozen_campaign_identity_from_fabricated_manifest(self, tmp_path):
        p = tmp_path / "fake_manifest.json"
        p.write_text(json.dumps(_fake_campaign_manifest()))
        identity = load_frozen_campaign_identity(p)
        assert identity.expected_cell_count == 2
        assert identity.cell_ids == FAKE_CELL_IDS


# ---------------------------------------------------------------------------
# Result-blindness guard: no default path resolves a live campaign-results dir
# ---------------------------------------------------------------------------

class TestResultBlindnessGuard:
    def test_module_has_no_reference_to_a_live_campaign_results_default_path(self):
        import robustbench.dataset.lssp_release_contract as mod

        src = Path(mod.__file__).read_text()
        assert "artifacts/campaign_results" not in src
        assert "campaign_results" not in src

    def test_scheduler_outcomes_never_built_without_explicit_validated_input(self):
        """The builder script requires --consolidated-input AND
        --matrix-validation-report; a bare --out-dir build only ever
        produces the four static tables. Verified structurally here
        rather than by invoking the CLI (kept as a fast unit check)."""
        import ast

        script = REPO_ROOT / "scripts/dataset/build_lssp_release.py"
        tree = ast.parse(script.read_text())
        source = script.read_text()
        assert "--consolidated-input" in source
        assert "--matrix-validation-report" in source
        assert "REFUSED" in source


# ---------------------------------------------------------------------------
# Integration against the REAL frozen (non-scientific-outcome) manifests.
# These manifests carry zero scheduler-performance content -- window
# identity, region-assignment provenance, and cell-ID/policy-ID sets only
# -- so reading them here does not violate result-blindness.
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not (REAL_CAMPAIGN_MANIFEST.exists() and REAL_WINDOWS_INDEX.exists()),
    reason="real frozen manifests not present in this checkout",
)
class TestStaticTablesAgainstRealFrozenManifests:
    def test_real_identity_counts(self):
        identity = load_frozen_campaign_identity(REAL_CAMPAIGN_MANIFEST)
        assert identity.expected_cell_count == 18720
        assert len(identity.cell_ids) == 18720
        assert len(identity.window_ids) == 120
        assert len(identity.region_assignment_keys) == 720
        assert len(identity.policy_ids) == 13

    def test_real_workload_windows_table_shape(self):
        windows_index = json.loads(REAL_WINDOWS_INDEX.read_text())
        rows = build_workload_windows_table(windows_index)
        assert len(rows) == 120
        per_source: dict[str, int] = {}
        for r in rows:
            per_source[r["source_family"]] = per_source.get(r["source_family"], 0) + 1
        assert all(n == 40 for n in per_source.values())
        assert len(per_source) == 3

    def test_real_load_region_assignments_table_shape(self):
        manifest = json.loads(REAL_CAMPAIGN_MANIFEST.read_text())
        rows = build_load_region_assignments_table(manifest)
        assert len(rows) == 720
        assert all(math.isfinite(r["lambda_ref"]) for r in rows)

    def test_no_scheduler_outcome_field_present_in_real_manifests(self):
        """Sanity check that these frozen manifests are genuinely
        result-free: no cell in the campaign-freeze manifest carries any
        outcome-shaped field."""
        manifest = json.loads(REAL_CAMPAIGN_MANIFEST.read_text())
        outcome_fields = {
            "arrival_normalized_weighted_goodput", "completion_fraction",
            "slo_violation_rate", "mean_latency", "success",
        }
        for cell in manifest["cells"][:50]:
            assert not (outcome_fields & set(cell.keys()))
