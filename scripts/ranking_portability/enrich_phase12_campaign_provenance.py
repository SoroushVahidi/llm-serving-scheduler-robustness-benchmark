#!/usr/bin/env python3
"""Phase-12D deterministic provenance enrichment for completed campaign shards.

Reads Phase-12C raw shard checkpoints *read-only*, writes metadata-enriched
copies to a separate namespace, proves non-provenance row invariance, records
original/repaired shard hashes, and emits a deterministic consolidated
artifact.  It performs no ranking/statistical analysis and never executes a
scientific cell.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.ranking_portability.phase12_provenance import (  # noqa: E402
    APPROVED_ENRICHMENT_FIELDS,
    PROVENANCE_CONTRACT_VERSION,
    enrich_row_provenance,
    expected_phase12_provenance,
    masked_non_provenance_view,
    phase12_simulator_config_payload,
    validate_analysis_admission_row,
)
from robustbench.ranking_portability.schema import validate_cell_result  # noqa: E402

EXPECTED_CAMPAIGN_FREEZE_SHA256 = "81fa3d9b48a2241001e6820942d4542dcc5b5e30973ad9d2786e72972494f57a"
EXPECTED_FULL_MATRIX_HASH = "832d96d7ff4d5e8843c233a6a4708bbbbc578ef6b65307c37f5ac127c62c1ccf"
EXPECTED_EXECUTION_REPO_SHA = "2b9a21fb58798292c95980d35d05e53b3c6f14f6"
EXPECTED_CELL_COUNT = 18_720
EXPECTED_SHARD_COUNT = 64

DEFAULT_MANIFEST = REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_campaign_freeze.json"
DEFAULT_SHARD_PLAN = REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_shard_plan.json"
DEFAULT_RAW_DIR = REPO_ROOT / "artifacts/campaign_results" / EXPECTED_CAMPAIGN_FREEZE_SHA256[:16]
DEFAULT_ENRICHED_DIR = REPO_ROOT / "artifacts/campaign_results_enriched" / EXPECTED_CAMPAIGN_FREEZE_SHA256[:16]
DEFAULT_RAW_LEDGER = REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_raw_shard_hashes.json"
DEFAULT_REPAIR_LEDGER = REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_repaired_shard_hashes.json"
DEFAULT_CONSOLIDATED = REPO_ROOT / "artifacts/campaign_results_enriched" / EXPECTED_CAMPAIGN_FREEZE_SHA256[:16] / "consolidated.json"
DEFAULT_AMENDMENT = REPO_ROOT / "docs/RANKING_PORTABILITY_PHASE12_PROVENANCE_AMENDMENT.md"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _canonical_sha256(payload) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).decode().strip()
    except Exception:
        return "unknown"


def _atomic_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp{os.getpid()}")
    with open(tmp, "w") as f:
        json.dump(payload, f, sort_keys=True, separators=(",", ":"), allow_nan=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _load_contract(manifest_path: Path, shard_plan_path: Path) -> tuple[dict, dict]:
    with open(manifest_path) as f:
        campaign = json.load(f)
    with open(shard_plan_path) as f:
        shard_plan = json.load(f)
    if campaign.get("campaign_freeze_sha256") != EXPECTED_CAMPAIGN_FREEZE_SHA256:
        raise ValueError("wrong campaign_freeze_sha256; refusing provenance repair")
    if campaign.get("full_matrix_hash") != EXPECTED_FULL_MATRIX_HASH:
        raise ValueError("wrong full_matrix_hash; refusing provenance repair")
    if campaign.get("n_cells_actual") != EXPECTED_CELL_COUNT:
        raise ValueError(f"campaign manifest does not contain exactly {EXPECTED_CELL_COUNT} cells")
    if shard_plan.get("campaign_manifest_freeze_sha256") != EXPECTED_CAMPAIGN_FREEZE_SHA256:
        raise ValueError("shard plan does not belong to the frozen campaign")
    if shard_plan.get("shard_count") != EXPECTED_SHARD_COUNT:
        raise ValueError(f"shard plan does not contain exactly {EXPECTED_SHARD_COUNT} shards")
    return campaign, shard_plan


def _expected_shard_paths(raw_dir: Path, shard_plan: dict) -> list[tuple[int, Path, list[str]]]:
    out = []
    for shard in shard_plan["shards"]:
        sid = int(shard["shard_id"])
        out.append((sid, raw_dir / f"shard_{sid:03d}.json", list(shard["cell_ids"])))
    return sorted(out)


def _build_raw_ledger(raw_dir: Path, campaign: dict, shard_plan: dict) -> dict:
    entries = []
    total = 0
    for sid, path, expected_ids in _expected_shard_paths(raw_dir, shard_plan):
        if not path.exists():
            raise FileNotFoundError(f"missing raw shard: {path}")
        with open(path) as f:
            rows = json.load(f)
        if not isinstance(rows, dict):
            raise ValueError(f"raw shard {sid} must be a dict keyed by cell_id")
        if set(rows) != set(expected_ids):
            missing = sorted(set(expected_ids) - set(rows))[:5]
            extra = sorted(set(rows) - set(expected_ids))[:5]
            raise ValueError(f"raw shard {sid} membership mismatch: missing={missing}, extra={extra}")
        total += len(rows)
        entries.append({
            "shard_id": sid,
            "original_path": str(path.resolve()),
            "original_sha256": _sha256_file(path),
            "row_count": len(rows),
            "campaign_freeze_sha256": EXPECTED_CAMPAIGN_FREEZE_SHA256,
        })
    if total != EXPECTED_CELL_COUNT:
        raise ValueError(f"raw shards contain {total} rows, expected {EXPECTED_CELL_COUNT}")
    return {
        "manifest_kind": "ranking_portability_phase12_raw_shard_hash_ledger",
        "campaign_freeze_sha256": EXPECTED_CAMPAIGN_FREEZE_SHA256,
        "full_matrix_hash": EXPECTED_FULL_MATRIX_HASH,
        "shard_count": EXPECTED_SHARD_COUNT,
        "total_rows": total,
        "shards": entries,
    }


def _verify_existing_raw_ledger(current: dict, ledger_path: Path) -> None:
    if not ledger_path.exists():
        return
    with open(ledger_path) as f:
        prior = json.load(f)
    # Paths may differ if the ledger is copied between Wulver/local worktrees;
    # immutability is keyed by shard id + SHA + row count + campaign identity.
    def stable(doc):
        return {
            "campaign_freeze_sha256": doc.get("campaign_freeze_sha256"),
            "full_matrix_hash": doc.get("full_matrix_hash"),
            "shard_count": doc.get("shard_count"),
            "total_rows": doc.get("total_rows"),
            "shards": [
                {
                    "shard_id": e["shard_id"],
                    "original_sha256": e["original_sha256"],
                    "row_count": e["row_count"],
                }
                for e in doc.get("shards", [])
            ],
        }
    if stable(current) != stable(prior):
        raise ValueError("raw shard ledger mismatch: raw campaign files changed after ledger creation")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--shard-plan", type=Path, default=DEFAULT_SHARD_PLAN)
    ap.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    ap.add_argument("--enriched-dir", type=Path, default=DEFAULT_ENRICHED_DIR)
    ap.add_argument("--raw-ledger", type=Path, default=DEFAULT_RAW_LEDGER)
    ap.add_argument("--repair-ledger", type=Path, default=DEFAULT_REPAIR_LEDGER)
    ap.add_argument("--consolidated", type=Path, default=DEFAULT_CONSOLIDATED)
    ap.add_argument("--amendment", type=Path, default=DEFAULT_AMENDMENT)
    args = ap.parse_args()

    campaign, shard_plan = _load_contract(args.manifest, args.shard_plan)
    expected_cells = {c["cell_id"]: c for c in campaign["cells"]}
    if len(expected_cells) != EXPECTED_CELL_COUNT:
        raise ValueError("campaign cell IDs are not exactly unique 18,720")

    raw_ledger = _build_raw_ledger(args.raw_dir, campaign, shard_plan)
    _verify_existing_raw_ledger(raw_ledger, args.raw_ledger)
    _atomic_json(args.raw_ledger, raw_ledger)
    raw_ledger_sha = _sha256_file(args.raw_ledger)

    expected_prov = expected_phase12_provenance(campaign)
    amendment_sha = _sha256_file(args.amendment)
    repair_git_sha = _git_sha()

    args.enriched_dir.mkdir(parents=True, exist_ok=True)
    repaired_entries = []
    consolidated_rows_by_id = {}
    non_provenance_differences = 0
    execution_schema_failures = 0
    analysis_admission_failures = 0

    raw_hash_by_sid = {e["shard_id"]: e["original_sha256"] for e in raw_ledger["shards"]}

    for sid, raw_path, expected_ids in _expected_shard_paths(args.raw_dir, shard_plan):
        # Recheck immediately before reading: the source namespace is immutable input.
        before_sha = _sha256_file(raw_path)
        if before_sha != raw_hash_by_sid[sid]:
            raise ValueError(f"raw shard {sid} changed after raw-ledger freeze")
        with open(raw_path) as f:
            raw_rows = json.load(f)

        enriched_rows = {}
        for cell_id in expected_ids:
            raw = raw_rows[cell_id]
            spec = expected_cells[cell_id]
            for field in ("cell_id", "source_family", "window_id", "load_region", "policy_id", "repetition", "synthesis_seed", "scientific_status"):
                if raw.get(field) != spec.get(field):
                    raise ValueError(
                        f"raw row identity mismatch {cell_id} field {field}: "
                        f"raw={raw.get(field)!r}, manifest={spec.get(field)!r}"
                    )
            if raw.get("success") is not True:
                raise ValueError(f"raw scientific row is not successful: {cell_id}")
            execution_problems = validate_cell_result(raw)
            if execution_problems:
                execution_schema_failures += 1
                raise ValueError(f"raw execution schema invalid {cell_id}: {execution_problems}")

            enriched = enrich_row_provenance(raw, expected_prov)
            if masked_non_provenance_view(raw) != masked_non_provenance_view(enriched):
                non_provenance_differences += 1
                raise ValueError(f"non-provenance row changed during enrichment: {cell_id}")
            admission_problems = validate_analysis_admission_row(
                enriched, campaign, expected_execution_repo_sha=EXPECTED_EXECUTION_REPO_SHA
            )
            if admission_problems:
                analysis_admission_failures += 1
                raise ValueError(f"analysis-admission validation failed {cell_id}: {admission_problems}")
            enriched_rows[cell_id] = enriched
            consolidated_rows_by_id[cell_id] = enriched

        enriched_path = args.enriched_dir / f"shard_{sid:03d}.json"
        _atomic_json(enriched_path, enriched_rows)
        after_sha = _sha256_file(raw_path)
        if after_sha != before_sha:
            raise ValueError(f"raw shard {sid} changed while repair was running")
        repaired_entries.append({
            "shard_id": sid,
            "original_sha256": before_sha,
            "repaired_sha256": _sha256_file(enriched_path),
            "row_count": len(enriched_rows),
            "enriched_fields": list(APPROVED_ENRICHMENT_FIELDS),
            "old_values": {field: "" for field in APPROVED_ENRICHMENT_FIELDS if field not in ("phase11_raw_fifo_calibration_sha256", "phase11_region_assignments_sha256")},
            "new_values": dict(expected_prov),
            "reconstruction_source": "frozen Phase-12B campaign manifest + exact Phase-12C runtime configuration contract",
        })

    if len(consolidated_rows_by_id) != EXPECTED_CELL_COUNT:
        raise ValueError(f"enrichment produced {len(consolidated_rows_by_id)} unique rows")

    repair_ledger = {
        "manifest_kind": "ranking_portability_phase12_repaired_shard_hash_ledger",
        "provenance_contract_version": PROVENANCE_CONTRACT_VERSION,
        "campaign_freeze_sha256": EXPECTED_CAMPAIGN_FREEZE_SHA256,
        "full_matrix_hash": EXPECTED_FULL_MATRIX_HASH,
        "raw_shard_ledger_sha256": raw_ledger_sha,
        "provenance_amendment_sha256": amendment_sha,
        "repair_code_git_sha": repair_git_sha,
        "expected_provenance": expected_prov,
        "simulator_config_payload": phase12_simulator_config_payload(),
        "shard_count": len(repaired_entries),
        "total_rows": sum(e["row_count"] for e in repaired_entries),
        "non_provenance_row_differences": non_provenance_differences,
        "execution_schema_failures": execution_schema_failures,
        "analysis_admission_failures": analysis_admission_failures,
        "shards": repaired_entries,
    }
    _atomic_json(args.repair_ledger, repair_ledger)
    repair_ledger_sha = _sha256_file(args.repair_ledger)

    ordered_rows = [consolidated_rows_by_id[c["cell_id"]] for c in campaign["cells"]]
    cells_content_sha = _canonical_sha256(ordered_rows)
    consolidated = {
        "manifest_kind": "ranking_portability_phase12_enriched_consolidated",
        "campaign_freeze_sha256": EXPECTED_CAMPAIGN_FREEZE_SHA256,
        "full_matrix_hash": EXPECTED_FULL_MATRIX_HASH,
        "execution_repo_sha": EXPECTED_EXECUTION_REPO_SHA,
        "raw_shard_ledger_sha256": raw_ledger_sha,
        "provenance_amendment_sha256": amendment_sha,
        "repaired_shard_ledger_sha256": repair_ledger_sha,
        "repair_code_git_sha": repair_git_sha,
        "provenance_contract_version": PROVENANCE_CONTRACT_VERSION,
        "n_cells": len(ordered_rows),
        "cells_content_sha256": cells_content_sha,
        "cells": ordered_rows,
    }
    _atomic_json(args.consolidated, consolidated)

    print(f"campaign_freeze_sha256={EXPECTED_CAMPAIGN_FREEZE_SHA256}")
    print(f"raw_shard_count={len(raw_ledger['shards'])}")
    print(f"enriched_shard_count={len(repaired_entries)}")
    print(f"n_cells={len(ordered_rows)}")
    print(f"NON_PROVENANCE_ROW_DIFFERENCES={non_provenance_differences}")
    print(f"raw_shard_ledger_sha256={raw_ledger_sha}")
    print(f"repaired_shard_ledger_sha256={repair_ledger_sha}")
    print(f"consolidated_cells_content_sha256={cells_content_sha}")
    print(f"consolidated_file_sha256={_sha256_file(args.consolidated)}")
    print(f"simulator_config_hash={expected_prov['simulator_config_hash']}")
    print("PHASE12_PROVENANCE_REPAIR_OUTCOME_INDEPENDENT = YES")
    print("PHASE12_RAW_SCIENTIFIC_RESULTS_UNMODIFIED = YES")


if __name__ == "__main__":
    main()
