#!/usr/bin/env python3
"""Freeze the Phase-12 campaign shard plan. Reuses Stage-0's proven
cost-aware longest-processing-time-first (LPT) shard balancer
(`scripts/stage0/stage0_harness.py::shard_cells`) verbatim -- no new
balancing algorithm is written. DOES NOT EXECUTE ANY CELL; only partitions
the already-frozen 18,720 cell IDs into shards.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

# Import shard_cells directly from the Stage-0 harness module by path,
# without importing the rest of that script's CLI machinery.
_spec = importlib.util.spec_from_file_location(
    "stage0_harness", REPO_ROOT / "scripts" / "stage0" / "stage0_harness.py"
)
_stage0_harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_stage0_harness)
shard_cells = _stage0_harness.shard_cells

DEFAULT_MANIFEST = REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_campaign_freeze.json"
DEFAULT_OUT = REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_shard_plan.json"

# Per-policy cost estimates (seconds/cell), from
# docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md's "Compute options" table,
# itself sourced from Stage-0's real measured per-cell costs
# (~18-20s/cell for FAITHFUL_EXTERNAL policies with real block-manager
# simulation, ~0.1-0.6s/cell for the rest). Midpoints used; not tuned
# against any scheduler-performance outcome -- these are wall-clock cost
# estimates only, never used to filter, reorder, or select which cells run.
FAITHFUL_EXTERNAL_POLICIES = {
    "vllm_faithful", "vllm_chunked_prefill_faithful", "sarathi_faithful", "slai_faithful",
}
COST_ESTIMATES_SECONDS = {
    "fifo": 0.35, "edf": 0.35, "least_laxity_first": 0.35,
    "estimated_service_time_first": 0.35, "weighted_fair_share": 0.35,
    "kv_constrained_online": 0.35, "admission_control": 0.35,
    "vllm_style_token_budget": 0.35, "scorpio_style_slo_guard": 0.35,
    "vllm_faithful": 19.0, "vllm_chunked_prefill_faithful": 19.0,
    "sarathi_faithful": 19.0, "slai_faithful": 19.0,
}
SHARD_COUNT = 64  # practical, deterministic; see freeze doc for rationale


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--shard-count", type=int, default=SHARD_COUNT)
    args = ap.parse_args()

    with open(args.manifest) as f:
        campaign = json.load(f)
    all_cells = campaign["cells"]

    assert set(COST_ESTIMATES_SECONDS.keys()) == set(campaign["campaign_policies"]), (
        "cost-estimate table policy set does not match the frozen campaign policy panel"
    )

    shards = []
    all_assigned_ids: list[str] = []
    shard_loads = []
    for shard_index in range(args.shard_count):
        shard = shard_cells(all_cells, shard_index, args.shard_count, cost_estimates=COST_ESTIMATES_SECONDS)
        cell_ids = [c["cell_id"] for c in shard]
        policy_counts: dict[str, int] = {}
        est_cost = 0.0
        for c in shard:
            policy_counts[c["policy_id"]] = policy_counts.get(c["policy_id"], 0) + 1
            est_cost += COST_ESTIMATES_SECONDS[c["policy_id"]]
        shards.append({
            "shard_id": shard_index,
            "cell_ids": cell_ids,
            "cell_count": len(cell_ids),
            "estimated_cost_seconds": est_cost,
            "policy_composition": policy_counts,
        })
        all_assigned_ids.extend(cell_ids)
        shard_loads.append(est_cost)

    # --- Verify coverage before writing anything ---
    all_expected_ids = {c["cell_id"] for c in all_cells}
    if len(all_assigned_ids) != len(set(all_assigned_ids)):
        raise ValueError("Shard plan produced duplicate cell_ids across shards. STOPPING.")
    if set(all_assigned_ids) != all_expected_ids:
        missing = all_expected_ids - set(all_assigned_ids)
        extra = set(all_assigned_ids) - all_expected_ids
        raise ValueError(f"Shard plan coverage mismatch: missing={len(missing)} extra={len(extra)}. STOPPING.")

    # --- Determinism check: rebuild once more, require identical membership ---
    rebuild_ids_by_shard = []
    for shard_index in range(args.shard_count):
        shard = shard_cells(all_cells, shard_index, args.shard_count, cost_estimates=COST_ESTIMATES_SECONDS)
        rebuild_ids_by_shard.append([c["cell_id"] for c in shard])
    for i, shard in enumerate(shards):
        if rebuild_ids_by_shard[i] != shard["cell_ids"]:
            raise ValueError(f"Shard {i} membership is not deterministic across rebuilds. STOPPING.")

    plan = {
        "manifest_kind": "ranking_portability_phase12_shard_plan",
        "campaign_manifest_full_matrix_hash": campaign["full_matrix_hash"],
        "campaign_manifest_freeze_sha256": campaign["campaign_freeze_sha256"],
        "shard_count": args.shard_count,
        "balancing_rule": "stage0_harness.shard_cells (greedy longest-processing-time-first bin-packing, deterministic, stable-sorted by cell_id on ties)",
        "cost_estimates_seconds": COST_ESTIMATES_SECONDS,
        "total_cells": len(all_cells),
        "total_estimated_cost_seconds": sum(shard_loads),
        "min_shard_estimated_cost_seconds": min(shard_loads),
        "max_shard_estimated_cost_seconds": max(shard_loads),
        "estimated_imbalance_ratio": max(shard_loads) / min(shard_loads) if min(shard_loads) > 0 else None,
        "shards": shards,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(plan, f, indent=2, sort_keys=True)

    print(f"shard_count={args.shard_count}")
    print(f"total_cells={len(all_cells)}")
    print(f"total_estimated_cost_hours={sum(shard_loads)/3600:.2f}")
    print(f"min/max shard estimated cost (s)={min(shard_loads):.1f}/{max(shard_loads):.1f}")
    print(f"estimated_imbalance_ratio={plan['estimated_imbalance_ratio']:.3f}")
    print(f"out_sha256={_sha256_file(args.out)}")


if __name__ == "__main__":
    main()
