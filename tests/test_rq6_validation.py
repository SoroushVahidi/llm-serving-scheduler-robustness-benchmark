from __future__ import annotations

import json
from pathlib import Path

import pytest

from robustbench.real_llm.rq6_validation import (
    POLICIES,
    RQ6_REGION,
    RQ6_SOURCES,
    VALID_CALIBRATION_TERMINAL_STATUSES,
    CalibrationLookupError,
    enumerate_validation_cells,
    load_calibrated_scale,
    load_window_requests,
    real_arrival_normalized_weighted_goodput,
    summarize_replay,
)
from robustbench.real_llm.rq6_calibration import WindowRequestReplayResult
from robustbench.real_llm.rq6_slo_metrics import RequestOutcome

REPO_ROOT = Path(__file__).resolve().parents[1]
REAL_MANIFEST_DIR = REPO_ROOT / "artifacts/manifests/rq6_real_vllm"


def _write_fake_workload_manifest(tmp_path: Path, source: str, n_windows: int) -> Path:
    windows = [
        {
            "window_id": f"{source}_w{i:02d}",
            "content_sha256": f"hash-{source}-{i}",
            "requests": [
                {
                    "request_id": f"r{j}", "window_id": f"{source}_w{i:02d}", "request_index": j,
                    "base_relative_arrival_s": 0.0, "base_slo_deadline_s": 1.0,
                    "input_tokens": 10, "output_tokens_target": 8, "predicted_output_tokens": 8,
                    "priority": 1.0, "weight": 1.0, "class_id": "stage0_uniform",
                    "prompt_generation_seed": j, "source_record_id": f"src:{j}",
                }
                for j in range(2)
            ],
        }
        for i in range(n_windows)
    ]
    manifest = {"source": source, "windows": windows}
    path = tmp_path / f"rq6_workload_{source}_20260903.json"
    path.write_text(json.dumps(manifest))
    return path


# ---------------------------------------------------------------------------
# Task matrix enumeration: 240 cells, deterministic, complete, no duplicates
# ---------------------------------------------------------------------------

def test_enumerate_validation_cells_fake_manifests(tmp_path):
    for source in RQ6_SOURCES:
        _write_fake_workload_manifest(tmp_path, source, n_windows=3)
    cells = enumerate_validation_cells(tmp_path)
    assert len(cells) == 3 * len(RQ6_SOURCES) * len(POLICIES)
    keys = [(c.policy, c.source, c.window_id) for c in cells]
    assert len(keys) == len(set(keys))
    assert [c.array_index for c in cells] == list(range(len(cells)))
    sources_seen = {c.source for c in cells}
    assert sources_seen == set(RQ6_SOURCES)
    policies_seen = {c.policy for c in cells}
    assert policies_seen == set(POLICIES)


def test_enumerate_validation_cells_deterministic(tmp_path):
    for source in RQ6_SOURCES:
        _write_fake_workload_manifest(tmp_path, source, n_windows=2)
    a = enumerate_validation_cells(tmp_path)
    b = enumerate_validation_cells(tmp_path)
    assert a == b


@pytest.mark.skipif(not REAL_MANIFEST_DIR.exists(), reason="RQ6 workload manifests not yet built")
def test_enumerate_validation_cells_real_manifests_240_total():
    cells = enumerate_validation_cells(REAL_MANIFEST_DIR)
    assert len(cells) == 240
    keys = [(c.policy, c.source, c.window_id) for c in cells]
    assert len(keys) == len(set(keys))
    for source in RQ6_SOURCES:
        assert sum(1 for c in cells if c.source == source) == 40 * len(POLICIES)
    for policy in POLICIES:
        assert sum(1 for c in cells if c.policy == policy) == 3 * 40


def test_load_window_requests_roundtrip(tmp_path):
    path = _write_fake_workload_manifest(tmp_path, "azure_llm_2024", n_windows=2)
    requests, manifest, window_entry = load_window_requests(path, "azure_llm_2024_w01")
    assert len(requests) == 2
    assert window_entry["window_id"] == "azure_llm_2024_w01"
    assert manifest["source"] == "azure_llm_2024"


