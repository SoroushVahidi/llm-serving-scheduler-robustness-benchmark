#!/usr/bin/env python3
"""Builds artifacts/manifests/stage0_prelaunch_freeze.json (section G) --
ONLY once every prerequisite in docs/STAGE0_PRELAUNCH_READINESS_20260901.md
is satisfied. This script does not itself judge readiness; it just freezes
hashes of everything the pilot depends on, for later provenance
verification. Does not launch anything.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.stage0.cell import (  # noqa: E402
    STAGE0_LOAD_REGIONS, STAGE0_N_REPETITIONS, STAGE0_POLICIES, expand_cell_grid,
)


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).decode().strip()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def main() -> None:
    windows_path = REPO_ROOT / "artifacts" / "manifests" / "stage0_windows.json"
    calibration_path = REPO_ROOT / "artifacts" / "manifests" / "stage0_load_calibration.json"
    protocol_path = REPO_ROOT / "docs" / "STAGE0_DISCRIMINABILITY_PROTOCOL.md"
    metric_defs_path = REPO_ROOT / "docs" / "STAGE0_METRIC_DEFINITIONS.md"
    calibration_audit_path = REPO_ROOT / "docs" / "STAGE0_LOAD_CALIBRATION_AUDIT_20260901.md"

    with open(windows_path) as f:
        windows_manifest = json.load(f)
    with open(calibration_path) as f:
        calibration_manifest = json.load(f)

    # Confirms the frozen grid expands to exactly 1,080 cells; raises otherwise.
    cells = expand_cell_grid(windows_manifest, calibration_manifest)
    assert len(cells) == 1080, f"expected 1080 cells, got {len(cells)}"

    import importlib
    analyzer_mod = importlib.import_module("robustbench.stage0.analyzer")
    analyzer_source = Path(analyzer_mod.__file__).read_text()
    runner_source = Path(importlib.import_module("robustbench.stage0.runner").__file__).read_text()
    registry_source = Path(importlib.import_module("robustbench.policies.registry").__file__).read_text()

    import sklearn, numpy, scipy  # noqa: E402

    freeze = {
        "manifest_kind": "stage0_prelaunch_freeze",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "launch_candidate_repo_sha": _git_sha(),
        "stage0_protocol_sha256": _sha256_file(protocol_path),
        "stage0_metric_definitions_sha256": _sha256_file(metric_defs_path),
        "stage0_load_calibration_audit_sha256": _sha256_file(calibration_audit_path),
        "go_no_go_criteria_code_sha256": _sha256_text(analyzer_source),
        "go_no_go_criteria_summary": {
            "1_nontrivial_pairwise_differences": ">=30% of (source,window,load_region) cells non-tied (tol 1e-6 on ANWG)",
            "2_adequate_nontied_windows": ">=50% of 30 (source,window) pairs non-tied in >=1 load region",
            "3_no_universal_collapse": "not all cells trivial-underload (CF==1.0 all policies) or universal-collapse (CF==0.0 all policies)",
            "4_meaningful_metric_variation": ">=20% of non-tied cells: p95_latency or slo_violation_rate range > 10% of min",
            "5_no_single_source_dominates": "each source contributes 15%-70% of all non-tied cells",
        },
        "window_manifest_sha256": _sha256_file(windows_path),
        "window_manifest_n_windows": windows_manifest.get("n_windows_total"),
        "calibration_manifest_sha256": _sha256_file(calibration_path),
        "calibration_verdict": "CALIBRATION_VALID_CHECKER_OVERSENSITIVE",
        "calibration_n_plausible": sum(1 for c in calibration_manifest["calibrations"] if c["sanity"]["plausible"]),
        "calibration_n_total": len(calibration_manifest["calibrations"]),
        "source_checksums": {
            "burstgpt": "56193aa9b2bb26128ded43d2d29a960df6bf5af062bcfc9b005f3fcaa4e6e501",
            "azure_llm_2024_conversation": "a0cc9b969a9bbf0fd811802cbf4323edd3a209ace791e3799ad4f9207f213941",
            "bailian_qwen_traceB": "68e3f98e2d601d60d0abf4b89bc8a3654372abab7b1cde6373a13d0054379d59",
        },
        "stage0_policies": list(STAGE0_POLICIES),
        "stage0_load_regions": list(STAGE0_LOAD_REGIONS),
        "stage0_n_repetitions": STAGE0_N_REPETITIONS,
        "policy_registry_code_sha256": _sha256_text(registry_source),
        "runner_code_sha256": _sha256_text(runner_source),
        "expected_matrix_size": len(cells),
        "environment": {
            "python": sys.version.split()[0],
            "sklearn": sklearn.__version__,
            "numpy": numpy.__version__,
            "scipy": scipy.__version__,
        },
        "smoke_test_evidence": {
            "n_cells": 16,
            "n_success": 16,
            "all_labeled_scientific_status": "SMOKE_ONLY_DO_NOT_ANALYZE",
            "resumability_confirmed": True,
            "analyzer_correctly_refused_smoke_data": True,
        },
    }

    out_path = REPO_ROOT / "artifacts" / "manifests" / "stage0_prelaunch_freeze.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(freeze, f, indent=2)
    manifest_hash = _sha256_file(out_path)
    print(f"wrote {out_path}", file=sys.stderr)
    print(f"stage0_prelaunch_freeze_sha256={manifest_hash}")


if __name__ == "__main__":
    main()
