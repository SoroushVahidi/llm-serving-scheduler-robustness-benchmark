#!/usr/bin/env python3
"""Run and freeze the preregistered six-region FIFO calibration over the
frozen 120-window Pilot-V2 manifest.

This does not execute any comparative Pilot-V2 scheduler panel. It only computes
`lambda_ref` via the Stage-0 FIFO calibration definition, evaluates the six
fixed region multipliers (`LOW`, `PRE_KNEE`, `KNEE`, `POST_KNEE`, `OVERLOAD`,
`HIGH_PRESSURE`), and writes the raw calibration matrix plus derived region
assignments.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.calibration.stage0_load_calibration import (  # noqa: E402
    STAGE0_REFERENCE_GPU_CONFIG,
    _rebase_and_scale,
)
from robustbench.evaluation.run_policy import run_policy  # noqa: E402
from robustbench.policies.registry import make_policy  # noqa: E402
from robustbench.ranking_portability.calibration import (  # noqa: E402
    CALIBRATION_PROTOCOL_VERSION,
    REGION_FACTORS,
    REGION_SEQUENCE,
    assign_fifo_regions,
    compute_lambda_ref,
    evaluate_fifo_region_curve,
)
from robustbench.workloads.external.benchmark_synthesis import (  # noqa: E402
    synthesize_requests_from_window,
)
from robustbench.workloads.external.schema import ExternalWorkloadRecord  # noqa: E402

DEFAULT_MANIFEST = "/mmfs1/project/ikoutis/sv96/github/llm-serving-scheduler-ranking-portability-windows/artifacts/manifests/ranking_portability_pilot_v2_windows.json"
DEFAULT_RAW_OUT = REPO_ROOT / "artifacts" / "manifests" / "ranking_portability_phase11_raw_fifo_calibration.json"
DEFAULT_ASSIGN_OUT = REPO_ROOT / "artifacts" / "manifests" / "ranking_portability_phase11_region_assignments.json"


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).decode().strip()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _canonical_manifest_hash(manifest: dict) -> str:
    payload = {k: v for k, v in manifest.items() if k not in {"generated_at_utc", "content_sha256"}}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _slo_violation_rate_at(factor: float, requests) -> float:
    scaled = _rebase_and_scale(requests, factor)
    policy = make_policy("fifo")
    metrics = run_policy(
        policy,
        scaled,
        [STAGE0_REFERENCE_GPU_CONFIG],
        workload_tag="phase11_calibration",
        seed=0,
    )
    if metrics.num_completed == 0:
        return 1.0
    return float(metrics.slo_violation_rate)


def _file_hashes() -> dict[str, str]:
    relevant = [
        REPO_ROOT / "src" / "robustbench" / "ranking_portability" / "calibration.py",
        REPO_ROOT / "scripts" / "ranking_portability" / "build_phase11_calibration.py",
        REPO_ROOT / "docs" / "RANKING_PORTABILITY_PHASE11_CALIBRATION_PLAN.md",
        REPO_ROOT / "docs" / "RANKING_PORTABILITY_PHASE11_PRELAUNCH_FREEZE.md",
        REPO_ROOT / "src" / "robustbench" / "calibration" / "stage0_load_calibration.py",
        REPO_ROOT / "src" / "robustbench" / "policies" / "fifo.py",
        REPO_ROOT / "src" / "robustbench" / "simulator" / "simulator.py",
        REPO_ROOT / "src" / "robustbench" / "ranking_portability" / "schema.py",
    ]
    return {str(p.relative_to(REPO_ROOT)): _sha256_file(p) for p in relevant}


def _prelaunch_freeze_record(window_hash: str, compact_index_hash: str) -> dict:
    aggregate_payload = {
        "branch_sha": _git_sha(),
        "phase10_window_hash": window_hash,
        "compact_window_index_hash": compact_index_hash,
        "calibration_impl_hash": _sha256_file(REPO_ROOT / "src" / "robustbench" / "ranking_portability" / "calibration.py"),
        "build_script_hash": _sha256_file(REPO_ROOT / "scripts" / "ranking_portability" / "build_phase11_calibration.py"),
        "calibration_plan_hash": _sha256_file(REPO_ROOT / "docs" / "RANKING_PORTABILITY_PHASE11_CALIBRATION_PLAN.md"),
        "candidate_factor_grid_hash": hashlib.sha256(json.dumps(REGION_FACTORS, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "six_region_definition_hash": hashlib.sha256(json.dumps(REGION_SEQUENCE, separators=(",", ":")).encode()).hexdigest(),
        "fifo_policy_hash": _sha256_file(REPO_ROOT / "src" / "robustbench" / "policies" / "fifo.py"),
        "simulator_implementation_hash": _sha256_file(REPO_ROOT / "src" / "robustbench" / "simulator" / "simulator.py"),
        "validator_schema_hash": _sha256_file(REPO_ROOT / "src" / "robustbench" / "ranking_portability" / "schema.py"),
    }
    aggregate = hashlib.sha256(json.dumps(aggregate_payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"aggregate_prelaunch_freeze_sha256": aggregate, **aggregate_payload}


def _write_prelaunch_freeze_doc(record: dict, window_hash: str, compact_index_hash: str) -> None:
    doc = REPO_ROOT / "docs" / "RANKING_PORTABILITY_PHASE11_PRELAUNCH_FREEZE.md"
    content = f'''# Phase-11 prelaunch freeze

This freeze is recorded before real calibration execution begins.

## Contract summary

- `lambda_ref`: the FIFO inter-arrival compression factor at which `fifo.slo_violation_rate` first crosses the frozen 0.5% threshold (`0.005`).
- FIFO pressure statistic used: `slo_violation_rate` from the simulator's `RunMetrics`, computed with the single reference policy `fifo` and the frozen simulator config.
- six regions: `LOW` = 0.5×, `PRE_KNEE` = 0.8×, `KNEE` = 1.0×, `POST_KNEE` = 1.1×, `OVERLOAD` = 1.2×, `HIGH_PRESSURE` = 1.5×.
- factor-selection rule: the six multipliers map directly to the six regions; they are not searched after seeing results. The calibration target is a fixed region grid.
- deterministic tie rule: if a value lands exactly on a tie, prefer the earlier factor in canonical region order (`LOW`, `PRE_KNEE`, `KNEE`, `POST_KNEE`, `OVERLOAD`, `HIGH_PRESSURE`).
- two regions may not select the same factor: each region is assigned its own fixed multiplier from the frozen grid, and there is no optimizer that reassigns two regions to the same candidate.
- unreachable-target behavior: nearest valid boundary candidate is used with explicit interpolation/edge status, without changing the predeclared grid.
- zero-completion behavior: zero completion is recorded as a valid zero-completion assignment and is never silently reinterpreted.
- simulator-failure behavior: a simulator failure emits a schema-valid failure status and prevents the record from being claimed as valid calibration output.

## Frozen identity

- branch SHA: `{record['branch_sha']}`
- Phase-10 window hash: `{window_hash}`
- compact index hash: `{compact_index_hash}`
- aggregate prelaunch-freeze SHA-256: `{record['aggregate_prelaunch_freeze_sha256']}`
- calibration implementation hash: `{record['calibration_impl_hash']}`
- build script hash: `{record['build_script_hash']}`
- calibration plan hash: `{record['calibration_plan_hash']}`
- candidate factor grid hash: `{record['candidate_factor_grid_hash']}`
- six-region definition hash: `{record['six_region_definition_hash']}`
- FIFO policy implementation hash: `{record['fifo_policy_hash']}`
- simulator implementation/config hash: `{record['simulator_implementation_hash']}`
- validator/schema hash: `{record['validator_schema_hash']}`

`PHASE11_PRELAUNCH_CONTRACT = SATISFIED`
'''
    doc.write_text(content)


def _build_window_calibration(window: dict, *, window_hash: str, compact_index_hash: str, protocol_hash: str) -> tuple[list[dict], list[dict]]:
    source_family = window["source_family"]
    window_id = window["window_id"]
    records = [ExternalWorkloadRecord(**r) for r in window["records"]]
    requests, _ = synthesize_requests_from_window(records, window_id=window_id, seed=900000 + int(window_id.rsplit("w", 1)[1]))

    lambda_ref = compute_lambda_ref(requests)
    factor_pressure = evaluate_fifo_region_curve(requests, lambda_ref=lambda_ref)
    assignments = assign_fifo_regions(factor_pressure, region_order=REGION_SEQUENCE)

    raw_rows: list[dict] = []
    for row in assignments:
        factor = float(row["factor"])
        actual_factor = float(lambda_ref * factor)
        metrics = run_policy(
            make_policy("fifo"),
            _rebase_and_scale(requests, actual_factor),
            [STAGE0_REFERENCE_GPU_CONFIG],
            workload_tag=f"phase11::{source_family}::{window_id}::{row['region']}",
            seed=0,
        )
        raw_rows.append(
            {
                "source": source_family,
                "window_id": window_id,
                "region": row["region"],
                "load_factor": actual_factor,
                "selected_load_factor": factor,
                "lambda_ref": lambda_ref,
                "target_definition": f"FIFO reference policy / {row['region']} target at {factor}x lambda_ref",
                "actual_fifo_pressure": float(row["actual_achieved_pressure"]),
                "completion_fraction": float(metrics.completion_fraction),
                "slo_violation_rate": float(metrics.slo_violation_rate),
                "cell_status": row["status"],
                "phase10_window_hash": window_hash,
                "phase11_prelaunch_hash": protocol_hash,
                "simulator_config_hash": hashlib.sha256(json.dumps({"gpu_config": STAGE0_REFERENCE_GPU_CONFIG.__dict__}, sort_keys=True).encode()).hexdigest(),
                "calibration_protocol_hash": protocol_hash,
                "window_freeze_hash": window_hash,
                "compact_index_hash": compact_index_hash,
            }
        )

    region_rows = []
    for row in raw_rows:
        region_rows.append({
            "source": row["source"],
            "window_id": row["window_id"],
            "region": row["region"],
            "selected_load_factor": row["selected_load_factor"],
            "lambda_ref": row["lambda_ref"],
            "target_definition": row["target_definition"],
            "actual_fifo_pressure": row["actual_fifo_pressure"],
            "completion_state": row["cell_status"],
            "calibration_status": row["cell_status"],
            "phase10_window_hash": row["phase10_window_hash"],
            "phase11_prelaunch_hash": row["phase11_prelaunch_hash"],
            "simulator_config_hash": row["simulator_config_hash"],
        })
    return raw_rows, region_rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=Path(DEFAULT_MANIFEST), help="Frozen 120-window manifest path")
    ap.add_argument("--out", type=Path, default=DEFAULT_RAW_OUT, help="Output path for the raw FIFO calibration manifest")
    ap.add_argument("--assignments-out", type=Path, default=DEFAULT_ASSIGN_OUT, help="Output path for derived region assignments")
    args = ap.parse_args()

    if not args.manifest.exists():
        raise FileNotFoundError(f"Manifest not found: {args.manifest}")

    with open(args.manifest, "r") as f:
        manifest = json.load(f)

    window_hash = manifest["content_sha256"]
    expected = "0d1aa06ccbee352207327ea369ae75f12e91c0cda006c813a41b381effd29eef"
    if window_hash != expected:
        raise ValueError(f"Frozen window manifest hash mismatch: expected {expected}, got {window_hash}")

    compact_index_hash = "d78ec1087fedae02174ca093a9860c70468be336ccb1d7e6de756c81ba331e53"
    prelaunch_record = _prelaunch_freeze_record(window_hash, compact_index_hash)
    _write_prelaunch_freeze_doc(prelaunch_record, window_hash, compact_index_hash)

    all_rows = []
    all_assignments = []
    for w in manifest["windows"]:
        raw_rows, region_rows = _build_window_calibration(w, window_hash=window_hash, compact_index_hash=compact_index_hash, protocol_hash=CALIBRATION_PROTOCOL_VERSION)
        all_rows.extend(raw_rows)
        all_assignments.extend(region_rows)

    if len(all_rows) != 720:
        raise ValueError(f"Expected 720 calibration cells but got {len(all_rows)}")
    if len(all_assignments) != 720:
        raise ValueError(f"Expected 720 region assignments but got {len(all_assignments)}")

    raw_manifest = {
        "manifest_kind": "ranking_portability_phase11_raw_fifo_calibration",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_sha": _git_sha(),
        "window_freeze_hash": window_hash,
        "compact_index_sha256": compact_index_hash,
        "prelaunch_freeze_sha256": prelaunch_record["aggregate_prelaunch_freeze_sha256"],
        "protocol_version": CALIBRATION_PROTOCOL_VERSION,
        "reference_policy": "fifo",
        "candidate_grid": REGION_FACTORS,
        "region_order": list(REGION_SEQUENCE),
        "n_windows": len(manifest["windows"]),
        "n_regions": len(REGION_SEQUENCE),
        "n_cells_expected": 720,
        "n_cells_actual": len(all_rows),
        "cells": all_rows,
    }
    assignments_manifest = {
        "manifest_kind": "ranking_portability_phase11_region_assignments",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_sha": _git_sha(),
        "window_freeze_hash": window_hash,
        "compact_index_sha256": compact_index_hash,
        "prelaunch_freeze_sha256": prelaunch_record["aggregate_prelaunch_freeze_sha256"],
        "protocol_version": CALIBRATION_PROTOCOL_VERSION,
        "reference_policy": "fifo",
        "n_expected": 720,
        "n_actual": len(all_assignments),
        "assignments": all_assignments,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.assignments_out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(raw_manifest, f, indent=2, sort_keys=True)
    with open(args.assignments_out, "w") as f:
        json.dump(assignments_manifest, f, indent=2, sort_keys=True)

    print(f"raw_calibration_sha256={_sha256_file(args.out)}")
    print(f"region_assignments_sha256={_sha256_file(args.assignments_out)}")
    print(f"n_windows={len(manifest['windows'])}")
    print(f"n_cells={len(all_rows)}")


if __name__ == "__main__":
    main()
