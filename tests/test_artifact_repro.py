from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    env["LSSP_ARTIFACT_REPRO_PREFREEZE_RESULT_BLIND"] = "YES"
    return env


def test_immutable_artifact_verifier_is_result_blind_and_passes() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/artifact/verify_immutable_artifacts.py"],
        cwd=REPO_ROOT,
        env=_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "IMMUTABLE_ARTIFACTS_VALID = YES" in proc.stdout
    assert "SCIENTIFIC_CAMPAIGN_EXECUTED = NO" in proc.stdout


def test_toy_reproduction_exercises_edge_cases(tmp_path: Path) -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/artifact/toy_reproduction.py", "--output-dir", str(tmp_path)],
        cwd=REPO_ROOT,
        env=_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "TOY_REPRODUCTION_PASS = YES" in proc.stdout
    rows = json.loads((tmp_path / "synthetic_cells.json").read_text())
    assert any(row["completion_fraction"] == 0.0 for row in rows)
    assert any(row["telemetry"]["kv_occupancy_max"] > 1.0 for row in rows)
    assert any(row["mean_ttft"] != row["mean_ttft"] for row in rows)
    ranks = json.loads((tmp_path / "analysis_fixture_rankings.json").read_text())
    winners = {row["load_region"]: row["policy_id"] for row in ranks if row["rank"] == 1}
    assert winners["LOW"] != winners["OVERLOAD"]


def test_verify_artifact_rejects_implicit_results_path() -> None:
    proc = subprocess.run(
        ["bash", "scripts/artifact/verify_artifact.sh", "--validate-results"],
        cwd=REPO_ROOT,
        env=_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 2
    assert "--validate-results PATH" in proc.stdout + proc.stderr
