#!/usr/bin/env python3
"""Write a machine-readable, result-blind LSSP provenance snapshot."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.ranking_portability.schema import CELL_SCHEMA_VERSION  # noqa: E402
from robustbench.simulator.telemetry import TELEMETRY_SCHEMA_VERSION  # noqa: E402

RESULT_BLIND_ENV = "LSSP_ARTIFACT_REPRO_PREFREEZE_RESULT_BLIND"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO_ROOT).decode().strip()


def _pkg_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "artifacts/generated/lssp_artifact_repro_provenance_snapshot.json")
    args = ap.parse_args()

    if os.environ.get(RESULT_BLIND_ENV) != "YES":
        print(f"ERROR: {RESULT_BLIND_ENV}=YES is required.", file=sys.stderr)
        return 2

    campaign = json.loads((REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_campaign_freeze.json").read_text())
    snapshot = {
        "snapshot_kind": "lssp_artifact_repro_prefreeze_provenance_snapshot",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "result_blind": True,
        RESULT_BLIND_ENV: "YES",
        "repository_sha": _git(["rev-parse", "HEAD"]),
        "repository_branch": _git(["rev-parse", "--abbrev-ref", "HEAD"]),
        "parent_sha": "2b9a21fb58798292c95980d35d05e53b3c6f14f6",
        "campaign_freeze_sha256": campaign["campaign_freeze_sha256"],
        "phase12_full_matrix_hash": campaign["full_matrix_hash"],
        "immutable_phase10_11_hashes": {
            "phase10_window_hash": campaign["phase10_window_hash"],
            "phase10_compact_index_hash": campaign["phase10_compact_index_hash"],
            "phase11_prelaunch_hash": campaign["phase11_prelaunch_hash"],
            "phase11_raw_fifo_hash": campaign["phase11_raw_fifo_hash"],
            "phase11_region_assignment_hash": campaign["phase11_region_assignment_hash"],
        },
        "python": {
            "version": platform.python_version(),
            "executable": sys.executable,
            "implementation": platform.python_implementation(),
        },
        "packages": {
            name: _pkg_version(name)
            for name in ["robustbench", "numpy", "pandas", "PyYAML", "scipy", "pytest"]
        },
        "os": {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "kernel": platform.version(),
            "machine": platform.machine(),
        },
        "environment_variables": {
            key: os.environ.get(key)
            for key in [
                RESULT_BLIND_ENV,
                "PYTHONPATH",
                "VIRTUAL_ENV",
                "CONDA_PREFIX",
                "LOADEDMODULES",
                "MODULEPATH",
                "SLURM_JOB_ID",
            ]
        },
        "wulver_environment": {
            "documented_module": "slurm/wulver",
            "loaded_modules": os.environ.get("LOADEDMODULES"),
            "required_for_tier1": False,
            "required_for_tier2_campaign_execution": True,
        },
        "filesystem_assumptions": {
            "repository_root": str(REPO_ROOT),
            "tracked_frozen_manifests": "artifacts/manifests/",
            "generated_local_outputs": "artifacts/generated/ (gitignored)",
            "campaign_results_default": "none; reviewer validation requires an explicit --validate-results path",
        },
        "implementation_hashes": {
            "simulator": _sha256_file(REPO_ROOT / "src/robustbench/simulator/simulator.py"),
            "policy_registry": _sha256_file(REPO_ROOT / "configs/policies/canonical_policy_registry.yaml"),
            "ranking_schema": _sha256_file(REPO_ROOT / "src/robustbench/ranking_portability/schema.py"),
            "telemetry": _sha256_file(REPO_ROOT / "src/robustbench/simulator/telemetry.py"),
        },
        "schema_versions": {
            "ranking_portability_cell": CELL_SCHEMA_VERSION,
            "ranking_portability_telemetry": TELEMETRY_SCHEMA_VERSION,
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.out}")
    print("PROVENANCE_SNAPSHOT_RESULT_BLIND = YES")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
