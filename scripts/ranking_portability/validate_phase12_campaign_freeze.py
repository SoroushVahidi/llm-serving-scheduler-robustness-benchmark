#!/usr/bin/env python3
"""Independent Phase-12B campaign-matrix validator.

Deliberately does NOT import or call anything from
`build_phase12_campaign_freeze.py` -- it re-derives the expected matrix
from the canonical frozen inputs (compact window index, Phase-11 region
assignments) itself, using only the shared, non-outcome-bearing contract
module (`robustbench.ranking_portability.phase12_campaign`), and diffs
that independently-reconstructed expectation against the generated
manifest. Performs NO ranking analysis and executes NO cell.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.policies.registry import make_policy_any  # noqa: E402
from robustbench.ranking_portability.phase12_campaign import (  # noqa: E402
    CAMPAIGN_POLICIES,
    CAMPAIGN_REGIONS,
    CAMPAIGN_REPETITIONS,
    CAMPAIGN_SOURCES,
    EXPECTED_ASSIGNMENT_KEY_COUNT,
    EXPECTED_CAMPAIGN_CELL_COUNT,
    SCIENTIFIC_STATUS_PILOT_V2_SCIENTIFIC,
    WINDOWS_PER_SOURCE,
    generate_campaign_cell_specs,
    load_campaign_window_ids,
    synthesis_seed_for_window,
)
from robustbench.ranking_portability.phase12_smoke import SCIENTIFIC_STATUS_ENGINEERING_SMOKE  # noqa: E402
from robustbench.ranking_portability.schema import CELL_SCHEMA_VERSION  # noqa: E402
from robustbench.simulator.telemetry import TELEMETRY_SCHEMA_VERSION  # noqa: E402

EXPECTED_HASHES = {
    "phase10_compact_index": "d78ec1087fedae02174ca093a9860c70468be336ccb1d7e6de756c81ba331e53",
    "phase11_raw_fifo": "201caaf04476ad8737ef6079fc0d6cb4e864601711d0b96c88750a717d8b2a6a",
    "phase11_region_assignment": "9fcb92f9ea1206ce185194527ada35d0e3b91bf4904be7ae23ba9ea997c17574",
}
EXPECTED_PHASE10_WINDOW_HASH = "0d1aa06ccbee352207327ea369ae75f12e91c0cda006c813a41b381effd29eef"
EXPECTED_PHASE11_PRELAUNCH_HASH = "e2564ea9484190832de50f63173c4b73ae054d6ae7008bb4ff6648c8dc917f7b"
SECONDARY_STRATUM_POLICIES = {"distserve_faithful", "llumnix_faithful", "apt_serve_faithful"}


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_campaign_freeze.json")
    ap.add_argument("--compact-index", type=Path, default=REPO_ROOT / "artifacts/manifests/ranking_portability_pilot_v2_windows_index.json")
    ap.add_argument("--assignments", type=Path, default=REPO_ROOT / "artifacts/manifests/ranking_portability_phase11_region_assignments.json")
    ap.add_argument("--report", type=Path, default=REPO_ROOT / "docs/RANKING_PORTABILITY_PHASE12_CAMPAIGN_FREEZE_VALIDATION.md")
    args = ap.parse_args()

    problems: list[str] = []
    info: list[str] = []

    # === 1. Immutable hashes (independent recompute, not trusting the manifest's self-report) ===
    hash_rows = []
    for name, path in [
        ("phase10_compact_index", args.compact_index),
        ("phase11_region_assignment", args.assignments),
        ("phase11_raw_fifo", REPO_ROOT / "artifacts/manifests/ranking_portability_phase11_raw_fifo_calibration.json"),
    ]:
        observed = _sha256_file(path)
        expected = EXPECTED_HASHES[name]
        hash_rows.append((name, expected, observed, observed == expected))
        if observed != expected:
            problems.append(f"HASH MISMATCH: {name} expected={expected} observed={observed}")

    with open(args.manifest) as f:
        manifest = json.load(f)

    for name, expected in [("phase10_window", EXPECTED_PHASE10_WINDOW_HASH), ("phase11_prelaunch", EXPECTED_PHASE11_PRELAUNCH_HASH)]:
        observed = manifest.get(f"{name}_hash")
        hash_rows.append((name, expected, observed, observed == expected))
        if observed != expected:
            problems.append(f"HASH MISMATCH (manifest self-report): {name} expected={expected} observed={observed}")

    # === 2. Independently reconstruct the expected matrix from canonical inputs ===
    with open(args.compact_index) as f:
        compact_index = json.load(f)
    window_ids_by_source = load_campaign_window_ids(compact_index)  # raises if != 40/source
    info.append(f"windows per source (independently loaded): {[len(v) for v in window_ids_by_source.values()]}")

    with open(args.assignments) as f:
        assign_doc = json.load(f)
    assignment_keys = {(a["source"], a["window_id"], a["region"]) for a in assign_doc["assignments"]}
    expected_assignment_keys = {
        (source, window_id, region)
        for source in CAMPAIGN_SOURCES
        for window_id in window_ids_by_source[source]
        for region in CAMPAIGN_REGIONS
    }
    if len(assignment_keys) != EXPECTED_ASSIGNMENT_KEY_COUNT:
        problems.append(f"assignment keys: expected {EXPECTED_ASSIGNMENT_KEY_COUNT}, found {len(assignment_keys)}")
    missing_assign = expected_assignment_keys - assignment_keys
    unexpected_assign = assignment_keys - expected_assignment_keys
    if missing_assign:
        problems.append(f"assignment keys missing: {len(missing_assign)} e.g. {sorted(missing_assign)[:3]}")
    if unexpected_assign:
        problems.append(f"assignment keys unexpected: {len(unexpected_assign)} e.g. {sorted(unexpected_assign)[:3]}")

    expected_specs = generate_campaign_cell_specs(window_ids_by_source)
    expected_cell_ids = {s.cell_id for s in expected_specs}
    if len(expected_specs) != EXPECTED_CAMPAIGN_CELL_COUNT:
        problems.append(f"independently-generated matrix has {len(expected_specs)} cells, expected {EXPECTED_CAMPAIGN_CELL_COUNT}")

    # === 3. Compare against the generated manifest ===
    manifest_cells = manifest["cells"]
    manifest_cell_ids = [c["cell_id"] for c in manifest_cells]

    if len(manifest_cells) != EXPECTED_CAMPAIGN_CELL_COUNT:
        problems.append(f"manifest cell count: expected {EXPECTED_CAMPAIGN_CELL_COUNT}, got {len(manifest_cells)}")
    if len(manifest_cell_ids) != len(set(manifest_cell_ids)):
        problems.append("manifest contains duplicate cell_ids")

    manifest_set = set(manifest_cell_ids)
    missing = expected_cell_ids - manifest_set
    unexpected = manifest_set - expected_cell_ids
    if missing:
        problems.append(f"manifest missing {len(missing)} expected cell(s), e.g. {sorted(missing)[:3]}")
    if unexpected:
        problems.append(f"manifest has {len(unexpected)} unexpected cell(s), e.g. {sorted(unexpected)[:3]}")

    # === 4. Field-level structural checks on every manifest cell ===
    seen_tuples = set()
    unexpected_sources, unexpected_windows, unexpected_regions = set(), set(), set()
    unexpected_policies, unexpected_reps = set(), set()
    leaked_secondary_policies = set()
    leaked_smoke_status = 0
    wrong_scientific_status = 0
    for c in manifest_cells:
        t = (c["source_family"], c["window_id"], c["load_region"], c["policy_id"], c["repetition"])
        seen_tuples.add(t)
        if c["source_family"] not in CAMPAIGN_SOURCES:
            unexpected_sources.add(c["source_family"])
        if c["load_region"] not in CAMPAIGN_REGIONS:
            unexpected_regions.add(c["load_region"])
        if c["policy_id"] not in CAMPAIGN_POLICIES:
            unexpected_policies.add(c["policy_id"])
        if c["policy_id"] in SECONDARY_STRATUM_POLICIES:
            leaked_secondary_policies.add(c["policy_id"])
        if c["repetition"] not in CAMPAIGN_REPETITIONS:
            unexpected_reps.add(c["repetition"])
        if c["window_id"] not in window_ids_by_source.get(c["source_family"], []):
            unexpected_windows.add(c["window_id"])
        if c.get("scientific_status") == SCIENTIFIC_STATUS_ENGINEERING_SMOKE:
            leaked_smoke_status += 1
        if c.get("scientific_status") != SCIENTIFIC_STATUS_PILOT_V2_SCIENTIFIC:
            wrong_scientific_status += 1
        expected_seed = synthesis_seed_for_window(c["window_id"])
        if c.get("synthesis_seed") != expected_seed:
            problems.append(f"cell {c['cell_id']}: synthesis_seed={c.get('synthesis_seed')} expected {expected_seed}")

    if len(seen_tuples) != EXPECTED_CAMPAIGN_CELL_COUNT:
        problems.append(f"manifest tuple set has {len(seen_tuples)} unique (source,window,region,policy,rep) tuples, expected {EXPECTED_CAMPAIGN_CELL_COUNT}")
    if unexpected_sources:
        problems.append(f"unexpected sources in manifest: {sorted(unexpected_sources)}")
    if unexpected_windows:
        problems.append(f"unexpected windows in manifest: {sorted(unexpected_windows)[:5]} (n={len(unexpected_windows)})")
    if unexpected_regions:
        problems.append(f"unexpected regions in manifest: {sorted(unexpected_regions)}")
    if unexpected_policies:
        problems.append(f"unexpected policies in manifest: {sorted(unexpected_policies)}")
    if unexpected_reps:
        problems.append(f"unexpected repetitions in manifest: {sorted(unexpected_reps)}")
    if leaked_secondary_policies:
        problems.append(f"secondary-stratum policies leaked into campaign: {sorted(leaked_secondary_policies)}")
    if leaked_smoke_status:
        problems.append(f"{leaked_smoke_status} cell(s) carry ENGINEERING_SMOKE status (leaked from Phase-12A)")
    if wrong_scientific_status:
        problems.append(f"{wrong_scientific_status} cell(s) do not carry scientific_status={SCIENTIFIC_STATUS_PILOT_V2_SCIENTIFIC!r}")
    else:
        info.append(f"all {len(manifest_cells)} cells carry scientific_status={SCIENTIFIC_STATUS_PILOT_V2_SCIENTIFIC!r}")

    # === 5. exact source/policy/region-order checks ===
    if set(manifest.get("campaign_sources", [])) != set(CAMPAIGN_SOURCES):
        problems.append("manifest campaign_sources does not match the frozen source list")
    if manifest.get("campaign_regions") != list(CAMPAIGN_REGIONS):
        problems.append("manifest campaign_regions order does not match the frozen region order")
    if manifest.get("campaign_policies") != list(CAMPAIGN_POLICIES):
        problems.append("manifest campaign_policies does not match the frozen 13-policy panel/order")
    if set(manifest.get("campaign_repetitions", [])) != {0, 1}:
        problems.append("manifest campaign_repetitions is not exactly {0,1}")

    # === 6. Every load assignment matches Phase-11; both reps share identical seed/input ===
    region_assignment_index = manifest.get("region_assignment_index", {})
    assign_by_key = {(a["source"], a["window_id"], a["region"]): a for a in assign_doc["assignments"]}
    load_mismatches = 0
    for key_str, row in region_assignment_index.items():
        source, window_id, region = key_str.split("::")
        frozen = assign_by_key.get((source, window_id, region))
        if frozen is None:
            load_mismatches += 1
            continue
        expected_abs = float(frozen["lambda_ref"]) * float(frozen["selected_load_factor"])
        if abs(expected_abs - float(row["absolute_load_factor"])) > 1e-6 * max(abs(expected_abs), 1.0):
            load_mismatches += 1
    if load_mismatches:
        problems.append(f"{load_mismatches} region_assignment_index entries disagree with the frozen Phase-11 artifact")
    else:
        info.append(f"all {len(region_assignment_index)} region_assignment_index entries agree exactly with the frozen Phase-11 artifact")

    # Both reps share identical seed/input: check per (source,window,region,policy) that rep0/rep1 cells reference the same synthesis_seed and region_assignment_key.
    by_pair: dict = {}
    for c in manifest_cells:
        key = (c["source_family"], c["window_id"], c["load_region"], c["policy_id"])
        by_pair.setdefault(key, {})[c["repetition"]] = c
    rep_input_mismatches = 0
    for key, reps in by_pair.items():
        if 0 in reps and 1 in reps:
            if reps[0]["synthesis_seed"] != reps[1]["synthesis_seed"] or reps[0]["region_assignment_key"] != reps[1]["region_assignment_key"]:
                rep_input_mismatches += 1
    if rep_input_mismatches:
        problems.append(f"{rep_input_mismatches} (source,window,region,policy) pair(s) have rep0/rep1 with different seed/input")
    else:
        info.append(f"all {len(by_pair)} (source,window,region,policy) pairs have identical rep0/rep1 seed/input")

    # === 7. Policy registry can instantiate all 13 policies ===
    registry_failures = []
    for name in CAMPAIGN_POLICIES:
        try:
            make_policy_any(name)
        except Exception as e:  # noqa: BLE001
            registry_failures.append(f"{name}: {e}")
    if registry_failures:
        problems.append(f"policy registry instantiation failures: {registry_failures}")
    else:
        info.append("all 13 campaign policies instantiate successfully via make_policy_any")

    # === 8. Telemetry/schema versions are the corrected prelaunch versions ===
    info.append(f"CELL_SCHEMA_VERSION={CELL_SCHEMA_VERSION}")
    info.append(f"TELEMETRY_SCHEMA_VERSION={TELEMETRY_SCHEMA_VERSION}")

    # === 9. Shard coverage (if a shard plan file is present) ===
    shard_plan_path = REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_shard_plan.json"
    if shard_plan_path.exists():
        with open(shard_plan_path) as f:
            shard_plan = json.load(f)
        union_ids: list[str] = []
        for shard in shard_plan["shards"]:
            union_ids.extend(shard["cell_ids"])
        if len(union_ids) != len(set(union_ids)):
            problems.append("shard plan has duplicate cell_ids across shards")
        if set(union_ids) != expected_cell_ids:
            missing_shard = expected_cell_ids - set(union_ids)
            extra_shard = set(union_ids) - expected_cell_ids
            if missing_shard:
                problems.append(f"shard plan missing {len(missing_shard)} cell(s)")
            if extra_shard:
                problems.append(f"shard plan has {len(extra_shard)} unexpected cell(s)")
        else:
            info.append(f"shard plan: union of {len(shard_plan['shards'])} shards covers exactly the 18,720-cell matrix, no duplicates")

    valid = len(problems) == 0
    verdict = "YES" if valid else "NO"

    lines = ["# RANKING_PORTABILITY_PHASE12_CAMPAIGN_FREEZE_VALIDATION.md", ""]
    lines.append("Independent Phase-12B campaign-matrix validation report. No ranking")
    lines.append("analysis, no scheduler-performance inspection, no cell executed.")
    lines.append("")
    lines.append("## Immutable hashes (independently recomputed)")
    for name, expected, observed, match in hash_rows:
        lines.append(f"- {name}: expected=`{expected}` observed=`{observed}` match={match}")
    lines.append("")
    lines.append("## Matrix")
    lines.append(f"- expected cells: {EXPECTED_CAMPAIGN_CELL_COUNT}")
    lines.append(f"- manifest cells: {len(manifest_cells)}")
    lines.append(f"- unique (source,window,region,policy,rep) tuples: {len(seen_tuples)}")
    lines.append(f"- missing vs. independently-reconstructed expectation: {len(missing)}")
    lines.append(f"- unexpected vs. independently-reconstructed expectation: {len(unexpected)}")
    lines.append("")
    lines.append("## Load assignments")
    lines.append(f"- expected assignment keys: {EXPECTED_ASSIGNMENT_KEY_COUNT}")
    lines.append(f"- consumed keys: {len(region_assignment_index)}")
    lines.append(f"- mismatches: {load_mismatches}")
    lines.append("")
    lines.append("## Info")
    for i in info:
        lines.append(f"- {i}")
    lines.append("")
    lines.append("## Problems" if problems else "## Problems: none")
    for p in problems:
        lines.append(f"- {p}")
    lines.append("")
    lines.append(f"PHASE12_CAMPAIGN_MATRIX_INDEPENDENTLY_VALID = {verdict}")
    lines.append("")

    args.report.write_text("\n".join(lines))
    print(f"PHASE12_CAMPAIGN_MATRIX_INDEPENDENTLY_VALID = {verdict}")
    print(f"n_problems={len(problems)}")
    for p in problems:
        print(f"PROBLEM: {p}")
    return 0 if valid else 1


if __name__ == "__main__":
    sys.exit(main())
