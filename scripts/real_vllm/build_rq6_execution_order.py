#!/usr/bin/env python3
"""Build the frozen RQ6 real-vLLM execution order.

Reuses the existing, tested orchestration primitives in
robustbench.real_llm.cell_orchestration (expand_cells_to_run_units,
abba_order) rather than inventing new ordering logic. abba_order already
alternates which scheduler goes first per (workload_family, load_region,
repetition) group -- this script adds one thing on top: a fixed-seed
shuffle of the resulting ABBA *pairs* (not the units within a pair, which
must stay adjacent for the counterbalancing to mean anything), so cells
are not always executed in the same (source, repetition) sequence either.

Cells: the two RQ6 case-selection conditions
(artifacts/manifests/phase12_rq6_case_selection_20260902.json) --
azure_llm_2024::HIGH_PRESSURE, burstgpt::HIGH_PRESSURE (reversal case) and
bailian_qwen::HIGH_PRESSURE (stable control's second leg; its first leg,
azure_llm_2024::HIGH_PRESSURE, is already covered) -- each run under both
policy_a (slai_faithful) and policy_b (vllm_faithful).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from robustbench.real_llm.cell_orchestration import (
    CellKey,
    abba_order,
    expand_cells_to_run_units,
)

SOURCES = ("azure_llm_2024", "burstgpt", "bailian_qwen")
LOAD_REGION = "HIGH_PRESSURE"
POLICIES = ("slai_faithful", "vllm_faithful")
DEFAULT_SEED = 20260902


def build_cells() -> list[CellKey]:
    return [
        CellKey(scheduler=policy, workload_family=source, load_region=LOAD_REGION)
        for source in SOURCES
        for policy in POLICIES
    ]


def seeded_pair_shuffle(ordered_units, seed: int):
    if len(ordered_units) % 2 != 0:
        raise ValueError("abba_order output must be pair-aligned (even length)")
    pairs = [ordered_units[i : i + 2] for i in range(0, len(ordered_units), 2)]
    rng = random.Random(seed)
    indexed = list(enumerate(pairs))
    rng.shuffle(indexed)
    shuffled_pairs = [p for _, p in indexed]
    return [unit for pair in shuffled_pairs for unit in pair]


def build_execution_order(*, repetitions: int, seed: int) -> dict:
    cells = build_cells()
    units = expand_cells_to_run_units(cells, repetitions)
    ordered = abba_order(units)
    ordered = seeded_pair_shuffle(ordered, seed)
    rows = [
        {
            "position": i,
            "run_id": u.run_id(),
            "source": u.cell.workload_family,
            "load_region": u.cell.load_region,
            "policy": u.cell.scheduler,
            "repetition": u.repetition,
        }
        for i, u in enumerate(ordered)
    ]
    return {
        "manifest_kind": "rq6_real_vllm_execution_order_v1",
        "manifest_date": "2026-09-02",
        "n_repetitions": repetitions,
        "seed": seed,
        "sources": list(SOURCES),
        "load_region": LOAD_REGION,
        "policies": list(POLICIES),
        "ordering_method": (
            "robustbench.real_llm.cell_orchestration.abba_order "
            "(policy order alternates by repetition parity within each "
            "source/repetition group), then a fixed-seed shuffle of the "
            "resulting ABBA pairs (pair contents never reordered)"
        ),
        "total_run_units": len(rows),
        "order": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repetitions", type=int, default=10)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    manifest = build_execution_order(repetitions=args.repetitions, seed=args.seed)
    payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(payload)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    print(json.dumps({"out": str(args.out), "sha256": digest, "total_run_units": manifest["total_run_units"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
