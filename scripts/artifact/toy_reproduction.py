#!/usr/bin/env python3
"""Fabricated, result-blind toy artifact path for reviewer smoke tests."""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.ranking_portability.schema import validate_cell_result  # noqa: E402
from robustbench.simulator.telemetry import TelemetrySummary, validate_telemetry  # noqa: E402

RESULT_BLIND_ENV = "LSSP_ARTIFACT_REPRO_PREFREEZE_RESULT_BLIND"
FIXTURE_FLAG = "SYNTHETIC_FIXTURE_NOT_SCIENTIFIC_EVIDENCE"
POLICIES = ("toy_fifo", "toy_kv_aware", "toy_slo_guard")
REGIONS = ("LOW", "OVERLOAD")
SOURCES = ("toy_source_a", "toy_source_b")
WINDOWS = ("w0", "w1")


def _telemetry(*, kv: float, queue: int = 2) -> dict:
    return {
        "schema_version": "ranking_portability_telemetry_v1",
        "queue_depth_mean": float(queue) / 2.0,
        "queue_depth_max": queue,
        "batch_saturation_mean": 0.5,
        "batch_saturation_max": 0.75,
        "prefill_decode_contention_fraction": 0.25,
        "kv_occupancy_mean": kv / 2.0,
        "kv_occupancy_max": kv,
        "admission_control_activations": 1 if kv > 1.0 else 0,
        "preemption_or_reorder_events": 1 if queue > 3 else 0,
        "token_budget_saturation_fraction": 0.4,
        "n_steps": 8,
    }


def _row(source: str, window: str, region: str, policy: str, rep: int) -> dict:
    base = {
        "toy_fifo": {"LOW": 0.91, "OVERLOAD": 0.42},
        "toy_kv_aware": {"LOW": 0.76, "OVERLOAD": 0.71},
        "toy_slo_guard": {"LOW": 0.64, "OVERLOAD": 0.52},
    }[policy][region]
    wiggle = 0.01 if rep == 1 else 0.0
    value = base + wiggle
    zero_completion = source == "toy_source_b" and window == "w1" and region == "OVERLOAD" and policy == "toy_fifo"
    completion = 0.0 if zero_completion else min(1.0, max(0.0, value))
    conditional = math.nan if zero_completion else 1.0 - completion
    cell_id = f"{source}::{window}::{region}::{policy}::rep{rep}"
    return {
        "schema_version": "ranking_portability_cell_result_v1",
        "cell_id": cell_id,
        "source_family": source,
        "window_id": window,
        "load_region": region,
        "load_factor": 0.5 if region == "LOW" else 1.2,
        "policy_id": policy,
        "repetition": rep,
        "synthesis_seed": 7000 + rep,
        "arrival_normalized_weighted_goodput": 0.0 if zero_completion else value,
        "completion_fraction": completion,
        "weighted_completion_fraction": completion,
        "slo_violation_rate": conditional,
        "weighted_goodput": math.nan if zero_completion else value * 10.0,
        "mean_latency": math.nan if zero_completion else 10.0 / max(value, 0.01),
        "p95_latency": math.nan if zero_completion else 18.0 / max(value, 0.01),
        "mean_ttft": math.nan if policy == "toy_slo_guard" and region == "LOW" else 2.0,
        "p95_ttft": math.nan if policy == "toy_slo_guard" and region == "LOW" else 3.0,
        "request_throughput": math.nan if zero_completion else value * 100.0,
        "token_throughput": math.nan if zero_completion else value * 1000.0,
        "telemetry_schema_version": "ranking_portability_telemetry_v1",
        "telemetry": _telemetry(kv=1.35 if policy == "toy_fifo" and region == "OVERLOAD" else 0.8, queue=5 if region == "OVERLOAD" else 2),
        "repo_sha": "SYNTHETIC_FIXTURE",
        "window_manifest_sha256": "SYNTHETIC_FIXTURE",
        "calibration_manifest_sha256": "SYNTHETIC_FIXTURE",
        "policy_registry_hash": "SYNTHETIC_FIXTURE",
        "simulator_config_hash": "SYNTHETIC_FIXTURE",
        "synthesis_version": "synthetic_artifact_fixture_v1",
        "environment": {FIXTURE_FLAG: "YES"},
        "success": True,
        "error_category": None,
        "error_detail": None,
        "scientific_status": "SYNTHETIC_FIXTURE_ONLY",
    }


def build_rows() -> list[dict]:
    return [
        _row(source, window, region, policy, rep)
        for source in SOURCES
        for window in WINDOWS
        for region in REGIONS
        for policy in POLICIES
        for rep in (0, 1)
    ]


