"""End-to-end resumability/idempotence test for scripts/stage0/stage0_harness.py
(section B6), run via subprocess against tiny synthetic manifests -- no real
Stage-0 data, small enough to run in a normal test suite."""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

from robustbench.workloads.external.adapters import burstgpt

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "configs" / "external_workloads" / "fixtures"
HARNESS = REPO_ROOT / "scripts" / "stage0" / "stage0_harness.py"


def _build_tiny_manifests(tmp_path: Path):
    adapter = burstgpt.BurstGPTAdapter()
    base = [asdict(r) for r in adapter.stream_records(FIXTURES / "burstgpt_sample.csv")]
    records = []
    for i, r in enumerate(base * 10):
        r = dict(r)
        r["arrival_time_s"] = (r["arrival_time_s"] or 0.0) + i * 0.01
        records.append(r)

    windows = [
        {"window_id": "burstgpt_tiny_w0", "source_family": "burstgpt", "records": records},
    ]
    calibrations = [
        {"window_id": "burstgpt_tiny_w0", "lambda_ref": 1.0,
         "load_regions": {"PRE_KNEE": 0.5, "KNEE": 1.0, "OVERLOAD": 5000.0}},
    ]
    windows_path = tmp_path / "windows.json"
    cal_path = tmp_path / "calibration.json"
    with open(windows_path, "w") as f:
        json.dump({"windows": windows}, f)
    with open(cal_path, "w") as f:
        json.dump({"calibrations": calibrations}, f)
    return windows_path, cal_path


def _run(args):
    result = subprocess.run(
        [sys.executable, str(HARNESS)] + args,
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    return result


def test_plan_run_status_validate_roundtrip(tmp_path):
    windows_path, cal_path = _build_tiny_manifests(tmp_path)
    out_dir = tmp_path / "out"

    plan = _run(["plan", "--output-dir", str(out_dir),
                 "--windows-manifest", str(windows_path), "--calibration-manifest", str(cal_path)])
    assert plan.returncode == 0, plan.stderr
    plan_summary = json.loads(plan.stdout.strip().splitlines()[-1])
    assert plan_summary["n_cells"] == 1 * 3 * 6 * 2  # 1 window x 3 regions x 6 policies x 2 reps = 36

    run1 = _run(["run", "--output-dir", str(out_dir),
                 "--windows-manifest", str(windows_path), "--calibration-manifest", str(cal_path)])
    assert run1.returncode == 0, run1.stderr
    run1_summary = json.loads(run1.stdout.strip().splitlines()[-1])
    assert run1_summary["ran"] == 36
    assert run1_summary["skipped"] == 0

    # Second run: everything already completed -> should skip all, not recompute.
    run2 = _run(["run", "--output-dir", str(out_dir),
                 "--windows-manifest", str(windows_path), "--calibration-manifest", str(cal_path)])
    run2_summary = json.loads(run2.stdout.strip().splitlines()[-1])
    assert run2_summary["ran"] == 0
    assert run2_summary["skipped"] == 36

    status = _run(["status", "--output-dir", str(out_dir)])
    status_summary = json.loads(status.stdout)
    assert status_summary["n_expected"] == 36
    assert status_summary["n_missing_or_pending"] == 0

    validate = _run(["validate", "--output-dir", str(out_dir)])
    validate_summary = json.loads(validate.stdout)
    assert validate_summary["matrix_complete_and_clean"] is True
    assert validate.returncode == 0


def test_corrupt_partial_file_is_recomputed_not_mistaken_for_valid(tmp_path):
    windows_path, cal_path = _build_tiny_manifests(tmp_path)
    out_dir = tmp_path / "out"
    _run(["plan", "--output-dir", str(out_dir),
          "--windows-manifest", str(windows_path), "--calibration-manifest", str(cal_path)])
    _run(["run", "--output-dir", str(out_dir),
          "--windows-manifest", str(windows_path), "--calibration-manifest", str(cal_path)])

    # Corrupt one result file (simulates a crash mid-write, or a partial file).
    cells_dir = out_dir / "cells"
    a_result = next(cells_dir.glob("*.json"))
    a_result.write_text("{not valid json")

    run_again = _run(["run", "--output-dir", str(out_dir),
                       "--windows-manifest", str(windows_path), "--calibration-manifest", str(cal_path)])
    summary = json.loads(run_again.stdout.strip().splitlines()[-1])
    assert summary["ran"] >= 1  # the corrupted cell was recomputed, not silently skipped
    # File is valid JSON again afterward.
    json.loads(a_result.read_text())


def test_validate_fails_on_missing_cell(tmp_path):
    windows_path, cal_path = _build_tiny_manifests(tmp_path)
    out_dir = tmp_path / "out"
    _run(["plan", "--output-dir", str(out_dir),
          "--windows-manifest", str(windows_path), "--calibration-manifest", str(cal_path)])
    _run(["run", "--output-dir", str(out_dir),
          "--windows-manifest", str(windows_path), "--calibration-manifest", str(cal_path)])

    cells_dir = out_dir / "cells"
    a_result = next(cells_dir.glob("*.json"))
    a_result.unlink()

    validate = _run(["validate", "--output-dir", str(out_dir)])
    assert validate.returncode == 1
    summary = json.loads(validate.stdout)
    assert summary["matrix_complete_and_clean"] is False
    assert any("MISSING" in p for p in summary["problems"])
