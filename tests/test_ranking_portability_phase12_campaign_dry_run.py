"""Tests the Phase-12C shard-runner entrypoint's dry-run guard
(scripts/ranking_portability/run_phase12_campaign_shard.py). Invoked as a
subprocess against the real, frozen campaign manifest/shard plan -- no
scientific cell is ever executed by this test.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "ranking_portability" / "run_phase12_campaign_shard.py"
PYTHON = sys.executable


def _run(*extra_args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return subprocess.run(
        [PYTHON, str(SCRIPT), *extra_args],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
        env=env,
    )


def test_dry_run_default_succeeds_with_zero_problems():
    result = _run("--shard-id", "0")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "DRY_RUN_ONLY = YES" in result.stdout
    assert "n_problems=0" in result.stdout


def test_dry_run_never_mentions_executing_a_cell():
    result = _run("--shard-id", "0")
    lowered = result.stdout.lower()
    assert "completion_fraction" not in lowered
    assert "arrival_normalized_weighted_goodput" not in lowered


def test_dry_run_output_path_disjoint_from_smoke_output_path():
    result = _run("--shard-id", "0")
    assert "would_write_to=" in result.stdout
    line = next(l for l in result.stdout.splitlines() if l.startswith("would_write_to="))
    path = line.split("=", 1)[1]
    assert "campaign_results" in path
    assert "ranking_portability_phase12_smoke_raw.json" not in path


def test_execute_and_dry_run_together_rejected():
    """`--execute` and `--dry-run` are mutually exclusive; this must be
    rejected before anything is loaded or executed. (The real `--execute`
    path itself is tested separately, in
    test_ranking_portability_phase12_campaign_execute.py, against a tiny
    synthetic fixture -- never against the real 293-cell shard 0 in a
    test, which would take tens of minutes.)"""
    result = _run("--shard-id", "0", "--execute", "--dry-run")
    assert result.returncode != 0
    assert "mutually exclusive" in (result.stdout + result.stderr)


def test_out_of_range_shard_id_rejected():
    result = _run("--shard-id", "999")
    assert result.returncode != 0
    assert "out of range" in (result.stdout + result.stderr)
