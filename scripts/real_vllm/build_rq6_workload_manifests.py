#!/usr/bin/env python3
"""Build the three frozen RQ6 real-vLLM workload manifests (azure_llm_2024,
burstgpt, bailian_qwen), per docs/RQ6_REAL_VLLM_SCIENTIFIC_PROTOCOL_20260902.md
("Statistics" section) and docs/RQ6_REAL_VLLM_WORKLOAD_MANIFEST_CONTRACT_20260902.md.

For each source: reads the verified authoritative Phase-12 window cache
(120 real windows, 40/source, 200 requests/window), applies the exact same
Stage-0 synthesis overlay (`stage0_synthesis_v1`) and the exact same
per-window HIGH_PRESSURE rebase/scale (`_rebase_and_scale` at each window's
own `1.5 x lambda_ref`) already used to produce the frozen Phase-12
campaign result that RQ6's case selection is drawn from. Each window is
kept as an INDEPENDENT episode, never concatenated with any other window:
Phase-12's own `execute_cell.py` constructs a fresh `Simulator` + calls
`policy.reset()` per (source, window, region, policy, repetition) cell, and
`ranking_portability/analysis/ranking_analysis.py` bootstrap-resamples over
windows as the independent experimental unit -- so the real-vLLM manifest
mirrors that: all 40 windows are retained (no window dropped, no
subsampling), each with its own local arrival timeline starting at its own
t=0.

Every synthesized field (priority/class_id/predicted_output_tokens/
slo_deadline) is carried through from the exact frozen synthesis contract,
never resynthesized independently. Prompt *text* is unavailable in any
upstream artifact (see docs/DATA_FIELD_PROVENANCE.md); each request gets a
deterministic tokenizer-exact-length-matched prompt, reconstructed from a
recorded seed + contract rather than stored verbatim (see
`calibration_common.build_exact_length_prompt`).

Does NOT execute any scheduler policy and does NOT touch Wulver/vLLM.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.calibration.stage0_load_calibration import _rebase_and_scale  # noqa: E402
from robustbench.real_llm.calibration_common import (  # noqa: E402
    build_exact_length_prompt,
    verify_exact_length_prompt,
)
from robustbench.workloads.external.benchmark_synthesis import (  # noqa: E402
    SYNTHESIS_VERSION,
    synthesize_requests_from_window,
)
from robustbench.workloads.external.schema import ExternalWorkloadRecord  # noqa: E402

SCHEMA_VERSION = "rq6_real_vllm_workload_manifest_v1"
MANIFEST_ROLE = "RQ6_REAL_VLLM_FROZEN_WORKLOAD"

SOURCES = ["azure_llm_2024", "burstgpt", "bailian_qwen"]
N_WINDOWS_PER_SOURCE = 40
WINDOW_SIZE = 200
LOAD_REGION = "HIGH_PRESSURE"
DEFAULT_TOKENIZER = "Qwen/Qwen2.5-0.5B-Instruct"

# --- Immutable-hash safety gate -------------------------------------------
# Citations: docs/ARTIFACT_HASH_LEDGER.md ("Phase-10 compact index hash" row)
# for the compact index; the other three are this repo's own committed
# files, hash-pinned to their content as of this branch (re-derive with
# `git show <path> | sha256sum` if this script ever needs updating after a
# legitimate re-freeze).
EXPECTED_COMPACT_INDEX_SHA256 = "d78ec1087fedae02174ca093a9860c70468be336ccb1d7e6de756c81ba331e53"
EXPECTED_CAMPAIGN_FREEZE_SHA256 = "44a81e98d9a3fa6646bd716125726bf732530d243a54d0952e98b20fda1d564a"
EXPECTED_CASE_SELECTION_SHA256 = "f34e1c6a9f8d4c695720d14f7929741594ac8f7818a427db832933554e909e5a"
EXPECTED_CALIBRATION_MANIFEST_SHA256 = "417dd8d3d07e770c4629beb59d3116b832516d3f59b7230b9a39b93eb7f65d2d"

DEFAULT_COMPACT_INDEX = REPO_ROOT / "artifacts/manifests/ranking_portability_pilot_v2_windows_index.json"
DEFAULT_CAMPAIGN_FREEZE = REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_campaign_freeze.json"
DEFAULT_CASE_SELECTION = REPO_ROOT / "artifacts/manifests/phase12_rq6_case_selection_20260902.json"
DEFAULT_CALIBRATION_MANIFEST = REPO_ROOT / "configs/real_vllm/rq6_calibration_manifest_20260902.json"
DEFAULT_OUT_DIR = REPO_ROOT / "artifacts/manifests/rq6_real_vllm"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _canonical_hash(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).decode().strip()


def _window_content_sha256(records: List[dict]) -> str:
    """Identical formula to scripts/ranking_portability/build_pilot_v2_windows.py
    (per-window content_sha256), so cache windows can be cross-checked
    against the compact index / campaign freeze at the correct semantic
    level (not the top-level file hash, which is a different artifact --
    see the STOPPING checks below)."""
    return hashlib.sha256(json.dumps(records, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class HashMismatchError(ValueError):
    pass


def load_and_verify_inputs(
    *, cache_path: Path, compact_index_path: Path, campaign_freeze_path: Path,
    case_selection_path: Path, calibration_manifest_path: Path,
) -> Dict[str, Any]:
    """Loads the four committed frozen inputs plus the uncommitted
    regenerable cache, verifying provenance at the correct artifact/
    serialization level for each (see docs/RQ6_REAL_VLLM_SCIENTIFIC_
    PROTOCOL_20260902.md and the case-selection doc's hash-correction note
    for why these are NOT interchangeable hashes). Raises HashMismatchError
    -- STOPPING -- on any mismatch rather than silently proceeding.
    """
    problems: List[str] = []

    compact_sha = _sha256_file(compact_index_path)
    if compact_sha != EXPECTED_COMPACT_INDEX_SHA256:
        problems.append(f"compact index hash mismatch: expected {EXPECTED_COMPACT_INDEX_SHA256}, got {compact_sha}")

    campaign_sha = _sha256_file(campaign_freeze_path)
    if campaign_sha != EXPECTED_CAMPAIGN_FREEZE_SHA256:
        problems.append(f"campaign freeze hash mismatch: expected {EXPECTED_CAMPAIGN_FREEZE_SHA256}, got {campaign_sha}")

    case_sha = _sha256_file(case_selection_path)
    if case_sha != EXPECTED_CASE_SELECTION_SHA256:
        problems.append(f"case selection manifest hash mismatch: expected {EXPECTED_CASE_SELECTION_SHA256}, got {case_sha}")

    calib_sha = _sha256_file(calibration_manifest_path)
    if calib_sha != EXPECTED_CALIBRATION_MANIFEST_SHA256:
        problems.append(f"calibration manifest hash mismatch: expected {EXPECTED_CALIBRATION_MANIFEST_SHA256}, got {calib_sha}")

    if problems:
        raise HashMismatchError("STOPPING before reading cache content:\n" + "\n".join(problems))

    with open(compact_index_path) as f:
        compact_index = json.load(f)
    with open(campaign_freeze_path) as f:
        campaign_freeze = json.load(f)
    with open(case_selection_path) as f:
        case_selection = json.load(f)

    cache_sha256_raw = _sha256_file(cache_path)
    with open(cache_path) as f:
        cache = json.load(f)

    # --- Per-window cross-artifact hash chain (the actually load-bearing
    # provenance check -- NOT the cache's own top-level `content_sha256`
    # field, which was found stale/mislabeled: it equals the unrelated
    # legacy Phase-10 git-freeze identifier from docs/ARTIFACT_HASH_LEDGER.md,
    # not a genuine recomputed hash of this file. Per-window content_sha256
    # is the correct, semantically-matched comparison and is what
    # campaign_freeze.json's own window_identities actually stores.) ---
    compact_by_id = {w["window_id"]: w for w in compact_index["windows"]}
    window_identities = campaign_freeze["window_identities"]
    seen_ids = set()
    for w in cache["windows"]:
        wid = w["window_id"]
        if wid in seen_ids:
            problems.append(f"duplicate window_id in cache: {wid}")
        seen_ids.add(wid)
        if w["request_count"] != WINDOW_SIZE or len(w["records"]) != WINDOW_SIZE:
            problems.append(f"{wid}: expected {WINDOW_SIZE} requests, got request_count={w['request_count']} len(records)={len(w['records'])}")
        recomputed = _window_content_sha256(w["records"])
        embedded = w.get("content_sha256")
        if recomputed != embedded:
            problems.append(f"{wid}: cache self-consistency FAIL recomputed={recomputed} embedded={embedded}")
        compact_w = compact_by_id.get(wid)
        if compact_w is None:
            problems.append(f"{wid}: missing from compact index")
        elif compact_w["content_sha256"] != embedded:
            problems.append(f"{wid}: cache vs compact index content_sha256 mismatch")
        campaign_hash = window_identities.get(wid)
        if campaign_hash is None:
            problems.append(f"{wid}: missing from campaign_freeze window_identities")
        elif campaign_hash != embedded:
            problems.append(f"{wid}: cache vs campaign_freeze window_identities mismatch")

    expected_ids = set(window_identities.keys())
    if seen_ids != expected_ids:
        problems.append(
            f"window ID set mismatch: in campaign but not cache={sorted(expected_ids - seen_ids)}, "
            f"in cache but not campaign={sorted(seen_ids - expected_ids)}"
        )

    from collections import Counter
    counts = Counter(w["source_family"] for w in cache["windows"])
    for source in SOURCES:
        if counts.get(source) != N_WINDOWS_PER_SOURCE:
            problems.append(f"{source}: expected {N_WINDOWS_PER_SOURCE} windows, got {counts.get(source, 0)}")
    if set(counts) != set(SOURCES):
        problems.append(f"unexpected source set in cache: {set(counts)} != {set(SOURCES)}")

    if problems:
        raise HashMismatchError("STOPPING -- cache provenance verification failed:\n" + "\n".join(problems))

    return {
        "cache": cache,
        "cache_sha256_raw": cache_sha256_raw,
        "compact_index": compact_index,
        "compact_index_sha256": compact_sha,
        "campaign_freeze": campaign_freeze,
        "campaign_freeze_sha256": campaign_sha,
        "case_selection": case_selection,
        "case_selection_sha256": case_sha,
        "calibration_manifest_sha256": calib_sha,
    }


def _synthesis_seeds_by_window(campaign_freeze: dict) -> Dict[str, int]:
    seeds: Dict[str, int] = {}
    for c in campaign_freeze["cells"]:
        wid = c["window_id"]
        seed = c["synthesis_seed"]
        if wid in seeds and seeds[wid] != seed:
            raise HashMismatchError(f"{wid}: inconsistent synthesis_seed across cells ({seeds[wid]} vs {seed})")
        seeds[wid] = seed
    return seeds


def _prompt_seed_for_request(derived_record_id: str) -> int:
    """Stable, deterministic per-request prompt seed derived from the
    request's stable identity (not the simulator's own locally-reset
    `Request.request_id`, per docs/RQ6_REAL_VLLM_SCIENTIFIC_PROTOCOL_
    20260902.md's "Stable request identity" finding)."""
    return int(hashlib.sha256(derived_record_id.encode()).hexdigest()[:8], 16)


