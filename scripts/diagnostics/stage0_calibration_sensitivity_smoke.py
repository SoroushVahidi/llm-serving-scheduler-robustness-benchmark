#!/usr/bin/env python3
"""Reference-calibration-ONLY sensitivity smoke (A5 of
docs/STAGE0_LOAD_CALIBRATION_AUDIT_20260901.md). Uses only the frozen
`fifo` reference mechanism -- never a Stage-0-study policy. NOT scheduler
evidence; purely a sanity check that lambda_ref/PRE_KNEE/KNEE/OVERLOAD sit
on a stable, monotonic response curve rather than noise.

Samples 2 windows per source (6 of 30 total) to keep this cheap.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.calibration.stage0_load_calibration import (  # noqa: E402
    REFERENCE_POLICY,
    STAGE0_REFERENCE_GPU_CONFIG,
    _rebase_and_scale,
)
from robustbench.evaluation.run_policy import run_policy  # noqa: E402
from robustbench.policies.registry import make_policy  # noqa: E402
from robustbench.workloads.external.benchmark_synthesis import (  # noqa: E402
    synthesize_requests_from_window,
)
from robustbench.workloads.external.schema import ExternalWorkloadRecord  # noqa: E402

SAMPLE_MULTIPLIERS = (0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.4)
SYNTHESIS_SEED_BASE = 900_000


def main() -> None:
    windows_path = REPO_ROOT / "artifacts" / "manifests" / "stage0_windows.json"
    cal_path = REPO_ROOT / "artifacts" / "manifests" / "stage0_load_calibration.json"
    with open(windows_path) as f:
        windows_manifest = json.load(f)
    with open(cal_path) as f:
        cal_manifest = json.load(f)
    lambda_ref_by_id = {c["window_id"]: c["lambda_ref"] for c in cal_manifest["calibrations"]}

    by_source: dict[str, list] = {}
    for i, w in enumerate(windows_manifest["windows"]):
        by_source.setdefault(w["source_family"], []).append((i, w))

    results = []
    n_monotonic_violations = 0
    for source, entries in by_source.items():
        sample = entries[:2]
        for i, w in sample:
            window_id = w["window_id"]
            lambda_ref = lambda_ref_by_id[window_id]
            records = [ExternalWorkloadRecord(**r) for r in w["records"]]
            seed = SYNTHESIS_SEED_BASE + i
            requests, _ = synthesize_requests_from_window(records, window_id=window_id, seed=seed)

            curve = []
            prev_rate = -1.0
            for mult in SAMPLE_MULTIPLIERS:
                factor = lambda_ref * mult
                scaled = _rebase_and_scale(requests, factor)
                policy = make_policy(REFERENCE_POLICY)
                m = run_policy(policy, scaled, [STAGE0_REFERENCE_GPU_CONFIG],
                                workload_tag="stage0_calibration_sensitivity", seed=0)
                curve.append({"multiplier": mult, "factor": factor, "slo_violation_rate": m.slo_violation_rate})
                if m.slo_violation_rate < prev_rate - 1e-9:
                    n_monotonic_violations += 1
                prev_rate = m.slo_violation_rate
            results.append({"source_family": source, "window_id": window_id,
                             "lambda_ref": lambda_ref, "curve": curve})
            print(f"[{source}] {window_id}: " +
                  ", ".join(f"{c['multiplier']}x={c['slo_violation_rate']:.4f}" for c in curve),
                  file=sys.stderr)

    out_path = REPO_ROOT / "artifacts" / "diagnostics" / "stage0_calibration_sensitivity_smoke.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({
            "purpose": "reference-calibration-only sensitivity check, NOT scheduler evidence",
            "reference_policy": REFERENCE_POLICY,
            "n_windows_sampled": len(results),
            "n_monotonicity_violations": n_monotonic_violations,
            "results": results,
        }, f, indent=2)
    print(f"wrote {out_path}: {len(results)} windows sampled, "
          f"{n_monotonic_violations} monotonicity violations", file=sys.stderr)


if __name__ == "__main__":
    main()
