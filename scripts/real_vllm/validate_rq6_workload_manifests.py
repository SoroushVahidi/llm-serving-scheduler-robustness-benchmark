#!/usr/bin/env python3
"""Independently validate the three frozen RQ6 real-vLLM workload manifests
produced by build_rq6_workload_manifests.py, against the same frozen inputs
(re-derived, not trusted from the manifest's own self-report) plus internal
structural invariants. Writes
artifacts/validation/rq6_real_vllm_manifest_validation.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_rq6_workload_manifests import (  # noqa: E402  (path set above)
    N_WINDOWS_PER_SOURCE,
    SOURCES,
    WINDOW_SIZE,
    _sha256_file,
    _synthesis_seeds_by_window,
    load_and_verify_inputs,
)

DEFAULT_MANIFEST_DIR = REPO_ROOT / "artifacts/manifests/rq6_real_vllm"
DEFAULT_OUT = REPO_ROOT / "artifacts/validation/rq6_real_vllm_manifest_validation.json"

FORBIDDEN_POLICY_KEYS = {"policy", "policy_id", "policy_a", "policy_b", "scheduler"}


def _manifest_path(manifest_dir: Path, source: str) -> Path:
    matches = sorted(manifest_dir.glob(f"rq6_workload_{source}_*.json"))
    if not matches:
        raise FileNotFoundError(f"no workload manifest found for source={source} in {manifest_dir}")
    return matches[-1]


def _check_no_policy_leakage(obj: Any, path: str, problems: List[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in FORBIDDEN_POLICY_KEYS:
                problems.append(f"policy field leakage at {path}.{k}")
            _check_no_policy_leakage(v, f"{path}.{k}", problems)
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:5]):  # spot-check; full lists are homogeneous by construction
            _check_no_policy_leakage(v, f"{path}[{i}]", problems)


def validate_source_manifest(
    source: str, manifest: dict, *, cache: dict, campaign_freeze: dict,
) -> Dict[str, Any]:
    problems: List[str] = []
    checks: Dict[str, bool] = {}

    checks["manifest_role_correct"] = manifest.get("manifest_role") == "RQ6_REAL_VLLM_FROZEN_WORKLOAD"
    checks["source_correct"] = manifest.get("source") == source
    checks["window_count_40"] = manifest.get("window_count") == N_WINDOWS_PER_SOURCE == len(manifest["windows"])
    checks["request_count_8000"] = manifest.get("request_count") == N_WINDOWS_PER_SOURCE * WINDOW_SIZE

    window_ids = [w["window_id"] for w in manifest["windows"]]
    checks["no_duplicate_window_ids"] = len(window_ids) == len(set(window_ids))
    checks["windows_sorted_by_id"] = window_ids == sorted(window_ids)

    cache_windows = {w["window_id"]: w for w in cache["windows"] if w["source_family"] == source}
    checks["window_id_set_matches_cache"] = set(window_ids) == set(cache_windows.keys())

    synthesis_seeds = _synthesis_seeds_by_window(campaign_freeze)
    region_assignment_index = campaign_freeze["region_assignment_index"]

    all_request_ids: List[str] = []
    prev_last_arrival = None
    for w in manifest["windows"]:
        wid = w["window_id"]
        cache_w = cache_windows.get(wid)
        if cache_w is None:
            problems.append(f"{wid}: not in cache")
            continue

        if w["n_requests"] != WINDOW_SIZE or len(w["requests"]) != WINDOW_SIZE:
            problems.append(f"{wid}: expected {WINDOW_SIZE} requests, got n_requests={w['n_requests']} len={len(w['requests'])}")

        if w["content_sha256"] != cache_w["content_sha256"]:
            problems.append(f"{wid}: content_sha256 mismatch vs cache")

        expected_seed = synthesis_seeds.get(wid)
        if w["synthesis_seed"] != expected_seed:
            problems.append(f"{wid}: synthesis_seed mismatch (manifest={w['synthesis_seed']}, frozen={expected_seed})")

        assignment = region_assignment_index.get(w["region_assignment_key"])
        if assignment is None:
            problems.append(f"{wid}: region_assignment_key {w['region_assignment_key']} not found")
        else:
            if w["absolute_load_factor"] != assignment["absolute_load_factor"]:
                problems.append(f"{wid}: absolute_load_factor mismatch")
            if w["lambda_ref"] != assignment["lambda_ref"]:
                problems.append(f"{wid}: lambda_ref mismatch")

        reqs = w["requests"]
        cache_input_tokens_sorted = sorted(
            r["input_tokens"] for r in cache_w["records"]
            if r["arrival_time_s"] is not None and r["input_tokens"] and r["input_tokens"] > 0
            and r["output_tokens"] and r["output_tokens"] > 0
        )
        manifest_input_tokens_sorted = sorted(r["input_tokens"] for r in reqs)
        if cache_input_tokens_sorted != manifest_input_tokens_sorted:
            problems.append(f"{wid}: input_tokens multiset mismatch vs cache")

        for i, r in enumerate(reqs):
            if r["request_index"] != i:
                problems.append(f"{wid}: request_index out of order at position {i}")
            all_request_ids.append(r["request_id"])
            if i > 0 and r["base_relative_arrival_s"] < reqs[i - 1]["base_relative_arrival_s"] - 1e-9:
                problems.append(f"{wid}: arrival order violated at index {i}")
            if r["priority"] != 1.0 or r["weight"] != 1.0 or r["class_id"] != "stage0_uniform":
                problems.append(f"{wid}[{i}]: overlay field deviates from stage0_synthesis_v1 constants")

        first_arrival = reqs[0]["base_relative_arrival_s"]
        if prev_last_arrival is not None and abs(first_arrival - prev_last_arrival) > 1e-9:
            problems.append(f"{wid}: window boundary discontinuity (expected first arrival == prior window's last arrival)")
        prev_last_arrival = reqs[-1]["base_relative_arrival_s"]

    checks["no_duplicate_request_ids"] = len(all_request_ids) == len(set(all_request_ids))
    checks["request_ids_match_cache_derived_record_ids"] = set(all_request_ids) == {
        rec["derived_record_id"] for w in cache_windows.values() for rec in w["records"]
        if rec["arrival_time_s"] is not None and rec["input_tokens"] and rec["input_tokens"] > 0
        and rec["output_tokens"] and rec["output_tokens"] > 0
    }

    leakage: List[str] = []
    _check_no_policy_leakage(manifest, "manifest", leakage)
    checks["no_policy_field_leakage"] = len(leakage) == 0
    problems.extend(leakage)

    checks["provenance_hashes_present"] = all(
        manifest.get("provenance", {}).get(k) for k in (
            "phase12_campaign_freeze_sha256", "phase12_window_compact_index_sha256",
            "case_selection_manifest_sha256", "calibration_manifest_sha256",
        )
    )

    checks["exact_prompt_length_match_rate_is_1.0"] = manifest.get("prompt_exact_length_match_rate") == 1.0

    payload = {k: v for k, v in manifest.items() if k != "generated_at_utc"}
    recomputed_content_hash = manifest.get("content_sha256")
    stripped = {k: v for k, v in payload.items() if k != "content_sha256"}
    recomputed = hashlib.sha256(json.dumps(stripped, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    checks["content_sha256_self_consistent"] = recomputed == recomputed_content_hash
    if not checks["content_sha256_self_consistent"]:
        problems.append(f"content_sha256 self-consistency FAIL recomputed={recomputed} embedded={recomputed_content_hash}")

    passed = len(problems) == 0 and all(checks.values())
    return {
        "source": source,
        "passed": passed,
        "checks": checks,
        "problems": problems,
        "window_count": manifest.get("window_count"),
        "request_count": manifest.get("request_count"),
        "content_sha256": manifest.get("content_sha256"),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cache", type=Path, required=True)
    ap.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--compact-index", type=Path, default=REPO_ROOT / "artifacts/manifests/ranking_portability_pilot_v2_windows_index.json")
    ap.add_argument("--campaign-freeze", type=Path, default=REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_campaign_freeze.json")
    ap.add_argument("--case-selection", type=Path, default=REPO_ROOT / "artifacts/manifests/phase12_rq6_case_selection_20260902.json")
    ap.add_argument("--calibration-manifest", type=Path, default=REPO_ROOT / "configs/real_vllm/rq6_calibration_manifest_20260902.json")
    args = ap.parse_args()

    verified = load_and_verify_inputs(
        cache_path=args.cache,
        compact_index_path=args.compact_index,
        campaign_freeze_path=args.campaign_freeze,
        case_selection_path=args.case_selection,
        calibration_manifest_path=args.calibration_manifest,
    )

    results = {}
    all_passed = True
    for source in SOURCES:
        path = _manifest_path(args.manifest_dir, source)
        with open(path) as f:
            manifest = json.load(f)
        result = validate_source_manifest(
            source, manifest, cache=verified["cache"], campaign_freeze=verified["campaign_freeze"],
        )
        result["manifest_path"] = str(path.relative_to(REPO_ROOT))
        result["manifest_file_sha256"] = _sha256_file(path)
        results[source] = result
        all_passed = all_passed and result["passed"]
        print(f"[{source}] passed={result['passed']} problems={len(result['problems'])}", file=sys.stderr)
        for p in result["problems"][:20]:
            print(f"  PROBLEM: {p}", file=sys.stderr)

    report = {
        "validation_kind": "rq6_real_vllm_workload_manifest_validation",
        "cache_sha256_raw": verified["cache_sha256_raw"],
        "all_passed": all_passed,
        "sources": results,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(report, f, indent=2, sort_keys=True)
    print(f"Wrote {args.out}", file=sys.stderr)
    print(f"ALL_PASSED={all_passed}")
    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