def build_source_manifest(
    source: str, *, cache: dict, campaign_freeze: dict, tokenizer: Any, tokenizer_name: str,
    generation_code_sha: str, verify_prompts: bool,
) -> Dict[str, Any]:
    windows_by_id = {w["window_id"]: w for w in cache["windows"] if w["source_family"] == source}
    window_ids = sorted(windows_by_id.keys())
    if len(window_ids) != N_WINDOWS_PER_SOURCE:
        raise HashMismatchError(f"{source}: expected {N_WINDOWS_PER_SOURCE} windows, got {len(window_ids)}")

    synthesis_seeds = _synthesis_seeds_by_window(campaign_freeze)
    region_assignment_index = campaign_freeze["region_assignment_index"]

    windows_out: List[Dict[str, Any]] = []
    n_exact_match = 0
    n_total = 0

    for wid in window_ids:
        w = windows_by_id[wid]
        records = [ExternalWorkloadRecord(**r) for r in w["records"]]
        seed = synthesis_seeds[wid]
        base_requests, synth_manifest = synthesize_requests_from_window(records, window_id=wid, seed=seed)
        if len(base_requests) != WINDOW_SIZE:
            raise HashMismatchError(
                f"{wid}: synthesis produced {len(base_requests)} requests, expected {WINDOW_SIZE} "
                f"(n_records_dropped_invalid={synth_manifest.n_records_dropped_invalid})"
            )

        assignment_key = f"{source}::{wid}::{LOAD_REGION}"
        assignment = region_assignment_index[assignment_key]
        scaled = _rebase_and_scale(base_requests, float(assignment["absolute_load_factor"]))

        # Stable per-window request identity: derived_record_id, in the
        # same (arrival-sorted) order synthesize_requests_from_window used
        # (it re-sorts by arrival_time_s before assigning local index i).
        sorted_records = sorted(
            [r for r in records if r.arrival_time_s is not None and r.input_tokens and r.input_tokens > 0
             and r.output_tokens and r.output_tokens > 0],
            key=lambda r: r.arrival_time_s,
        )
        assert len(sorted_records) == len(scaled)

        requests_out = []
        for i, (rec, req) in enumerate(zip(sorted_records, scaled)):
            # Each window is an INDEPENDENT episode (Phase-12's own
            # execute_cell.py constructs a fresh Simulator + policy.reset()
            # per (source, window, region, policy, repetition) cell -- see
            # docs/RQ6_REAL_VLLM_SCIENTIFIC_PROTOCOL_20260902.md's
            # "Execution unit -- corrected 2026-09-03"). No cross-window
            # arrival offset: every window's own arrival timeline starts at
            # its own t=0, exactly mirroring the frozen simulator campaign.
            arrival = req.arrival_time
            deadline = req.slo_deadline
            prompt_seed = _prompt_seed_for_request(rec.derived_record_id)
            exact_match = None
            if verify_prompts:
                prompt_text = build_exact_length_prompt(tokenizer, req.prompt_tokens, prompt_seed)
                exact_match = verify_exact_length_prompt(tokenizer, prompt_text, req.prompt_tokens)
                n_total += 1
                n_exact_match += int(exact_match)
            requests_out.append({
                "request_id": rec.derived_record_id,
                "window_id": wid,
                "request_index": i,
                "base_relative_arrival_s": arrival,
                "base_slo_deadline_s": deadline,
                "input_tokens": req.prompt_tokens,
                "output_tokens_target": req.actual_output_tokens,
                "predicted_output_tokens": req.predicted_output_tokens,
                "priority": req.priority,
                "weight": req.priority,
                "class_id": req.class_id,
                "prompt_generation_seed": prompt_seed,
                "source_record_id": rec.source_record_id,
            })

        windows_out.append({
            "window_id": wid,
            "evidence_class": w["evidence_class"],
            "source_file": w["source_file"],
            "source_file_sha256": w["source_file_sha256"],
            "sampling_algorithm": w["sampling_algorithm"],
            "sampling_seed": w["sampling_seed"],
            "content_sha256": w["content_sha256"],
            "synthesis_seed": seed,
            "region_assignment_key": assignment_key,
            "lambda_ref": assignment["lambda_ref"],
            "selected_load_factor": assignment["selected_load_factor"],
            "absolute_load_factor": assignment["absolute_load_factor"],
            "n_requests": len(requests_out),
            "requests": requests_out,
        })

    total_requests = sum(w["n_requests"] for w in windows_out)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "manifest_role": MANIFEST_ROLE,
        "source": source,
        "load_region": LOAD_REGION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_sha": _git_sha(),
        "generation_code_sha": generation_code_sha,
        "synthesis_version": SYNTHESIS_VERSION,
        "window_execution_unit": "40_independent_window_episodes_per_source",
        "window_execution_unit_note": (
            "Corrected 2026-09-03 from an earlier draft that concatenated all "
            "40 windows into one continuous 8000-request trace per source. "
            "Forensic inspection of Phase-12's own execution code "
            "(src/robustbench/ranking_portability/execute_cell.py) found each "
            "(source, window, load_region, policy, repetition) cell "
            "constructs a FRESH Simulator instance and calls policy.reset() "
            "before running -- i.e. each of the 40 frozen windows per source "
            "was executed as an independent episode with fresh scheduler/KV "
            "state, never concatenated. The analysis layer "
            "(ranking_portability/analysis/ranking_analysis.py) confirms this: "
            "'(policy,window) rows treated as independent', with bootstrap "
            "resampling performed OVER WINDOWS as the experimental unit. The "
            "real-vLLM manifest now mirrors this exactly: each window's "
            "requests are an independent episode, timed from its own local "
            "t=0, never offset by any other window."
        ),
        "timing_transform_formula": (
            "base_relative_arrival_s: per-window arrival rebased to window-local "
            "t=0, scaled by _rebase_and_scale(requests, absolute_load_factor) "
            "(absolute_load_factor = 1.5 x that window's own lambda_ref, from "
            "region_assignment_index). Each window is independent -- there is "
            "no concatenation offset. This is the frozen per-window "
            "HIGH_PRESSURE trace SHAPE, not a real-engine rate -- the "
            "calibration runner applies a further real_arrival_i = "
            "base_relative_arrival_i / s and real_slo_deadline_i = "
            "real_arrival_i + (base_slo_deadline_i - base_relative_arrival_i) "
            "/ s for its own hardware-measured per-window candidate scale s, "
            "never reusing the simulator's absolute lambda_ref as a "
            "real-engine rate."
        ),
        "prompt_reconstruction_contract": {
            "method": "deterministic tokenizer-exact-length-matched synthetic text",
            "function": "robustbench.real_llm.calibration_common.build_exact_length_prompt",
            "tokenizer": tokenizer_name,
            "disclosure": (
                "Original prompt text was unavailable in the trace-derived Phase-12 "
                "workload representation; real-vLLM validation therefore uses "
                "deterministic tokenizer-length-matched executable prompts while "
                "preserving frozen request timing and token-length descriptors. "
                "This is a threat to external validity: real token content differs "
                "from the source trace even though token counts match exactly."
            ),
        },
        "output_token_execution_contract": (
            "output_tokens_target (= frozen actual_output_tokens, ground truth) is "
            "the value the calibration runner must send as vLLM's max_tokens with "
            "ignore_eos=true, so the real server reproduces the frozen trace's "
            "decode-length footprint exactly rather than stopping at a natural "
            "EOS. predicted_output_tokens is carried through separately as the "
            "SYNTHESIZED_IMPUTED length *estimate* available to prediction-aware "
            "policies (docs/DATA_FIELD_PROVENANCE.md) -- never used as the "
            "execution cap itself."
        ),
        "provenance": {
            "phase12_campaign_freeze_path": "artifacts/manifests/ranking_portability_phase12_campaign_freeze.json",
            "phase12_campaign_freeze_sha256": EXPECTED_CAMPAIGN_FREEZE_SHA256,
            "phase12_window_compact_index_path": "artifacts/manifests/ranking_portability_pilot_v2_windows_index.json",
            "phase12_window_compact_index_sha256": EXPECTED_COMPACT_INDEX_SHA256,
            "case_selection_manifest_path": "artifacts/manifests/phase12_rq6_case_selection_20260902.json",
            "case_selection_manifest_sha256": EXPECTED_CASE_SELECTION_SHA256,
            "calibration_manifest_path": "configs/real_vllm/rq6_calibration_manifest_20260902.json",
            "calibration_manifest_sha256": EXPECTED_CALIBRATION_MANIFEST_SHA256,
            "note": (
                "The 120-window full-request cache (pilot_v2_windows_full_cache.json) "
                "is an un-committed, regenerable local artifact; its provenance is "
                "verified per-window against phase12_window_compact_index's and "
                "phase12_campaign_freeze's window_identities content_sha256 (not "
                "its own top-level content_sha256 field, which is a stale/mislabeled "
                "carry-over of an unrelated legacy Phase-10 identifier -- see "
                "docs/RQ6_REAL_VLLM_SCIENTIFIC_PROTOCOL_20260902.md)."
            ),
        },
        "window_count": len(windows_out),
        "request_count": total_requests,
        "prompt_exact_length_match_rate": (n_exact_match / n_total) if n_total else None,
        "windows": windows_out,
    }
    # Canonical content hash excluding generated_at_utc (same convention as
    # scripts/ranking_portability/build_pilot_v2_windows.py's
    # _canonical_content_sha256), so re-running the generator against the
    # same inputs reproduces an identical scientific identity even though
    # the raw file's timestamp differs run to run.
    payload = {k: v for k, v in manifest.items() if k != "generated_at_utc"}
    manifest["content_sha256"] = _canonical_hash(payload)
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cache", type=Path, required=True, help="Path to pilot_v2_windows_full_cache.json")
    ap.add_argument("--compact-index", type=Path, default=DEFAULT_COMPACT_INDEX)
    ap.add_argument("--campaign-freeze", type=Path, default=DEFAULT_CAMPAIGN_FREEZE)
    ap.add_argument("--case-selection", type=Path, default=DEFAULT_CASE_SELECTION)
    ap.add_argument("--calibration-manifest", type=Path, default=DEFAULT_CALIBRATION_MANIFEST)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--tokenizer", default=DEFAULT_TOKENIZER)
    ap.add_argument("--no-verify-prompts", action="store_true",
                     help="Skip per-request exact-length verification (much faster; for smoke use only).")
    args = ap.parse_args()

    verified = load_and_verify_inputs(
        cache_path=args.cache,
        compact_index_path=args.compact_index,
        campaign_freeze_path=args.campaign_freeze,
        case_selection_path=args.case_selection,
        calibration_manifest_path=args.calibration_manifest,
    )
    print(f"Cache verified: {verified['cache_sha256_raw']} (120/120 windows, per-window hash chain OK)", file=sys.stderr)

    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer)

    generation_code_sha = _sha256_file(Path(__file__))
    args.out_dir.mkdir(parents=True, exist_ok=True)

    manifest_hashes = {}
    for source in SOURCES:
        print(f"[{source}] synthesizing + scaling 40 independent window episodes...", file=sys.stderr)
        manifest = build_source_manifest(
            source,
            cache=verified["cache"],
            campaign_freeze=verified["campaign_freeze"],
            tokenizer=tokenizer,
            tokenizer_name=args.tokenizer,
            generation_code_sha=generation_code_sha,
            verify_prompts=not args.no_verify_prompts,
        )
        out_path = args.out_dir / f"rq6_workload_{source}_20260903.json"
        with open(out_path, "w") as f:
            json.dump(manifest, f, sort_keys=True, separators=(",", ":"))
        sha = _sha256_file(out_path)
        manifest_hashes[source] = {"file_sha256": sha, "content_sha256": manifest["content_sha256"]}
        print(
            f"[{source}] wrote {out_path} windows={manifest['window_count']} "
            f"requests={manifest['request_count']} exact_match_rate="
            f"{manifest['prompt_exact_length_match_rate']} file_sha256={sha} "
            f"content_sha256={manifest['content_sha256']}",
            file=sys.stderr,
        )

    print(json.dumps(manifest_hashes, indent=2))


if __name__ == "__main__":
    main()
