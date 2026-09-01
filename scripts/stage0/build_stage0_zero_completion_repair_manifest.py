#!/usr/bin/env python3
"""Builds artifacts/manifests/stage0_zero_completion_repair.json -- the
provenance record for docs/STAGE0_ZERO_COMPLETION_METRIC_AMENDMENT_20260901.md
(same gitignored-manifest convention as
artifacts/manifests/stage0_prelaunch_freeze.json). Records what changed
(schema validity semantics only), what did not (every scientific input
hash), and the exact 12 affected cell IDs -- so the repair is auditable
independently of this session's report. Does not launch or modify anything.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).decode().strip()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


AFFECTED_CELLS = [
    "azure_llm_2024::azure_llm_2024_stage0_w06::KNEE::vllm_faithful::rep0",
    "azure_llm_2024::azure_llm_2024_stage0_w06::KNEE::vllm_faithful::rep1",
    "azure_llm_2024::azure_llm_2024_stage0_w06::OVERLOAD::vllm_faithful::rep0",
    "azure_llm_2024::azure_llm_2024_stage0_w06::OVERLOAD::vllm_faithful::rep1",
    "azure_llm_2024::azure_llm_2024_stage0_w06::PRE_KNEE::vllm_faithful::rep0",
    "azure_llm_2024::azure_llm_2024_stage0_w06::PRE_KNEE::vllm_faithful::rep1",
    "azure_llm_2024::azure_llm_2024_stage0_w09::KNEE::vllm_faithful::rep0",
    "azure_llm_2024::azure_llm_2024_stage0_w09::KNEE::vllm_faithful::rep1",
    "azure_llm_2024::azure_llm_2024_stage0_w09::OVERLOAD::vllm_faithful::rep0",
    "azure_llm_2024::azure_llm_2024_stage0_w09::OVERLOAD::vllm_faithful::rep1",
    "azure_llm_2024::azure_llm_2024_stage0_w09::PRE_KNEE::vllm_faithful::rep0",
    "azure_llm_2024::azure_llm_2024_stage0_w09::PRE_KNEE::vllm_faithful::rep1",
]


def main() -> None:
    amendment_path = REPO_ROOT / "docs" / "STAGE0_ZERO_COMPLETION_METRIC_AMENDMENT_20260901.md"
    schema_path = REPO_ROOT / "src" / "robustbench" / "stage0" / "schema.py"
    metrics_path = REPO_ROOT / "src" / "robustbench" / "core" / "metrics.py"
    protocol_path = REPO_ROOT / "docs" / "STAGE0_DISCRIMINABILITY_PROTOCOL.md"
    metric_defs_path = REPO_ROOT / "docs" / "STAGE0_METRIC_DEFINITIONS.md"
    windows_path = REPO_ROOT / "artifacts" / "manifests" / "stage0_windows.json"
    calibration_path = REPO_ROOT / "artifacts" / "manifests" / "stage0_load_calibration.json"
    analyzer_path = REPO_ROOT / "src" / "robustbench" / "stage0" / "analyzer.py"
    registry_path = REPO_ROOT / "src" / "robustbench" / "policies" / "registry.py"

    manifest = {
        "manifest_kind": "stage0_zero_completion_repair",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "original_launch_branch": "research/stage0-orchestration-prelaunch-20260901",
        "original_launch_sha_claimed": "17de339f4a0f5f352c5d847e29d33b789f171fa6",
        "original_run_repo_sha_recorded_in_cells": "30f9152beb3392b103ca7e1d197a07e960959b25",
        "original_array_job_id": "1213964",
        "original_merge_job_id": "1213965 (FAILED -- validate rejected 12/1080 cells before analyzer could run)",
        "repair_branch": "research/stage0-zero-completion-undefined-metrics-20260901",
        "repair_sha": None,  # filled in after commit, before Wulver re-execution
        "amendment_doc_path": "docs/STAGE0_ZERO_COMPLETION_METRIC_AMENDMENT_20260901.md",
        "amendment_doc_sha256": _sha256_file(amendment_path),
        "bug": {
            "field": "slo_violation_rate",
            "root_cause": (
                "compute_metrics() only assigns slo_violation_rate inside "
                "'if completed:' (src/robustbench/core/metrics.py); it keeps "
                "its NaN dataclass default at zero completions. The frozen "
                "schema required slo_violation_rate non-NaN whenever "
                "success=True, so real zero-completion cells were incorrectly "
                "rejected as harness failures."
            ),
            "human_decision": (
                "slo_violation_rate is CONDITIONAL_ON_COMPLETION; NaN is its "
                "correct, undefined representation when completion_fraction "
                "== 0.0. No numerical value (0.0 or 1.0) is imputed. Decided "
                "AFTER the real launch exposed the 12 affected cells, BEFORE "
                "the frozen five-criterion analyzer ran or any verdict "
                "existed -- disclosed as a post-launch, pre-analysis protocol "
                "clarification, not a pre-registered definition."
            ),
        },
        "affected_cells": AFFECTED_CELLS,
        "n_affected_cells": len(AFFECTED_CELLS),
        "prior_successful_cells_required_regeneration": False,
        "prior_successful_cells_audited": 1068,
        "prior_successful_cells_with_completion_fraction_zero": 0,
        "core_metric_formula_changed": False,
        "anwg_changed": False,
        "scientific_inputs_unchanged": {
            "note": "Re-hashed on the repair worktree (checked out at the "
                    "claimed launch SHA 17de339) and diffed byte-for-byte "
                    "against the prelaunch worktree (de9f0a3) -- identical.",
            "stage0_protocol_sha256": _sha256_file(protocol_path),
            "stage0_metric_definitions_sha256_before_amendment_note": (
                "docs/STAGE0_METRIC_DEFINITIONS.md gained a new "
                "'Conditional metric audit' section by this repair; its "
                "ANWG section (the frozen primary-metric definition) is "
                "byte-for-byte unchanged."
            ),
            "window_manifest_sha256": _sha256_file(windows_path) if windows_path.exists() else None,
            "calibration_manifest_sha256": _sha256_file(calibration_path) if calibration_path.exists() else None,
            "go_no_go_criteria_code_sha256": _sha256_file(analyzer_path),
            "policy_registry_code_sha256": _sha256_file(registry_path),
        },
        "code_changed": {
            "src/robustbench/stage0/schema.py": (
                "validate_cell_result: slo_violation_rate NaN is accepted "
                "iff completion_fraction == 0.0; still required finite "
                "otherwise. arrival_normalized_weighted_goodput and "
                "completion_fraction remain required finite unconditionally "
                "(ALWAYS_DEFINED, unchanged)."
            ),
            "src/robustbench/core/metrics.py": "UNCHANGED",
            "src/robustbench/stage0/analyzer.py": "UNCHANGED (frozen)",
        },
        "tests": {"prior_total": 123, "new_total": 129, "new_tests_added": 6, "failures": 0},
        "repo_sha_at_manifest_build": _git_sha(),
    }

    out_path = REPO_ROOT / "artifacts" / "manifests" / "stage0_zero_completion_repair.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"wrote {out_path}", file=sys.stderr)
    print(f"stage0_zero_completion_repair_sha256={_sha256_file(out_path)}")


if __name__ == "__main__":
    main()