def validate_rows(rows: list[dict]) -> list[str]:
    problems: list[str] = []
    expected = len(SOURCES) * len(WINDOWS) * len(REGIONS) * len(POLICIES) * 2
    if len(rows) != expected:
        problems.append(f"row count {len(rows)} != expected {expected}")
    seen = set()
    for row in rows:
        cid = row.get("cell_id")
        if cid in seen:
            problems.append(f"duplicate cell_id: {cid}")
        seen.add(cid)
        if row.get("environment", {}).get(FIXTURE_FLAG) != "YES":
            problems.append(f"{cid}: missing synthetic fixture flag")
        if row.get("scientific_status") != "SYNTHETIC_FIXTURE_ONLY":
            problems.append(f"{cid}: not labeled SYNTHETIC_FIXTURE_ONLY")
        problems.extend(f"{cid}: {p}" for p in validate_cell_result(row))
        try:
            telemetry = TelemetrySummary(**row["telemetry"])
        except TypeError as e:
            problems.append(f"{cid}: bad telemetry: {e}")
        else:
            problems.extend(f"{cid}: telemetry.{p}" for p in validate_telemetry(telemetry))
    if not any(r["completion_fraction"] == 0.0 for r in rows):
        problems.append("fixture missing zero-completion case")
    if not any(math.isnan(r["mean_ttft"]) for r in rows):
        problems.append("fixture missing undefined conditional TTFT case")
    if not any(r["telemetry"]["kv_occupancy_max"] > 1.0 for r in rows):
        problems.append("fixture missing normalized KV demand > 1")
    return problems


def rankings(rows: list[dict]) -> list[dict]:
    values: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rows:
        values[(row["load_region"], row["policy_id"])].append(row["arrival_normalized_weighted_goodput"])
    out = []
    for region in REGIONS:
        means = [
            {
                "load_region": region,
                "policy_id": policy,
                "mean_arrival_normalized_weighted_goodput": sum(values[(region, policy)]) / len(values[(region, policy)]),
            }
            for policy in POLICIES
        ]
        means.sort(key=lambda r: (-r["mean_arrival_normalized_weighted_goodput"], r["policy_id"]))
        for rank, row in enumerate(means, start=1):
            out.append({"rank": rank, **row})
    if out[0]["policy_id"] == [r for r in out if r["load_region"] == "OVERLOAD" and r["rank"] == 1][0]["policy_id"]:
        raise ValueError("toy fixture failed to produce the intended ranking change")
    return out


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-dir", type=Path, default=REPO_ROOT / "artifacts/generated/toy_reproduction")
    args = ap.parse_args()

    if os.environ.get(RESULT_BLIND_ENV) != "YES":
        print(f"ERROR: {RESULT_BLIND_ENV}=YES is required.", file=sys.stderr)
        return 2

    rows = build_rows()
    problems = validate_rows(rows)
    if problems:
        for p in problems:
            print(f"PROBLEM: {p}")
        print("TOY_REPRODUCTION_PASS = NO")
        return 1

    ranks = rankings(rows)
    out = args.output_dir
    package = out / "dataset_package"
    package.mkdir(parents=True, exist_ok=True)
    (out / "synthetic_cells.json").write_text(json.dumps(rows, indent=2, sort_keys=True, allow_nan=True) + "\n")
    (out / "consolidated_cells.json").write_text(json.dumps({"cells": rows}, indent=2, sort_keys=True, allow_nan=True) + "\n")
    (out / "analysis_fixture_rankings.json").write_text(json.dumps(ranks, indent=2, sort_keys=True) + "\n")
    write_csv(package / "policy_outcomes.csv", rows, ["cell_id", "source_family", "window_id", "load_region", "policy_id", "repetition", "arrival_normalized_weighted_goodput", "completion_fraction", "weighted_completion_fraction"])
    write_csv(package / "rankings.csv", ranks, ["load_region", "rank", "policy_id", "mean_arrival_normalized_weighted_goodput"])
    (package / "metadata.json").write_text(json.dumps({
        FIXTURE_FLAG: "YES",
        "scientific_evidence": False,
        "rows": len(rows),
        "policies": list(POLICIES),
        "regions": list(REGIONS),
        "sources": list(SOURCES),
        "contains_zero_completion_case": True,
        "contains_undefined_conditional_metric_case": True,
        "contains_normalized_kv_demand_above_one": True,
        "contains_deliberate_ranking_change": True,
    }, indent=2, sort_keys=True) + "\n")
    print(f"toy_output_dir={out}")
    print(f"toy_rows={len(rows)}")
    print(f"{FIXTURE_FLAG} = YES")
    print("TOY_REPRODUCTION_PASS = YES")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
