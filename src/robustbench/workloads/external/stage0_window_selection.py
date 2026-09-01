"""Generic, source-agnostic deterministic window selection for Stage 0.

Used by all three Stage-0 real sources (Azure 2024, Bailian/Qwen, BurstGPT)
so the same auditable rule applies everywhere: stream Layer-1 records in
source-native chronological order, drop rows missing the fields the
simulator needs (arrival time, positive prompt/output token counts), skip a
frozen offset into the valid-row sequence, then take `n_windows` contiguous
`window_size`-request blocks spread at an even stride across the remaining
valid rows.

Two-pass streaming by design: the largest Stage-0 source (Azure 2024
conversation split) has ~27M rows, far too many to materialize as
`ExternalWorkloadRecord` objects in memory at once. `record_source` is a
zero-argument callable that returns a *fresh* iterator each time it is
called (e.g. `lambda: adapter.stream_records(path)`), so this module can
make one pass to count valid rows and a second pass to materialize only the
rows that fall inside a selected window -- peak memory is
O(n_windows * window_size), never O(file size).

This module deliberately does not special-case BurstGPT's independence
requirement -- see `burstgpt_independent_sampling.py`, which wraps this
function with BurstGPT-specific frozen parameters and the disclosure text
required by docs/EVIDENCE_INDEPENDENCE_PLAN.md.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable, Iterable, List

import numpy as np

from .schema import ExternalWorkloadRecord

SELECTION_ALGORITHM_VERSION = "stage0_stride_window_selection_v2_streaming"


def _is_valid_for_windowing(r: ExternalWorkloadRecord) -> bool:
    return (
        r.arrival_time_s is not None
        and r.input_tokens is not None
        and r.input_tokens > 0
        and r.output_tokens is not None
        and r.output_tokens > 0
    )


@dataclass
class WindowSelectionReport:
    selection_algorithm_version: str
    n_records_seen: int
    n_records_valid: int
    n_records_dropped_invalid: int
    offset_valid_rows: int
    window_size: int
    n_windows_requested: int
    n_windows_selected: int
    stride_valid_rows: int
    seed: int
    window_start_indices: List[int]  # indices into the valid-row sequence

    def to_dict(self) -> dict:
        return asdict(self)


def _compute_start_indices(
    n_available: int,
    *,
    window_size: int,
    n_windows: int,
    seed: int,
) -> tuple[List[int], int]:
    stride = n_available // n_windows
    rng = np.random.default_rng(seed)
    starts: List[int] = []
    for i in range(n_windows):
        bucket_start = i * stride
        bucket_end = bucket_start + stride if i < n_windows - 1 else n_available
        max_start = bucket_end - window_size
        start = (
            int(rng.integers(bucket_start, max_start + 1))
            if max_start > bucket_start
            else bucket_start
        )
        starts.append(start)
    return starts, stride


def select_stride_windows(
    record_source: Callable[[], Iterable[ExternalWorkloadRecord]],
    *,
    window_size: int,
    n_windows: int,
    offset_valid_rows: int,
    seed: int = 0,
) -> tuple[List[List[ExternalWorkloadRecord]], WindowSelectionReport]:
    """Two-pass streaming window selection (see module docstring for why).

    `record_source()` must return a fresh iterator each call (it is called
    exactly twice: once to count valid rows, once to materialize the
    selected windows).

    The available valid-row range past `offset_valid_rows` is divided into
    `n_windows` equal-width stride buckets; within each bucket, `seed`
    deterministically picks one random `window_size`-row start position
    (via `numpy.random.default_rng(seed)`, drawn once per bucket in bucket
    order) rather than always the bucket's first row -- this avoids a
    purely mechanical, trivially-predictable window placement while
    remaining fully reproducible from the frozen seed. `seed=0` (the
    default) reduces to picking the first available start in each bucket.

    Raises ValueError if there are not enough valid rows past the offset to
    materialize `n_windows` full windows -- this is treated as a hard
    failure (caller must not silently reduce window count or size).
    """
    # Pass 1: count only, no materialization.
    n_seen = 0
    n_valid = 0
    for r in record_source():
        n_seen += 1
        if _is_valid_for_windowing(r):
            n_valid += 1

    n_dropped = n_seen - n_valid
    n_available = n_valid - offset_valid_rows
    needed = n_windows * window_size
    if n_available < needed:
        raise ValueError(
            f"Not enough valid rows past offset to build {n_windows} windows of "
            f"{window_size}: have {n_available} valid rows after offset "
            f"{offset_valid_rows}, need {needed}. n_seen={n_seen}, n_valid={n_valid}."
        )

    starts, stride = _compute_start_indices(
        n_available, window_size=window_size, n_windows=n_windows, seed=seed
    )
    # Selection ranges expressed in absolute valid-row-index terms (i.e.
    # including the offset), sorted so pass 2 can consume them in one
    # left-to-right sweep over the valid-row stream.
    ranges = sorted(
        (offset_valid_rows + s, offset_valid_rows + s + window_size, i)
        for i, s in enumerate(starts)
    )

    # Pass 2: materialize only rows that fall inside a selected range.
    windows: List[List[ExternalWorkloadRecord]] = [[] for _ in range(n_windows)]
    range_idx = 0
    valid_idx = 0
    for r in record_source():
        if not _is_valid_for_windowing(r):
            continue
        while range_idx < len(ranges) and valid_idx >= ranges[range_idx][1]:
            range_idx += 1
        if range_idx >= len(ranges):
            break
        lo, hi, window_i = ranges[range_idx]
        if lo <= valid_idx < hi:
            windows[window_i].append(r)
        valid_idx += 1

    for i, block in enumerate(windows):
        if len(block) != window_size:
            raise ValueError(
                f"Window {i} materialized {len(block)} rows, expected {window_size} "
                "(record_source() likely did not return a stable, repeatable stream "
                "across the two passes)"
            )

    report = WindowSelectionReport(
        selection_algorithm_version=SELECTION_ALGORITHM_VERSION,
        n_records_seen=n_seen,
        n_records_valid=n_valid,
        n_records_dropped_invalid=n_dropped,
        offset_valid_rows=offset_valid_rows,
        window_size=window_size,
        n_windows_requested=n_windows,
        n_windows_selected=len(windows),
        stride_valid_rows=stride,
        seed=seed,
        window_start_indices=[offset_valid_rows + s for s in starts],
    )
    return windows, report
