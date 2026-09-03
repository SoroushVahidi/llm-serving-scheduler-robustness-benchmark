from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, rel_path: str):
    path = REPO_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator_mod = _load_module("validate_rq6_validation_outputs", "scripts/real_vllm/validate_rq6_validation_outputs.py")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


SOURCES = ("azure_llm_2024", "bailian_qwen", "burstgpt")
POLICIES = ("slai_faithful", "vllm_faithful")


def _write_fixture_manifest(tmp_path: Path, manifest_dir: Path, n_windows: int) -> Path:
    for source in SOURCES:
        windows = [
            {
                "window_id": f"{source}_w{i:02d}", "content_sha256": f"hash-{source}-{i}",
                "requests": [],
            }
            for i in range(n_windows)
        ]
        (manifest_dir / f"rq6_workload_{source}_20260903.json").write_text(
            json.dumps({"source": source, "windows": windows})
        )

    validation_manifest = {
        "frozen_code_sha": "deadbeef",
        "case_selection": {"manifest_sha256": "caseselhash"},
        "calibration_dependency": {"calibration_manifest_sha256": "calhash"},
        "scheduler_mapping": {
            "slai_faithful": {"scheduling_policy": "priority", "scheduler_cls": "pkg.SLAIScheduler"},
            "vllm_faithful": {"scheduling_policy": "fcfs", "scheduler_cls": None},
        },
    }
    path = tmp_path / "rq6_validation_manifest_v1_fixture.json"
    path.write_text(json.dumps(validation_manifest))
    return path


def _completed_record(*, policy, source, window_id, validation_manifest_sha256):
    return {
        "stamp": "RQ6_REAL_VLLM_SCIENTIFIC_VALIDATION", "run_status": "COMPLETED",
        "policy": policy, "source": source, "window_id": window_id, "region": "HIGH_PRESSURE",
        "candidate_scale": 1.5, "real_lambda_ref": 1.0, "calibration_convergence_status": "CONVERGED",
        "scheduler_cls": "pkg.SLAIScheduler" if policy == "slai_faithful" else None,
        "scheduling_policy": "priority" if policy == "slai_faithful" else "fcfs",
        "replicate_seed": 0, "model": "m", "gpu": "A100", "selected_port": 12345,
        "port_selection_method": "os_ephemeral_bind0",
        "started_at_utc": "t0", "finished_at_utc": "t1",
        "offered_request_count": 200, "completed_request_count": 200,
        "arrival_normalized_weighted_goodput": 0.9, "slo_violation_rate": 0.01,
        "workload_manifest_path": "p", "workload_manifest_content_sha256": f"hash-{source}-0",
        "calibration_manifest_sha256": "calhash", "validation_manifest_path": "p",
        "validation_manifest_sha256": validation_manifest_sha256,
        "case_selection_manifest_sha256": "caseselhash", "environment_spec_sha256": "envhash",
        "repo_sha": "deadbeef",
    }


def _all_cells_completed(out_dir: Path, validation_manifest_path: Path, n_windows: int):
    vm_hash = _sha256_file(validation_manifest_path)
    for source in SOURCES:
        for policy in POLICIES:
            for i in range(n_windows):
                window_id = f"{source}_w{i:02d}"
                d = out_dir / policy / source
                d.mkdir(parents=True, exist_ok=True)
                (d / f"{window_id}.json").write_text(json.dumps(
                    _completed_record(policy=policy, source=source, window_id=window_id,
                                       validation_manifest_sha256=vm_hash)
                ))


def test_validate_all_present_passes(tmp_path):
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    vm_path = _write_fixture_manifest(tmp_path, manifest_dir, n_windows=2)
    out_dir = tmp_path / "out"
    _all_cells_completed(out_dir, vm_path, n_windows=2)

    report = validator_mod.validate(out_dir, manifest_dir=manifest_dir, validation_manifest_path=vm_path)
    assert report["passed"] is True
    assert report["n_expected_cells"] == len(SOURCES) * len(POLICIES) * 2
    assert report["n_missing_cells"] == 0
    assert report["n_duplicates"] == 0
    assert report["n_problems"] == 0


def test_validate_detects_missing_cell(tmp_path):
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    vm_path = _write_fixture_manifest(tmp_path, manifest_dir, n_windows=2)
    out_dir = tmp_path / "out"
    _all_cells_completed(out_dir, vm_path, n_windows=2)
    (out_dir / "slai_faithful" / "azure_llm_2024" / "azure_llm_2024_w00.json").unlink()

    report = validator_mod.validate(out_dir, manifest_dir=manifest_dir, validation_manifest_path=vm_path)
    assert report["passed"] is False
    assert report["n_missing_cells"] == 1
    assert ["slai_faithful", "azure_llm_2024", "azure_llm_2024_w00"] in report["missing_cells"]


def test_validate_detects_duplicate(tmp_path):
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    vm_path = _write_fixture_manifest(tmp_path, manifest_dir, n_windows=1)
    out_dir = tmp_path / "out"
    _all_cells_completed(out_dir, vm_path, n_windows=1)
    # A duplicate: same (policy, source, window_id) content, second file
    src = out_dir / "slai_faithful" / "azure_llm_2024" / "azure_llm_2024_w00.json"
    dup = out_dir / "slai_faithful" / "azure_llm_2024" / "azure_llm_2024_w00_retry.json"
    dup.write_text(src.read_text())

    report = validator_mod.validate(out_dir, manifest_dir=manifest_dir, validation_manifest_path=vm_path)
    assert report["passed"] is False
    assert report["n_duplicates"] == 1


