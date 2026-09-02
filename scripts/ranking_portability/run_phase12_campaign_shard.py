#!/usr/bin/env python3
"""Phase-12C campaign-shard runner entrypoint. THIS QUERY (Phase-12B) ONLY
EXERCISES `--dry-run` (the default). Real execution (`--execute`) is out
of scope for Phase-12B and is not invoked by anything in this repository
state -- it exists so Phase-12C's launch can reuse a tested entrypoint
rather than improvising one under time pressure.

Dry-run mode (default, and the ONLY mode exercised/tested here):
  - loads the frozen campaign manifest and shard plan
  - resolves the requested shard's cell list
  - validates every cell's provenance resolves (window identity present in
    the manifest, region-assignment entry present, policy name resolves
    via the registry) -- WITHOUT synthesizing a single `Request`,
    constructing a `Simulator`, or calling `execute_cell`
  - computes the output path this shard WOULD write to, in an output
    directory namespaced by `campaign_freeze_sha256` -- structurally
    disjoint from the Phase-12A smoke's output path
    (`artifacts/manifests/ranking_portability_phase12_smoke_raw.json`),
    so a future resumption/checkpoint pass can never mistake smoke output
    for campaign output, or vice versa
  - checks the output directory is writable (creates it if absent) and
    that the frozen inputs are readable
  - prints a summary and exits 0

Execute mode (`--execute`) is guarded by a separate, explicit flag; this
script raises `NotImplementedError` if `--execute` is passed, because the
actual per-cell execution loop (identical in structure to
`build_phase12_smoke.py`'s, generalized to read from the shard plan) is
Phase-12C's task to write and test against a live campaign launch, not to
be silently enabled by a flag no one has reviewed a real run against yet.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.policies.registry import make_policy_any  # noqa: E402

DEFAULT_MANIFEST = REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_campaign_freeze.json"
DEFAULT_SHARD_PLAN = REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_shard_plan.json"
CAMPAIGN_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "campaign_results"  # disjoint from smoke's output path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--shard-id", type=int, required=True)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--shard-plan", type=Path, default=DEFAULT_SHARD_PLAN)
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--execute", action="store_true", default=False,
                     help="NOT IMPLEMENTED in this repository state -- raises NotImplementedError.")
    args = ap.parse_args()

    if args.execute:
        raise NotImplementedError(
            "Real campaign-cell execution is Phase-12C's task. This entrypoint "
            "currently supports --dry-run only, by design -- see this file's "
            "module docstring."
        )

    with open(args.manifest) as f:
        campaign = json.load(f)
    with open(args.shard_plan) as f:
        shard_plan = json.load(f)

    if campaign["campaign_freeze_sha256"] != shard_plan["campaign_manifest_freeze_sha256"]:
        raise ValueError(
            "Shard plan was built against a different campaign-freeze identity "
            f"({shard_plan['campaign_manifest_freeze_sha256']}) than the manifest "
            f"currently loaded ({campaign['campaign_freeze_sha256']}). STOPPING."
        )

    if args.shard_id < 0 or args.shard_id >= shard_plan["shard_count"]:
        raise ValueError(f"shard_id {args.shard_id} out of range [0, {shard_plan['shard_count']}).")

    shard = shard_plan["shards"][args.shard_id]
    assert shard["shard_id"] == args.shard_id

    cells_by_id = {c["cell_id"]: c for c in campaign["cells"]}
    shard_cells = [cells_by_id[cid] for cid in shard["cell_ids"]]

    # --- Validate every cell's provenance resolves, without executing anything. ---
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

    # --- Compute (but do not create real output for) the campaign output path. ---
    out_dir = CAMPAIGN_OUTPUT_ROOT / campaign["campaign_freeze_sha256"][:16]
    out_path = out_dir / f"shard_{args.shard_id:03d}.json"
    smoke_output_path = REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_smoke_raw.json"
    if out_path.resolve() == smoke_output_path.resolve():
        problems.append("computed campaign output path collides with the Phase-12A smoke output path")

    # --- Writability / readability checks (dry-run: create dir only, write nothing). ---
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        writable = out_dir.exists() and out_dir.is_dir()
    except OSError as e:  # noqa: BLE001
        writable = False
        problems.append(f"output directory not writable: {e}")

    readable_inputs = args.manifest.exists() and args.shard_plan.exists()
    if not readable_inputs:
        problems.append("manifest or shard plan path not readable")

    print(f"shard_id={args.shard_id}")
    print(f"cell_count={len(shard_cells)}")
    print(f"policy_composition={shard['policy_composition']}")
    print(f"would_write_to={out_path}")
    print(f"output_dir_writable={writable}")
    print(f"inputs_readable={readable_inputs}")
    print(f"n_problems={len(problems)}")
    for p in problems[:10]:
        print(f"PROBLEM: {p}")
    print("DRY_RUN_ONLY = YES (no cell executed, no simulator constructed, no Request synthesized)")

    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
