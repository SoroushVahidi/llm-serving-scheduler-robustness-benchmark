#!/usr/bin/env python3
"""Result-blind verifier for the frozen LSSP artifact identities.

This command verifies manifest/hash/schema relationships only. It never
loads campaign result directories, never synthesizes requests, never creates
a Simulator, never submits Slurm, and never executes a scientific cell.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.ranking_portability.phase12_campaign import (  # noqa: E402
    EXPECTED_ASSIGNMENT_KEY_COUNT,
    EXPECTED_CAMPAIGN_CELL_COUNT,
)

RESULT_BLIND_ENV = "LSSP_ARTIFACT_REPRO_PREFREEZE_RESULT_BLIND"

EXPECTED = {
    "phase10_window_hash": "0d1aa06ccbee352207327ea369ae75f12e91c0cda006c813a41b381effd29eef",
    "phase10_compact_index_hash": "d78ec1087fedae02174ca093a9860c70468be336ccb1d7e6de756c81ba331e53",
    "phase11_prelaunch_hash": "e2564ea9484190832de50f63173c4b73ae054d6ae7008bb4ff6648c8dc917f7b",
    "phase11_raw_fifo_hash": "201caaf04476ad8737ef6079fc0d6cb4e864601711d0b96c88750a717d8b2a6a",
    "phase11_region_assignment_hash": "9fcb92f9ea1206ce185194527ada35d0e3b91bf4904be7ae23ba9ea997c17574",
    "phase12_campaign_manifest_file_sha256": "44a81e98d9a3fa6646bd716125726bf732530d243a54d0952e98b20fda1d564a",
    "phase12_campaign_freeze_sha256": "81fa3d9b48a2241001e6820942d4542dcc5b5e30973ad9d2786e72972494f57a",
    "phase12_full_matrix_hash": "832d96d7ff4d5e8843c233a6a4708bbbbc578ef6b65307c37f5ac127c62c1ccf",
    "phase12_shard_plan_file_sha256": "27d2740c5f1585f1b781680a813890c473236bbd2feb8e3a669bd2cf7d857511",
    "expected_campaign_cell_count": 18720,
    "expected_assignment_key_count": 720,
    "expected_shard_count": 64,
}

COMPACT_INDEX = REPO_ROOT / "artifacts/manifests/ranking_portability_pilot_v2_windows_index.json"
RAW_FIFO = REPO_ROOT / "artifacts/manifests/ranking_portability_phase11_raw_fifo_calibration.json"
REGION_ASSIGNMENTS = REPO_ROOT / "artifacts/manifests/ranking_portability_phase11_region_assignments.json"
CAMPAIGN_MANIFEST = REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_campaign_freeze.json"
SHARD_PLAN = REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_shard_plan.json"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _canonical_hash(payload: object) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def _fmt(v: object) -> object:
    if isinstance(v, set):
        return f"set(len={len(v)})"
    return v


def _check(label: str, observed: object, expected: object, problems: list[str]) -> None:
    ok = observed == expected
    print(f"{label}: observed={_fmt(observed)} expected={_fmt(expected)} match={ok}")
    if not ok:
        if isinstance(observed, set) and isinstance(expected, set):
            problems.append(
                f"{label}: missing={len(expected - observed)} unexpected={len(observed - expected)}"
            )
        else:
            problems.append(f"{label}: observed={observed!r} expected={expected!r}")


def main() -> int:
    if os.environ.get(RESULT_BLIND_ENV) != "YES":
        print(f"ERROR: {RESULT_BLIND_ENV}=YES is required.", file=sys.stderr)
        return 2

    problems: list[str] = []
    compact = _load_json(COMPACT_INDEX)
    region = _load_json(REGION_ASSIGNMENTS)
    campaign = _load_json(CAMPAIGN_MANIFEST)
    shard_plan = _load_json(SHARD_PLAN)

    _check("Phase-10 window hash", campaign.get("phase10_window_hash"), EXPECTED["phase10_window_hash"], problems)
    _check("Phase-10 compact index file SHA-256", _sha256_file(COMPACT_INDEX), EXPECTED["phase10_compact_index_hash"], problems)
    _check("Phase-10 compact index in campaign", campaign.get("phase10_compact_index_hash"), EXPECTED["phase10_compact_index_hash"], problems)
    _check("Phase-10 compact index in Phase-11 assignments", region.get("compact_index_sha256"), EXPECTED["phase10_compact_index_hash"], problems)
    _check("Phase-10 compact window count", compact.get("n_windows_total"), 120, problems)

    _check("Phase-11 prelaunch freeze hash", campaign.get("phase11_prelaunch_hash"), EXPECTED["phase11_prelaunch_hash"], problems)
    _check("Phase-11 prelaunch in assignments", region.get("prelaunch_freeze_sha256"), EXPECTED["phase11_prelaunch_hash"], problems)
    _check("Phase-11 raw FIFO calibration file SHA-256", _sha256_file(RAW_FIFO), EXPECTED["phase11_raw_fifo_hash"], problems)
    _check("Phase-11 raw FIFO in campaign", campaign.get("phase11_raw_fifo_hash"), EXPECTED["phase11_raw_fifo_hash"], problems)
    _check("Phase-11 region assignments file SHA-256", _sha256_file(REGION_ASSIGNMENTS), EXPECTED["phase11_region_assignment_hash"], problems)
    _check("Phase-11 region assignments in campaign", campaign.get("phase11_region_assignment_hash"), EXPECTED["phase11_region_assignment_hash"], problems)
    _check("Phase-11 assignment key count", region.get("n_actual"), EXPECTED_ASSIGNMENT_KEY_COUNT, problems)

    _check("Phase-12 campaign manifest file SHA-256", _sha256_file(CAMPAIGN_MANIFEST), EXPECTED["phase12_campaign_manifest_file_sha256"], problems)
    _check("Phase-12 campaign freeze SHA-256", campaign.get("campaign_freeze_sha256"), EXPECTED["phase12_campaign_freeze_sha256"], problems)
    _check("Phase-12 campaign cell count", campaign.get("n_cells_actual"), EXPECTED_CAMPAIGN_CELL_COUNT, problems)
    _check("Phase-12 campaign expected cell count", campaign.get("EXPECTED_PHASE12_CAMPAIGN_CELLS"), EXPECTED["expected_campaign_cell_count"], problems)
    _check("Phase-12 assignment keys used", campaign.get("n_assignment_keys_used"), EXPECTED["expected_assignment_key_count"], problems)

    full_matrix_payload = {
        "window_identities": campaign["window_identities"],
        "region_assignment_index": campaign["region_assignment_index"],
        "cells": campaign["cells"],
    }
    _check("Phase-12 full matrix hash recomputed", _canonical_hash(full_matrix_payload), EXPECTED["phase12_full_matrix_hash"], problems)
    _check("Phase-12 full matrix hash in campaign", campaign.get("full_matrix_hash"), EXPECTED["phase12_full_matrix_hash"], problems)

    _check("Phase-12 shard plan file SHA-256", _sha256_file(SHARD_PLAN), EXPECTED["phase12_shard_plan_file_sha256"], problems)
    _check("Shard plan campaign freeze relationship", shard_plan.get("campaign_manifest_freeze_sha256"), campaign.get("campaign_freeze_sha256"), problems)
    _check("Shard plan full-matrix relationship", shard_plan.get("campaign_manifest_full_matrix_hash"), campaign.get("full_matrix_hash"), problems)
    _check("Shard plan total cell count", shard_plan.get("total_cells"), EXPECTED["expected_campaign_cell_count"], problems)
    _check("Shard count", shard_plan.get("shard_count"), EXPECTED["expected_shard_count"], problems)

    campaign_ids = {c["cell_id"] for c in campaign["cells"]}
    shard_ids: list[str] = []
    for shard in shard_plan["shards"]:
        shard_ids.extend(shard["cell_ids"])
    _check("Shard-plan duplicate cell IDs", len(shard_ids), len(set(shard_ids)), problems)
    _check("Shard-plan covers campaign cell IDs", set(shard_ids), campaign_ids, problems)

    print("SCIENTIFIC_CAMPAIGN_EXECUTED = NO")
    print(f"{RESULT_BLIND_ENV} = YES")
    if problems:
        print("IMMUTABLE_ARTIFACTS_VALID = NO")
        for p in problems:
            print(f"PROBLEM: {p}")
        return 1
    print("IMMUTABLE_ARTIFACTS_VALID = YES")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
