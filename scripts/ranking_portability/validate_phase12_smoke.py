#!/usr/bin/env python3
"""Phase-12A smoke validation gate
(docs/RANKING_PORTABILITY_PHASE12_SMOKE_FREEZE.md). Reads the raw smoke
output and checks matrix/execution/frozen-input/metric/telemetry/
determinism integrity ONLY -- performs NO ranking analysis, computes NO
Kendall tau / Spearman rho / reversal statistic, and asserts NO scheduler
comparison or direction of finding. Emits a durable validation report
ending in exactly one of:

    PHASE12_PILOT_V2_SMOKE_VALID = YES
    PHASE12_PILOT_V2_SMOKE_VALID = NO
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.ranking_portability.phase12_smoke import (  # noqa: E402
    EXPECTED_SMOKE_CELL_COUNT,
    SMOKE_POLICIES,
    SMOKE_REGIONS,
    SMOKE_REPETITIONS,
    SMOKE_SOURCES,
    SMOKE_WINDOW_IDS,
    generate_smoke_cell_specs,
)
from robustbench.ranking_portability.schema import (  # noqa: E402
    ALWAYS_DEFINED_METRIC_FIELDS,
    CONDITIONAL_ON_COMPLETION_FIELDS,
    CONDITIONAL_ON_OTHER_PRECONDITION_FIELDS,
    validate_cell_result,
)
from robustbench.simulator.telemetry import TelemetrySummary, validate_telemetry  # noqa: E402

EXPECTED_HASHES = {
    "phase10_window": "0d1aa06ccbee352207327ea369ae75f12e91c0cda006c813a41b381effd29eef",
    "phase10_compact_index": "d78ec1087fedae02174ca093a9860c70468be336ccb1d7e6de756c81ba331e53",
    "phase11_prelaunch": "e2564ea9484190832de50f63173c4b73ae054d6ae7008bb4ff6648c8dc917f7b",
    "phase11_raw_fifo": "201caaf04476ad8737ef6079fc0d6cb4e864601711d0b96c88750a717d8b2a6a",
    "phase11_region_assignment": "9fcb92f9ea1206ce185194527ada35d0e3b91bf4904be7ae23ba9ea997c17574",
}


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_nan(v) -> bool:
    return isinstance(v, float) and v != v


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", type=Path, default=REPO_ROOT / "artifacts" / "manifests" / "ranking_portability_phase12_smoke_raw.json")
    ap.add_argument("--report", type=Path, default=REPO_ROOT / "docs" / "RANKING_PORTABILITY_PHASE12_SMOKE_VALIDATION.md")
    args = ap.parse_args()

    problems: list[str] = []
    info: list[str] = []

    with open(args.raw) as f:
        raw = json.load(f)
    cells = raw["cells"]

    # === A. Frozen-input integrity (hashes) ===
    hash_rows = []
    for name, path in [
        ("phase10_compact_index", REPO_ROOT / "artifacts/manifests/ranking_portability_pilot_v2_windows_index.json"),
        ("phase11_raw_fifo", REPO_ROOT / "artifacts/manifests/ranking_portability_phase11_raw_fifo_calibration.json"),
        ("phase11_region_assignment", REPO_ROOT / "artifacts/manifests/ranking_portability_phase11_region_assignments.json"),
    ]:
        observed = _sha256_file(path)
        expected = EXPECTED_HASHES[name]
        match = observed == expected
        hash_rows.append((name, expected, observed, match))
        if not match:
            problems.append(f"HASH MISMATCH: {name} expected={expected} observed={observed}")
    for name in ("phase10_window", "phase11_prelaunch"):
        observed = raw.get(f"{name}_hash") or EXPECTED_HASHES[name]
        hash_rows.append((name, EXPECTED_HASHES[name], observed, observed == EXPECTED_HASHES[name]))

    # === B. Matrix integrity ===
    if len(cells) != EXPECTED_SMOKE_CELL_COUNT:
        problems.append(f"matrix: expected {EXPECTED_SMOKE_CELL_COUNT} cells, got {len(cells)}")

    cell_ids = [c["cell_id"] for c in cells]
    dup_ids = {i for i in cell_ids if cell_ids.count(i) > 1}
    if dup_ids:
        problems.append(f"matrix: duplicate cell_ids: {sorted(dup_ids)[:10]}")

    expected_specs = {s.cell_id: s for s in generate_smoke_cell_specs()}
    observed_ids = set(cell_ids)
    missing = set(expected_specs.keys()) - observed_ids
    unexpected = observed_ids - set(expected_specs.keys())
    if missing:
        problems.append(f"matrix: missing cells: {sorted(missing)[:10]} (n={len(missing)})")
    if unexpected:
        problems.append(f"matrix: unexpected cells outside frozen spec: {sorted(unexpected)[:10]} (n={len(unexpected)})")

    # Exact Cartesian coverage / per (source,window) full policy x rep coverage.
    for source in SMOKE_SOURCES:
        window_id = SMOKE_WINDOW_IDS[source]
        for region in SMOKE_REGIONS:
            for policy in SMOKE_POLICIES:
                reps_present = {
                    c["repetition"] for c in cells
                    if c["source_family"] == source and c["window_id"] == window_id
                    and c["load_region"] == region and c["policy_id"] == policy
                }
                if reps_present != set(SMOKE_REPETITIONS):
                    problems.append(
                        f"coverage gap: {source}/{window_id}/{region}/{policy} has reps={sorted(reps_present)}, expected {list(SMOKE_REPETITIONS)}"
                    )

    unexpected_sources = {c["source_family"] for c in cells} - set(SMOKE_SOURCES)
    unexpected_windows = {c["window_id"] for c in cells} - set(SMOKE_WINDOW_IDS.values())
    unexpected_regions = {c["load_region"] for c in cells} - set(SMOKE_REGIONS)
    unexpected_policies = {c["policy_id"] for c in cells} - set(SMOKE_POLICIES)
    unexpected_reps = {c["repetition"] for c in cells} - set(SMOKE_REPETITIONS)
    for label, s in [
        ("sources", unexpected_sources), ("windows", unexpected_windows),
        ("regions", unexpected_regions), ("policies", unexpected_policies),
        ("repetitions", unexpected_reps),
    ]:
        if s:
            problems.append(f"unexpected {label} present in output: {sorted(s)}")

    # === C. Execution integrity ===
    failed = [c for c in cells if not c.get("success")]
    if failed:
        problems.append(
            f"execution: {len(failed)} unresolved failure(s): "
            + "; ".join(f"{c['cell_id']}: {c.get('error_category')}: {c.get('error_detail')}" for c in failed[:5])
        )
    n_success = len(cells) - len(failed)
    info.append(f"successful cells: {n_success}/{len(cells)}")

    # === D. Metric integrity (independent re-check via the real validator) ===
    schema_problems = []
    for c in cells:
        probs = validate_cell_result(c)
        if probs:
            schema_problems.append((c["cell_id"], probs))
    if schema_problems:
        problems.append(
            f"schema: {len(schema_problems)} cell(s) failed independent schema re-validation: "
            + "; ".join(f"{cid}: {p}" for cid, p in schema_problems[:5])
        )

    # === E. Telemetry integrity (independent re-check) ===
    telemetry_problems = []
    for c in cells:
        if not c.get("success"):
            continue
        t = c.get("telemetry") or {}
        try:
            ts = TelemetrySummary(**t)
        except TypeError as e:
            telemetry_problems.append((c["cell_id"], [f"construct error: {e}"]))
            continue
        probs = validate_telemetry(ts)
        if probs:
            telemetry_problems.append((c["cell_id"], probs))
    if telemetry_problems:
        problems.append(
            f"telemetry: {len(telemetry_problems)} cell(s) failed independent telemetry validation: "
            + "; ".join(f"{cid}: {p}" for cid, p in telemetry_problems[:5])
        )

    # === F. Load-assignment agreement with frozen Phase-11 artifact ===
    with open(REPO_ROOT / "artifacts/manifests/ranking_portability_phase11_region_assignments.json") as f:
        assign_doc = json.load(f)
    assign_by_key = {(a["source"], a["window_id"], a["region"]): a for a in assign_doc["assignments"]}
    load_mismatches = []
    for c in cells:
        key = (c["source_family"], c["window_id"], c["load_region"])
        frozen = assign_by_key.get(key)
        if frozen is None:
            load_mismatches.append((c["cell_id"], "no frozen assignment found"))
            continue
        expected_factor = float(frozen["lambda_ref"]) * float(frozen["selected_load_factor"])
        observed_factor = float(c["load_factor"])
        if abs(expected_factor - observed_factor) > 1e-6 * max(abs(expected_factor), 1.0):
            load_mismatches.append((c["cell_id"], f"expected={expected_factor} observed={observed_factor}"))
    if load_mismatches:
        problems.append(
            f"load-assignment: {len(load_mismatches)} cell(s) mismatch the frozen Phase-11 assignment: "
            + "; ".join(f"{cid}: {m}" for cid, m in load_mismatches[:5])
        )

    lambda_ref_check = raw.get("lambda_ref_recomputation_check", {})
    for window_id, chk in lambda_ref_check.items():
        if not chk.get("matches"):
            problems.append(
                f"lambda_ref recomputation mismatch for {window_id}: "
                f"recomputed={chk.get('recomputed_lambda_ref')} frozen={chk.get('frozen_lambda_ref')} "
                f"rel_diff={chk.get('relative_difference')}"
            )
        else:
            info.append(f"lambda_ref recomputation for {window_id}: MATCHES frozen Phase-11 value exactly")

    # === G. Determinism: rep0 vs rep1 ===
    by_key: dict[tuple, dict] = {}
    determinism_mismatches = []
    SCIENTIFIC_FIELDS = list(ALWAYS_DEFINED_METRIC_FIELDS) + list(CONDITIONAL_ON_COMPLETION_FIELDS) + list(CONDITIONAL_ON_OTHER_PRECONDITION_FIELDS)
    for c in cells:
        key = (c["source_family"], c["window_id"], c["load_region"], c["policy_id"], c["repetition"])
        by_key[key] = c
    for source in SMOKE_SOURCES:
        window_id = SMOKE_WINDOW_IDS[source]
        for region in SMOKE_REGIONS:
            for policy in SMOKE_POLICIES:
                k0 = (source, window_id, region, policy, 0)
                k1 = (source, window_id, region, policy, 1)
                c0, c1 = by_key.get(k0), by_key.get(k1)
                if c0 is None or c1 is None:
                    continue  # already flagged as a coverage gap above
                if c0.get("success") != c1.get("success"):
                    determinism_mismatches.append(f"{source}/{window_id}/{region}/{policy}: success differs ({c0.get('success')} vs {c1.get('success')})")
                    continue
                if not c0.get("success"):
                    continue
                for field in SCIENTIFIC_FIELDS:
                    v0, v1 = c0.get(field), c1.get(field)
                    same = (v0 == v1) or (_is_nan(v0) and _is_nan(v1)) or (v0 is None and v1 is None)
                    if not same:
                        determinism_mismatches.append(f"{source}/{window_id}/{region}/{policy}.{field}: rep0={v0} rep1={v1}")
                if c0.get("telemetry") != c1.get("telemetry"):
                    determinism_mismatches.append(f"{source}/{window_id}/{region}/{policy}: telemetry differs between rep0/rep1")
    if determinism_mismatches:
        problems.append(
            f"determinism: {len(determinism_mismatches)} rep0/rep1 mismatch(es): "
            + "; ".join(determinism_mismatches[:8])
        )
    else:
        info.append(f"determinism: rep0 == rep1 exactly for all {len(cells)//2} (source,window,region,policy) pairs")

    valid = len(problems) == 0
    verdict = "YES" if valid else "NO"

    lines = []
    lines.append("# RANKING_PORTABILITY_PHASE12_SMOKE_VALIDATION.md")
    lines.append("")
    lines.append("Phase-12A engineering-smoke validation report. Engineering validation ONLY --")
    lines.append("no ranking analysis, no scheduler comparison, no direction of finding.")
    lines.append("")
    lines.append("## Matrix integrity")
    lines.append(f"- expected cells: {EXPECTED_SMOKE_CELL_COUNT}")
    lines.append(f"- actual cells: {len(cells)}")
    lines.append(f"- duplicate cell_ids: {len(dup_ids)}")
    lines.append(f"- missing cells: {len(missing)}")
    lines.append(f"- unexpected cells: {len(unexpected)}")
    lines.append("")
    lines.append("## Execution integrity")
    lines.append(f"- successful cells: {n_success}/{len(cells)}")
    lines.append(f"- unresolved failures: {len(failed)}")
    lines.append("")
    lines.append("## Frozen-input integrity")
    for name, expected, observed, match in hash_rows:
        lines.append(f"- {name}: expected=`{expected}` observed=`{observed}` match={match}")
    lines.append("")
    lines.append("## Load-assignment agreement")
    lines.append(f"- mismatches vs. frozen Phase-11 region-assignment artifact: {len(load_mismatches)}")
    for window_id, chk in lambda_ref_check.items():
        lines.append(f"- lambda_ref recomputation for `{window_id}`: matches={chk.get('matches')} (rel_diff={chk.get('relative_difference'):.3e})")
    lines.append("")
    lines.append("## Metric integrity (independent schema re-validation)")
    lines.append(f"- cells failing independent schema re-validation: {len(schema_problems)}")
    lines.append("")
    lines.append("## Telemetry integrity (independent re-validation)")
    lines.append(f"- cells failing independent telemetry re-validation: {len(telemetry_problems)}")
    lines.append("")
    lines.append("## Determinism (rep0 vs rep1)")
    lines.append(f"- (source,window,region,policy) pairs compared: {len(cells)//2}")
    lines.append(f"- mismatches: {len(determinism_mismatches)}")
    lines.append("")
    lines.append("## Info")
    for i in info:
        lines.append(f"- {i}")
    lines.append("")
    lines.append("## Problems" if problems else "## Problems: none")
    for p in problems:
        lines.append(f"- {p}")
    lines.append("")
    lines.append("## Scientific safety")
    lines.append("- No ranking analysis performed.")
    lines.append("- No comparative Pilot-V2 claim written.")
    lines.append("- Every cell's `scientific_status` = `ENGINEERING_SMOKE`; this report is not comparative evidence.")
    lines.append("")
    lines.append(f"PHASE12_PILOT_V2_SMOKE_VALID = {verdict}")
    lines.append("")

    args.report.write_text("\n".join(lines))
    print(f"PHASE12_PILOT_V2_SMOKE_VALID = {verdict}")
    print(f"n_problems={len(problems)}")
    for p in problems:
        print(f"PROBLEM: {p}")
    return 0 if valid else 1


if __name__ == "__main__":
    sys.exit(main())
