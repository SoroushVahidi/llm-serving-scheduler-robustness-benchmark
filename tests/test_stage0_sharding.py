"""Regression test: cost-aware shard balancing must be far more balanced
than naive stride slicing when per-policy cost varies wildly -- found
while sizing the real Stage-0 launch (vllm_faithful measured ~100x slower
than the other 5 policies)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("stage0_harness", REPO_ROOT / "scripts" / "stage0" / "stage0_harness.py")
stage0_harness = importlib.util.module_from_spec(spec)
sys.path.insert(0, str(REPO_ROOT / "src"))
spec.loader.exec_module(stage0_harness)

shard_cells = stage0_harness.shard_cells


def _skewed_cells(n_cheap=900, n_expensive=180):
    """Mimics expand_cell_grid's real ordering: policy cycles fastest within
    each (window,region) block -- here, 5 cheap cells then 1 expensive cell,
    repeated."""
    cheap = [{"cell_id": f"cheap_{i}", "policy_id": "fifo"} for i in range(n_cheap)]
    expensive = [{"cell_id": f"expensive_{i}", "policy_id": "vllm_faithful"} for i in range(n_expensive)]
    out = []
    ci = ei = 0
    while ci < len(cheap) or ei < len(expensive):
        for _ in range(5):
            if ci < len(cheap):
                out.append(cheap[ci])
                ci += 1
        if ei < len(expensive):
            out.append(expensive[ei])
            ei += 1
    return out


COST = {"fifo": 0.1, "vllm_faithful": 18.0}


def test_naive_stride_can_be_badly_imbalanced_on_skewed_costs():
    cells = _skewed_cells()
    N = 6
    loads = []
    for i in range(N):
        shard = shard_cells(cells, i, N, cost_estimates=None)  # stride fallback
        loads.append(sum(COST[c["policy_id"]] for c in shard))
    # Demonstrates the problem this fix addresses -- not asserting a specific
    # ratio (that's the point of the fix below), just that imbalance CAN happen.
    assert max(loads) / max(min(loads), 1e-9) > 5


def test_cost_aware_sharding_is_well_balanced():
    cells = _skewed_cells()
    N = 6
    loads = []
    all_assigned = []
    for i in range(N):
        shard = shard_cells(cells, i, N, cost_estimates=COST)
        loads.append(sum(COST[c["policy_id"]] for c in shard))
        all_assigned.extend(shard)
    assert max(loads) / min(loads) < 1.15, loads  # within 15% of each other
    # No cell lost or duplicated across shards.
    assert sorted(c["cell_id"] for c in all_assigned) == sorted(c["cell_id"] for c in cells)


def test_cost_aware_sharding_deterministic():
    cells = _skewed_cells()
    shard_a = shard_cells(cells, 2, 6, cost_estimates=COST)
    shard_b = shard_cells(cells, 2, 6, cost_estimates=COST)
    assert [c["cell_id"] for c in shard_a] == [c["cell_id"] for c in shard_b]


def test_shard_count_one_returns_everything():
    cells = _skewed_cells()
    assert shard_cells(cells, 0, 1, cost_estimates=COST) == cells