def test_validate_excludes_non_scientific_stamped_files(tmp_path):
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    vm_path = _write_fixture_manifest(tmp_path, manifest_dir, n_windows=1)
    out_dir = tmp_path / "out"
    _all_cells_completed(out_dir, vm_path, n_windows=1)
    eng_dir = out_dir / "engineering_smoke"
    eng_dir.mkdir()
    (eng_dir / "smoke.json").write_text(json.dumps({"stamp": "ENGINEERING_ONLY_NOT_SCIENTIFIC_EVIDENCE"}))

    report = validator_mod.validate(out_dir, manifest_dir=manifest_dir, validation_manifest_path=vm_path)
    assert report["n_non_scientific_files_excluded"] == 1
    # Engineering file must not count toward expected cells or break "passed"
    assert report["passed"] is True


def test_validate_detects_schema_missing_keys(tmp_path):
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    vm_path = _write_fixture_manifest(tmp_path, manifest_dir, n_windows=1)
    out_dir = tmp_path / "out"
    _all_cells_completed(out_dir, vm_path, n_windows=1)
    path = out_dir / "slai_faithful" / "azure_llm_2024" / "azure_llm_2024_w00.json"
    record = json.loads(path.read_text())
    del record["arrival_normalized_weighted_goodput"]
    path.write_text(json.dumps(record))

    report = validator_mod.validate(out_dir, manifest_dir=manifest_dir, validation_manifest_path=vm_path)
    assert report["passed"] is False
    assert any("missing keys" in p for p in report["problems"])


def test_validate_detects_scheduler_mapping_mismatch(tmp_path):
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    vm_path = _write_fixture_manifest(tmp_path, manifest_dir, n_windows=1)
    out_dir = tmp_path / "out"
    _all_cells_completed(out_dir, vm_path, n_windows=1)
    path = out_dir / "slai_faithful" / "azure_llm_2024" / "azure_llm_2024_w00.json"
    record = json.loads(path.read_text())
    record["scheduler_cls"] = None  # slai_faithful must have a non-null scheduler_cls
    path.write_text(json.dumps(record))

    report = validator_mod.validate(out_dir, manifest_dir=manifest_dir, validation_manifest_path=vm_path)
    assert report["passed"] is False
    assert any("scheduler_cls" in p for p in report["problems"])


def test_validate_detects_hash_mismatch(tmp_path):
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    vm_path = _write_fixture_manifest(tmp_path, manifest_dir, n_windows=1)
    out_dir = tmp_path / "out"
    _all_cells_completed(out_dir, vm_path, n_windows=1)
    path = out_dir / "slai_faithful" / "azure_llm_2024" / "azure_llm_2024_w00.json"
    record = json.loads(path.read_text())
    record["calibration_manifest_sha256"] = "WRONG"
    path.write_text(json.dumps(record))

    report = validator_mod.validate(out_dir, manifest_dir=manifest_dir, validation_manifest_path=vm_path)
    assert report["passed"] is False
    assert any("calibration_manifest_sha256 mismatch" in p for p in report["problems"])


def test_validate_never_inspects_anwg_value_for_pass_fail(tmp_path):
    """The validator must not treat any particular ANWG value/sign as a
    pass/fail criterion -- it only checks presence/type. A negative,
    positive, or extreme-but-numeric value must not affect `passed`."""
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    vm_path = _write_fixture_manifest(tmp_path, manifest_dir, n_windows=1)
    out_dir = tmp_path / "out"
    _all_cells_completed(out_dir, vm_path, n_windows=1)
    path = out_dir / "slai_faithful" / "azure_llm_2024" / "azure_llm_2024_w00.json"
    record = json.loads(path.read_text())
    record["arrival_normalized_weighted_goodput"] = -999.0
    path.write_text(json.dumps(record))

    report = validator_mod.validate(out_dir, manifest_dir=manifest_dir, validation_manifest_path=vm_path)
    assert report["passed"] is True


def test_validate_accepts_failed_status_records_without_full_schema(tmp_path):
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    vm_path = _write_fixture_manifest(tmp_path, manifest_dir, n_windows=1)
    out_dir = tmp_path / "out"
    _all_cells_completed(out_dir, vm_path, n_windows=1)
    path = out_dir / "slai_faithful" / "azure_llm_2024" / "azure_llm_2024_w00.json"
    path.write_text(json.dumps({
        "stamp": "RQ6_REAL_VLLM_SCIENTIFIC_VALIDATION", "run_status": "FAILED_SERVER_START",
        "policy": "slai_faithful", "source": "azure_llm_2024", "window_id": "azure_llm_2024_w00",
    }))

    report = validator_mod.validate(out_dir, manifest_dir=manifest_dir, validation_manifest_path=vm_path)
    assert report["status_counts"].get("FAILED_SERVER_START") == 1
    # A failed cell is present (not missing) but the run is not "passed" in
    # the sense of full 240/240 COMPLETED -- passed only tracks structural
    # validity (identity/schema/dupes), so this specific fixture still
    # structurally passes; a caller who wants "all COMPLETED" must check
    # status_counts separately.
    assert report["n_missing_cells"] == 0
