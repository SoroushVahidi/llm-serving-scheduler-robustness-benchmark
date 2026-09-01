#!/usr/bin/env python3
"""Build the deterministic characterization window corpus for ONE source and
compute its WorkloadCharacterizationDescriptor rows, at every requested
window size. Designed to be one SLURM array task per source (see
scripts/slurm/workload_characterization.sbatch) -- writes a self-contained
per-source fragment; a separate merge step
(scripts/characterization/merge_and_analyze.py) combines all sources'
fragments and runs the section-6 distribution-shift analyses.

This script and everything it imports (`robustbench.characterization.*`) is
entirely independent of the frozen Stage-0 pipeline
(`scripts/build_stage0_windows.py`, `burstgpt_independent_sampling.py`) --
it is a NEW sampling run with its own seed/offset, not a reuse of Stage-0's
frozen windows, per
docs/WORKLOAD_DISTRIBUTION_CHARACTERIZATION_PROTOCOL.md. It never runs a
scheduler policy and never touches `robustbench.policies` /
`robustbench.simulator` / `robustbench.evaluation`.

Deterministic sampling parameters (frozen before any result was inspected):
  - seed = 20260910 for every source (distinct from every Stage-0 seed:
    20260901/20260902/20260903).
  - offset_valid_rows = 0 for every source -- unlike Stage-0 (which used a
    large offset specifically to move away from a *different* project's
    likely window placement), this experiment needs the FULL available
    chronological range to construct meaningful EARLY/MIDDLE/LATE temporal
    strata (section 6C), so no rows are skipped at the front.
  - n_windows target = 100 per (source, window_size); if a source has too
    few valid rows for 100 non-overlapping windows at a given window size,
    the maximum scientifically defensible count is used instead and
    recorded (never padded/duplicated) -- section 4's explicit fallback
    rule.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

import pandas as pd  # noqa: E402

from robustbench.characterization.chronology import assign_time_buckets  # noqa: E402
from robustbench.characterization.descriptors import (  # noqa: E402
    compute_characterization_descriptor,
)
from robustbench.workloads.external.adapters.azure_llm import AzureLLMAdapter  # noqa: E402
from robustbench.workloads.external.adapters.bailian import BailianAdapter  # noqa: E402
from robustbench.workloads.external.adapters.burstgpt import BurstGPTAdapter  # noqa: E402
from robustbench.workloads.external.adapters.tracelab import TraceLabAdapter  # noqa: E402
from robustbench.workloads.external.schema import ExternalWorkloadRecord  # noqa: E402
from robustbench.workloads.external.stage0_window_selection import (  # noqa: E402
    SELECTION_ALGORITHM_VERSION,
    _is_valid_for_windowing,
    select_stride_windows,
)

SEED = 20260910
OFFSET_VALID_ROWS = 0
TARGET_N_WINDOWS = 100
MIN_DEFENSIBLE_N_WINDOWS = 10
WINDOW_SIZES = (100, 200, 500)

BUILDER_VERSION = "workload_characterization_window_builder_v1"


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).decode().strip()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def make_record_source(source: str, path: Path) -> Callable[[], Iterable[ExternalWorkloadRecord]]:
    if source == "burstgpt":
        adapter = BurstGPTAdapter()
        return lambda: adapter.stream_records(path)
    if source == "azure_llm_2024":
        adapter = AzureLLMAdapter(split_name="conversation", dataset_year="2024")
        return lambda: adapter.stream_records(path)
    if source == "bailian_qwen":
        adapter = BailianAdapter()
        return lambda: adapter.stream_records(path)
    if source == "tracelab":
        adapter = TraceLabAdapter()
        return lambda: adapter.stream_records(path)
    raise ValueError(f"unknown source {source!r}")


def _count_valid(record_source: Callable[[], Iterable[ExternalWorkloadRecord]]) -> tuple[int, int]:
    n_seen = 0
    n_valid = 0
    for r in record_source():
        n_seen += 1
        if _is_valid_for_windowing(r):
            n_valid += 1
    return n_seen, n_valid


def build_one_window_size(
    source: str,
    record_source: Callable[[], Iterable[ExternalWorkloadRecord]],
    window_size: int,
) -> tuple[list[list[ExternalWorkloadRecord]], dict, int]:
    """Returns (windows, selection_report_dict, n_windows_actual). Falls
    back to the maximum defensible window count if 100 windows do not fit;
    raises if even MIN_DEFENSIBLE_N_WINDOWS do not fit."""
    try:
        windows, report = select_stride_windows(
            record_source,
            window_size=window_size,
            n_windows=TARGET_N_WINDOWS,
            offset_valid_rows=OFFSET_VALID_ROWS,
            seed=SEED,
        )
        return windows, report.to_dict(), TARGET_N_WINDOWS
    except ValueError:
        n_seen, n_valid = _count_valid(record_source)
        n_available = n_valid - OFFSET_VALID_ROWS
        max_windows = n_available // window_size
        if max_windows < MIN_DEFENSIBLE_N_WINDOWS:
            raise ValueError(
                f"{source} window_size={window_size}: only {max_windows} non-overlapping "
                f"windows fit ({n_available} valid rows available past offset), below the "
                f"minimum defensible count of {MIN_DEFENSIBLE_N_WINDOWS} -- excluding this "
                f"(source, window_size) combination rather than padding/duplicating."
            )
        windows, report = select_stride_windows(
            record_source,
            window_size=window_size,
            n_windows=max_windows,
            offset_valid_rows=OFFSET_VALID_ROWS,
            seed=SEED,
        )
        return windows, report.to_dict(), max_windows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True, choices=["burstgpt", "azure_llm_2024", "bailian_qwen", "tracelab"])
    ap.add_argument("--raw-path", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[{args.source}] computing raw-file checksum...", file=sys.stderr)
    source_sha256 = _sha256_file(args.raw_path)
    record_source = make_record_source(args.source, args.raw_path)

    window_manifest_entries = []
    descriptor_rows = []
    excluded = []

    for ws in WINDOW_SIZES:
        print(f"[{args.source}] window_size={ws}: selecting windows...", file=sys.stderr)
        try:
            windows, report_dict, n_windows_actual = build_one_window_size(args.source, record_source, ws)
        except ValueError as e:
            print(f"[{args.source}] window_size={ws}: EXCLUDED -- {e}", file=sys.stderr)
            excluded.append({"window_size": ws, "reason": str(e)})
            continue

        n_available = report_dict["n_records_valid"] - OFFSET_VALID_ROWS
        time_buckets = assign_time_buckets(
            report_dict["window_start_indices"], offset_valid_rows=OFFSET_VALID_ROWS, n_available=n_available
        )

        for i, (records, bucket) in enumerate(zip(windows, time_buckets)):
            window_id = f"{args.source}_ws{ws}_w{i:03d}"
            arrivals = sorted(r.arrival_time_s for r in records if r.arrival_time_s is not None)
            window_manifest_entries.append({
                "window_id": window_id,
                "source_family": args.source,
                "source_file": args.raw_path.name,
                "source_file_sha256": source_sha256,
                "window_size_requested": ws,
                "window_index": i,
                "time_bucket": bucket,
                "sampling_algorithm": SELECTION_ALGORITHM_VERSION,
                "builder_version": BUILDER_VERSION,
                "sampling_seed": SEED,
                "offset_valid_rows": OFFSET_VALID_ROWS,
                "start_index_in_valid_rows": report_dict["window_start_indices"][i],
                "n_records_valid_in_source": report_dict["n_records_valid"],
                "n_records_seen_in_source": report_dict["n_records_seen"],
                "request_count": len(records),
                "arrival_time_s_min": arrivals[0] if arrivals else None,
                "arrival_time_s_max": arrivals[-1] if arrivals else None,
            })
            descriptor = compute_characterization_descriptor(
                records,
                source_family=args.source,
                window_id=window_id,
                window_size_requested=ws,
                time_bucket=bucket,
            )
            row = descriptor.to_dict()
            row["field_provenance_summary"] = json.dumps(row["field_provenance_summary"])
            descriptor_rows.append(row)

        print(f"[{args.source}] window_size={ws}: {n_windows_actual} windows built", file=sys.stderr)

    frag_manifest_path = args.out_dir / f"windows_{args.source}.json"
    frag = {
        "source_family": args.source,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_sha": _git_sha(),
        "builder_version": BUILDER_VERSION,
        "sampling_algorithm": SELECTION_ALGORITHM_VERSION,
        "seed": SEED,
        "offset_valid_rows": OFFSET_VALID_ROWS,
        "target_n_windows": TARGET_N_WINDOWS,
        "window_sizes": list(WINDOW_SIZES),
        "source_file": str(args.raw_path),
        "source_file_sha256": source_sha256,
        "excluded_window_sizes": excluded,
        "n_windows_total": len(window_manifest_entries),
        "windows": window_manifest_entries,
    }
    with open(frag_manifest_path, "w") as f:
        json.dump(frag, f, indent=2)
    frag_hash = _sha256_file(frag_manifest_path)
    print(f"[{args.source}] wrote {frag_manifest_path} sha256={frag_hash}", file=sys.stderr)

    frag_parquet_path = args.out_dir / f"descriptors_{args.source}.parquet"
    df = pd.DataFrame(descriptor_rows)
    df.to_parquet(frag_parquet_path, index=False)
    print(f"[{args.source}] wrote {frag_parquet_path} ({len(df)} rows)", file=sys.stderr)

    integrity_path = args.out_dir / f"integrity_{args.source}.json"
    with open(integrity_path, "w") as f:
        json.dump({
            "source_family": args.source,
            "n_windows_manifest": len(window_manifest_entries),
            "n_descriptor_rows": len(df),
            "excluded_window_sizes": excluded,
            "manifest_fragment_sha256": frag_hash,
        }, f, indent=2)
    print(f"[{args.source}] DONE", file=sys.stderr)


if __name__ == "__main__":
    main()