def test_load_window_requests_missing_window_raises(tmp_path):
    path = _write_fake_workload_manifest(tmp_path, "azure_llm_2024", n_windows=1)
    with pytest.raises(KeyError):
        load_window_requests(path, "nonexistent")


# ---------------------------------------------------------------------------
# Calibration terminal-status contract: all three are valid, none special-cased
# ---------------------------------------------------------------------------

def test_valid_calibration_terminal_statuses_is_exactly_the_three_bisection_outcomes():
    assert VALID_CALIBRATION_TERMINAL_STATUSES == {
        "CONVERGED", "LOWER_BOUND_ALREADY_VIOLATING", "UPPER_BOUND_NEVER_VIOLATING",
    }


def _write_calibration_output(cal_dir: Path, source: str, window_id: str, *, status: str, extra: dict | None = None):
    record = {
        "source": source, "window_id": window_id, "reference_policy": "vllm_faithful",
        "real_lambda_ref": 1.0, "derived_high_pressure": 1.5, "convergence_status": status,
        "window_content_sha256": "hash-a-0", "calibration_manifest_sha256": "calhash",
        "repo_sha": "deadbeef",
    }
    if extra:
        record.update(extra)
    d = cal_dir / source
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{window_id}.json").write_text(json.dumps(record))
    return record


@pytest.mark.parametrize("status", sorted(VALID_CALIBRATION_TERMINAL_STATUSES))
def test_load_calibrated_scale_accepts_every_valid_terminal_status(tmp_path, status):
    _write_calibration_output(tmp_path, "azure_llm_2024", "w00", status=status)
    record = load_calibrated_scale(
        tmp_path, "azure_llm_2024", "w00",
        expected_calibration_manifest_sha256="calhash", expected_window_content_sha256="hash-a-0",
    )
    assert record["convergence_status"] == status
    assert record["derived_high_pressure"] == 1.5


def test_load_calibrated_scale_rejects_unrecognized_status(tmp_path):
    _write_calibration_output(tmp_path, "azure_llm_2024", "w00", status="SOME_OTHER_STATUS")
    with pytest.raises(CalibrationLookupError, match="unrecognized convergence_status"):
        load_calibrated_scale(
            tmp_path, "azure_llm_2024", "w00",
            expected_calibration_manifest_sha256="calhash", expected_window_content_sha256="hash-a-0",
        )


def test_load_calibrated_scale_missing_file_raises(tmp_path):
    with pytest.raises(CalibrationLookupError, match="missing calibration output"):
        load_calibrated_scale(
            tmp_path, "azure_llm_2024", "w00",
            expected_calibration_manifest_sha256="calhash", expected_window_content_sha256="hash-a-0",
        )


def test_load_calibrated_scale_rejects_calibration_manifest_hash_mismatch(tmp_path):
    _write_calibration_output(tmp_path, "azure_llm_2024", "w00", status="CONVERGED")
    with pytest.raises(CalibrationLookupError, match="calibration_manifest_sha256 mismatch"):
        load_calibrated_scale(
            tmp_path, "azure_llm_2024", "w00",
            expected_calibration_manifest_sha256="WRONG", expected_window_content_sha256="hash-a-0",
        )


def test_load_calibrated_scale_rejects_window_content_hash_mismatch(tmp_path):
    _write_calibration_output(tmp_path, "azure_llm_2024", "w00", status="CONVERGED")
    with pytest.raises(CalibrationLookupError, match="window_content_sha256 mismatch"):
        load_calibrated_scale(
            tmp_path, "azure_llm_2024", "w00",
            expected_calibration_manifest_sha256="calhash", expected_window_content_sha256="WRONG",
        )


def test_load_calibrated_scale_rejects_missing_keys(tmp_path):
    d = tmp_path / "azure_llm_2024"
    d.mkdir(parents=True)
    (d / "w00.json").write_text(json.dumps({"source": "azure_llm_2024", "window_id": "w00"}))
    with pytest.raises(CalibrationLookupError, match="missing required keys"):
        load_calibrated_scale(
            tmp_path, "azure_llm_2024", "w00",
            expected_calibration_manifest_sha256="calhash", expected_window_content_sha256="hash-a-0",
        )


