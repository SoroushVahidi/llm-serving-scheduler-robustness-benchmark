"""Schema-version and backward-compatibility tests for the ranking-
portability pilot's cell schema (docs/RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md,
section 6 of the telemetry task). Confirms: (1) historical Stage-0 cells
(no telemetry field at all) remain valid under Stage-0's OWN, completely
untouched validator; (2) the new ranking_portability schema requires
telemetry and rejects a cell missing it; (3) a valid telemetry block
round-trips through the new validator.
"""
from __future__ import annotations

from robustbench.ranking_portability.schema import (
    CELL_SCHEMA_VERSION,
    RankingPortabilityCellResult,
    validate_cell_result,
)
from robustbench.simulator.telemetry import TELEMETRY_SCHEMA_VERSION, TelemetrySummary
from robustbench.stage0.schema import (
    CELL_RESULT_SCHEMA_VERSION as STAGE0_SCHEMA_VERSION,
)
from robustbench.stage0.schema import validate_cell_result as stage0_validate_cell_result


def _telemetry_dict(**overrides) -> dict:
    t = TelemetrySummary(
        schema_version=TELEMETRY_SCHEMA_VERSION,
        queue_depth_mean=1.0, queue_depth_max=2, batch_saturation_mean=0.5,
        batch_saturation_max=1.0, prefill_decode_contention_fraction=0.0,
        kv_occupancy_mean=0.3, kv_occupancy_max=0.6,
        admission_control_activations=0, preemption_or_reorder_events=0,
        token_budget_saturation_fraction=0.0, n_steps=10,
    )
    d = t.to_dict()
    d.update(overrides)
    return d


def _base_kwargs(**overrides) -> dict:
    d = dict(
        cell_id="s::w::KNEE::fifo::rep0", source_family="s", window_id="w",
        load_region="KNEE", load_factor=10.0, policy_id="fifo", repetition=0,
        synthesis_seed=1, arrival_normalized_weighted_goodput=0.9,
        completion_fraction=0.95, weighted_completion_fraction=0.95,
        slo_violation_rate=0.05, weighted_goodput=0.9, mean_latency=1.0,
        p95_latency=2.0, mean_ttft=0.1, p95_ttft=0.2, request_throughput=10.0,
        token_throughput=100.0, success=True, repo_sha="deadbeef",
        telemetry_schema_version=TELEMETRY_SCHEMA_VERSION,
        telemetry=_telemetry_dict(),
    )
    d.update(overrides)
    return d


# --- Backward compatibility: Stage-0's OWN validator, untouched ----------

def test_stage0_schema_version_unchanged():
    assert STAGE0_SCHEMA_VERSION == "stage0_cell_result_v1"


def test_historical_stage0_cell_without_telemetry_still_valid_under_stage0_validator():
    """A cell shaped exactly like real Stage-0 evidence (no telemetry field
    at all) must still validate under robustbench.stage0.schema -- this
    repo's Stage-0 cell format is completely untouched by this change."""
    historical_cell = dict(
        cell_id="azure_llm_2024::azure_llm_2024_stage0_w00::KNEE::fifo::rep0",
        canonical_hash="abc123", source_family="azure_llm_2024",
        window_id="azure_llm_2024_stage0_w00", load_region="KNEE", load_factor=10.0,
        policy_id="fifo", repetition=0, synthesis_seed=1,
        arrival_normalized_weighted_goodput=0.9, completion_fraction=0.95,
        slo_violation_rate=0.05, success=True, repo_sha="deadbeef",
        window_manifest_sha256="a" * 64, calibration_manifest_sha256="b" * 64,
        policy_registry_hash="c" * 64,
    )
    assert "telemetry" not in historical_cell
    assert stage0_validate_cell_result(historical_cell) == []


# --- New ranking-portability schema: telemetry is REQUIRED ---------------

def test_new_schema_version_is_distinct_from_stage0():
    assert CELL_SCHEMA_VERSION == "ranking_portability_cell_result_v1"
    assert CELL_SCHEMA_VERSION != STAGE0_SCHEMA_VERSION


def test_valid_pilot_v2_cell_has_no_problems():
    assert validate_cell_result(_base_kwargs()) == []


def test_pilot_v2_cell_missing_telemetry_block_is_invalid():
    d = _base_kwargs(telemetry={})
    problems = validate_cell_result(d)
    assert any("telemetry" in p for p in problems)


def test_pilot_v2_cell_missing_telemetry_field_entirely_is_invalid():
    d = _base_kwargs()
    del d["telemetry"]
    problems = validate_cell_result(d)
    assert any("telemetry" in p for p in problems)


def test_pilot_v2_cell_with_malformed_telemetry_is_invalid():
    d = _base_kwargs(telemetry={"not_a_real_telemetry_field": 1})
    problems = validate_cell_result(d)
    assert any("telemetry" in p for p in problems)


def test_pilot_v2_cell_with_invalid_inner_telemetry_value_is_invalid():
    d = _base_kwargs(telemetry=_telemetry_dict(batch_saturation_mean=5.0))
    problems = validate_cell_result(d)
    assert any("telemetry.batch_saturation_mean" in p for p in problems)


def test_pilot_v2_always_defined_metric_nan_is_invalid():
    d = _base_kwargs(completion_fraction=float("nan"))
    problems = validate_cell_result(d)
    assert any("completion_fraction" in p for p in problems)


def test_pilot_v2_conditional_metric_nan_valid_iff_completion_fraction_zero():
    # Invalid: nonzero completion_fraction, NaN slo_violation_rate.
    d = _base_kwargs(completion_fraction=0.3, slo_violation_rate=float("nan"))
    assert any("slo_violation_rate" in p for p in validate_cell_result(d))

    # Valid: zero-completion cell, NaN slo_violation_rate/latency/throughput.
    d2 = _base_kwargs(
        arrival_normalized_weighted_goodput=0.0, completion_fraction=0.0,
        weighted_completion_fraction=0.0, slo_violation_rate=float("nan"),
        weighted_goodput=float("nan"), mean_latency=float("nan"),
        p95_latency=float("nan"), request_throughput=float("nan"),
        token_throughput=float("nan"), mean_ttft=None, p95_ttft=None,
    )
    assert validate_cell_result(d2) == []


def test_cell_result_to_dict_roundtrips_through_validator():
    telemetry = TelemetrySummary(
        schema_version=TELEMETRY_SCHEMA_VERSION,
        queue_depth_mean=0.0, queue_depth_max=0, batch_saturation_mean=0.0,
        batch_saturation_max=0.0, prefill_decode_contention_fraction=0.0,
        kv_occupancy_mean=0.0, kv_occupancy_max=0.0,
        admission_control_activations=0, preemption_or_reorder_events=0,
        token_budget_saturation_fraction=0.0, n_steps=1,
    )

    class _FakeMetrics:
        arrival_normalized_weighted_goodput = 1.0
        completion_fraction = 1.0
        weighted_completion_fraction = 1.0
        slo_violation_rate = 0.0
        weighted_goodput = 1.0
        mean_latency = 1.0
        p95_latency = 1.0
        mean_ttft = 0.1
        p95_ttft = 0.1
        request_throughput = 1.0
        token_throughput = 1.0

    cr = RankingPortabilityCellResult.from_run(
        cell_id="x", source_family="s", window_id="w", load_region="KNEE",
        load_factor=1.0, policy_id="fifo", repetition=0, synthesis_seed=1,
        repo_sha="x", telemetry=telemetry, m=_FakeMetrics(),
    )
    assert validate_cell_result(cr.to_dict()) == []
