from __future__ import annotations

import math

from robustbench.core.metrics import compute_metrics
from robustbench.stage0.schema import CellResult, validate_cell_result


def _base_kwargs(**overrides):
    d = dict(
        cell_id="s::w::KNEE::fifo::rep0", canonical_hash="abc123",
        source_family="s", window_id="w", load_region="KNEE", load_factor=10.0,
        policy_id="fifo", repetition=0, synthesis_seed=1,
        arrival_normalized_weighted_goodput=0.9, completion_fraction=0.95,
        slo_violation_rate=0.05, success=True,
        repo_sha="deadbeef", window_manifest_sha256="a" * 64,
        calibration_manifest_sha256="b" * 64, policy_registry_hash="c" * 64,
    )
    d.update(overrides)
    return d


def test_valid_success_cell_has_no_problems():
    assert validate_cell_result(_base_kwargs()) == []


def test_missing_required_field_detected():
    d = _base_kwargs()
    del d["repo_sha"]
    problems = validate_cell_result(d)
    assert any("repo_sha" in p for p in problems)


def test_success_true_with_none_metric_is_invalid():
    d = _base_kwargs(arrival_normalized_weighted_goodput=None)
    problems = validate_cell_result(d)
    assert any("arrival_normalized_weighted_goodput" in p for p in problems)


def test_success_true_with_nan_metric_is_invalid():
    d = _base_kwargs(completion_fraction=float("nan"))
    problems = validate_cell_result(d)
    assert any("completion_fraction" in p for p in problems)


def test_success_false_requires_error_category():
    d = _base_kwargs(success=False, error_category=None,
                      arrival_normalized_weighted_goodput=None,
                      completion_fraction=None, slo_violation_rate=None)
    problems = validate_cell_result(d)
    assert any("error_category" in p for p in problems)


def test_success_false_with_error_category_is_valid():
    d = _base_kwargs(success=False, error_category="SomeError", error_detail="boom",
                      arrival_normalized_weighted_goodput=None,
                      completion_fraction=None, slo_violation_rate=None)
    assert validate_cell_result(d) == []


def test_invalid_repetition_detected():
    d = _base_kwargs(repetition=2)
    problems = validate_cell_result(d)
    assert any("repetition" in p for p in problems)


def test_cell_result_to_dict_roundtrips_through_validator():
    cr = CellResult(cell_id="x", canonical_hash="y", source_family="s", window_id="w",
                     load_region="KNEE", load_factor=1.0, policy_id="fifo", repetition=0,
                     synthesis_seed=1, arrival_normalized_weighted_goodput=1.0,
                     completion_fraction=1.0, slo_violation_rate=0.0, success=True,
                     repo_sha="x", window_manifest_sha256="x", calibration_manifest_sha256="x",
                     policy_registry_hash="x")
    assert validate_cell_result(cr.to_dict()) == []


# --- docs/STAGE0_ZERO_COMPLETION_METRIC_AMENDMENT_20260901.md regression tests ---
#
# slo_violation_rate is CONDITIONAL_ON_COMPLETION: NaN is the documented,
# valid representation of "undefined" exactly when completion_fraction ==
# 0.0, and must still be finite whenever completion_fraction != 0.0. No
# numerical value (0.0 or 1.0) is ever imputed for the undefined case.

def test_zero_completion_nan_slo_violation_rate_is_schema_valid():
    """(1) The real Stage-0 zero-completion case: ANWG=0.0,
    completion_fraction=0.0, slo_violation_rate=NaN -- schema-valid."""
    d = _base_kwargs(
        arrival_normalized_weighted_goodput=0.0,
        completion_fraction=0.0,
        slo_violation_rate=float("nan"),
    )
    assert validate_cell_result(d) == []


def test_nonzero_completion_nan_slo_violation_rate_is_still_invalid():
    """(2) NaN slo_violation_rate remains a real schema violation whenever
    its population (completed requests) is non-empty."""
    d = _base_kwargs(completion_fraction=0.3, slo_violation_rate=float("nan"))
    problems = validate_cell_result(d)
    assert any("slo_violation_rate" in p for p in problems)


def test_ordinary_historical_cell_unchanged():
    """(4) A normal, fully-defined cell validates exactly as before."""
    assert validate_cell_result(_base_kwargs()) == []


def test_no_blanket_nan_acceptance_at_zero_completion():
    """(5) The zero-completion NaN exception applies ONLY to
    slo_violation_rate -- ANWG and completion_fraction remain
    ALWAYS_DEFINED and must still be finite even when
    completion_fraction == 0.0."""
    d = _base_kwargs(
        arrival_normalized_weighted_goodput=float("nan"),
        completion_fraction=0.0,
        slo_violation_rate=float("nan"),
    )
    problems = validate_cell_result(d)
    assert any("arrival_normalized_weighted_goodput" in p for p in problems)


def test_anwg_zero_completion_value_unchanged_by_repair():
    """(6) This repair touches schema.py only -- compute_metrics()'s ANWG
    zero-completion behavior (0.0, pre-registered in
    docs/STAGE0_METRIC_DEFINITIONS.md) is untouched."""
    from robustbench.core.types import Request

    reqs = [Request(request_id=i, arrival_time=0.0, prompt_tokens=10,
                     predicted_output_tokens=10, actual_output_tokens=10,
                     slo_deadline=100.0, priority=1.0, class_id="t")
            for i in range(3)]
    m = compute_metrics([], dropped=list(reqs), sim_duration=10.0,
                         gpu_utilization_history=[], active_batch_history=[],
                         num_total=3, all_requests=reqs)
    assert m.arrival_normalized_weighted_goodput == 0.0
    assert m.completion_fraction == 0.0
    assert math.isnan(m.slo_violation_rate)


def test_zero_completion_result_roundtrips_runner_style_through_validator():
    """(7) The exact field set runner.py::execute_cell copies from
    RunMetrics into CellResult, for a zero-completion run, round-trips
    through to_dict() -> validate_cell_result() as schema-valid -- i.e. the
    12 real affected cells are correctly accepted once regenerated."""
    from robustbench.core.types import Request

    reqs = [Request(request_id=i, arrival_time=0.0, prompt_tokens=10,
                     predicted_output_tokens=10, actual_output_tokens=10,
                     slo_deadline=100.0, priority=1.0, class_id="t")
            for i in range(5)]
    m = compute_metrics([], dropped=list(reqs), sim_duration=10.0,
                         gpu_utilization_history=[], active_batch_history=[],
                         num_total=5, all_requests=reqs)
    cr = CellResult(
        cell_id="azure_llm_2024::azure_llm_2024_stage0_w06::KNEE::vllm_faithful::rep1",
        canonical_hash="deadbeef", source_family="azure_llm_2024",
        window_id="azure_llm_2024_stage0_w06", load_region="KNEE", load_factor=96.3,
        policy_id="vllm_faithful", repetition=1, synthesis_seed=900016,
        arrival_normalized_weighted_goodput=m.arrival_normalized_weighted_goodput,
        completion_fraction=m.completion_fraction,
        slo_violation_rate=m.slo_violation_rate,
        weighted_goodput=m.weighted_goodput,
        mean_latency=m.mean_latency, p95_latency=m.p95_latency,
        mean_ttft=m.mean_ttft, p95_ttft=m.p95_ttft,
        request_throughput=m.request_throughput, token_throughput=m.token_throughput,
        success=True,
        repo_sha="x", window_manifest_sha256="x", calibration_manifest_sha256="x",
        policy_registry_hash="x",
    )
    assert validate_cell_result(cr.to_dict()) == []
