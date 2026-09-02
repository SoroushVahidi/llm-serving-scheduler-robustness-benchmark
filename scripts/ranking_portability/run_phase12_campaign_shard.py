#!/usr/bin/env python3
"""Phase-12C campaign-shard runner. Generalizes the already-validated
Phase-12A smoke execution machinery
(`scripts/ranking_portability/build_phase12_smoke.py`) to run one shard of
the frozen 18,720-cell campaign, with idempotent, crash-safe checkpointing.

Dry-run mode (default): loads the frozen campaign manifest and shard plan,
resolves the requested shard's cell list, validates every cell's
provenance resolves (window identity present, region-assignment entry
present, policy resolves via the registry) WITHOUT synthesizing a single
`Request`, constructing a `Simulator`, or calling `execute_cell`. Computes
(but does not write to) the checkpoint output path.

Execute mode (`--execute`): actually runs the shard's cells through the
real Pilot-V2 execution path (`robustbench.ranking_portability.execute_cell`,
`synthesize_requests_from_window`, `_rebase_and_scale`, `make_policy_any`
-- identical machinery to the Phase-12A smoke, not a new simulator path).

Idempotent checkpoint/resume: the shard's output file is a JSON object
`{cell_id: RankingPortabilityCellResult.to_dict()}`. On start, any existing
checkpoint file is loaded and every entry is INDEPENDENTLY RE-VALIDATED
(schema + telemetry) before being trusted -- an entry that is missing,
that has `success != True`, or that fails re-validation is (re)computed;
a pre-existing invalid row is never silently accepted as done. The
checkpoint file is rewritten after every cell (small JSON, cheap relative
to cell compute time), so a crash mid-shard loses at most one cell's
progress, and a repeated cell_id can never appear twice in the file (it is
a dict keyed by cell_id, not an append-only list).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.calibration.stage0_load_calibration import (  # noqa: E402
    STAGE0_REFERENCE_GPU_CONFIG,
    _rebase_and_scale,
)
from robustbench.policies.registry import make_policy_any  # noqa: E402
from robustbench.ranking_portability.execute_cell import execute_cell  # noqa: E402
from robustbench.ranking_portability.phase12_campaign import (  # noqa: E402
    SCIENTIFIC_STATUS_PILOT_V2_SCIENTIFIC,
)
from robustbench.ranking_portability.schema import validate_cell_result  # noqa: E402
from robustbench.simulator.telemetry import TelemetrySummary, validate_telemetry  # noqa: E402
from robustbench.workloads.external.benchmark_synthesis import (  # noqa: E402
    synthesize_requests_from_window,
)
from robustbench.workloads.external.schema import ExternalWorkloadRecord  # noqa: E402

DEFAULT_MANIFEST = REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_campaign_freeze.json"
DEFAULT_SHARD_PLAN = REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_shard_plan.json"
DEFAULT_FULL_WINDOWS = REPO_ROOT / "artifacts/pilot_v2_windows_full_cache.json"
CAMPAIGN_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "campaign_results"  # disjoint from smoke's output path
SMOKE_OUTPUT_PATH = REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_smoke_raw.json"
EXPECTED_PHASE10_WINDOW_HASH = "0d1aa06ccbee352207327ea369ae75f12e91c0cda006c813a41b381effd29eef"


def _git_sha() -> str:
    import subprocess
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).decode().strip()


def _is_valid_checkpoint_row(row: dict) -> bool:
    """Independently re-validates a checkpoint row (schema + telemetry).
    Never trusts a pre-existing `success: True` at face value."""
    if not isinstance(row, dict) or row.get("success") is not True:
        return False
    if validate_cell_result(row):
        return False
    telemetry = row.get("telemetry")
    if not isinstance(telemetry, dict):
        return False
    try:
        t = TelemetrySummary(**telemetry)
    except TypeError:
        return False
    if validate_telemetry(t):
        return False
    return True


def _output_path(campaign: dict, shard_id: int) -> Path:
    freeze_prefix = campaign["campaign_freeze_sha256"][:16]
    return CAMPAIGN_OUTPUT_ROOT / freeze_prefix / f"shard_{shard_id:03d}.json"


def _load_shard(manifest_path: Path, shard_plan_path: Path, shard_id: int):
    with open(manifest_path) as f:
        campaign = json.load(f)
    with open(shard_plan_path) as f:
        shard_plan = json.load(f)
    if campaign["campaign_freeze_sha256"] != shard_plan["campaign_manifest_freeze_sha256"]:
        raise ValueError(
            "Shard plan was built against a different campaign-freeze identity "
            f"({shard_plan['campaign_manifest_freeze_sha256']}) than the manifest "
            f"currently loaded ({campaign['campaign_freeze_sha256']}). STOPPING."
        )
    if shard_id < 0 or shard_id >= shard_plan["shard_count"]:
        raise ValueError(f"shard_id {shard_id} out of range [0, {shard_plan['shard_count']}).")
    shard = shard_plan["shards"][shard_id]
    assert shard["shard_id"] == shard_id
    cells_by_id = {c["cell_id"]: c for c in campaign["cells"]}
    shard_cells = [cells_by_id[cid] for cid in shard["cell_ids"]]
    return campaign, shard_plan, shard, shard_cells


def _dry_run(campaign: dict, shard: dict, shard_cells: list) -> int:
    window_identities = campaign["window_identities"]
    region_assignment_index = campaign["region_assignment_index"]
    problems = []
    policy_cache: dict[str, bool] = {}
    for c in shard_cells:
        if c["window_id"] not in window_identities:
            problems.append(f"{c['cell_id']}: window_id {c['window_id']} not in campaign window_identities")
        if c["region_assignment_key"] not in region_assignment_index:
            problems.append(f"{c['cell_id']}: region_assignment_key {c['region_assignment_key']} not in campaign region_assignment_index")
        pid = c["policy_id"]
        if pid not in policy_cache:
            try:
                make_policy_any(pid)
                policy_cache[pid] = True
            except Exception as e:  # noqa: BLE001
                policy_cache[pid] = False
                problems.append(f"{c['cell_id']}: policy {pid!r} failed to instantiate: {e}")
        elif not policy_cache[pid]:
            problems.append(f"{c['cell_id']}: policy {pid!r} previously failed to instantiate")

    out_path = _output_path(campaign, shard["shard_id"])
    if out_path.resolve() == SMOKE_OUTPUT_PATH.resolve():
        problems.append("computed campaign output path collides with the Phase-12A smoke output path")

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        writable = out_path.parent.exists() and out_path.parent.is_dir()
    except OSError as e:  # noqa: BLE001
        writable = False
        problems.append(f"output directory not writable: {e}")

    print(f"shard_id={shard['shard_id']}")
    print(f"cell_count={len(shard_cells)}")
    print(f"policy_composition={shard['policy_composition']}")
    print(f"would_write_to={out_path}")
    print(f"output_dir_writable={writable}")
    print(f"n_problems={len(problems)}")
    for p in problems[:10]:
        print(f"PROBLEM: {p}")
    print("DRY_RUN_ONLY = YES (no cell executed, no simulator constructed, no Request synthesized)")
    return 0 if not problems else 1


def _execute(campaign: dict, shard: dict, shard_cells: list, full_windows_path: Path) -> int:
    with open(full_windows_path) as f:
        full_windows = json.load(f)
    if full_windows.get("content_sha256") != EXPECTED_PHASE10_WINDOW_HASH:
        raise ValueError(
            f"Full window manifest content hash mismatch: expected "
            f"{EXPECTED_PHASE10_WINDOW_HASH}, got {full_windows.get('content_sha256')}. STOPPING."
        )
    windows_by_id = {w["window_id"]: w for w in full_windows["windows"]}

    out_path = _output_path(campaign, shard["shard_id"])
    if out_path.resolve() == SMOKE_OUTPUT_PATH.resolve():
        raise ValueError("Computed campaign output path collides with the Phase-12A smoke output path. STOPPING.")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    checkpoint: dict = {}
    if out_path.exists():
        with open(out_path) as f:
            checkpoint = json.load(f)

    n_skipped_valid = 0
    n_rerun_invalid_or_missing = 0
    needed_cell_ids = {c["cell_id"] for c in shard_cells}
    # Idempotence: never let a stale checkpoint row for a cell_id NOT in
    # this shard leak into the rewritten file (defensive; should never
    # happen since this shard's output path is unique to this shard_id).
    checkpoint = {cid: row for cid, row in checkpoint.items() if cid in needed_cell_ids}

    for cid in list(checkpoint.keys()):
        if not _is_valid_checkpoint_row(checkpoint[cid]):
            del checkpoint[cid]

    repo_sha = _git_sha()
    region_assignment_index = campaign["region_assignment_index"]

    # Synthesize base requests once per window, and scaled requests once
    # per (window, region) -- shared identically across policies and both
    # repetitions of that (window, region), never resynthesized per-cell.
    base_requests_cache: dict[str, list] = {}
    scaled_requests_cache: dict[tuple, list] = {}

    n_computed = 0
    for c in shard_cells:
        cid = c["cell_id"]
        if cid in checkpoint:
            n_skipped_valid += 1
            continue
        n_rerun_invalid_or_missing += 1

        window_id = c["window_id"]
        if window_id not in base_requests_cache:
            w = windows_by_id[window_id]
            records = [ExternalWorkloadRecord(**r) for r in w["records"]]
            requests, _synth = synthesize_requests_from_window(
                records, window_id=window_id, seed=c["synthesis_seed"]
            )
            base_requests_cache[window_id] = requests

        scale_key = (window_id, c["load_region"])
        if scale_key not in scaled_requests_cache:
            assignment = region_assignment_index[c["region_assignment_key"]]
            scaled_requests_cache[scale_key] = _rebase_and_scale(
                base_requests_cache[window_id], float(assignment["absolute_load_factor"])
            )

        policy = make_policy_any(c["policy_id"])
        result = execute_cell(
            cell_id=cid,
            source_family=c["source_family"],
            window_id=window_id,
            load_region=c["load_region"],
            load_factor=float(region_assignment_index[c["region_assignment_key"]]["absolute_load_factor"]),
            policy_id=c["policy_id"],
            repetition=c["repetition"],
            synthesis_seed=c["synthesis_seed"],
            repo_sha=repo_sha,
            policy=policy,
            requests=scaled_requests_cache[scale_key],
            gpu_configs=[STAGE0_REFERENCE_GPU_CONFIG],
            scientific_status=SCIENTIFIC_STATUS_PILOT_V2_SCIENTIFIC,
        )
        row = result.to_dict()
        # Only checkpoint as complete if it independently re-validates --
        # a failed cell (success=False) is written too (so its error is
        # visible), but will be retried on the next resume because
        # _is_valid_checkpoint_row rejects it above.
        checkpoint[cid] = row
        n_computed += 1

        # Atomic write: write to a temp file in the same directory, then
        # os.replace (atomic on POSIX) -- a crash/kill mid-write can never
        # leave `out_path` truncated or corrupted; the previous complete
        # checkpoint (or none, on the first cell) is preserved until the
        # new one is fully flushed.
        tmp_path = out_path.with_suffix(out_path.suffix + f".tmp{os.getpid()}")
        with open(tmp_path, "w") as f:
            json.dump(checkpoint, f, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, out_path)

    n_valid_after = sum(1 for row in checkpoint.values() if _is_valid_checkpoint_row(row))
    print(f"shard_id={shard['shard_id']}")
    print(f"cell_count={len(shard_cells)}")
    print(f"skipped_already_valid={n_skipped_valid}")
    print(f"computed_this_run={n_computed}")
    print(f"valid_after_run={n_valid_after}")
    print(f"invalid_or_failed_after_run={len(checkpoint) - n_valid_after}")
    print(f"output_path={out_path}")
    return 0 if n_valid_after == len(shard_cells) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--shard-id", type=int, required=True)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--shard-plan", type=Path, default=DEFAULT_SHARD_PLAN)
    ap.add_argument("--full-windows", type=Path, default=DEFAULT_FULL_WINDOWS)
    ap.add_argument("--dry-run", action="store_true", default=False)
    ap.add_argument("--execute", action="store_true", default=False)
    args = ap.parse_args()

    if args.execute == args.dry_run and args.execute:
        raise ValueError("--execute and --dry-run are mutually exclusive.")
    if not args.execute:
        args.dry_run = True  # default mode when neither/only --dry-run given

    campaign, shard_plan, shard, shard_cells = _load_shard(args.manifest, args.shard_plan, args.shard_id)

    if args.dry_run:
        return _dry_run(campaign, shard, shard_cells)
    return _execute(campaign, shard, shard_cells, args.full_windows)


if __name__ == "__main__":
    sys.exit(main())
