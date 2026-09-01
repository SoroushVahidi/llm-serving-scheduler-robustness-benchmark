#!/usr/bin/env python3
"""Stage-0 orchestration harness CLI (section B).

Subcommands: plan | run | status | validate

    plan     expand the canonical cell grid from the frozen windows +
             load-calibration manifests, write stage0_plan.json (the cell
             list + its hash) -- does not execute anything.
    run      execute cells from an existing plan, optionally sharded by
             --shard-index/--shard-count (for a SLURM array). Skips cells
             that already have a valid result file (resumable/idempotent).
             Writes one result file per cell, atomically.
    status   summarize completed/failed/pending cells against the plan.
    validate compares the completed result set against the plan: exact
             expected cell count, no missing, no duplicate, no extra.

Output layout under --output-dir:
    stage0_plan.json
    cells/<cell_id_safe>.json   (one per executed cell)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.stage0.cell import CellSpec, expand_cell_grid  # noqa: E402
from robustbench.stage0.runner import execute_cell  # noqa: E402
from robustbench.stage0.schema import validate_cell_result  # noqa: E402


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).decode().strip()
    except Exception:
        return "unknown"


def _sha256_file(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_text(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode()).hexdigest()


def _cell_file_slug(cell_id: str) -> str:
    return cell_id.replace("::", "__") + ".json"


def _policy_registry_hash() -> str:
    from robustbench.stage0.cell import STAGE0_POLICIES
    return _sha256_text(json.dumps(sorted(STAGE0_POLICIES)))


def _load_manifests(windows_path: Path, calibration_path: Path):
    with open(windows_path) as f:
        windows_manifest = json.load(f)
    with open(calibration_path) as f:
        calibration_manifest = json.load(f)
    return windows_manifest, calibration_manifest


def cmd_plan(args: argparse.Namespace) -> None:
    windows_path = Path(args.windows_manifest)
    calibration_path = Path(args.calibration_manifest)
    windows_manifest, calibration_manifest = _load_manifests(windows_path, calibration_path)
    cells = expand_cell_grid(windows_manifest, calibration_manifest)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    plan = {
        "plan_kind": "stage0_cell_plan",
        "repo_sha": _git_sha(),
        "window_manifest_sha256": _sha256_file(windows_path),
        "calibration_manifest_sha256": _sha256_file(calibration_path),
        "policy_registry_hash": _policy_registry_hash(),
        "n_cells": len(cells),
        "cells": [c.to_dict() for c in cells],
    }
    plan_path = out_dir / "stage0_plan.json"
    with open(plan_path, "w") as f:
        json.dump(plan, f, indent=2)
    plan_hash = _sha256_file(plan_path)
    print(f"wrote {plan_path}: {len(cells)} cells, plan_sha256={plan_hash}", file=sys.stderr)
    print(json.dumps({"n_cells": len(cells), "plan_sha256": plan_hash}))


def _load_plan(out_dir: Path) -> dict:
    with open(out_dir / "stage0_plan.json") as f:
        return json.load(f)


def cmd_run(args: argparse.Namespace) -> None:
    out_dir = Path(args.output_dir)
    plan = _load_plan(out_dir)
    windows_manifest, _ = _load_manifests(Path(args.windows_manifest), Path(args.calibration_manifest))
    records_by_window = {w["window_id"]: w["records"] for w in windows_manifest["windows"]}

    cells_dir = out_dir / "cells"
    cells_dir.mkdir(parents=True, exist_ok=True)

    all_cells = plan["cells"]
    shard = all_cells[args.shard_index::args.shard_count] if args.shard_count > 1 else all_cells

    n_run, n_skipped, n_failed = 0, 0, 0
    for cd in shard:
        result_path = cells_dir / _cell_file_slug(cd["cell_id"])
        if result_path.exists() and not args.force:
            try:
                with open(result_path) as f:
                    existing = json.load(f)
                if existing.get("success") and not validate_cell_result(existing):
                    n_skipped += 1
                    continue
            except (json.JSONDecodeError, OSError):
                pass  # corrupt/partial file -- fall through and recompute

        spec = CellSpec(
            source_family=cd["source_family"], window_id=cd["window_id"],
            load_region=cd["load_region"], load_factor=cd["load_factor"],
            policy_id=cd["policy_id"], repetition=cd["repetition"],
            synthesis_seed=cd["synthesis_seed"], scenario_config_hash=cd["scenario_config_hash"],
        )
        assert spec.cell_id == cd["cell_id"], "plan/spec cell_id mismatch -- plan corruption"

        result = execute_cell(
            spec, window_records=records_by_window[spec.window_id],
            repo_sha=plan["repo_sha"], window_manifest_sha256=plan["window_manifest_sha256"],
            calibration_manifest_sha256=plan["calibration_manifest_sha256"],
            policy_registry_hash=plan["policy_registry_hash"],
        )
        n_run += 1
        if not result.success:
            n_failed += 1

        # Atomic write: temp file + rename (POSIX rename is atomic on the
        # same filesystem) -- a partial write can never be mistaken for a
        # valid completed cell.
        tmp_path = result_path.with_suffix(".json.tmp")
        with open(tmp_path, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        tmp_path.rename(result_path)

    print(f"shard {args.shard_index}/{args.shard_count}: ran={n_run} skipped={n_skipped} failed={n_failed}",
          file=sys.stderr)
    print(json.dumps({"ran": n_run, "skipped": n_skipped, "failed": n_failed}))


def cmd_status(args: argparse.Namespace) -> None:
    out_dir = Path(args.output_dir)
    plan = _load_plan(out_dir)
    cells_dir = out_dir / "cells"
    expected_ids = {c["cell_id"] for c in plan["cells"]}

    done_success, done_failed, missing = [], [], []
    for cell_id in expected_ids:
        p = cells_dir / _cell_file_slug(cell_id)
        if not p.exists():
            missing.append(cell_id)
            continue
        try:
            with open(p) as f:
                d = json.load(f)
        except (json.JSONDecodeError, OSError):
            missing.append(cell_id)
            continue
        (done_success if d.get("success") else done_failed).append(cell_id)

    summary = {
        "n_expected": len(expected_ids), "n_success": len(done_success),
        "n_failed": len(done_failed), "n_missing_or_pending": len(missing),
        "failed_cell_ids": sorted(done_failed)[:20],
    }
    print(json.dumps(summary, indent=2))


def cmd_validate(args: argparse.Namespace) -> None:
    out_dir = Path(args.output_dir)
    plan = _load_plan(out_dir)
    cells_dir = out_dir / "cells"
    expected = {c["cell_id"]: c["canonical_hash"] for c in plan["cells"]}

    problems = []
    seen_hashes = set()
    n_success = 0
    for cell_id, expected_hash in expected.items():
        p = cells_dir / _cell_file_slug(cell_id)
        if not p.exists():
            problems.append(f"MISSING: {cell_id}")
            continue
        with open(p) as f:
            d = json.load(f)
        if d.get("canonical_hash") != expected_hash:
            problems.append(f"HASH_MISMATCH: {cell_id}")
        if d.get("canonical_hash") in seen_hashes:
            problems.append(f"DUPLICATE_HASH: {cell_id}")
        seen_hashes.add(d.get("canonical_hash"))
        schema_problems = validate_cell_result(d)
        if schema_problems:
            problems.append(f"SCHEMA_INVALID: {cell_id}: {'; '.join(schema_problems)}")
        elif d.get("success"):
            n_success += 1

    extra_files = [p.name for p in cells_dir.glob("*.json")
                   if p.stem.replace("__", "::") not in expected] if cells_dir.exists() else []
    for f in extra_files:
        problems.append(f"UNEXPECTED_FILE: {f}")

    result = {
        "n_expected": len(expected), "n_success": n_success,
        "n_problems": len(problems), "problems": problems[:50],
        "matrix_complete_and_clean": len(problems) == 0 and n_success == len(expected),
    }
    print(json.dumps(result, indent=2))
    if not result["matrix_complete_and_clean"]:
        sys.exit(1)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)

    common = dict(required=True)
    for name, fn in [("plan", cmd_plan), ("run", cmd_run), ("status", cmd_status), ("validate", cmd_validate)]:
        p = sub.add_parser(name)
        p.add_argument("--output-dir", **common)
        if name in ("plan", "run"):
            p.add_argument("--windows-manifest", **common)
            p.add_argument("--calibration-manifest", **common)
        if name == "run":
            p.add_argument("--shard-index", type=int, default=0)
            p.add_argument("--shard-count", type=int, default=1)
            p.add_argument("--force", action="store_true")
        p.set_defaults(func=fn)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
