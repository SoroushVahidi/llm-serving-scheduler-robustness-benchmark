#!/usr/bin/env python3
"""Independent Phase-12D completed-campaign admission validator.

Validates matrix completeness, frozen-input provenance, metadata-enrichment
integrity, schema/telemetry semantics, and repetition input identity.  It
never ranks policies, compares scheduler performance, or computes any
statistical result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.ranking_portability.phase12_provenance import (  # noqa: E402
    APPROVED_ENRICHMENT_FIELDS,
    expected_phase12_provenance,
    masked_non_provenance_view,
    validate_analysis_admission_row,
)

EXPECTED = {
    "campaign_freeze_sha256": "81fa3d9b48a2241001e6820942d4542dcc5b5e30973ad9d2786e72972494f57a",
    "full_matrix_hash": "832d96d7ff4d5e8843c233a6a4708bbbbc578ef6b65307c37f5ac127c62c1ccf",
    "phase10_window_hash": "0d1aa06ccbee352207327ea369ae75f12e91c0cda006c813a41b381effd29eef",
    "phase10_compact_index_hash": "d78ec1087fedae02174ca093a9860c70468be336ccb1d7e6de756c81ba331e53",
    "phase11_prelaunch_hash": "e2564ea9484190832de50f63173c4b73ae054d6ae7008bb4ff6648c8dc917f7b",
    "phase11_raw_fifo_hash": "201caaf04476ad8737ef6079fc0d6cb4e864601711d0b96c88750a717d8b2a6a",
    "phase11_region_assignment_hash": "9fcb92f9ea1206ce185194527ada35d0e3b91bf4904be7ae23ba9ea997c17574",
    "execution_repo_sha": "2b9a21fb58798292c95980d35d05e53b3c6f14f6",
    "n_cells": 18_720,
    "n_shards": 64,
    "n_sources": 3,
    "n_windows": 120,
    "windows_per_source": 40,
    "n_regions": 6,
    "n_policies": 13,
    "n_reps": 2,
    "n_assignment_keys": 720,
    "n_rep_pairs": 9_360,
}

DEFAULT_MANIFEST = REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_campaign_freeze.json"
DEFAULT_RAW_LEDGER = REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_raw_shard_hashes.json"
DEFAULT_REPAIR_LEDGER = REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_repaired_shard_hashes.json"
DEFAULT_RAW_DIR = REPO_ROOT / "artifacts/campaign_results" / EXPECTED["campaign_freeze_sha256"][:16]
DEFAULT_ENRICHED_DIR = REPO_ROOT / "artifacts/campaign_results_enriched" / EXPECTED["campaign_freeze_sha256"][:16]
DEFAULT_CONSOLIDATED = DEFAULT_ENRICHED_DIR / "consolidated.json"
DEFAULT_ANALYSIS_INPUT = REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_analysis_input.json"
DEFAULT_COMPACT_INDEX = REPO_ROOT / "artifacts/manifests/ranking_portability_pilot_v2_windows_index.json"
DEFAULT_RAW_FIFO = REPO_ROOT / "artifacts/manifests/ranking_portability_phase11_raw_fifo_calibration.json"
DEFAULT_REGION_ASSIGNMENTS = REPO_ROOT / "artifacts/manifests/ranking_portability_phase11_region_assignments.json"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).decode().strip()
    except Exception:
        return "unknown"


def _atomic_json(path: Path, payload) -> None:
    import os
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp{os.getpid()}")
    with open(tmp, "w") as f:
        json.dump(payload, f, sort_keys=True, separators=(",", ":"), allow_nan=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _problem(problems: list[str], message: str) -> None:
    problems.append(message)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--raw-ledger", type=Path, default=DEFAULT_RAW_LEDGER)
    ap.add_argument("--repair-ledger", type=Path, default=DEFAULT_REPAIR_LEDGER)
    ap.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    ap.add_argument("--enriched-dir", type=Path, default=DEFAULT_ENRICHED_DIR)
    ap.add_argument("--consolidated", type=Path, default=DEFAULT_CONSOLIDATED)
    ap.add_argument("--analysis-input", type=Path, default=DEFAULT_ANALYSIS_INPUT)
    ap.add_argument("--compact-index", type=Path, default=DEFAULT_COMPACT_INDEX)
    ap.add_argument("--raw-fifo", type=Path, default=DEFAULT_RAW_FIFO)
    ap.add_argument("--region-assignments", type=Path, default=DEFAULT_REGION_ASSIGNMENTS)
    args = ap.parse_args()

    problems: list[str] = []
    with open(args.manifest) as f:
        campaign = json.load(f)
    with open(args.raw_ledger) as f:
        raw_ledger = json.load(f)
    with open(args.repair_ledger) as f:
        repair_ledger = json.load(f)
    with open(args.consolidated) as f:
        consolidated = json.load(f)

    # Frozen identity checks.
    for key in (
        "campaign_freeze_sha256", "full_matrix_hash", "phase10_window_hash",
        "phase10_compact_index_hash", "phase11_prelaunch_hash",
        "phase11_raw_fifo_hash", "phase11_region_assignment_hash",
    ):
        observed = campaign.get(key)
        if observed != EXPECTED[key]:
            _problem(problems, f"campaign manifest {key} mismatch: {observed}")

    file_hash_checks = {
        "phase10_compact_index_hash": (args.compact_index, EXPECTED["phase10_compact_index_hash"]),
        "phase11_raw_fifo_hash": (args.raw_fifo, EXPECTED["phase11_raw_fifo_hash"]),
        "phase11_region_assignment_hash": (args.region_assignments, EXPECTED["phase11_region_assignment_hash"]),
    }
    for label, (path, expected_hash) in file_hash_checks.items():
        observed = _sha256_file(path) if path.exists() else "MISSING"
        if observed != expected_hash:
            _problem(problems, f"{label} file hash mismatch: expected={expected_hash}, observed={observed}")

    expected_cells = {c["cell_id"]: c for c in campaign.get("cells", [])}
    expected_ids = set(expected_cells)
    if len(expected_cells) != EXPECTED["n_cells"]:
        _problem(problems, f"expected campaign cell count is {len(expected_cells)}")
    if len(campaign.get("region_assignment_index", {})) != EXPECTED["n_assignment_keys"]:
        _problem(problems, "campaign does not contain exactly 720 region assignment keys")

    # Raw/repaired ledger and source immutability.
    if raw_ledger.get("campaign_freeze_sha256") != EXPECTED["campaign_freeze_sha256"]:
        _problem(problems, "raw ledger campaign identity mismatch")
    if repair_ledger.get("campaign_freeze_sha256") != EXPECTED["campaign_freeze_sha256"]:
        _problem(problems, "repair ledger campaign identity mismatch")
    if raw_ledger.get("shard_count") != EXPECTED["n_shards"]:
        _problem(problems, "raw ledger shard count mismatch")
    if repair_ledger.get("shard_count") != EXPECTED["n_shards"]:
        _problem(problems, "repair ledger shard count mismatch")

    raw_entries = {int(e["shard_id"]): e for e in raw_ledger.get("shards", [])}
    repaired_entries = {int(e["shard_id"]): e for e in repair_ledger.get("shards", [])}
    raw_rows_by_id = {}
    enriched_rows_by_id = {}
    non_provenance_differences = 0
    schema_or_provenance_failures = 0

    for sid in range(EXPECTED["n_shards"]):
        raw_path = args.raw_dir / f"shard_{sid:03d}.json"
        enriched_path = args.enriched_dir / f"shard_{sid:03d}.json"
        if not raw_path.exists() or not enriched_path.exists():
            _problem(problems, f"missing raw/enriched shard {sid}")
            continue
        if sid not in raw_entries or sid not in repaired_entries:
            _problem(problems, f"ledger entry missing for shard {sid}")
            continue
        raw_sha = _sha256_file(raw_path)
        enriched_sha = _sha256_file(enriched_path)
        if raw_sha != raw_entries[sid].get("original_sha256"):
            _problem(problems, f"raw shard {sid} changed after ledger freeze")
        if raw_sha != repaired_entries[sid].get("original_sha256"):
            _problem(problems, f"repair ledger original hash mismatch for shard {sid}")
        if enriched_sha != repaired_entries[sid].get("repaired_sha256"):
            _problem(problems, f"repaired shard hash mismatch for shard {sid}")

        with open(raw_path) as f:
            raw_rows = json.load(f)
        with open(enriched_path) as f:
            enriched_rows = json.load(f)
        if set(raw_rows) != set(enriched_rows):
            _problem(problems, f"raw/enriched membership differs for shard {sid}")
            continue
        for cid in raw_rows:
            raw = raw_rows[cid]
            enriched = enriched_rows[cid]
            if masked_non_provenance_view(raw) != masked_non_provenance_view(enriched):
                non_provenance_differences += 1
                _problem(problems, f"non-provenance difference: {cid}")
            admission = validate_analysis_admission_row(
                enriched, campaign, expected_execution_repo_sha=EXPECTED["execution_repo_sha"]
            )
            if admission:
                schema_or_provenance_failures += 1
                _problem(problems, f"analysis-admission invalid {cid}: {admission}")
            raw_rows_by_id[cid] = raw
            enriched_rows_by_id[cid] = enriched

    actual_ids = set(enriched_rows_by_id)
    missing_ids = expected_ids - actual_ids
    unexpected_ids = actual_ids - expected_ids
    duplicate_count = EXPECTED["n_cells"] - len(actual_ids) if len(actual_ids) < EXPECTED["n_cells"] else 0
    if missing_ids:
        _problem(problems, f"missing cells: {len(missing_ids)}")
    if unexpected_ids:
        _problem(problems, f"unexpected cells: {len(unexpected_ids)}")
    if len(actual_ids) != EXPECTED["n_cells"]:
        _problem(problems, f"actual unique cell count={len(actual_ids)}, expected={EXPECTED['n_cells']}")

    # Exact matrix dimensions and load-assignment agreement.
    sources = {r.get("source_family") for r in enriched_rows_by_id.values()}
    windows = {r.get("window_id") for r in enriched_rows_by_id.values()}
    regions = {r.get("load_region") for r in enriched_rows_by_id.values()}
    policies = {r.get("policy_id") for r in enriched_rows_by_id.values()}
    reps = {r.get("repetition") for r in enriched_rows_by_id.values()}
    if len(sources) != EXPECTED["n_sources"]: _problem(problems, f"source count={len(sources)}")
    if len(windows) != EXPECTED["n_windows"]: _problem(problems, f"window count={len(windows)}")
    if len(regions) != EXPECTED["n_regions"]: _problem(problems, f"region count={len(regions)}")
    if len(policies) != EXPECTED["n_policies"]: _problem(problems, f"policy count={len(policies)}")
    if reps != {0, 1}: _problem(problems, f"repetition set={reps}")
    windows_by_source = Counter((r.get("source_family"), r.get("window_id")) for r in enriched_rows_by_id.values())
    unique_windows_by_source = Counter(source for source, _wid in windows_by_source)
    for source in sources:
        if unique_windows_by_source[source] != EXPECTED["windows_per_source"]:
            _problem(problems, f"{source} unique windows={unique_windows_by_source[source]}")

    successful = 0
    load_mismatches = 0
    for cid, row in enriched_rows_by_id.items():
        if row.get("success") is True:
            successful += 1
        spec = expected_cells.get(cid)
        if spec is None:
            continue
        assignment = campaign["region_assignment_index"][spec["region_assignment_key"]]
        if row.get("load_factor") != assignment["absolute_load_factor"]:
            load_mismatches += 1
            _problem(problems, f"load assignment mismatch: {cid}")
    if successful != EXPECTED["n_cells"]:
        _problem(problems, f"successful cells={successful}")

    # Rep0/rep1 scientific-input identity only; no metric/output comparison.
    rep_groups = {}
    rep_input_mismatches = 0
    input_fields = (
        "source_family", "window_id", "load_region", "load_factor", "policy_id",
        "synthesis_seed", "window_manifest_sha256", "calibration_manifest_sha256",
        "policy_registry_hash", "simulator_config_hash", "synthesis_version",
        "phase11_raw_fifo_calibration_sha256", "phase11_region_assignments_sha256",
        "scientific_status",
    )
    for row in enriched_rows_by_id.values():
        key = (row["source_family"], row["window_id"], row["load_region"], row["policy_id"])
        rep_groups.setdefault(key, {})[row["repetition"]] = row
    if len(rep_groups) != EXPECTED["n_rep_pairs"]:
        _problem(problems, f"rep-pair groups={len(rep_groups)}")
    for key, pair in rep_groups.items():
        if set(pair) != {0, 1}:
            rep_input_mismatches += 1
            _problem(problems, f"missing repetition in group: {key}")
            continue
        if any(pair[0].get(f) != pair[1].get(f) for f in input_fields):
            rep_input_mismatches += 1
            _problem(problems, f"rep scientific-input mismatch: {key}")

    # Consolidated artifact must be exactly the same enriched rows in frozen order.
    if consolidated.get("campaign_freeze_sha256") != EXPECTED["campaign_freeze_sha256"]:
        _problem(problems, "consolidated campaign identity mismatch")
    consolidated_cells = consolidated.get("cells", [])
    if len(consolidated_cells) != EXPECTED["n_cells"]:
        _problem(problems, f"consolidated cell count={len(consolidated_cells)}")
    else:
        for spec, row in zip(campaign["cells"], consolidated_cells):
            expected_row = enriched_rows_by_id.get(spec["cell_id"])
            if expected_row != row:
                _problem(problems, f"consolidated row differs from enriched shard: {spec['cell_id']}")
                break

    expected_prov = expected_phase12_provenance(campaign)
    if repair_ledger.get("expected_provenance") != expected_prov:
        _problem(problems, "repair ledger provenance contract differs from independent reconstruction")

    valid = len(problems) == 0
    report = {
        "campaign_freeze_sha256": EXPECTED["campaign_freeze_sha256"],
        "full_matrix_hash": EXPECTED["full_matrix_hash"],
        "expected_cells": EXPECTED["n_cells"],
        "actual_unique_cells": len(actual_ids),
        "missing_cells": len(missing_ids),
        "unexpected_cells": len(unexpected_ids),
        "duplicate_cells": duplicate_count,
        "successful_cells": successful,
        "unresolved_failures": EXPECTED["n_cells"] - successful,
        "sources": len(sources),
        "windows": len(windows),
        "regions": len(regions),
        "policies": len(policies),
        "repetitions": sorted(reps),
        "assignment_keys": len(campaign.get("region_assignment_index", {})),
        "load_assignment_mismatches": load_mismatches,
        "rep_pair_groups": len(rep_groups),
        "rep_scientific_input_mismatches": rep_input_mismatches,
        "schema_or_provenance_failures": schema_or_provenance_failures,
        "non_provenance_row_differences": non_provenance_differences,
        "raw_shard_ledger_sha256": _sha256_file(args.raw_ledger),
        "repaired_shard_ledger_sha256": _sha256_file(args.repair_ledger),
        "consolidated_artifact_sha256": _sha256_file(args.consolidated),
        "validator_sha256": _sha256_file(Path(__file__)),
        "problems": problems[:100],
        "PHASE12_COMPLETED_CAMPAIGN_VALID": valid,
        "PHASE12_ANALYSIS_INPUT_ADMITTED": valid,
    }

    if valid:
        analysis_input = {
            "manifest_kind": "ranking_portability_phase12_analysis_input",
            "campaign_freeze_sha256": EXPECTED["campaign_freeze_sha256"],
            "full_matrix_hash": EXPECTED["full_matrix_hash"],
            "raw_shard_ledger_sha256": report["raw_shard_ledger_sha256"],
            "provenance_amendment_sha256": repair_ledger["provenance_amendment_sha256"],
            "repaired_shard_ledger_sha256": report["repaired_shard_ledger_sha256"],
            "consolidated_artifact_sha256": report["consolidated_artifact_sha256"],
            "completed_matrix_validator_sha256": report["validator_sha256"],
            "validation_git_sha": _git_sha(),
            "execution_repo_sha": EXPECTED["execution_repo_sha"],
            "cell_count": EXPECTED["n_cells"],
            "PHASE12_COMPLETED_CAMPAIGN_VALID": True,
            "PHASE12_ANALYSIS_INPUT_ADMITTED": True,
            "COMPARATIVE_PILOT_V2_RESULTS": "NONE",
        }
        _atomic_json(args.analysis_input, analysis_input)

    print(json.dumps(report, indent=2, sort_keys=True))
    if not valid:
        sys.exit(1)


if __name__ == "__main__":
    main()
