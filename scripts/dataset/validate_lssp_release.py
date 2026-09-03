#!/usr/bin/env python3
"""Standalone public-release validator for the LSSP dataset
(docs/LSSP_DATASET_RELEASE_SCHEMA.md, docs/LSSP_DATASET_RELEASE_CHECKLIST.md).

Validates a release directory's tables against the frozen campaign
identity and the reused scheduler_outcomes row schema. Result-blind: it
checks *structure* (row counts, unique IDs, foreign-key integrity, hashes,
undefined-metric semantics) never scheduler-performance direction, and it
never computes a ranking. If `scheduler_outcomes` rows are present, this
reads them only to check schema/identity conformance -- it deliberately
never inspects which policy "won" any cell.

Exit code 0 iff zero problems.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.dataset.lssp_release_contract import (  # noqa: E402
    LSSP_DATASET_RELEASE_VERSION,
    LSSP_DATASET_TABLES,
    RESULT_DEPENDENT_TABLES,
    STATIC_TABLES_BUILDABLE_PREFREEZE,
    FrozenCampaignIdentity,
    load_frozen_campaign_identity,
    validate_scheduler_outcomes_row,
)

DEFAULT_CAMPAIGN_MANIFEST = (
    REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_campaign_freeze.json"
)


def _load_jsonl_or_json_list(path: Path) -> list[dict]:
    text = path.read_text()
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    data = json.loads(text)
    if isinstance(data, dict) and "rows" in data:
        return data["rows"]
    if isinstance(data, list):
        return data
    raise ValueError(f"{path}: expected a JSON list or {{'rows': [...]}} object")


def validate_workload_windows(rows: list[dict]) -> list[str]:
    problems = []
    if len(rows) != 120:
        problems.append(f"workload_windows: expected 120 rows, got {len(rows)}")
    ids = [r.get("workload_window_id") for r in rows]
    if len(set(ids)) != len(ids):
        problems.append("workload_windows: duplicate workload_window_id values")
    per_source: dict[str, int] = {}
    for r in rows:
        per_source[r.get("source_family")] = per_source.get(r.get("source_family"), 0) + 1
    for src, n in per_source.items():
        if n != 40:
            problems.append(f"workload_windows: source {src!r} has {n} windows, expected 40")
    return problems


def validate_load_region_assignments(
    rows: list[dict], identity: FrozenCampaignIdentity
) -> list[str]:
    problems = []
    if len(rows) != 720:
        problems.append(f"load_region_assignments: expected 720 rows, got {len(rows)}")
    keys = [f'{r.get("source_family")}::{r.get("workload_window_id")}::{r.get("load_region")}'
            for r in rows]
    if len(set(keys)) != len(keys):
        problems.append("load_region_assignments: duplicate (source, window, region) keys")
    missing = identity.region_assignment_keys - set(keys)
    unexpected = set(keys) - identity.region_assignment_keys
    if missing:
        problems.append(f"load_region_assignments: {len(missing)} frozen keys missing")
    if unexpected:
        problems.append(f"load_region_assignments: {len(unexpected)} keys not in the frozen 720")
    for r in rows:
        if not r.get("phase11_region_assignment_hash"):
            problems.append(
                f"load_region_assignments: row for {r.get('workload_window_id')} missing "
                "phase11_region_assignment_hash"
            )
    return problems


def validate_policy_registry(rows: list[dict], identity: FrozenCampaignIdentity) -> list[str]:
    problems = []
    ids = {r.get("policy_id") or r.get("policy") for r in rows}
    if ids != identity.policy_ids:
        problems.append(
            f"policy_registry: {ids} does not exactly match the frozen 13-policy panel "
            f"{identity.policy_ids}"
        )
    return problems


def validate_scheduler_outcomes(
    rows: list[dict], identity: FrozenCampaignIdentity
) -> tuple[list[str], dict]:
    """Structural validation only. Never reads/reports which policy has a
    higher/lower metric value than another -- only whether the row is
    schema/identity-valid."""
    problems: list[str] = []
    seen_ids: set[str] = set()
    duplicates = 0
    for row in rows:
        row_problems = validate_scheduler_outcomes_row(row, identity)
        problems.extend(f"scheduler_outcomes[{row.get('cell_id')}]: {p}" for p in row_problems)
        cid = row.get("cell_id")
        if cid in seen_ids:
            duplicates += 1
            problems.append(f"scheduler_outcomes: duplicate cell_id {cid!r}")
        seen_ids.add(cid)

    missing = identity.cell_ids - seen_ids
    unexpected = seen_ids - identity.cell_ids
    summary = {
        "n_rows": len(rows),
        "n_unique_cell_ids": len(seen_ids),
        "n_duplicates": duplicates,
        "n_missing_vs_frozen_18720": len(missing),
        "n_unexpected_cell_ids": len(unexpected),
        "n_expected": identity.expected_cell_count,
        "matrix_complete": (
            len(missing) == 0
            and len(unexpected) == 0
            and duplicates == 0
            and len(rows) == identity.expected_cell_count
        ),
    }
    if unexpected:
        problems.append(f"scheduler_outcomes: {len(unexpected)} cell_ids not in the frozen matrix")
    return problems, summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--release-dir", type=Path, required=True,
                     help="Directory containing exported table files "
                          "(<table_name>.json or .jsonl per table).")
    ap.add_argument("--campaign-manifest", type=Path, default=DEFAULT_CAMPAIGN_MANIFEST)
    ap.add_argument("--allow-missing-tables", action="store_true",
                     help="Do not fail if result-dependent tables "
                          "(scheduler_outcomes, telemetry) are absent -- "
                          "expected before the campaign completes.")
    args = ap.parse_args()

    identity = load_frozen_campaign_identity(args.campaign_manifest)
    all_problems: list[str] = []
    info: dict = {"dataset_release_version": LSSP_DATASET_RELEASE_VERSION,
                  "campaign_freeze_sha256": identity.campaign_freeze_sha256}

    def _table_path(name: str) -> Path | None:
        for ext in (".json", ".jsonl"):
            p = args.release_dir / f"{name}{ext}"
            if p.exists():
                return p
        return None

    for table in STATIC_TABLES_BUILDABLE_PREFREEZE:
        path = _table_path(table)
        if path is None:
            all_problems.append(f"{table}: missing from release dir {args.release_dir}")
            continue
        rows = _load_jsonl_or_json_list(path)
        if table == "workload_windows":
            all_problems.extend(validate_workload_windows(rows))
        elif table == "load_region_assignments":
            all_problems.extend(validate_load_region_assignments(rows, identity))
        elif table == "policy_registry":
            all_problems.extend(validate_policy_registry(rows, identity))
        info[f"n_{table}_rows"] = len(rows)

    for table in RESULT_DEPENDENT_TABLES:
        path = _table_path(table)
        if path is None:
            if not args.allow_missing_tables:
                all_problems.append(
                    f"{table}: missing (pass --allow-missing-tables if the campaign "
                    "has not completed yet)"
                )
            continue
        if table == "scheduler_outcomes":
            rows = _load_jsonl_or_json_list(path)
            problems, summary = validate_scheduler_outcomes(rows, identity)
            all_problems.extend(problems)
            info["scheduler_outcomes_summary"] = summary

    info["n_problems"] = len(all_problems)
    print(json.dumps(info, indent=2, default=str))
    for p in all_problems:
        print(f"PROBLEM: {p}", file=sys.stderr)

    if all_problems:
        print("LSSP_RELEASE_VALID = NO")
        return 1
    print("LSSP_RELEASE_VALID = YES")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
