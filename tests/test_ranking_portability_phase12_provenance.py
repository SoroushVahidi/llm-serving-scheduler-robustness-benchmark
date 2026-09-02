"""Result-blind tests for Phase-12D provenance enrichment.

All rows/manifests are fabricated.  This file never opens the real Phase-12
campaign output namespace.
"""
from __future__ import annotations

import copy

import pytest

from robustbench.ranking_portability.phase12_provenance import (
    APPROVED_ENRICHMENT_FIELDS,
    canonical_json_sha256,
    enrich_row_provenance,
    expected_phase12_provenance,
    masked_non_provenance_view,
    phase12_simulator_config_hash,
    phase12_simulator_config_payload,
    validate_analysis_admission_row,
)
from robustbench.ranking_portability.schema import validate_cell_result

EXPECTED_PHASE12_SIMULATOR_CONFIG_HASH = (
    "a7a8920a43d4c1ba90da249f64d60e9929355e66f150aa1afd60f3599f98717b"
)


def _campaign() -> dict:
    return {
        "phase10_window_hash": "a" * 64,
        "phase11_raw_fifo_hash": "b" * 64,
        "phase11_region_assignment_hash": "c" * 64,
        "execution_file_hashes": {
            "src/robustbench/policies/registry.py": "d" * 64,
        },
    }


def _telemetry() -> dict:
    return {
        "schema_version": "ranking_portability_telemetry_v1",
        "queue_depth_mean": 1.0,
        "queue_depth_max": 2,
        "batch_saturation_mean": 0.2,
        "batch_saturation_max": 0.4,
        "prefill_decode_contention_fraction": 0.0,
        "kv_occupancy_mean": 1.01,
        "kv_occupancy_max": 1.02,
        "admission_control_activations": 0,
        "preemption_or_reorder_events": 0,
        "token_budget_saturation_fraction": 0.0,
        "n_steps": 10,
    }


def _raw_row() -> dict:
    return {
        "schema_version": "ranking_portability_cell_result_v1",
        "cell_id": "fake::fake_w00::KNEE::fifo::rep0",
        "source_family": "fake",
        "window_id": "fake_w00",
        "load_region": "KNEE",
        "load_factor": 1.0,
        "policy_id": "fifo",
        "repetition": 0,
        "synthesis_seed": 900000,
        "arrival_normalized_weighted_goodput": 1.0,
        "completion_fraction": 1.0,
        "weighted_completion_fraction": 1.0,
        "slo_violation_rate": 0.0,
        "weighted_goodput": 1.0,
        "mean_latency": 1.0,
        "p95_latency": 1.1,
        "mean_ttft": float("nan"),
        "p95_ttft": float("nan"),
        "request_throughput": 1.0,
        "token_throughput": 2.0,
        "telemetry_schema_version": "ranking_portability_telemetry_v1",
        "telemetry": _telemetry(),
        "repo_sha": "e" * 40,
        "window_manifest_sha256": "",
        "calibration_manifest_sha256": "",
        "policy_registry_hash": "",
        "simulator_config_hash": "",
        "synthesis_version": "",
        "environment": {},
        "success": True,
        "error_category": None,
        "error_detail": None,
        "scientific_status": "PILOT_V2_SCIENTIFIC",
    }


def test_calibration_manifest_semantics_are_region_assignment_not_raw_fifo():
    expected = expected_phase12_provenance(_campaign())
    assert expected["calibration_manifest_sha256"] == "c" * 64
    assert expected["phase11_region_assignments_sha256"] == "c" * 64
    assert expected["phase11_raw_fifo_calibration_sha256"] == "b" * 64
    assert expected["calibration_manifest_sha256"] != expected["phase11_raw_fifo_calibration_sha256"]


def test_window_policy_and_synthesis_provenance_come_from_frozen_contract():
    expected = expected_phase12_provenance(_campaign())
    assert expected["window_manifest_sha256"] == "a" * 64
    assert expected["policy_registry_hash"] == "d" * 64
    assert expected["synthesis_version"] == "stage0_synthesis_v1"


def test_simulator_config_hash_is_deterministic_value_hash_not_source_hash():
    payload1 = phase12_simulator_config_payload()
    payload2 = phase12_simulator_config_payload()
    assert payload1 == payload2
    assert phase12_simulator_config_hash() == canonical_json_sha256(payload1)
    assert phase12_simulator_config_hash() == EXPECTED_PHASE12_SIMULATOR_CONFIG_HASH
    assert payload1["simulator_config"]["drain_steps"] == 50_000
    assert payload1["simulator_config"]["max_steps"] is None
    assert payload1["simulator_config"]["warn_on_invalid_action"] is True
    assert payload1["gpu_configs"][0]["max_active_sequences"] == 64
    assert payload1["gpu_configs"][0]["max_batch_tokens"] == 4096
    assert payload1["gpu_configs"][0]["max_kv_tokens"] == 131072


def test_raw_historical_row_remains_execution_schema_valid_but_not_analysis_admitted():
    raw = _raw_row()
    assert validate_cell_result(raw) == []
    problems = validate_analysis_admission_row(raw, _campaign())
    assert any("provenance field empty" in p for p in problems)


def test_enrichment_is_deterministic_idempotent_and_analysis_admitted():
    raw = _raw_row()
    expected = expected_phase12_provenance(_campaign())
    once = enrich_row_provenance(raw, expected)
    twice = enrich_row_provenance(once, expected)
    assert once == twice
    assert masked_non_provenance_view(raw) == masked_non_provenance_view(once)
    assert validate_analysis_admission_row(once, _campaign(), expected_execution_repo_sha="e" * 40) == []
    for field in APPROVED_ENRICHMENT_FIELDS:
        assert once[field] == expected[field]


def test_conflicting_nonempty_provenance_is_rejected_not_rewritten():
    raw = _raw_row()
    raw["window_manifest_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="conflicting provenance"):
        enrich_row_provenance(raw, expected_phase12_provenance(_campaign()))


def test_only_approved_provenance_fields_can_differ_after_enrichment():
    raw = _raw_row()
    enriched = enrich_row_provenance(raw, expected_phase12_provenance(_campaign()))
    changed = {k for k in set(raw) | set(enriched) if raw.get(k) != enriched.get(k)}
    # Explicit Phase-11 fields are newly added; the original five are filled.
    assert changed == set(APPROVED_ENRICHMENT_FIELDS)


def test_metric_or_telemetry_change_is_detected_by_masked_invariance_view():
    raw = _raw_row()
    enriched = enrich_row_provenance(raw, expected_phase12_provenance(_campaign()))
    bad = copy.deepcopy(enriched)
    bad["arrival_normalized_weighted_goodput"] = 999.0
    assert masked_non_provenance_view(raw) != masked_non_provenance_view(bad)
    bad2 = copy.deepcopy(enriched)
    bad2["telemetry"]["queue_depth_mean"] = 999.0
    assert masked_non_provenance_view(raw) != masked_non_provenance_view(bad2)
