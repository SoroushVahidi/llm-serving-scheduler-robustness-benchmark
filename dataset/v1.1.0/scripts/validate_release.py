#!/usr/bin/env python3
"""Public-only, read-only validator for the LSSP v1.1.0 release candidate.

Uses only files in this package; --verify-public-smoke additionally downloads
one pinned, already-public 976 KB GitHub artifact. It never runs simulations
or regenerates statistical analyses.
"""
from __future__ import annotations

import argparse
import decimal
import hashlib
import json
import math
import re
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
FREEZE = "81fa3d9b48a2241001e6820942d4542dcc5b5e30973ad9d2786e72972494f57a"
FULL_MATRIX_HASH = "832d96d7ff4d5e8843c233a6a4708bbbbc578ef6b65307c37f5ac127c62c1ccf"
EXECUTION_SHA = "2b9a21fb58798292c95980d35d05e53b3c6f14f6"
ANALYSIS_SHA = "eb574a8ce5c34a80fddbcfd4417f6626fbdddfd1"
VALIDATOR_SHA = "904e6287812bf5b69aac51fd29eac0971ba79f9dcf3b44a8e2bd6e0dbba822dc"
SOURCE_HASHES = {
    "scientific/campaign/consolidated.json": "73adf7d97f06985ec8f8e1c2f794fd43178433eb198e1c00705e817f4bde9c26",
    "scientific/analysis/pairwise_reversals.json": "c90619e822925146ad4395deebbf0cc8ccd0fd66cc13a8aa84202fc39a5cfdde",
    "scientific/analysis/ranking_correlations.json": "d77d5e973f70f8dfe443ebdf35b9c01e94adb84cc62cecef3a2c9afbb88773ff",
    "scientific/analysis/sample_complexity.json": "cb54afc0e1bb868580b6a8c929d94f4718dbc1eaa01d527b0a2c265c07578dcf",
    "scientific/analysis/telemetry_explanation.json": "b073fa0bbe91efe670151e7250d603f020ed7c0f1a60b90397fa7c18c5d591f6",
    "scientific/analysis/temporal_robustness.json": "c19a3c6400336525beda132386585e9d709782f5e0b05dec36867ee1850675d0",
    "scientific/analysis/topk_overlap.json": "585e916acfb32cb02a8f99cdce65a882c5dee7acc6cbdfbad2e86716d0001b37",
}
METRICS = (
    "arrival_normalized_weighted_goodput", "completion_fraction", "mean_latency", "mean_ttft",
    "p95_latency", "p95_ttft", "request_throughput", "slo_violation_rate",
    "token_throughput", "weighted_completion_fraction", "weighted_goodput",
)
ALWAYS_DEFINED = ("arrival_normalized_weighted_goodput", "completion_fraction", "weighted_completion_fraction")
COMPLETION_CONDITIONAL = (
    "slo_violation_rate", "weighted_goodput", "mean_latency", "p95_latency",
    "request_throughput", "token_throughput",
)
REGIONS = {"LOW", "PRE_KNEE", "KNEE", "POST_KNEE", "OVERLOAD", "HIGH_PRESSURE"}
SOURCES = {"burstgpt", "azure_llm_2024", "bailian_qwen"}
PRIMARY_COUNTS = {
    "pairwise_reversals": 10890, "ranking_correlations": 198, "sample_complexity": 33,
    "telemetry_explanation": 990, "temporal_robustness": 36, "topk_overlap": 198,
}
ANALYSIS_KEYS = {
    "pairwise_reversals": "records", "ranking_correlations": "comparisons",
    "sample_complexity": "per_source_metric", "telemetry_explanation": "records",
    "temporal_robustness": "records", "topk_overlap": "comparisons",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def equal(a, b) -> bool:
    if isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b):
        return True
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(equal(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
    return type(a) is type(b) and a == b


def normalized_number(value):
    if isinstance(value, decimal.Decimal):
        return {"number": "NaN" if value.is_nan() else str(value.normalize())}
    if isinstance(value, dict):
        return {key: normalized_number(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [normalized_number(item) for item in value]
    return value


def result_projection(row: dict) -> dict:
    return {
        "cell_id": row["cell_id"],
        "metrics": {key: normalized_number(row.get(key)) for key in METRICS},
        "telemetry": normalized_number(row.get("telemetry")),
    }


def projected_hash(rows: list[dict]) -> str:
    payload = [result_projection(row) for row in sorted(rows, key=lambda item: item["cell_id"])]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def source_analysis_rows(name: str, data: dict) -> list[dict]:
    source = data[ANALYSIS_KEYS[name]]
    if isinstance(source, dict):
        rows = []
        for metric, values in source.items():
            for value in values:
                row = dict(value)
                row.setdefault("metric", metric)
                assert row["metric"] == metric
                rows.append(row)
        return rows
    return source


def validate_inventory(problems: list[str]) -> dict:
    allow_path = ROOT / "release" / "ALLOWLIST.txt"
    sums_path = ROOT / "checksums" / "v1.1.0.sha256"
    if not allow_path.exists() or not sums_path.exists():
        problems.append("release allowlist/checksum ledger missing")
        return {}
    allowed = {line.strip() for line in allow_path.read_text().splitlines() if line.strip() and not line.startswith("#")}
    actual = {str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file()}
    if allowed != actual:
        problems.append(f"allowlist differs: missing={sorted(allowed-actual)}, extra={sorted(actual-allowed)}")
    sums = {}
    for line in sums_path.read_text().splitlines():
        digest, rel = line.split("  ", 1)
        sums[rel] = digest
    if set(sums) != actual - {str(sums_path.relative_to(ROOT))}:
        problems.append("checksum ledger paths do not cover every non-self file")
    bad = [rel for rel, expected in sums.items() if not (ROOT / rel).is_file() or sha(ROOT / rel) != expected]
    if bad:
        problems.append(f"checksum mismatch/missing: {bad[:12]}")
    return {"allowlisted_files": len(allowed), "checksum_entries": len(sums), "checksum_mismatches": len(bad)}


def validate_package(verify_public_smoke: bool) -> dict:
    problems: list[str] = []
    report: dict = {}
    report["inventory"] = validate_inventory(problems)
    bad_source_hashes = [rel for rel, expected in SOURCE_HASHES.items() if sha(ROOT / rel) != expected]
    if bad_source_hashes:
        problems.append(f"frozen source hashes differ: {bad_source_hashes}")
    report["frozen_scientific_file_hashes_valid"] = len(bad_source_hashes) == 0

    matrix = json.loads((ROOT / "scientific/campaign/consolidated.json").read_text())
    cells = matrix["cells"]
    freeze = json.loads((ROOT / "manifests/ranking_portability_phase12_campaign_freeze.json").read_text())
    admission = json.loads((ROOT / "manifests/ranking_portability_phase12_analysis_input.json").read_text())
    amended = json.loads((ROOT / "validation/phase12_amended_matrix_validation.json").read_text())
    ids = [row["cell_id"] for row in cells]
    frozen_ids = {row["cell_id"] for row in freeze["cells"]}
    if len(cells) != 18720 or len(ids) != len(set(ids)) or set(ids) != frozen_ids:
        problems.append("matrix count, uniqueness, or frozen cell-id set invalid")
    if len({row["window_id"] for row in cells}) != 120:
        problems.append("window count invalid")
    if {row["source_family"] for row in cells} != SOURCES:
        problems.append("source families invalid")
    if {row["load_region"] for row in cells} != REGIONS:
        problems.append("region set invalid")
    if {row["policy_id"] for row in cells} != set(freeze["campaign_policies"]):
        problems.append("policy set invalid")
    if len({row["synthesis_seed"] for row in cells}) != 40:
        problems.append("synthesis-seed count invalid")
    if len({row["simulator_config_hash"] for row in cells}) != 1:
        problems.append("simulator config hashes inconsistent")
    if {row["repo_sha"] for row in cells} != {EXECUTION_SHA}:
        problems.append("execution code identity inconsistent")
    for object_name, obj in (("matrix", matrix), ("freeze", freeze), ("admission", admission), ("amended validation", amended)):
        if obj.get("campaign_freeze_sha256") != FREEZE:
            problems.append(f"{object_name}: campaign freeze identity differs")
    if matrix.get("full_matrix_hash") != FULL_MATRIX_HASH or freeze.get("full_matrix_hash") != FULL_MATRIX_HASH:
        problems.append("full matrix hash differs")
    if admission.get("consolidated_artifact_sha256") != SOURCE_HASHES["scientific/campaign/consolidated.json"]:
        problems.append("admission manifest points to another matrix")
    if admission.get("completed_matrix_validator_sha256") != VALIDATOR_SHA:
        problems.append("admission validator source hash differs")
    if not amended.get("PHASE12_COMPLETED_CAMPAIGN_VALID") or amended.get("problems") != []:
        problems.append("amended matrix validation does not pass")
    if amended.get("actual_unique_cells") != 18720 or amended.get("successful_cells") != 18720:
        problems.append("amended matrix validation counts differ")
    if amended.get("consolidated_artifact_sha256") != SOURCE_HASHES["scientific/campaign/consolidated.json"]:
        problems.append("amended validator matrix hash differs")
    if amended.get("independently_recomputed_full_matrix_hash") != FULL_MATRIX_HASH:
        problems.append("amended validator full matrix hash differs")

    expected_schema = {
        "arrival_normalized_weighted_goodput", "calibration_manifest_sha256", "cell_id", "completion_fraction",
        "environment", "error_category", "error_detail", "load_factor", "load_region", "mean_latency",
        "mean_ttft", "p95_latency", "p95_ttft", "phase11_raw_fifo_calibration_sha256",
        "phase11_region_assignments_sha256", "policy_id", "policy_registry_hash", "repetition", "repo_sha",
        "request_throughput", "schema_version", "scientific_status", "simulator_config_hash",
        "slo_violation_rate", "source_family", "success", "synthesis_seed", "synthesis_version",
        "telemetry", "telemetry_schema_version", "token_throughput", "weighted_completion_fraction",
        "weighted_goodput", "window_id", "window_manifest_sha256",
    }
    telemetry_schema = {
        "admission_control_activations", "batch_saturation_max", "batch_saturation_mean", "kv_occupancy_max",
        "kv_occupancy_mean", "n_steps", "preemption_or_reorder_events", "prefill_decode_contention_fraction",
        "queue_depth_max", "queue_depth_mean", "schema_version", "token_budget_saturation_fraction",
    }
    group: dict[tuple, dict[int, dict]] = defaultdict(dict)
    undefined = 0
    for row in cells:
        if set(row) != expected_schema or set(row["telemetry"]) != telemetry_schema:
            problems.append(f"row schema differs: {row.get('cell_id')}")
            break
        if row["schema_version"] != "ranking_portability_cell_result_v1" or row["telemetry_schema_version"] != "ranking_portability_telemetry_v1":
            problems.append(f"row version differs: {row['cell_id']}")
        if row["success"] is not True or row["scientific_status"] != "PILOT_V2_SCIENTIFIC":
            problems.append(f"non-scientific/failed cell: {row['cell_id']}")
        if any(not isinstance(row[k], (int, float)) or not math.isfinite(row[k]) for k in ALWAYS_DEFINED):
            problems.append(f"always-defined metric invalid: {row['cell_id']}")
        conditional_nan = [k for k in COMPLETION_CONDITIONAL if isinstance(row[k], float) and math.isnan(row[k])]
        if conditional_nan and row["completion_fraction"] != 0:
            problems.append(f"conditional undefined metric with completion: {row['cell_id']}")
        if any(isinstance(row[k], float) and math.isnan(row[k]) for k in METRICS):
            undefined += 1
        key = (row["source_family"], row["window_id"], row["load_region"], row["policy_id"])
        if row["repetition"] in group[key]:
            problems.append(f"duplicate configuration repetition: {key}")
        group[key][row["repetition"]] = row
    if len(group) != 9360:
        problems.append("unique configuration count invalid")
    nonidentical = 0
    for reps in group.values():
        if set(reps) != {0, 1}:
            problems.append("missing deterministic pass")
            continue
        a = {k: v for k, v in reps[0].items() if k not in {"cell_id", "repetition"}}
        b = {k: v for k, v in reps[1].items() if k not in {"cell_id", "repetition"}}
        nonidentical += not equal(a, b)
    if nonidentical:
        problems.append(f"{nonidentical} deterministic pass pairs differ")
    if undefined != 422:
        problems.append(f"undefined metric row count {undefined}, expected 422")
    report["matrix"] = {"rows": len(cells), "unique_cell_ids": len(set(ids)), "configurations": len(group), "nonidentical_deterministic_pairs": nonidentical, "undefined_metric_rows": undefined}

    # Analysis identity/count checks never recompute the statistical results.
    analysis_data = {}
    internal_hashes = set()
    for name, expected_count in PRIMARY_COUNTS.items():
        data = json.loads((ROOT / "scientific/analysis" / f"{name}.json").read_text())
        analysis_data[name] = data
        rows = source_analysis_rows(name, data)
        if len(rows) != expected_count:
            problems.append(f"{name} record count {len(rows)}, expected {expected_count}")
        if data.get("campaign_freeze_sha256") != FREEZE or data.get("analysis_code_git_sha") != ANALYSIS_SHA:
            problems.append(f"{name} frozen analysis identity differs")
        internal_hashes.add(data.get("consolidated_result_sha256"))
    if len(internal_hashes) != 1:
        problems.append("analysis files disagree on internal input identity")
    report["canonical_analysis_counts"] = PRIMARY_COUNTS

    # Compare every Parquet row to its source object, with only documented
    # convenience aliases/JSON-encoding exceptions.
    views = {
        "scheduler_outcomes": cells,
        "workload_windows": json.loads((ROOT / "manifests/ranking_portability_pilot_v2_windows_index.json").read_text())["windows"],
        "load_region_assignments": json.loads((ROOT / "manifests/ranking_portability_phase11_region_assignments.json").read_text())["assignments"],
    }
    for name, data in analysis_data.items():
        views[name] = source_analysis_rows(name, data)
    views["unique_configurations"] = [
        {"source_family": key[0], "window_id": key[1], "load_region": key[2], "policy_id": key[3],
         "load_factor": reps[0]["load_factor"], "synthesis_seed": reps[0]["synthesis_seed"],
         "cell_id_rep0": reps[0]["cell_id"], "cell_id_rep1": reps[1]["cell_id"],
         "deterministic_passes_equal": True}
        for key, reps in sorted(group.items()) if set(reps) == {0, 1}
    ]
    view_counts = {}
    for name, source_rows in views.items():
        path = ROOT / "data/tables" / f"{name}.parquet"
        actual_rows = pq.read_table(path).to_pylist()
        view_counts[name] = len(actual_rows)
        if len(source_rows) != len(actual_rows):
            problems.append(f"{name} Parquet row count differs")
            continue
        for index, (source, actual) in enumerate(zip(source_rows, actual_rows)):
            actual = dict(actual)
            if name == "scheduler_outcomes":
                actual["environment"] = json.loads(actual.pop("environment_json"))
            elif name == "workload_windows":
                actual["descriptor"] = json.loads(actual.pop("descriptor_json"))
            elif name == "load_region_assignments":
                if actual.pop("source_family") != source["source"] or actual.pop("load_region") != source["region"]:
                    problems.append(f"region assignment alias differs at {index}")
            if name in PRIMARY_COUNTS:
                if name == "topk_overlap":
                    if actual.pop("metric") != source["metric"]:
                        problems.append(f"topk_overlap metric alias differs at {index}")
                    source = {key: value for key, value in source.items() if key != "metric"}
                present = actual.pop("_source_keys")
                if sorted(source) != present:
                    problems.append(f"{name} source field list differs at {index}")
                actual = {key: actual[key] for key in present}
            if not equal(source, actual):
                problems.append(f"{name} Parquet row {index} differs from source")
                break
    policy_rows = pq.read_table(ROOT / "data/tables/policy_registry.parquet").to_pylist()
    if len(policy_rows) != 13 or {r["policy_id"] for r in policy_rows} != set(freeze["campaign_policies"]):
        problems.append("policy registry view differs from frozen panel")
    if sum(r["panel_status"] == "PRIMARY" for r in policy_rows) != 11:
        problems.append("policy registry PRIMARY count differs")
    view_counts["policy_registry"] = len(policy_rows)
    report["parquet_view_rows_checked"] = view_counts

    # Established public numerical overlap, with optional independent fetch.
    reference = json.loads((ROOT / "validation/public_smoke_overlap.json").read_text())
    shared_ids = set(reference["cell_ids"])
    if len(shared_ids) != 468 or not shared_ids <= set(ids):
        problems.append("public overlap key list invalid")
    matrix_raw = json.loads((ROOT / "scientific/campaign/consolidated.json").read_text(), parse_float=decimal.Decimal, parse_constant=decimal.Decimal)
    selected = [row for row in matrix_raw["cells"] if row["cell_id"] in shared_ids]
    selected_hash = projected_hash(selected)
    if len(selected) != 468 or selected_hash != reference["normalized_keyed_metric_telemetry_sha256"]:
        problems.append("468-key metric/telemetry overlap projection differs")
    if verify_public_smoke:
        with urllib.request.urlopen(reference["public_url"], timeout=30) as response:
            public_bytes = response.read(2_000_000)
        if hashlib.sha256(public_bytes).hexdigest() != reference["public_sha256"]:
            problems.append("pinned public smoke file hash differs")
        else:
            smoke = json.loads(public_bytes, parse_float=decimal.Decimal, parse_constant=decimal.Decimal)
            if projected_hash(smoke["cells"]) != selected_hash:
                problems.append("pinned public smoke rows differ from 468 selected matrix outcomes")
    report["public_overlap"] = {"matching_keyed_outcomes": len(selected), "previously_unavailable_keyed_outcomes": len(cells)-len(selected), "normalized_projection_sha256": selected_hash, "pinned_public_source_fetched": verify_public_smoke}

    # Scientific payload/manifests may not contain original request text,
    # credentials, or workstation/HPC absolute paths.
    sensitive_key = re.compile(r"^(?:prompt|response|question|session_id|request_text|api_key|access_token|private_key)$", re.I)
    sensitive_string = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----|\b(?:ghp_|gho_|hf_|sk-)[A-Za-z0-9_-]{16,}|\bAKIA[A-Z0-9]{16}\b|/mmfs1/|/home/soroush/|/project/ikoutis/", re.I)
    scan_paths = list((ROOT / "scientific").rglob("*.json")) + list((ROOT / "manifests").rglob("*.json"))
    flagged = []
    def scan(value, location):
        if isinstance(value, dict):
            for key, item in value.items():
                if sensitive_key.fullmatch(key):
                    flagged.append(location + "." + key)
                scan(item, location + "." + key)
        elif isinstance(value, list):
            for item in value:
                scan(item, location + "[]")
        elif isinstance(value, str) and sensitive_string.search(value):
            flagged.append(location)
    for path in scan_paths:
        scan(json.loads(path.read_text()), str(path.relative_to(ROOT)))
    if flagged:
        problems.append(f"sensitive content flags: {flagged[:12]}")
    report["restricted_payload_scan"] = {"json_files_scanned": len(scan_paths), "flags": len(flagged)}

    # Existing v1 scientific payload bytes remain untouched in this staged
    # revision. README is intentionally replaced by the updated v1.1 card.
    legacy = json.loads((ROOT / "validation/legacy_v1_baseline.json").read_text())
    bad_legacy = [entry["path"] for entry in legacy["files"] if entry["path"] != "README.md" and sha(ROOT / entry["path"]) != entry["sha256"]]
    if bad_legacy:
        problems.append(f"v1 existing files changed: {bad_legacy}")
    report["v1_unchanged_files"] = len(legacy["files"]) - 1 - len(bad_legacy)

    report["problems"] = problems
    report["release_candidate_valid"] = not problems
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-public-smoke", action="store_true", help="Fetch and verify pinned public GitHub smoke JSON")
    args = parser.parse_args()
    result = validate_package(args.verify_public_smoke)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["release_candidate_valid"] else 1)
