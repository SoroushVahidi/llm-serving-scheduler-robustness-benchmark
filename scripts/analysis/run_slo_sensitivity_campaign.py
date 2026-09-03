#!/usr/bin/env python3
"""POST_PHASE12_SLO_DEFINITION_SENSITIVITY_EXTENSION campaign runner.

Reuses the sealed pipeline unmodified: synthesize_requests_from_window ->
apply_slo_variant (new, this extension) -> _rebase_and_scale -> execute_cell.
Never modifies benchmark_synthesis.py, execute_cell.py, or the sealed
campaign_freeze/shard_plan manifests.

Modes:
  --mode pilot  Small representative subset (every variant, KNEE and
                HIGH_PRESSURE regions, burstgpt, a small policy/window
                subset). Stamped SLO_SENSITIVITY_PIPELINE_PILOT_NOT_HEADLINE_EVIDENCE.
                Output: artifacts/analysis/slo_sensitivity/<manifest_sha256>/pilot/results.json
  --mode full   All cells in the frozen manifest.
                Output: artifacts/analysis/slo_sensitivity/<manifest_sha256>/full/results.json

Idempotent checkpointing: the output file is a JSON object
{cell_id: result_dict}, independently re-validated on load (never trusts a
pre-existing success=True at face value), rewritten after every cell.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.analysis.slo_variant import (  # noqa: E402
    apply_slo_variant_to_window,
    validate_slo_variant,
)
from robustbench.calibration.stage0_load_calibration import STAGE0_REFERENCE_GPU_CONFIG, _rebase_and_scale  # noqa: E402
from robustbench.policies.registry import make_policy_any  # noqa: E402
from robustbench.ranking_portability.execute_cell import execute_cell  # noqa: E402
from robustbench.ranking_portability.schema import validate_cell_result  # noqa: E402
from robustbench.simulator.telemetry import TelemetrySummary, validate_telemetry  # noqa: E402
from robustbench.workloads.external.benchmark_synthesis import synthesize_requests_from_window  # noqa: E402
from robustbench.workloads.external.schema import ExternalWorkloadRecord  # noqa: E402

DEFAULT_MANIFEST = REPO_ROOT / "artifacts/manifests/slo_sensitivity_campaign_manifest_20260903.json"
DEFAULT_FULL_WINDOWS = REPO_ROOT / "artifacts/pilot_v2_windows_full_cache.json"
OUTPUT_ROOT = REPO_ROOT / "artifacts/analysis/slo_sensitivity"

PILOT_SOURCE = "burstgpt"
PILOT_REGIONS = {"KNEE", "HIGH_PRESSURE"}
PILOT_POLICIES = {"slai_faithful", "vllm_faithful", "edf"}
PILOT_N_WINDOWS = 2


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).decode().strip()


def _is_valid_checkpoint_row(row: dict) -> bool:
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


def _select_pilot_cells(cells: List[dict]) -> List[dict]:
    by_window_order: Dict[str, int] = {}
    selected = []
    for c in cells:
        if c["source_family"] != PILOT_SOURCE:
            continue
        if c["load_region"] not in PILOT_REGIONS:
            continue
        if c["policy_id"] not in PILOT_POLICIES:
            continue
        idx = by_window_order.setdefault(c["window_id"], len(by_window_order))
        if idx >= PILOT_N_WINDOWS:
            continue
        selected.append(c)
    return selected


def run(mode: str, manifest_path: Path, full_windows_path: Path) -> int:
    with open(manifest_path) as f:
        manifest = json.load(f)
    with open(full_windows_path) as f:
        full_windows = json.load(f)
    windows_by_id = {w["window_id"]: w for w in full_windows["windows"]}

    cells = manifest["cells"]
    scientific_status = (
        "SLO_SENSITIVITY_PIPELINE_PILOT_NOT_HEADLINE_EVIDENCE" if mode == "pilot"
        else "POST_PHASE12_SLO_DEFINITION_SENSITIVITY_EXTENSION"
    )
    if mode == "pilot":
        cells = _select_pilot_cells(cells)

    out_dir = OUTPUT_ROOT / manifest["manifest_sha256"] / mode
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "results.json"

    checkpoint: dict = {}
    if out_path.exists():
        with open(out_path) as f:
            checkpoint = json.load(f)
    needed_ids = {c["cell_id"] for c in cells}
    checkpoint = {cid: row for cid, row in checkpoint.items() if cid in needed_ids}
    for cid in list(checkpoint.keys()):
        if not _is_valid_checkpoint_row(checkpoint[cid]):
            del checkpoint[cid]

    repo_sha = _git_sha()
    base_requests_cache: Dict[str, list] = {}
    variant_requests_cache: Dict[tuple, list] = {}
    scaled_requests_cache: Dict[tuple, list] = {}

    n_total = len(cells)
    n_skipped = 0
    n_computed = 0
    n_validation_failures = 0
    t_start = time.time()

    for i, c in enumerate(cells):
        cid = c["cell_id"]
        if cid in checkpoint:
            n_skipped += 1
            continue

        window_id = c["window_id"]
        if window_id not in base_requests_cache:
            w = windows_by_id[window_id]
            records = [ExternalWorkloadRecord(**r) for r in w["records"]]
            requests, _synth = synthesize_requests_from_window(records, window_id=window_id, seed=c["synthesis_seed"])
            base_requests_cache[window_id] = requests

        variant_key = (window_id, c["slo_variant"])
        if variant_key not in variant_requests_cache:
            base = base_requests_cache[window_id]
            variant_requests = apply_slo_variant_to_window(base, c["slo_multiplier"])
            report = validate_slo_variant(base, variant_requests)
            if not report.passed:
                n_validation_failures += 1
                checkpoint[cid] = {
                    "cell_id": cid, "success": False,
                    "error_category": "slo_variant_validation_failed",
                    "error_detail": "; ".join(report.problems[:10]),
                }
                continue
            variant_requests_cache[variant_key] = variant_requests

        scale_key = (window_id, c["slo_variant"], c["load_region"])
        if scale_key not in scaled_requests_cache:
            scaled_requests_cache[scale_key] = _rebase_and_scale(
                variant_requests_cache[variant_key], float(c["absolute_load_factor"])
            )

        policy = make_policy_any(c["policy_id"])
        result = execute_cell(
            cell_id=cid,
            source_family=c["source_family"],
            window_id=window_id,
            load_region=c["load_region"],
            load_factor=float(c["absolute_load_factor"]),
            policy_id=c["policy_id"],
            repetition=0,
            synthesis_seed=c["synthesis_seed"],
            repo_sha=repo_sha,
            policy=policy,
            requests=scaled_requests_cache[scale_key],
            gpu_configs=[STAGE0_REFERENCE_GPU_CONFIG],
            scientific_status=scientific_status,
        )
        row = result.to_dict()
        row["slo_variant"] = c["slo_variant"]
        row["slo_multiplier"] = c["slo_multiplier"]
        row["manifest_sha256"] = manifest["manifest_sha256"]
        checkpoint[cid] = row
        n_computed += 1

        if (i + 1) % 500 == 0 or (i + 1) == n_total:
            with open(out_path, "w") as f:
                json.dump(checkpoint, f)
            elapsed = time.time() - t_start
            print(f"progress: {i + 1}/{n_total} done_this_run={n_computed} skipped={n_skipped} "
                  f"validation_failures={n_validation_failures} elapsed_s={elapsed:.1f}", flush=True)

    with open(out_path, "w") as f:
        json.dump(checkpoint, f)

    n_success = sum(1 for r in checkpoint.values() if r.get("success"))
    n_failed = len(checkpoint) - n_success
    print(f"DONE mode={mode} n_total={n_total} n_success={n_success} n_failed={n_failed} "
          f"n_validation_failures={n_validation_failures} out_path={out_path}")
    return 0 if n_failed == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["pilot", "full"], required=True)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--full-windows", type=Path, default=DEFAULT_FULL_WINDOWS)
    args = ap.parse_args()
    return run(args.mode, args.manifest, args.full_windows)


if __name__ == "__main__":
    raise SystemExit(main())
