#!/usr/bin/env python3
"""Execute the frozen Phase-12A Pilot-V2 engineering smoke
(docs/RANKING_PORTABILITY_PHASE12_SMOKE_FREEZE.md): 468 cells over the
real Pilot-V2 execution path (`robustbench.ranking_portability.execute_cell`),
the real 13-policy panel, the real frozen Phase-11 region-load assignments,
and the real telemetry schema.

ENGINEERING VALIDATION ONLY. Every cell's `scientific_status` is set to
`ENGINEERING_SMOKE`. This script performs NO ranking analysis, computes NO
Kendall tau / Spearman rho / reversal statistic, and asserts NO direction
of finding -- it only executes cells and reports matrix/schema/telemetry/
determinism integrity, per the smoke's own validation gate (docs above).

Must be run with access to `artifacts/smoke_input_windows_raw.json` (a
verified byte-identical 3-window subset of the canonical
`ranking_portability_pilot_v2_windows.json` manifest -- see the freeze doc
for the extraction provenance) and
`artifacts/manifests/ranking_portability_phase11_region_assignments.json`
(committed, frozen).
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
from robustbench.policies.registry import make_policy_any  # noqa: E402
from robustbench.ranking_portability.calibration import compute_lambda_ref  # noqa: E402
from robustbench.ranking_portability.execute_cell import execute_cell  # noqa: E402
from robustbench.ranking_portability.phase12_smoke import (  # noqa: E402
    SCIENTIFIC_STATUS_ENGINEERING_SMOKE,
    SMOKE_WINDOW_IDS,
    EXPECTED_SMOKE_CELL_COUNT,
    generate_smoke_cell_specs,
    synthesis_seed_for_window,
)
from robustbench.workloads.external.benchmark_synthesis import (  # noqa: E402
    synthesize_requests_from_window,
)
from robustbench.workloads.external.schema import ExternalWorkloadRecord  # noqa: E402

DEFAULT_WINDOWS_JSON = REPO_ROOT / "artifacts" / "smoke_input_windows_raw.json"
DEFAULT_ASSIGNMENTS_JSON = (
    REPO_ROOT / "artifacts" / "manifests" / "ranking_portability_phase11_region_assignments.json"
)
DEFAULT_OUT = REPO_ROOT / "artifacts" / "manifests" / "ranking_portability_phase12_smoke_raw.json"

EXPECTED_PHASE10_WINDOW_HASH = "0d1aa06ccbee352207327ea369ae75f12e91c0cda006c813a41b381effd29eef"
EXPECTED_PHASE11_REGION_ASSIGNMENT_HASH = (
    "9fcb92f9ea1206ce185194527ada35d0e3b91bf4904be7ae23ba9ea997c17574"
)


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).decode().strip()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--windows-json", type=Path, default=DEFAULT_WINDOWS_JSON)
    ap.add_argument("--assignments-json", type=Path, default=DEFAULT_ASSIGNMENTS_JSON)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    # --- Immutable-hash safety gate: re-verify before touching anything. ---
    assignment_sha = _sha256_file(args.assignments_json)
    if assignment_sha != EXPECTED_PHASE11_REGION_ASSIGNMENT_HASH:
        raise ValueError(
            f"Phase-11 region assignment hash mismatch: expected "
            f"{EXPECTED_PHASE11_REGION_ASSIGNMENT_HASH}, got {assignment_sha}. STOPPING."
        )

    with open(args.windows_json) as f:
        windows_payload = json.load(f)
    if windows_payload["source_manifest_content_sha256"] != EXPECTED_PHASE10_WINDOW_HASH:
        raise ValueError(
            "Phase-10 window manifest hash mismatch on extracted smoke input windows. STOPPING."
        )
    windows_by_id = {w["window_id"]: w for w in windows_payload["windows"]}
    expected_ids = set(SMOKE_WINDOW_IDS.values())
    if set(windows_by_id.keys()) != expected_ids:
        raise ValueError(
            f"Smoke input windows do not match the frozen selection: "
            f"got {sorted(windows_by_id.keys())}, expected {sorted(expected_ids)}. STOPPING."
        )
    for w in windows_by_id.values():
        if len(w["records"]) != 200:
            raise ValueError(f"Window {w['window_id']} has {len(w['records'])} records, expected 200.")

    with open(args.assignments_json) as f:
        assignments_doc = json.load(f)
    assignments_by_key = {
        (a["source"], a["window_id"], a["region"]): a for a in assignments_doc["assignments"]
    }

    repo_sha = _git_sha()

    # --- Build per-window base requests once; verify lambda_ref recomputation. ---
    base_requests_by_window: dict[str, list] = {}
    lambda_ref_check: dict[str, dict] = {}
    for source, window_id in SMOKE_WINDOW_IDS.items():
        w = windows_by_id[window_id]
        records = [ExternalWorkloadRecord(**r) for r in w["records"]]
        seed = synthesis_seed_for_window(window_id)
        requests, synth_manifest = synthesize_requests_from_window(
            records, window_id=window_id, seed=seed
        )
        if len(requests) != 200:
            raise ValueError(
                f"Window {window_id} synthesized {len(requests)} requests, expected 200 "
                f"(n_records_dropped_invalid={synth_manifest.n_records_dropped_invalid})."
            )
        base_requests_by_window[window_id] = requests

        recomputed_lambda_ref = compute_lambda_ref(requests)
        frozen_row = next(
            a for a in assignments_doc["assignments"]
            if a["source"] == source and a["window_id"] == window_id
        )
        frozen_lambda_ref = float(frozen_row["lambda_ref"])
        rel_diff = abs(recomputed_lambda_ref - frozen_lambda_ref) / max(abs(frozen_lambda_ref), 1e-12)
        lambda_ref_check[window_id] = {
            "recomputed_lambda_ref": recomputed_lambda_ref,
            "frozen_lambda_ref": frozen_lambda_ref,
            "relative_difference": rel_diff,
            "matches": rel_diff < 1e-9,
        }

    # --- Execute the frozen 468-cell matrix. ---
    specs = generate_smoke_cell_specs()
    if len(specs) != EXPECTED_SMOKE_CELL_COUNT:
        raise ValueError(f"Cell spec generation produced {len(specs)}, expected {EXPECTED_SMOKE_CELL_COUNT}.")

    cells = []
    scaled_cache: dict = {}
    for spec in specs:
        key = (spec.source_family, spec.window_id, spec.load_region)
        if key not in assignments_by_key:
            raise ValueError(f"No frozen Phase-11 region assignment for {key}. STOPPING.")
        row = assignments_by_key[key]
        lambda_ref = float(row["lambda_ref"])
        selected_load_factor = float(row["selected_load_factor"])
        actual_factor = lambda_ref * selected_load_factor

        if key not in scaled_cache:
            base_requests = base_requests_by_window[spec.window_id]
            scaled_cache[key] = _rebase_and_scale(base_requests, actual_factor)
        scaled_requests = scaled_cache[key]

        synthesis_seed = synthesis_seed_for_window(spec.window_id)
        policy = make_policy_any(spec.policy_id)

        result = execute_cell(
            cell_id=spec.cell_id,
            source_family=spec.source_family,
            window_id=spec.window_id,
            load_region=spec.load_region,
            load_factor=actual_factor,
            policy_id=spec.policy_id,
            repetition=spec.repetition,
            synthesis_seed=synthesis_seed,
            repo_sha=repo_sha,
            policy=policy,
            requests=scaled_requests,
            gpu_configs=[STAGE0_REFERENCE_GPU_CONFIG],
            scientific_status=SCIENTIFIC_STATUS_ENGINEERING_SMOKE,
        )
        d = result.to_dict()
        d["selected_load_factor"] = selected_load_factor
        d["lambda_ref"] = lambda_ref
        d["phase11_region_assignment_hash"] = EXPECTED_PHASE11_REGION_ASSIGNMENT_HASH
        cells.append(d)

    manifest = {
        "manifest_kind": "ranking_portability_phase12_smoke_raw",
        "scientific_status": "ENGINEERING_SMOKE_ONLY",
        "smoke_results_must_not_be_used_as_comparative_pilot_v2_evidence": True,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_sha": repo_sha,
        "phase10_window_hash": EXPECTED_PHASE10_WINDOW_HASH,
        "phase11_region_assignment_hash": EXPECTED_PHASE11_REGION_ASSIGNMENT_HASH,
        "lambda_ref_recomputation_check": lambda_ref_check,
        "n_cells_expected": EXPECTED_SMOKE_CELL_COUNT,
        "n_cells_actual": len(cells),
        "cells": cells,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)

    print(f"n_cells={len(cells)}")
    print(f"out_sha256={_sha256_file(args.out)}")
    for window_id, chk in lambda_ref_check.items():
        print(f"lambda_ref_check[{window_id}]: matches={chk['matches']} rel_diff={chk['relative_difference']:.3e}")


if __name__ == "__main__":
    main()
