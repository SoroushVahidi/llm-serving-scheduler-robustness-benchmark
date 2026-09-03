#!/usr/bin/env python3
"""Future-mode validator for an explicit, supplied completed-campaign artifact."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.ranking_portability.schema import validate_cell_result  # noqa: E402

RESULT_BLIND_ENV = "LSSP_ARTIFACT_REPRO_PREFREEZE_RESULT_BLIND"


def _rows(doc: object) -> list[dict]:
    if isinstance(doc, dict):
        if "cells" in doc and isinstance(doc["cells"], list):
            return doc["cells"]
        if all(isinstance(v, dict) for v in doc.values()):
            return list(doc.values())
    if isinstance(doc, list):
        return doc
    raise ValueError("expected a list, a {'cells': [...]} object, or a {cell_id: row} checkpoint object")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", type=Path)
    ap.add_argument("--allow-partial", action="store_true")
    args = ap.parse_args()

    if os.environ.get(RESULT_BLIND_ENV) != "YES":
        print(f"ERROR: {RESULT_BLIND_ENV}=YES is required.", file=sys.stderr)
        return 2
    if not args.path.exists():
        print(f"ERROR: supplied results path does not exist: {args.path}", file=sys.stderr)
        return 2

    rows = _rows(json.loads(args.path.read_text()))
    campaign = json.loads((REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_campaign_freeze.json").read_text())
    expected_ids = {c["cell_id"] for c in campaign["cells"]}
    observed_ids = {r.get("cell_id") for r in rows}
    problems: list[str] = []
    if None in observed_ids:
        problems.append("at least one row is missing cell_id")
    if len(observed_ids) != len(rows):
        problems.append("duplicate cell_id in supplied artifact")
    if not observed_ids <= expected_ids and not all(str(cid).startswith("toy_") or "::toy_" in str(cid) for cid in observed_ids):
        problems.append("supplied artifact contains cell IDs outside the frozen Phase-12 manifest")
    if not args.allow_partial and observed_ids != expected_ids:
        problems.append(f"supplied artifact is not complete: observed {len(observed_ids)} of {len(expected_ids)} expected cell IDs")
    for row in rows:
        problems.extend(f"{row.get('cell_id')}: {p}" for p in validate_cell_result(row))

    print(f"supplied_results_path={args.path}")
    print(f"rows={len(rows)}")
    print("SCIENTIFIC_CAMPAIGN_EXECUTED = NO")
    if problems:
        print("SUPPLIED_RESULTS_VALID = NO")
        for p in problems[:50]:
            print(f"PROBLEM: {p}")
        return 1
    print("SUPPLIED_RESULTS_VALID = YES")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
