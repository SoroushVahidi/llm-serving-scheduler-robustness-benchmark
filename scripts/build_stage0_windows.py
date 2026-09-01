#!/usr/bin/env python3
"""Freeze the 30 real Stage-0 windows (10 Azure-2024 + 10 Bailian/Qwen + 10
independent BurstGPT), per docs/STAGE0_DISCRIMINABILITY_PROTOCOL.md and
docs/EVIDENCE_INDEPENDENCE_PLAN.md.

Must be run where the real source files live (this project does not copy
multi-GB raw datasets locally -- see docs/DATA_LICENSE_AUDIT.md). Produces a
single self-contained JSON manifest (`artifacts/manifests/stage0_windows.json`
by default) that embeds the actual extracted Layer-1 records for all 30
windows (a few thousand small records total -- not the raw multi-GB files),
so downstream steps (load calibration, the Stage-0 campaign itself) can run
from the committed manifest alone without touching the source files again.

Frozen per-source sampling parameters (documented here, not chosen after
seeing any result):

- BurstGPT: see robustbench.workloads.external.burstgpt_independent_sampling
  (file BurstGPT_without_fails_2.csv, offset 500,000 valid rows, seed
  20260901) -- the independence-motivated choice.
- Azure 2024: `conversation` split (larger of the two released splits;
  chosen for a bigger available-window pool, not for any scheduler-outcome
  reason), offset 200,000 valid rows, seed 20260902.
- Bailian/Qwen: `qwen_traceB_blksz_16.jsonl` (the larger of the two general
  to_b/to_c traces, avoiding the coder/thinking specialized traces so the
  Stage-0 sample represents general production traffic), offset 50,000
  valid rows, seed 20260903.

All three use window_size=200, n_windows=10, per
docs/STAGE0_DISCRIMINABILITY_PROTOCOL.md.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.descriptors.window_descriptors import compute_window_descriptor  # noqa: E402
from robustbench.workloads.external.adapters.azure_llm import AzureLLMAdapter  # noqa: E402
from robustbench.workloads.external.adapters.bailian import BailianAdapter  # noqa: E402
from robustbench.workloads.external.burstgpt_independent_sampling import (  # noqa: E402
    build_burstgpt_stage0_windows,
)
from robustbench.workloads.external.schema import ExternalWorkloadRecord  # noqa: E402
from robustbench.workloads.external.stage0_window_selection import (  # noqa: E402
    select_stride_windows,
)

WINDOW_SIZE = 200
N_WINDOWS = 10

AZURE_2024_CONV_OFFSET = 200_000
AZURE_2024_CONV_SEED = 20260902

BAILIAN_TRACEB_OFFSET = 50_000
BAILIAN_TRACEB_SEED = 20260903


def _git_sha() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT
    ).decode().strip()


def _sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _window_entry(
    source_family: str,
    window_id: str,
    records: List[ExternalWorkloadRecord],
    *,
    source_path: Path,
    source_sha256: str,
    sampling_algorithm: str,
    sampling_seed: int,
    offset_valid_rows: int,
    start_index: int,
) -> dict:
    descriptor = compute_window_descriptor(records, source_family=source_family, window_id=window_id)
    arrivals = sorted(r.arrival_time_s for r in records if r.arrival_time_s is not None)
    return {
        "window_id": window_id,
        "source_family": source_family,
        "source_file": source_path.name,
        "source_file_sha256": source_sha256,
        "sampling_algorithm": sampling_algorithm,
        "sampling_seed": sampling_seed,
        "offset_valid_rows": offset_valid_rows,
        "start_index_in_valid_rows": start_index,
        "request_count": len(records),
        "arrival_time_s_min": arrivals[0] if arrivals else None,
        "arrival_time_s_max": arrivals[-1] if arrivals else None,
        "descriptor": asdict(descriptor),
        "records": [r.to_dict() for r in records],
    }


def build_burstgpt(path: Path) -> List[dict]:
    windows, manifest = build_burstgpt_stage0_windows(path)
    source_sha256 = _sha256_file(path)
    entries = []
    for i, w in enumerate(windows):
        entries.append(
            _window_entry(
                "burstgpt",
                f"burstgpt_stage0_w{i:02d}",
                w,
                source_path=path,
                source_sha256=source_sha256,
                sampling_algorithm=manifest.selection_report["selection_algorithm_version"],
                sampling_seed=manifest.seed,
                offset_valid_rows=manifest.offset_valid_rows,
                start_index=manifest.selection_report["window_start_indices"][i],
            )
        )
    return entries, manifest.to_dict()


def build_azure_2024_conversation(path: Path) -> List[dict]:
    adapter = AzureLLMAdapter(split_name="conversation", dataset_year="2024")
    windows, report = select_stride_windows(
        adapter.stream_records(path),
        window_size=WINDOW_SIZE,
        n_windows=N_WINDOWS,
        offset_valid_rows=AZURE_2024_CONV_OFFSET,
        seed=AZURE_2024_CONV_SEED,
    )
    source_sha256 = _sha256_file(path)
    entries = []
    for i, w in enumerate(windows):
        entries.append(
            _window_entry(
                "azure_llm_2024",
                f"azure_llm_2024_stage0_w{i:02d}",
                w,
                source_path=path,
                source_sha256=source_sha256,
                sampling_algorithm=report.selection_algorithm_version,
                sampling_seed=AZURE_2024_CONV_SEED,
                offset_valid_rows=AZURE_2024_CONV_OFFSET,
                start_index=report.window_start_indices[i],
            )
        )
    return entries, report.to_dict()


def build_bailian_traceb(path: Path) -> List[dict]:
    adapter = BailianAdapter()
    windows, report = select_stride_windows(
        adapter.stream_records(path),
        window_size=WINDOW_SIZE,
        n_windows=N_WINDOWS,
        offset_valid_rows=BAILIAN_TRACEB_OFFSET,
        seed=BAILIAN_TRACEB_SEED,
    )
    source_sha256 = _sha256_file(path)
    entries = []
    for i, w in enumerate(windows):
        entries.append(
            _window_entry(
                "bailian_qwen",
                f"bailian_qwen_stage0_w{i:02d}",
                w,
                source_path=path,
                source_sha256=source_sha256,
                sampling_algorithm=report.selection_algorithm_version,
                sampling_seed=BAILIAN_TRACEB_SEED,
                offset_valid_rows=BAILIAN_TRACEB_OFFSET,
                start_index=report.window_start_indices[i],
            )
        )
    return entries, report.to_dict()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--burstgpt-path", required=True, type=Path)
    ap.add_argument("--azure-path", required=True, type=Path)
    ap.add_argument("--bailian-path", required=True, type=Path)
    ap.add_argument(
        "--out", type=Path, default=REPO_ROOT / "artifacts" / "manifests" / "stage0_windows.json"
    )
    args = ap.parse_args()

    print(f"[1/3] BurstGPT windows from {args.burstgpt_path}", file=sys.stderr)
    burstgpt_windows, burstgpt_manifest = build_burstgpt(args.burstgpt_path)

    print(f"[2/3] Azure-2024 conversation windows from {args.azure_path}", file=sys.stderr)
    azure_windows, azure_report = build_azure_2024_conversation(args.azure_path)

    print(f"[3/3] Bailian/Qwen traceB windows from {args.bailian_path}", file=sys.stderr)
    bailian_windows, bailian_report = build_bailian_traceb(args.bailian_path)

    all_windows = burstgpt_windows + azure_windows + bailian_windows
    window_ids = [w["window_id"] for w in all_windows]
    assert len(window_ids) == 30, f"expected 30 windows, got {len(window_ids)}"
    assert len(set(window_ids)) == 30, "duplicate window_id detected"
    for w in all_windows:
        assert w["request_count"] == WINDOW_SIZE, f"{w['window_id']} has {w['request_count']} requests"

    manifest = {
        "manifest_kind": "stage0_windows",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_sha": _git_sha(),
        "window_size": WINDOW_SIZE,
        "n_windows_per_source": N_WINDOWS,
        "n_sources": 3,
        "n_windows_total": len(all_windows),
        "source_sampling_reports": {
            "burstgpt": burstgpt_manifest,
            "azure_llm_2024_conversation": azure_report,
            "bailian_qwen_traceB": bailian_report,
        },
        "windows": all_windows,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(manifest, f, indent=2)

    manifest_sha256 = _sha256_file(args.out)
    print(f"Wrote {args.out} ({args.out.stat().st_size} bytes)", file=sys.stderr)
    print(f"manifest_sha256={manifest_sha256}")
    print(f"n_windows={len(all_windows)}")
    for source in ("burstgpt", "azure_llm_2024", "bailian_qwen"):
        n = sum(1 for w in all_windows if w["source_family"] == source)
        print(f"  {source}: {n} windows")


if __name__ == "__main__":
    main()
