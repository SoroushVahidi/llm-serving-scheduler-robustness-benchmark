#!/usr/bin/env python3
"""Builds the full per-window diagnostic table (A2 of
docs/STAGE0_LOAD_CALIBRATION_AUDIT_20260901.md) from
artifacts/manifests/stage0_load_calibration.json.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
IN_PATH = REPO_ROOT / "artifacts" / "manifests" / "stage0_load_calibration.json"
OUT_PATH = REPO_ROOT / "artifacts" / "diagnostics" / "stage0_load_calibration_audit.csv"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

with open(IN_PATH) as f:
    d = json.load(f)

rows = []
for c in d["calibrations"]:
    s = c["sanity"]
    regions = c["load_regions"]
    blocking = [n for n in s["notes"] if "informational only" not in n]
    informational = [n for n in s["notes"] if "informational only" in n]
    rows.append({
        "source_family": c["source_family"],
        "window_id": c["window_id"],
        "lambda_ref": c["lambda_ref"],
        "pre_knee_factor": regions["PRE_KNEE"],
        "knee_factor": regions["KNEE"],
        "overload_factor": regions["OVERLOAD"],
        "pre_knee_violation_rate": s["pre_knee_slo_violation_rate"],
        "pre_knee_completion_fraction": s["pre_knee_completion_fraction"],
        "knee_violation_rate": s["knee_slo_violation_rate"],
        "knee_completion_fraction": s["knee_completion_fraction"],
        "overload_violation_rate": s["overload_slo_violation_rate"],
        "overload_completion_fraction": s["overload_completion_fraction"],
        "overload_margin_from_2x_threshold": s["overload_slo_violation_rate"] - 0.01,
        "ordering_pre_lt_knee_lt_over_holds": regions["PRE_KNEE"] < regions["KNEE"] < regions["OVERLOAD"],
        "plausible": s["plausible"],
        "blocking_notes": " | ".join(blocking),
        "informational_notes": " | ".join(informational),
    })

with open(OUT_PATH, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

n_plausible = sum(1 for r in rows if r["plausible"])
print(f"wrote {OUT_PATH} ({len(rows)} rows, {n_plausible}/{len(rows)} plausible)", file=sys.stderr)
