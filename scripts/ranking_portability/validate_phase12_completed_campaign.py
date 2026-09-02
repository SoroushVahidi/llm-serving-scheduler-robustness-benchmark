#!/usr/bin/env python3
"""Independent Phase-12D completed-campaign admission validator.

Reconstructs the frozen scientific matrix and load mapping independently from
canonical Phase-10/11 inputs, then validates metadata-enriched Phase-12C rows.
It never ranks policies, compares scheduler performance, or computes any
statistical result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.ranking_portability.phase12_campaign import (  # noqa: E402
    CAMPAIGN_POLICIES,
    CAMPAIGN_REGIONS,
    CAMPAIGN_REPETITIONS,
    CAMPAIGN_SOURCES,
    generate_campaign_cell_specs,
    load_campaign_window_ids,
    synthesis_seed_for_window,
)
from robustbench.ranking_portability.phase12_provenance import (  # noqa: E402
    expected_phase12_provenance,
    masked_non_provenance_hash,
    validate_analysis_admission_row,
)
from robustbench.ranking_portability.schema import validate_cell_result  # noqa: E402

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
DEFAULT_SHARD_PLAN = REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_shard_plan.json"
DEFAULT_RAW_LEDGER = REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_raw_shard_hashes.json"
DEFAULT_REPAIR_LEDGER = REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_repaired_shard_hashes.json"
DEFAULT_RAW_DIR = REPO_ROOT / "artifacts/campaign_results" / EXPECTED["campaign_freeze_sha256"][:16]
DEFAULT_ENRICHED_DIR = REPO_ROOT / "artifacts/campaign_results_enriched" / EXPECTED["campaign_freeze_sha256"][:16]
DEFAULT_CONSOLIDATED = DEFAULT_ENRICHED_DIR / "consolidated.json"
DEFAULT_ANALYSIS_INPUT = REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_analysis_input.json"
DEFAULT_COMPACT_INDEX = REPO_ROOT / "artifacts/manifests/ranking_portability_pilot_v2_windows_index.json"
DEFAULT_RAW_FIFO = REPO_ROOT / "artifacts/manifests/ranking_portability_phase11_raw_fifo_calibration.json"
DEFAULT_REGION_ASSIGNMENTS = REPO_ROOT / "artifacts/manifests/ranking_portability_phase11_region_assignments.json"
DEFAULT_PHASE11_PREFREEZE = REPO_ROOT / "docs/RANKING_PORTABILITY_PHASE11_PRELAUNCH_FREEZE.md"
DEFAULT_FULL_WINDOW_MANIFEST = Path(
    "/mmfs1/project/ikoutis/sv96/github/llm-serving-scheduler-ranking-portability-windows/"
    "artifacts/manifests/ranking_portability_pilot_v2_windows.json"
)
PHASE11_FREEZE_FINALIZATION_COMMIT = "6e2c02fc46b287a5f741c0907475c92c9e33fc87"
PHASE11_PRELAUNCH_DOC_REL = "docs/RANKING_PORTABILITY_PHASE11_PRELAUNCH_FREEZE.md"
PHASE11_PRELAUNCH_AGGREGATE_LABEL = "aggregate prelaunch-freeze SHA-256"
PHASE11_PRELAUNCH_CONSTITUENT_LABELS = (
    ("branch_sha", "branch SHA"),
    ("phase10_window_hash", "Phase-10 window hash"),
    ("compact_window_index_hash", "compact index hash"),
    ("calibration_impl_hash", "calibration implementation hash"),
    ("build_script_hash", "build script hash"),
    ("calibration_plan_hash", "calibration plan hash"),
    ("candidate_factor_grid_hash", "candidate factor grid hash"),
    ("six_region_definition_hash", "six-region definition hash"),
    ("fifo_policy_hash", "FIFO policy implementation hash"),
    ("simulator_implementation_hash", "simulator implementation/config hash"),
    ("validator_schema_hash", "validator/schema hash"),
)
PHASE11_PRELAUNCH_CROSS_BINDINGS = (
    (
        "phase11_calibration_freeze_document",
        REPO_ROOT / "docs/RANKING_PORTABILITY_PHASE11_CALIBRATION_FREEZE.md",
        "Phase-11 prelaunch freeze hash",
    ),
    (
        "phase12_campaign_prelaunch_freeze_document",
        REPO_ROOT / "docs/RANKING_PORTABILITY_PHASE12_CAMPAIGN_PRELAUNCH_FREEZE.md",
        "Phase-11 prelaunch freeze",
    ),
    (
        "artifact_hash_ledger",
        REPO_ROOT / "docs/ARTIFACT_HASH_LEDGER.md",
        "Phase-11 prelaunch freeze",
    ),
    (
        "canonical_handoff",
        REPO_ROOT / "docs/CANONICAL_HANDOFF.md",
        "Phase-11 prelaunch freeze contract",
    ),
    (
        "project_status",
        REPO_ROOT / "docs/PROJECT_STATUS.md",
        "Phase-11 prelaunch freeze hash",
    ),
)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_sha256(payload) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).decode().strip()
    except Exception:
        return "unknown"


def _git_commit_exists(commit: str) -> bool:
    return subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def _git_file_bytes(commit: str, relpath: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{relpath}"], cwd=REPO_ROOT)


def _atomic_json(path: Path, payload) -> None:
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


def _load_json(path: Path):
    with open(path) as f:
        return json.load(f)


def _extract_labeled_sha256(text: str, label: str) -> str:
    for line in text.splitlines():
        if label in line:
            match = re.search(r"`([0-9a-f]{40}|[0-9a-f]{64})`", line)
            if match:
                return match.group(1)
    raise ValueError(f"could not find SHA-256 for label: {label}")


def _phase11_prelaunch_payload_from_text(text: str) -> dict[str, str]:
    return {
        key: _extract_labeled_sha256(text, label)
        for key, label in PHASE11_PRELAUNCH_CONSTITUENT_LABELS
    }


def _phase11_prelaunch_aggregate_from_text(text: str) -> str:
    return _canonical_sha256(_phase11_prelaunch_payload_from_text(text))


def _file_artifact_identity_checks(
    compact_index: Path,
    raw_fifo: Path,
    region_assignments: Path,
) -> dict[str, str]:
    return {
        "phase10_compact_index_hash": _sha256_file(compact_index),
        "phase11_raw_fifo_hash": _sha256_file(raw_fifo),
        "phase11_region_assignment_hash": _sha256_file(region_assignments),
    }


def _verify_phase11_prelaunch_contract(
    phase11_prelaunch: Path,
    campaign: Mapping,
    problems: list[str],
    *,
    cross_bindings: Sequence[tuple[str, Path, str]] = PHASE11_PRELAUNCH_CROSS_BINDINGS,
) -> dict[str, object]:
    expected = EXPECTED["phase11_prelaunch_hash"]
    info: dict[str, object] = {
        "phase11_prelaunch_finalization_commit": PHASE11_FREEZE_FINALIZATION_COMMIT,
        "PHASE11_PRELAUNCH_IDENTITY_IS_AGGREGATE_CONTRACT_HASH": True,
    }

    if not _git_commit_exists(PHASE11_FREEZE_FINALIZATION_COMMIT):
        _problem(problems, f"Phase-11 finalization commit missing: {PHASE11_FREEZE_FINALIZATION_COMMIT}")
        historical_bytes = b""
    else:
        try:
            historical_bytes = _git_file_bytes(PHASE11_FREEZE_FINALIZATION_COMMIT, PHASE11_PRELAUNCH_DOC_REL)
        except subprocess.CalledProcessError as exc:
            _problem(problems, f"Phase-11 finalized prelaunch document missing from git history: {exc}")
            historical_bytes = b""

    current_bytes = phase11_prelaunch.read_bytes() if phase11_prelaunch.exists() else b""
    if not current_bytes:
        _problem(problems, f"Phase-11 prelaunch document missing: {phase11_prelaunch}")

    info["phase11_prelaunch_document_file_sha256"] = _sha256_bytes(current_bytes)
    info["phase11_prelaunch_historical_document_file_sha256"] = _sha256_bytes(historical_bytes)
    info["phase11_prelaunch_document_matches_finalization_commit"] = bool(
        current_bytes and historical_bytes and current_bytes == historical_bytes
    )
    if current_bytes and historical_bytes and current_bytes != historical_bytes:
        _problem(problems, "Phase-11 prelaunch document differs from finalization commit")

    historical_text = historical_bytes.decode("utf-8") if historical_bytes else ""
    current_text = current_bytes.decode("utf-8") if current_bytes else ""
    try:
        aggregate_identity = _extract_labeled_sha256(historical_text, PHASE11_PRELAUNCH_AGGREGATE_LABEL)
    except ValueError as exc:
        aggregate_identity = "MISSING"
        _problem(problems, str(exc))
    info["phase11_prelaunch_contract_identity"] = aggregate_identity
    if aggregate_identity != expected:
        _problem(problems, f"Phase-11 prelaunch aggregate identity mismatch: expected={expected}, observed={aggregate_identity}")

    if current_text:
        try:
            current_identity = _extract_labeled_sha256(current_text, PHASE11_PRELAUNCH_AGGREGATE_LABEL)
        except ValueError as exc:
            current_identity = "MISSING"
            _problem(problems, str(exc))
        if current_identity != expected:
            _problem(problems, f"current Phase-11 prelaunch aggregate identity mismatch: {current_identity}")

    try:
        recomputed_aggregate = _phase11_prelaunch_aggregate_from_text(historical_text)
    except ValueError as exc:
        recomputed_aggregate = "UNAVAILABLE"
        _problem(problems, str(exc))
    info["phase11_prelaunch_recomputed_aggregate_sha256"] = recomputed_aggregate
    if recomputed_aggregate != expected:
        _problem(problems, f"Phase-11 prelaunch aggregate reconstruction mismatch: expected={expected}, observed={recomputed_aggregate}")

    bindings = {
        "phase11_finalized_prelaunch_document": aggregate_identity,
        "phase12_campaign_manifest": campaign.get("phase11_prelaunch_hash"),
    }
    for name, path, label in cross_bindings:
        try:
            bindings[name] = _extract_labeled_sha256(path.read_text(), label)
        except (OSError, ValueError) as exc:
            bindings[name] = "MISSING"
            _problem(problems, f"Phase-11 prelaunch cross-binding unavailable in {name}: {exc}")
    info["phase11_prelaunch_cross_bindings"] = bindings
    for name, observed in bindings.items():
        if observed != expected:
            _problem(problems, f"Phase-11 prelaunch cross-binding mismatch: {name}: {observed}")
    return info


def _independent_expected_cells(compact_index: dict, campaign: dict) -> dict[str, dict]:
    window_ids_by_source = load_campaign_window_ids(compact_index)
    specs = generate_campaign_cell_specs(window_ids_by_source)
    out = {}
    for spec in specs:
        key = f"{spec.source_family}::{spec.window_id}::{spec.load_region}"
        out[spec.cell_id] = {
            "cell_id": spec.cell_id,
            "source_family": spec.source_family,
            "window_id": spec.window_id,
            "load_region": spec.load_region,
            "policy_id": spec.policy_id,
            "repetition": spec.repetition,
            "synthesis_seed": synthesis_seed_for_window(spec.window_id),
            "region_assignment_key": key,
            "scientific_status": "PILOT_V2_SCIENTIFIC",
        }
    return out


def _independent_region_index(assign_doc: dict, expected_cell_specs: dict[str, dict]) -> dict[str, dict]:
    expected_keys = {c["region_assignment_key"] for c in expected_cell_specs.values()}
    rows = {}
    for a in assign_doc["assignments"]:
        key = f"{a['source']}::{a['window_id']}::{a['region']}"
        if key in expected_keys:
            rows[key] = {
                "lambda_ref": float(a["lambda_ref"]),
                "selected_load_factor": float(a["selected_load_factor"]),
                "absolute_load_factor": float(a["lambda_ref"]) * float(a["selected_load_factor"]),
            }
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--shard-plan", type=Path, default=DEFAULT_SHARD_PLAN)
    ap.add_argument("--raw-ledger", type=Path, default=DEFAULT_RAW_LEDGER)
    ap.add_argument("--repair-ledger", type=Path, default=DEFAULT_REPAIR_LEDGER)
    ap.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    ap.add_argument("--enriched-dir", type=Path, default=DEFAULT_ENRICHED_DIR)
    ap.add_argument("--consolidated", type=Path, default=DEFAULT_CONSOLIDATED)
    ap.add_argument("--analysis-input", type=Path, default=DEFAULT_ANALYSIS_INPUT)
    ap.add_argument("--compact-index", type=Path, default=DEFAULT_COMPACT_INDEX)
    ap.add_argument("--full-window-manifest", type=Path, default=DEFAULT_FULL_WINDOW_MANIFEST)
    ap.add_argument("--phase11-prelaunch", type=Path, default=DEFAULT_PHASE11_PREFREEZE)
    ap.add_argument("--raw-fifo", type=Path, default=DEFAULT_RAW_FIFO)
    ap.add_argument("--region-assignments", type=Path, default=DEFAULT_REGION_ASSIGNMENTS)
    args = ap.parse_args()

    problems: list[str] = []
    campaign = _load_json(args.manifest)
    shard_plan = _load_json(args.shard_plan)
    raw_ledger = _load_json(args.raw_ledger)
    repair_ledger = _load_json(args.repair_ledger)
    consolidated = _load_json(args.consolidated)
    compact_index = _load_json(args.compact_index)
    assign_doc = _load_json(args.region_assignments)

    # ---- Five immutable scientific identities, independently rechecked. ----
    phase11_prelaunch_info = _verify_phase11_prelaunch_contract(args.phase11_prelaunch, campaign, problems)
    immutable_checks = _file_artifact_identity_checks(
        args.compact_index,
        args.raw_fifo,
        args.region_assignments,
    )
    if not args.full_window_manifest.exists():
        _problem(problems, f"full Phase-10 materialized manifest missing: {args.full_window_manifest}")
        observed_phase10_window = "MISSING"
    else:
        full_window_doc = _load_json(args.full_window_manifest)
        observed_phase10_window = full_window_doc.get("content_sha256")
    immutable_checks["phase10_window_hash"] = observed_phase10_window

    for key, observed in immutable_checks.items():
        if observed != EXPECTED[key]:
            _problem(problems, f"immutable {key} mismatch: expected={EXPECTED[key]}, observed={observed}")
        if campaign.get(key) != EXPECTED[key]:
            _problem(problems, f"campaign manifest embedded {key} mismatch: {campaign.get(key)}")

    if campaign.get("campaign_freeze_sha256") != EXPECTED["campaign_freeze_sha256"]:
        _problem(problems, "campaign_freeze_sha256 mismatch")
    if campaign.get("full_matrix_hash") != EXPECTED["full_matrix_hash"]:
        _problem(problems, "campaign full_matrix_hash field mismatch")

    # Recompute every frozen execution source-file hash on this repair branch.
    # Phase-12D changes only new repair files/status docs, never these frozen files.
    execution_hash_mismatches = 0
    for rel, expected_hash in campaign.get("execution_file_hashes", {}).items():
        path = REPO_ROOT / rel
        observed = _sha256_file(path) if path.exists() else "MISSING"
        if observed != expected_hash:
            execution_hash_mismatches += 1
            _problem(problems, f"frozen execution file hash mismatch: {rel}: {observed}")

    # ---- Independently reconstruct windows, cell Cartesian product and load mapping. ----
    independent_window_identities = {
        w["window_id"]: w["content_sha256"]
        for w in compact_index["windows"]
        if w["source_family"] in CAMPAIGN_SOURCES
    }
    if independent_window_identities != campaign.get("window_identities", {}):
        _problem(problems, "campaign window_identities differ from compact-index reconstruction")

    independent_cells = _independent_expected_cells(compact_index, campaign)
    if len(independent_cells) != EXPECTED["n_cells"]:
        _problem(problems, f"independent cell count={len(independent_cells)}")
    campaign_cells_by_id = {c["cell_id"]: c for c in campaign.get("cells", [])}
    if set(campaign_cells_by_id) != set(independent_cells):
        _problem(problems, "campaign cell IDs differ from independently reconstructed Cartesian product")
    else:
        for cid, expected_spec in independent_cells.items():
            observed_spec = campaign_cells_by_id[cid]
            for field, value in expected_spec.items():
                if observed_spec.get(field) != value:
                    _problem(problems, f"campaign cell-spec mismatch {cid} field {field}")
                    break

    independent_region_index = _independent_region_index(assign_doc, independent_cells)
    if len(independent_region_index) != EXPECTED["n_assignment_keys"]:
        _problem(problems, f"independent region-assignment key count={len(independent_region_index)}")
    if independent_region_index != campaign.get("region_assignment_index", {}):
        _problem(problems, "campaign region_assignment_index differs from Phase-11 artifact reconstruction")

    recomputed_matrix_hash = _canonical_sha256({
        "window_identities": independent_window_identities,
        "region_assignment_index": independent_region_index,
        "cells": [campaign_cells_by_id[c["cell_id"]] for c in campaign.get("cells", [])],
    }) if set(campaign_cells_by_id) == set(independent_cells) else "UNAVAILABLE"
    if recomputed_matrix_hash != EXPECTED["full_matrix_hash"]:
        _problem(problems, f"independently recomputed full_matrix_hash={recomputed_matrix_hash}")

    # ---- Frozen shard plan and raw/repaired ledgers. ----
    if shard_plan.get("campaign_manifest_freeze_sha256") != EXPECTED["campaign_freeze_sha256"]:
        _problem(problems, "shard-plan campaign identity mismatch")
    if shard_plan.get("shard_count") != EXPECTED["n_shards"]:
        _problem(problems, f"shard-plan shard_count={shard_plan.get('shard_count')}")
    if raw_ledger.get("campaign_freeze_sha256") != EXPECTED["campaign_freeze_sha256"]:
        _problem(problems, "raw-ledger campaign identity mismatch")
    if repair_ledger.get("campaign_freeze_sha256") != EXPECTED["campaign_freeze_sha256"]:
        _problem(problems, "repair-ledger campaign identity mismatch")

    raw_entries = {int(e["shard_id"]): e for e in raw_ledger.get("shards", [])}
    repaired_entries = {int(e["shard_id"]): e for e in repair_ledger.get("shards", [])}
    plan_shards = {int(s["shard_id"]): s for s in shard_plan.get("shards", [])}
    if set(plan_shards) != set(range(EXPECTED["n_shards"])):
        _problem(problems, "shard plan does not contain exact IDs 0..63")

    enriched_rows_by_id: dict[str, dict] = {}
    seen_raw_ids: set[str] = set()
    duplicate_raw_ids = 0
    non_provenance_differences = 0
    execution_schema_failures = 0
    telemetry_failures = 0
    provenance_failures = 0
    raw_shard_hash_drift = 0

    for sid in range(EXPECTED["n_shards"]):
        raw_path = args.raw_dir / f"shard_{sid:03d}.json"
        enriched_path = args.enriched_dir / f"shard_{sid:03d}.json"
        if not raw_path.exists() or not enriched_path.exists():
            _problem(problems, f"missing raw/enriched shard {sid}")
            continue
        if sid not in raw_entries or sid not in repaired_entries or sid not in plan_shards:
            _problem(problems, f"ledger/plan entry missing for shard {sid}")
            continue

        raw_sha = _sha256_file(raw_path)
        enriched_sha = _sha256_file(enriched_path)
        if raw_sha != raw_entries[sid].get("original_sha256"):
            raw_shard_hash_drift += 1
            _problem(problems, f"raw shard {sid} changed after ledger freeze")
        if raw_sha != repaired_entries[sid].get("original_sha256"):
            _problem(problems, f"repair ledger original hash mismatch for shard {sid}")
        if enriched_sha != repaired_entries[sid].get("repaired_sha256"):
            _problem(problems, f"repaired shard hash mismatch for shard {sid}")

        raw_rows = _load_json(raw_path)
        enriched_rows = _load_json(enriched_path)
        expected_shard_ids = set(plan_shards[sid]["cell_ids"])
        if set(raw_rows) != expected_shard_ids:
            _problem(problems, f"raw shard {sid} membership differs from frozen shard plan")
        if set(enriched_rows) != expected_shard_ids:
            _problem(problems, f"enriched shard {sid} membership differs from frozen shard plan")

        for cid in raw_rows:
            if cid in seen_raw_ids:
                duplicate_raw_ids += 1
                _problem(problems, f"duplicate raw cell across shards: {cid}")
            seen_raw_ids.add(cid)
            raw = raw_rows[cid]
            enriched = enriched_rows.get(cid)
            if enriched is None:
                continue
            if masked_non_provenance_hash(raw) != masked_non_provenance_hash(enriched):
                non_provenance_differences += 1
                _problem(problems, f"non-provenance difference: {cid}")

            schema_problems = validate_cell_result(enriched)
            if schema_problems:
                execution_schema_failures += 1
                if any("telemetry" in p.lower() for p in schema_problems):
                    telemetry_failures += 1
                _problem(problems, f"enriched execution-schema invalid {cid}: {schema_problems}")
            admission = validate_analysis_admission_row(
                enriched, campaign, expected_execution_repo_sha=EXPECTED["execution_repo_sha"]
            )
            provenance_only = [p for p in admission if p not in schema_problems]
            if provenance_only:
                provenance_failures += 1
                _problem(problems, f"analysis provenance invalid {cid}: {provenance_only}")
            enriched_rows_by_id[cid] = enriched

    actual_ids = set(enriched_rows_by_id)
    independent_ids = set(independent_cells)
    missing_ids = independent_ids - actual_ids
    unexpected_ids = actual_ids - independent_ids
    if missing_ids:
        _problem(problems, f"missing cells: {len(missing_ids)}")
    if unexpected_ids:
        _problem(problems, f"unexpected cells: {len(unexpected_ids)}")
    if duplicate_raw_ids:
        _problem(problems, f"duplicate raw IDs across shards: {duplicate_raw_ids}")

    # ---- Dimensions, exact load factor and success state. ----
    sources = {r.get("source_family") for r in enriched_rows_by_id.values()}
    windows = {r.get("window_id") for r in enriched_rows_by_id.values()}
    regions = {r.get("load_region") for r in enriched_rows_by_id.values()}
    policies = {r.get("policy_id") for r in enriched_rows_by_id.values()}
    reps = {r.get("repetition") for r in enriched_rows_by_id.values()}
    dimension_expectations = {
        "sources": (len(sources), EXPECTED["n_sources"]),
        "windows": (len(windows), EXPECTED["n_windows"]),
        "regions": (len(regions), EXPECTED["n_regions"]),
        "policies": (len(policies), EXPECTED["n_policies"]),
        "reps": (len(reps), EXPECTED["n_reps"]),
    }
    for label, (observed, expected) in dimension_expectations.items():
        if observed != expected:
            _problem(problems, f"{label}={observed}, expected={expected}")
    if sources != set(CAMPAIGN_SOURCES): _problem(problems, f"source set mismatch: {sources}")
    if regions != set(CAMPAIGN_REGIONS): _problem(problems, f"region set mismatch: {regions}")
    if policies != set(CAMPAIGN_POLICIES): _problem(problems, f"policy set mismatch: {policies}")
    if reps != set(CAMPAIGN_REPETITIONS): _problem(problems, f"rep set mismatch: {reps}")

    unique_windows_by_source = Counter()
    for source in CAMPAIGN_SOURCES:
        ws = {r["window_id"] for r in enriched_rows_by_id.values() if r.get("source_family") == source}
        unique_windows_by_source[source] = len(ws)
        if len(ws) != EXPECTED["windows_per_source"]:
            _problem(problems, f"{source} unique windows={len(ws)}")

    successful = 0
    load_mismatches = 0
    for cid, row in enriched_rows_by_id.items():
        if row.get("success") is True:
            successful += 1
        spec = independent_cells.get(cid)
        if spec is None:
            continue
        assignment = independent_region_index[spec["region_assignment_key"]]
        if row.get("load_factor") != assignment["absolute_load_factor"]:
            load_mismatches += 1
            _problem(problems, f"load assignment mismatch: {cid}")
    if successful != EXPECTED["n_cells"]:
        _problem(problems, f"successful cells={successful}")

    # ---- Rep0/rep1 scientific-input identity only; no output comparison. ----
    rep_groups: dict[tuple, dict[int, dict]] = {}
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

    # ---- Consolidated artifact identity. ----
    if consolidated.get("campaign_freeze_sha256") != EXPECTED["campaign_freeze_sha256"]:
        _problem(problems, "consolidated campaign identity mismatch")
    consolidated_cells = consolidated.get("cells", [])
    if len(consolidated_cells) != EXPECTED["n_cells"]:
        _problem(problems, f"consolidated cell count={len(consolidated_cells)}")
    else:
        expected_prov = expected_phase12_provenance(campaign)
        for frozen_spec, row in zip(campaign["cells"], consolidated_cells):
            expected_row = enriched_rows_by_id.get(frozen_spec["cell_id"])
            if expected_row is None:
                _problem(problems, f"consolidated row has no enriched source: {frozen_spec['cell_id']}")
                break
            if masked_non_provenance_hash(expected_row) != masked_non_provenance_hash(row):
                _problem(problems, f"consolidated scientific row differs from enriched shard: {frozen_spec['cell_id']}")
                break
            if any(row.get(field) != value for field, value in expected_prov.items()):
                _problem(problems, f"consolidated provenance differs from expected: {frozen_spec['cell_id']}")
                break

    expected_prov = expected_phase12_provenance(campaign)
    if repair_ledger.get("expected_provenance") != expected_prov:
        _problem(problems, "repair ledger provenance contract differs from independent reconstruction")

    valid = len(problems) == 0
    report = {
        "campaign_freeze_sha256": EXPECTED["campaign_freeze_sha256"],
        "full_matrix_hash": EXPECTED["full_matrix_hash"],
        "independently_recomputed_full_matrix_hash": recomputed_matrix_hash,
        "expected_cells": EXPECTED["n_cells"],
        "actual_unique_cells": len(actual_ids),
        "missing_cells": len(missing_ids),
        "unexpected_cells": len(unexpected_ids),
        "duplicate_cells_across_shards": duplicate_raw_ids,
        "successful_cells": successful,
        "unresolved_failures": EXPECTED["n_cells"] - successful,
        "sources": len(sources),
        "windows": len(windows),
        "windows_per_source": dict(unique_windows_by_source),
        "regions": len(regions),
        "policies": len(policies),
        "repetitions": sorted(reps),
        "assignment_keys": len(independent_region_index),
        "load_assignment_mismatches": load_mismatches,
        "rep_pair_groups": len(rep_groups),
        "rep_scientific_input_mismatches": rep_input_mismatches,
        "execution_schema_failures": execution_schema_failures,
        "telemetry_failures": telemetry_failures,
        "conditional_metric_semantic_violations": execution_schema_failures,
        "analysis_provenance_failures": provenance_failures,
        "non_provenance_row_differences": non_provenance_differences,
        "frozen_execution_file_hash_mismatches": execution_hash_mismatches,
        "raw_shard_hash_drift": raw_shard_hash_drift,
        "raw_shard_ledger_sha256": _sha256_file(args.raw_ledger),
        "repaired_shard_ledger_sha256": _sha256_file(args.repair_ledger),
        "consolidated_artifact_sha256": _sha256_file(args.consolidated),
        "validator_sha256": _sha256_file(Path(__file__)),
        "problems": problems[:100],
        "PHASE12_COMPLETED_CAMPAIGN_VALID": valid,
        "PHASE12_ANALYSIS_INPUT_ADMITTED": valid,
    }
    report.update(phase11_prelaunch_info)

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
