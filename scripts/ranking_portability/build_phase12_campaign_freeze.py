#!/usr/bin/env python3
"""Freeze the complete Phase-12 Pilot-V2 scientific-campaign matrix
(docs/RANKING_PORTABILITY_PHASE12_CAMPAIGN_PRELAUNCH_FREEZE.md): 18,720
cell identities over the frozen 120-window Phase-10 manifest, the frozen
Phase-11 region-load assignments, the 13-policy panel, and 2 verification
repetitions.

THIS SCRIPT DOES NOT EXECUTE ANY CELL. It only enumerates cell identity
and provenance-lookup indices and writes them to a manifest. No simulator
is constructed, no policy is run, no `Request` is synthesized, no
scheduler outcome is generated. `PHASE12_CAMPAIGN_EXECUTION_STARTED = NO`
after this script runs, same as before.
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

from robustbench.ranking_portability.phase12_campaign import (  # noqa: E402
    CAMPAIGN_POLICIES,
    CAMPAIGN_REGIONS,
    CAMPAIGN_REPETITIONS,
    CAMPAIGN_SOURCES,
    EXPECTED_ASSIGNMENT_KEY_COUNT,
    EXPECTED_CAMPAIGN_CELL_COUNT,
    SCIENTIFIC_STATUS_PILOT_V2_SCIENTIFIC,
    WINDOWS_PER_SOURCE,
    compute_campaign_freeze_identity,
    generate_campaign_cell_specs,
    load_campaign_window_ids,
    synthesis_seed_for_window,
)

EXPECTED_HASHES = {
    "phase10_window": "0d1aa06ccbee352207327ea369ae75f12e91c0cda006c813a41b381effd29eef",
    "phase10_compact_index": "d78ec1087fedae02174ca093a9860c70468be336ccb1d7e6de756c81ba331e53",
    "phase11_prelaunch": "e2564ea9484190832de50f63173c4b73ae054d6ae7008bb4ff6648c8dc917f7b",
    "phase11_raw_fifo": "201caaf04476ad8737ef6079fc0d6cb4e864601711d0b96c88750a717d8b2a6a",
    "phase11_region_assignment": "9fcb92f9ea1206ce185194527ada35d0e3b91bf4904be7ae23ba9ea997c17574",
}
TELEMETRY_AMENDMENT_SHA256 = "da85c2d52e7018ecee26994c4ff38b7c3a08deb58b65ee3a3ab20f9c56736061"

DEFAULT_COMPACT_INDEX = REPO_ROOT / "artifacts/manifests/ranking_portability_pilot_v2_windows_index.json"
DEFAULT_ASSIGNMENTS = REPO_ROOT / "artifacts/manifests/ranking_portability_phase11_region_assignments.json"
DEFAULT_OUT = REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_campaign_freeze.json"


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).decode().strip()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _canonical_hash(payload) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--compact-index", type=Path, default=DEFAULT_COMPACT_INDEX)
    ap.add_argument("--assignments", type=Path, default=DEFAULT_ASSIGNMENTS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    # === Immutable-hash safety gate ===
    compact_sha = _sha256_file(args.compact_index)
    assign_sha = _sha256_file(args.assignments)
    if compact_sha != EXPECTED_HASHES["phase10_compact_index"]:
        raise ValueError(f"compact index hash mismatch: expected {EXPECTED_HASHES['phase10_compact_index']}, got {compact_sha}. STOPPING.")
    if assign_sha != EXPECTED_HASHES["phase11_region_assignment"]:
        raise ValueError(f"region assignment hash mismatch: expected {EXPECTED_HASHES['phase11_region_assignment']}, got {assign_sha}. STOPPING.")

    with open(args.compact_index) as f:
        compact_index = json.load(f)
    # Note: the compact index itself (verified above via its own file hash,
    # `phase10_compact_index`) does not carry the full manifest's top-level
    # `content_sha256` field -- that hash exists only on the full 52MB
    # materialized manifest (`ranking_portability_pilot_v2_windows.json`),
    # which is not re-read here. The compact index's own file-hash check
    # above is the correct, sufficient integrity gate for this input.

    with open(args.assignments) as f:
        assign_doc = json.load(f)

    # === Window identities (120) ===
    window_ids_by_source = load_campaign_window_ids(compact_index)
    window_identities = {
        w["window_id"]: w["content_sha256"]
        for w in compact_index["windows"]
        if w["source_family"] in CAMPAIGN_SOURCES
    }
    all_window_ids = {wid for ids in window_ids_by_source.values() for wid in ids}
    if set(window_identities.keys()) != all_window_ids:
        raise ValueError("window_identities keys do not match the loaded campaign window ID set. STOPPING.")
    if len(window_identities) != 120:
        raise ValueError(f"Expected 120 window identities, got {len(window_identities)}. STOPPING.")

    # === Region-assignment index (720), verified exhaustive before building any cell ===
    assignment_rows = {
        (a["source"], a["window_id"], a["region"]): a for a in assign_doc["assignments"]
    }
    expected_keys = {
        (source, window_id, region)
        for source in CAMPAIGN_SOURCES
        for window_id in window_ids_by_source[source]
        for region in CAMPAIGN_REGIONS
    }
    missing_keys = expected_keys - set(assignment_rows.keys())
    unexpected_keys = set(assignment_rows.keys()) - expected_keys
    if missing_keys:
        raise ValueError(f"{len(missing_keys)} missing Phase-11 assignment key(s), e.g. {sorted(missing_keys)[:3]}. STOPPING.")
    if unexpected_keys:
        raise ValueError(f"{len(unexpected_keys)} unexpected Phase-11 assignment key(s), e.g. {sorted(unexpected_keys)[:3]}. STOPPING.")
    if len(assignment_rows) != EXPECTED_ASSIGNMENT_KEY_COUNT:
        raise ValueError(f"Expected {EXPECTED_ASSIGNMENT_KEY_COUNT} assignment keys, got {len(assignment_rows)}. STOPPING.")

    region_assignment_index = {}
    for (source, window_id, region), row in assignment_rows.items():
        lambda_ref = float(row["lambda_ref"])
        selected_load_factor = float(row["selected_load_factor"])
        key = f"{source}::{window_id}::{region}"
        region_assignment_index[key] = {
            "lambda_ref": lambda_ref,
            "selected_load_factor": selected_load_factor,
            "absolute_load_factor": lambda_ref * selected_load_factor,
        }

    # === Cell matrix (18,720) ===
    specs = generate_campaign_cell_specs(window_ids_by_source)
    if len(specs) != EXPECTED_CAMPAIGN_CELL_COUNT:
        raise ValueError(f"Generated {len(specs)} cell specs, expected {EXPECTED_CAMPAIGN_CELL_COUNT}. STOPPING.")

    cells = []
    for spec in specs:
        assignment_key = f"{spec.source_family}::{spec.window_id}::{spec.load_region}"
        cells.append({
            "cell_id": spec.cell_id,
            "source_family": spec.source_family,
            "window_id": spec.window_id,
            "load_region": spec.load_region,
            "policy_id": spec.policy_id,
            "repetition": spec.repetition,
            "synthesis_seed": synthesis_seed_for_window(spec.window_id),
            "region_assignment_key": assignment_key,
            "scientific_status": SCIENTIFIC_STATUS_PILOT_V2_SCIENTIFIC,
        })

    cell_ids = [c["cell_id"] for c in cells]
    if len(cell_ids) != len(set(cell_ids)):
        raise ValueError("Duplicate cell_id detected in generated campaign matrix. STOPPING.")

    # === Execution/schema/policy/simulator/campaign-module file hashes ===
    relevant_files = [
        "src/robustbench/ranking_portability/phase12_campaign.py",
        "src/robustbench/ranking_portability/phase12_smoke.py",
        "src/robustbench/ranking_portability/execute_cell.py",
        "src/robustbench/ranking_portability/schema.py",
        "src/robustbench/ranking_portability/calibration.py",
        "src/robustbench/workloads/external/benchmark_synthesis.py",
        "src/robustbench/calibration/stage0_load_calibration.py",
        "src/robustbench/policies/registry.py",
        "src/robustbench/simulator/simulator.py",
        "src/robustbench/simulator/telemetry.py",
    ]
    execution_file_hashes = {rel: _sha256_file(REPO_ROOT / rel) for rel in relevant_files}

    full_matrix_payload = {
        "window_identities": window_identities,
        "region_assignment_index": region_assignment_index,
        "cells": cells,
    }
    full_matrix_hash = _canonical_hash(full_matrix_payload)

    parent_smoke_branch_sha = "38188eca740c3bfeafa0463c80aaaff34b725e5a"
    freeze_identity = compute_campaign_freeze_identity(
        parent_smoke_branch_sha=parent_smoke_branch_sha,
        telemetry_amendment_sha256=TELEMETRY_AMENDMENT_SHA256,
        phase10_window_hash=EXPECTED_HASHES["phase10_window"],
        phase11_prelaunch_hash=EXPECTED_HASHES["phase11_prelaunch"],
        phase11_raw_fifo_hash=EXPECTED_HASHES["phase11_raw_fifo"],
        phase11_region_assignment_hash=EXPECTED_HASHES["phase11_region_assignment"],
        window_ids_by_source=window_ids_by_source,
        execution_file_hashes=execution_file_hashes,
        full_matrix_hash=full_matrix_hash,
    )

    manifest = {
        "manifest_kind": "ranking_portability_phase12_campaign_freeze",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_sha": _git_sha(),
        "parent_smoke_branch_sha": parent_smoke_branch_sha,
        "telemetry_amendment_sha256": TELEMETRY_AMENDMENT_SHA256,
        **{f"{k}_hash": v for k, v in EXPECTED_HASHES.items()},
        "campaign_sources": list(CAMPAIGN_SOURCES),
        "windows_per_source": WINDOWS_PER_SOURCE,
        "campaign_regions": list(CAMPAIGN_REGIONS),
        "campaign_policies": list(CAMPAIGN_POLICIES),
        "campaign_repetitions": list(CAMPAIGN_REPETITIONS),
        "expected_assignment_key_count": EXPECTED_ASSIGNMENT_KEY_COUNT,
        "n_assignment_keys_used": len(region_assignment_index),
        "EXPECTED_PHASE12_CAMPAIGN_CELLS": EXPECTED_CAMPAIGN_CELL_COUNT,
        "n_cells_actual": len(cells),
        "execution_file_hashes": execution_file_hashes,
        "full_matrix_hash": full_matrix_hash,
        "campaign_freeze_sha256": freeze_identity["campaign_freeze_sha256"],
        "window_identities": window_identities,
        "region_assignment_index": region_assignment_index,
        "cells": cells,
        "PHASE12_CAMPAIGN_EXECUTION_STARTED": False,
        "COMPARATIVE_PILOT_V2_RESULTS": "NONE",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)

    print(f"n_cells={len(cells)}")
    print(f"n_window_identities={len(window_identities)}")
    print(f"n_assignment_keys={len(region_assignment_index)}")
    print(f"full_matrix_hash={full_matrix_hash}")
    print(f"campaign_freeze_sha256={freeze_identity['campaign_freeze_sha256']}")
    print(f"out_sha256={_sha256_file(args.out)}")


if __name__ == "__main__":
    main()