def test_load_calibrated_scale_rejects_non_vllm_faithful_reference_policy(tmp_path):
    _write_calibration_output(tmp_path, "azure_llm_2024", "w00", status="CONVERGED",
                               extra={"reference_policy": "slai_faithful"})
    with pytest.raises(CalibrationLookupError, match="reference_policy must be vllm_faithful"):
        load_calibrated_scale(
            tmp_path, "azure_llm_2024", "w00",
            expected_calibration_manifest_sha256="calhash", expected_window_content_sha256="hash-a-0",
        )


# ---------------------------------------------------------------------------
# ANWG (arrival-normalized-weighted-goodput): arrival-normalized, not
# completion-normalized -- distinct from slo_violation_rate's denominator.
# ---------------------------------------------------------------------------

def test_anwg_all_completed_all_met_is_one():
    outcomes = [RequestOutcome(weight=1.0, slo_deadline_s=10.0, t_done_s=1.0) for _ in range(5)]
    assert real_arrival_normalized_weighted_goodput(outcomes) == pytest.approx(1.0)


def test_anwg_arrival_normalized_not_completion_normalized():
    # 4 requests total; only 2 complete and meet SLO. ANWG divides by ALL 4
    # (arrival-normalized), unlike slo_violation_rate which would divide by
    # the 2 completed only.
    outcomes = [
        RequestOutcome(weight=1.0, slo_deadline_s=10.0, t_done_s=1.0),
        RequestOutcome(weight=1.0, slo_deadline_s=10.0, t_done_s=1.0),
        RequestOutcome(weight=1.0, slo_deadline_s=10.0, t_done_s=None),  # never completed
        RequestOutcome(weight=1.0, slo_deadline_s=10.0, t_done_s=None),
    ]
    assert real_arrival_normalized_weighted_goodput(outcomes) == pytest.approx(2.0 / 4.0)


def test_anwg_missed_deadline_excluded_from_numerator():
    outcomes = [
        RequestOutcome(weight=1.0, slo_deadline_s=1.0, t_done_s=5.0),  # completed but late
        RequestOutcome(weight=1.0, slo_deadline_s=1.0, t_done_s=0.5),  # completed and on time
    ]
    assert real_arrival_normalized_weighted_goodput(outcomes) == pytest.approx(0.5)


def test_anwg_weighted():
    outcomes = [
        RequestOutcome(weight=3.0, slo_deadline_s=10.0, t_done_s=1.0),
        RequestOutcome(weight=1.0, slo_deadline_s=10.0, t_done_s=None),
    ]
    assert real_arrival_normalized_weighted_goodput(outcomes) == pytest.approx(3.0 / 4.0)


def test_anwg_zero_arrival_weight_is_nan():
    outcomes = [RequestOutcome(weight=0.0, slo_deadline_s=10.0, t_done_s=1.0)]
    result = real_arrival_normalized_weighted_goodput(outcomes)
    assert result != result  # nan


def test_summarize_replay_uses_anwg_and_slo_violation_rate_consistently():
    replay = WindowRequestReplayResult(
        slo_violation_rate=0.25, n_completed=3, n_total=4,
        outcomes=[
            RequestOutcome(weight=1.0, slo_deadline_s=10.0, t_done_s=1.0),
            RequestOutcome(weight=1.0, slo_deadline_s=10.0, t_done_s=1.0),
            RequestOutcome(weight=1.0, slo_deadline_s=10.0, t_done_s=1.0),
            RequestOutcome(weight=1.0, slo_deadline_s=10.0, t_done_s=None),
        ],
    )
    result = summarize_replay("vllm_faithful", "azure_llm_2024", "w00", 1.5, replay)
    assert result.slo_violation_rate == pytest.approx(0.25)
    assert result.arrival_normalized_weighted_goodput == pytest.approx(3.0 / 4.0)
    assert result.n_completed == 3 and result.n_total == 4


def test_rq6_region_and_sources_frozen():
    assert RQ6_REGION == "HIGH_PRESSURE"
    assert set(RQ6_SOURCES) == {"azure_llm_2024", "bailian_qwen", "burstgpt"}
