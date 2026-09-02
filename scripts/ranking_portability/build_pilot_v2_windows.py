#!/usr/bin/env python3
"""Freeze the 120 real Pilot-V2 workload windows (40 azure_llm_2024 + 40
bailian_qwen + 40 burstgpt), per
docs/RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md section 4 and
docs/EVIDENCE_INDEPENDENCE_PLAN.md.

For each source: the 10 already-frozen Stage-0 windows
(`artifacts/manifests/stage0_windows.json`, read-only, never modified) are
copied VERBATIM as evidence_class=STAGE0_WINDOW, and exactly 30 new
windows are drawn from the same real source file's remaining valid-row
space, past the same offset, using the pinned-extension algorithm
(`robustbench.ranking_portability.window_sampling`) so they can never
overlap the original 10 -- evidence_class=PILOT_V2_NEW_WINDOW.

Must be run where the real source files live (this project does not copy
multi-GB raw datasets locally). Produces a single self-contained JSON
manifest embedding the actual extracted Layer-1 records for all 120
windows (a few thousand small records total), so downstream steps (load
calibration, telemetry collection) can run from the committed manifest
alone without touching the source files again.

Extension seeds (documented here, chosen before running against real
data, applied identically to every source -- symmetric by construction,
never tuned per source): `new_seed = stage0_seed + 1_000_000`.

Does NOT run load calibration, does NOT execute any scheduler policy, and
does NOT submit anything.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.descriptors.window_descriptors import compute_window_descriptor  # noqa: E402
from robustbench.ranking_portability.window_sampling import (  # noqa: E402
    PinnedRange,
    assert_no_overlap,
    select_extension_stride_windows,
)
from robustbench.workloads.external.adapters.azure_llm import AzureLLMAdapter  # noqa: E402
from robustbench.workloads.external.adapters.bailian import BailianAdapter  # noqa: E402
from robustbench.workloads.external.adapters.burstgpt import BurstGPTAdapter  # noqa: E402
from robustbench.workloads.external.burstgpt_independent_sampling import (  # noqa: E402
    BURSTGPT_OFFSET_VALID_ROWS,
    BURSTGPT_STAGE0_SEED,
    STAGE0_BURSTGPT_SOURCE_FILE,
    INDEPENDENCE_DISCLOSURE as BURSTGPT_INDEPENDENCE_DISCLOSURE,
)
from robustbench.workloads.external.schema import ExternalWorkloadRecord  # noqa: E402

WINDOW_SIZE = 200
N_STAGE0_WINDOWS = 10
N_NEW_WINDOWS = 30
N_TOTAL_PER_SOURCE = N_STAGE0_WINDOWS + N_NEW_WINDOWS
SEED_EXTENSION_OFFSET = 1_000_000  # applied identically to every source

AZURE_2024_CONV_OFFSET = 200_000
AZURE_2024_CONV_SEED = 20260902

BAILIAN_TRACEB_OFFSET = 50_000
BAILIAN_TRACEB_SEED = 20260903


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).decode().strip()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _canonical_content_sha256(manifest: dict) -> str:
    """Hash over the manifest with `generated_at_utc` excluded, so reruns
    at different wall-clock times still produce an identical scientific
    hash (docs/RANKING_PORTABILITY_WINDOW_FREEZE.md's reproducibility
    requirement)."""
    payload = {k: v for k, v in manifest.items() if k != "generated_at_utc"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _load_stage0_windows(stage0_manifest_path: Path, source_family: str) -> List[dict]:
    with open(stage0_manifest_path) as f:
        d = json.load(f)
    windows = [w for w in d["windows"] if w["source_family"] == source_family]
    assert len(windows) == N_STAGE0_WINDOWS, (
        f"expected {N_STAGE0_WINDOWS} frozen Stage-0 {source_family} windows, got {len(windows)}"
    )
    return windows


def _new_window_entry(
    source_family: str, window_id: str, records: List[ExternalWorkloadRecord],
    *, source_path: Path, source_sha256: str, sampling_algorithm: str, sampling_seed: int,
    offset_valid_rows: int, start_index: int, chronology_stratum: str,
) -> dict:
    descriptor = compute_window_descriptor(records, source_family=source_family, window_id=window_id)
    arrivals = sorted(r.arrival_time_s for r in records if r.arrival_time_s is not None)
    return {
        "window_id": window_id,
        "source_family": source_family,
        "evidence_class": "PILOT_V2_NEW_WINDOW",
        "source_file": source_path.name,
        "source_file_sha256": source_sha256,
        "sampling_algorithm": sampling_algorithm,
        "sampling_seed": sampling_seed,
        "offset_valid_rows": offset_valid_rows,
        "start_index_in_valid_rows": start_index,
        "request_count": len(records),
        "arrival_time_s_min": arrivals[0] if arrivals else None,
        "arrival_time_s_max": arrivals[-1] if arrivals else None,
        "chronology_stratum": chronology_stratum,
        "descriptor": asdict(descriptor),
        "records": [r.to_dict() for r in records],
    }


def _assign_temporal_strata(n: int) -> List[str]:
    """Deterministic EARLY/MIDDLE/LATE allocation by position (windows are
    already produced in ascending start-index / chronological order by
    construction) -- documented, fixed split, not chosen per source after
    seeing content. n=30 -> 10/10/10 exactly; documented remainder rule
    (extra windows go to LATE, then MIDDLE) covers any n not divisible by
    3, applied identically to every source."""
    base = n // 3
    rem = n % 3
    counts = [base, base, base]
    for i in range(rem):
        counts[2 - i] += 1  # LATE first, then MIDDLE
    strata = ["EARLY"] * counts[0] + ["MIDDLE"] * counts[1] + ["LATE"] * counts[2]
    assert len(strata) == n
    return strata


def _build_source(
    source_family: str, path: Path, adapter, *, offset: int, stage0_seed: int,
    stage0_windows: List[dict],
) -> tuple[List[dict], dict]:
    pinned = [
        PinnedRange(w["start_index_in_valid_rows"], w["start_index_in_valid_rows"] + w["request_count"])
        for w in stage0_windows
    ]
    new_seed = stage0_seed + SEED_EXTENSION_OFFSET
    new_windows, report = select_extension_stride_windows(
        lambda: adapter.stream_records(path),
        window_size=WINDOW_SIZE, n_new_windows=N_NEW_WINDOWS,
        offset_valid_rows=offset, seed=new_seed, pinned_ranges=pinned,
    )
    source_sha256 = _sha256_file(path)

    # Order new windows by start index (ascending = chronological for
    # sources with real timestamps; within-trace order for relative-time
    # sources) before assigning temporal strata.
    order = sorted(range(N_NEW_WINDOWS), key=lambda i: report["window_start_indices"][i])
    strata = _assign_temporal_strata(N_NEW_WINDOWS)

    entries = []
    for rank, i in enumerate(order):
        w_idx = N_STAGE0_WINDOWS + i  # window w10..w39
        entries.append(_new_window_entry(
            source_family, f"{source_family}_pilot_v2_w{w_idx:02d}", new_windows[i],
            source_path=path, source_sha256=source_sha256,
            sampling_algorithm=report["selection_algorithm_version"],
            sampling_seed=new_seed, offset_valid_rows=offset,
            start_index=report["window_start_indices"][i],
            chronology_stratum=strata[rank],
        ))

    # Re-tag the 10 verbatim Stage-0 entries with evidence_class + stratum
    # (EARLY, by convention -- they were the original, earliest-drawn
    # sample; documented, not a claim about their absolute timestamps).
    stage0_entries = []
    for w in stage0_windows:
        w2 = dict(w)
        w2["evidence_class"] = "STAGE0_WINDOW"
        w2["chronology_stratum"] = "EARLY"
        stage0_entries.append(w2)

    all_ranges = [(e["start_index_in_valid_rows"], e["start_index_in_valid_rows"] + e["request_count"])
                  for e in stage0_entries + entries]
    assert_no_overlap(all_ranges)

    return stage0_entries + entries, report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--burstgpt-path", required=True, type=Path)
    ap.add_argument("--azure-path", required=True, type=Path)
    ap.add_argument("--bailian-path", required=True, type=Path)
    ap.add_argument("--stage0-windows", required=True, type=Path,
                     help="Path to the existing, frozen artifacts/manifests/stage0_windows.json")
    ap.add_argument("--out", type=Path,
                     default=REPO_ROOT / "artifacts" / "manifests" / "ranking_portability_pilot_v2_windows.json")
    args = ap.parse_args()

    print(f"[1/3] BurstGPT: {N_STAGE0_WINDOWS} Stage-0 + {N_NEW_WINDOWS} new from {args.burstgpt_path}", file=sys.stderr)
    if args.burstgpt_path.name != STAGE0_BURSTGPT_SOURCE_FILE:
        raise ValueError(f"BurstGPT source must be {STAGE0_BURSTGPT_SOURCE_FILE}, got {args.burstgpt_path.name}")
    burstgpt_stage0 = _load_stage0_windows(args.stage0_windows, "burstgpt")
    burstgpt_windows, burstgpt_report = _build_source(
        "burstgpt", args.burstgpt_path, BurstGPTAdapter(),
        offset=BURSTGPT_OFFSET_VALID_ROWS, stage0_seed=BURSTGPT_STAGE0_SEED,
        stage0_windows=burstgpt_stage0,
    )

    print(f"[2/3] Azure-2024: {N_STAGE0_WINDOWS} Stage-0 + {N_NEW_WINDOWS} new from {args.azure_path}", file=sys.stderr)
    azure_stage0 = _load_stage0_windows(args.stage0_windows, "azure_llm_2024")
    azure_windows, azure_report = _build_source(
        "azure_llm_2024", args.azure_path, AzureLLMAdapter(split_name="conversation", dataset_year="2024"),
        offset=AZURE_2024_CONV_OFFSET, stage0_seed=AZURE_2024_CONV_SEED,
        stage0_windows=azure_stage0,
    )

    print(f"[3/3] Bailian/Qwen: {N_STAGE0_WINDOWS} Stage-0 + {N_NEW_WINDOWS} new from {args.bailian_path}", file=sys.stderr)
    bailian_stage0 = _load_stage0_windows(args.stage0_windows, "bailian_qwen")
    bailian_windows, bailian_report = _build_source(
        "bailian_qwen", args.bailian_path, BailianAdapter(),
        offset=BAILIAN_TRACEB_OFFSET, stage0_seed=BAILIAN_TRACEB_SEED,
        stage0_windows=bailian_stage0,
    )

    all_windows = burstgpt_windows + azure_windows + bailian_windows
    window_ids = [w["window_id"] for w in all_windows]
    assert len(window_ids) == 3 * N_TOTAL_PER_SOURCE, f"expected {3*N_TOTAL_PER_SOURCE} windows, got {len(window_ids)}"
    assert len(set(window_ids)) == len(window_ids), "duplicate window_id detected"
    for w in all_windows:
        assert w["request_count"] == WINDOW_SIZE, f"{w['window_id']} has {w['request_count']} requests"

    content_hashes = [hashlib.sha256(
        json.dumps(w["records"], sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest() for w in all_windows]
    assert len(set(content_hashes)) == len(content_hashes), "duplicate window content hash detected"
    for w, h in zip(all_windows, content_hashes):
        w["content_sha256"] = h

    manifest = {
        "manifest_kind": "ranking_portability_pilot_v2_windows",
        "dataset_name": "LLM-Serving Scheduler Portability Benchmark",
        "dataset_short_name": "LSSP Benchmark",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_sha": _git_sha(),
        "window_size": WINDOW_SIZE,
        "n_windows_per_source": N_TOTAL_PER_SOURCE,
        "n_stage0_windows_per_source": N_STAGE0_WINDOWS,
        "n_new_windows_per_source": N_NEW_WINDOWS,
        "n_sources": 3,
        "n_windows_total": len(all_windows),
        "seed_extension_offset": SEED_EXTENSION_OFFSET,
        "burstgpt_independence_disclosure": BURSTGPT_INDEPENDENCE_DISCLOSURE,
        "stage0_windows_manifest_sha256": _sha256_file(args.stage0_windows),
        "source_sampling_reports": {
            "burstgpt_extension": burstgpt_report,
            "azure_llm_2024_conversation_extension": azure_report,
            "bailian_qwen_traceB_extension": bailian_report,
        },
        "windows": all_windows,
    }
    manifest["content_sha256"] = _canonical_content_sha256(manifest)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(manifest, f, indent=2)

    manifest_sha256 = _sha256_file(args.out)
    print(f"Wrote {args.out} ({args.out.stat().st_size} bytes)", file=sys.stderr)
    print(f"manifest_sha256={manifest_sha256}")
    print(f"content_sha256={manifest['content_sha256']}")
    print(f"n_windows={len(all_windows)}")
    for source in ("burstgpt", "azure_llm_2024", "bailian_qwen"):
        n = sum(1 for w in all_windows if w["source_family"] == source)
        n_stage0 = sum(1 for w in all_windows if w["source_family"] == source and w["evidence_class"] == "STAGE0_WINDOW")
        n_new = sum(1 for w in all_windows if w["source_family"] == source and w["evidence_class"] == "PILOT_V2_NEW_WINDOW")
        print(f"  {source}: {n} windows ({n_stage0} STAGE0_WINDOW + {n_new} PILOT_V2_NEW_WINDOW)")


if __name__ == "__main__":
    main()
