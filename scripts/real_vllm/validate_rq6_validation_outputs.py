#!/usr/bin/env python3
"""Validates a directory of RQ6 real-vLLM scientific-validation outputs
against the frozen task matrix, schema, and provenance chain.

Deliberately does NOT decide whether the scientific hypothesis "won" --
it never inspects arrival_normalized_weighted_goodput's sign or magnitude
for anything other than presence/type checking. Its job is strictly:
identity, completeness, schema, and provenance, per docs/RQ6_REAL_VLLM_
VALIDATION_PREFREEZE_20260903.md's "Result validator" section.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.real_llm.rq6_validation import (  # noqa: E402
    POLICIES,
    RQ6_SOURCES,
    VALID_CALIBRATION_TERMINAL_STATUSES,
    enumerate_validation_cells,
)

REQUIRED_COMPLETED_KEYS = frozenset({
    "stamp", "run_status", "policy", "source", "window_id", "region",
    "candidate_scale", "real_lambda_ref", "calibration_convergence_status",
    "scheduler_cls", "scheduling_policy", "replicate_seed", "model", "gpu",
    "selected_port", "port_selection_method", "started_at_utc", "finished_at_utc",
    "offered_request_count", "completed_request_count",
    "arrival_normalized_weighted_goodput", "slo_violation_rate",
    "workload_manifest_path", "workload_manifest_content_sha256",
    "calibration_manifest_sha256", "validation_manifest_path", "validation_manifest_sha256",
    "case_selection_manifest_sha256", "environment_spec_sha256", "repo_sha",
})

VALID_RUN_STATUSES = frozenset({
    "COMPLETED", "FAILED_CALIBRATION_DEPENDENCY", "FAILED_SERVER_START", "FAILED_DURING_REPLAY",
})


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate(
    out_dir: Path, *, manifest_dir: Path, validation_manifest_path: Path,
) -> Dict[str, Any]:
    with open(validation_manifest_path) as f:
        manifest = json.load(f)
    expected_validation_manifest_sha256 = _sha256_file(validation_manifest_path)
    expected_case_selection_sha256 = manifest["case_selection"]["manifest_sha256"]
    expected_calibration_manifest_sha256 = manifest["calibration_dependency"]["calibration_manifest_sha256"]

    cells = enumerate_validation_cells(manifest_dir)
    expected_keys = {(c.policy, c.source, c.window_id) for c in cells}

    problems: List[str] = []
    found_keys = set()
    duplicates: List[str] = []
    status_counts: Dict[str, int] = {}
    non_scientific_files: List[str] = []

    json_paths = sorted(out_dir.rglob("*.json"))
    for path in json_paths:
        if path.name.endswith(".server.log"):
            continue
        try:
            with open(path) as f:
                record = json.load(f)
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{path}: unreadable/invalid JSON ({exc})")
            continue

        stamp = record.get("stamp")
        if stamp != "RQ6_REAL_VLLM_SCIENTIFIC_VALIDATION":
            non_scientific_files.append(str(path))
            continue

        key = (record.get("policy"), record.get("source"), record.get("window_id"))
        if key in found_keys:
            duplicates.append(str(path))
        found_keys.add(key)

        if key not in expected_keys:
            problems.append(f"{path}: (policy, source, window_id)={key} is not a frozen task-matrix cell")

        status = record.get("run_status")
        status_counts[status] = status_counts.get(status, 0) + 1
        if status not in VALID_RUN_STATUSES:
            problems.append(f"{path}: unrecognized run_status {status!r}")
            continue

        if status != "COMPLETED":
            continue  # a valid FAILED_* record only needs run_status + identity, checked above

        missing = REQUIRED_COMPLETED_KEYS - record.keys()
        if missing:
            problems.append(f"{path}: COMPLETED record missing keys {sorted(missing)}")
            continue

        if record["validation_manifest_sha256"] != expected_validation_manifest_sha256:
            problems.append(f"{path}: validation_manifest_sha256 mismatch")
        if record["case_selection_manifest_sha256"] != expected_case_selection_sha256:
            problems.append(f"{path}: case_selection_manifest_sha256 mismatch")
        if record["calibration_manifest_sha256"] != expected_calibration_manifest_sha256:
            problems.append(f"{path}: calibration_manifest_sha256 mismatch")

        if record["policy"] not in POLICIES:
            problems.append(f"{path}: policy {record['policy']!r} not in frozen POLICIES {POLICIES}")
        if record["source"] not in RQ6_SOURCES:
            problems.append(f"{path}: source {record['source']!r} not in frozen RQ6_SOURCES {RQ6_SOURCES}")
        if record["calibration_convergence_status"] not in VALID_CALIBRATION_TERMINAL_STATUSES:
            problems.append(f"{path}: calibration_convergence_status {record['calibration_convergence_status']!r} invalid")

        expected_scheduler = manifest["scheduler_mapping"][record["policy"]]
        if record["scheduler_cls"] != expected_scheduler["scheduler_cls"]:
            problems.append(f"{path}: scheduler_cls {record['scheduler_cls']!r} != expected {expected_scheduler['scheduler_cls']!r} for policy {record['policy']}")
        if record["scheduling_policy"] != expected_scheduler["scheduling_policy"]:
            problems.append(f"{path}: scheduling_policy mismatch for policy {record['policy']}")

        n_total = record["offered_request_count"]
        n_completed = record["completed_request_count"]
        if not (isinstance(n_total, int) and n_total == 200):
            problems.append(f"{path}: offered_request_count {n_total!r} != 200")
        if not (isinstance(n_completed, int) and 0 <= n_completed <= n_total):
            problems.append(f"{path}: completed_request_count {n_completed!r} inconsistent with offered_request_count {n_total!r}")

        anwg = record["arrival_normalized_weighted_goodput"]
        if not isinstance(anwg, (int, float)):
            problems.append(f"{path}: arrival_normalized_weighted_goodput is not numeric ({anwg!r})")

    missing_cells = [list(k) for k in sorted(expected_keys - found_keys)]

    report = {
        "out_dir": str(out_dir),
        "n_expected_cells": len(expected_keys),
        "n_found_scientific_files": len(found_keys),
        "n_missing_cells": len(missing_cells),
        "missing_cells": missing_cells[:50],  # cap for readability; full count above
        "n_duplicates": len(duplicates),
        "duplicate_files": duplicates,
        "status_counts": status_counts,
        "n_non_scientific_files_excluded": len(non_scientific_files),
        "non_scientific_files_excluded": non_scientific_files,
        "n_problems": len(problems),
        "problems": problems,
        "passed": (
            len(problems) == 0 and len(duplicates) == 0 and len(missing_cells) == 0
        ),
    }
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--manifest-dir", type=Path, default=REPO_ROOT / "artifacts/manifests/rq6_real_vllm")
    ap.add_argument("--validation-manifest", type=Path,
                     default=REPO_ROOT / "configs/real_vllm/rq6_validation_manifest_v1_20260903.json")
    ap.add_argument("--report-out", type=Path, default=None)
    args = ap.parse_args()

    report = validate(args.out_dir, manifest_dir=args.manifest_dir, validation_manifest_path=args.validation_manifest)
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.report_out:
        args.report_out.write_text(text)
    sys.exit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
