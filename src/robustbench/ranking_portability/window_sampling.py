"""Pilot-V2 workload window construction (docs/RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md
section 4): extends each source's frozen Stage-0 10-window sample to 40
windows/source, keeping Stage-0's original 10 as an untouched, verbatim,
non-overlapping subset ("evidence class" `STAGE0_WINDOW`) and drawing 30
new, deterministically-selected, non-overlapping windows past them
("evidence class" `PILOT_V2_NEW_WINDOW`).

Genuine implementation finding, disclosed rather than silently worked
around: `stage0_window_selection.select_stride_windows`'s bucket
boundaries are `n_available // n_windows` -- a function of `n_windows`
itself. Re-invoking it with `n_windows=40` on the same valid-row range
does NOT reproduce the original 10 windows as a subset; it recomputes an
entirely different, disjoint bucket partition (verified in
`tests/test_ranking_portability_window_sampling.py`). This module
implements the "pinned + extend" algorithm actually required by the
preregistered "Stage-0's 10 are a strict subset of Pilot-V2's 40"
decision (docs/RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md section 4): the
30 new windows are drawn from the FREE valid-row space remaining after
excising the 10 pinned Stage-0 ranges, each new window placed entirely
within one contiguous free interval (never straddling an excised range,
so every window remains internally chronologically contiguous).

No scheduler policy is imported by this module or anything it calls.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable, Iterable, List, Tuple

import numpy as np

from ..workloads.external.schema import ExternalWorkloadRecord
from ..workloads.external.stage0_window_selection import _is_valid_for_windowing

SELECTION_ALGORITHM_VERSION = "ranking_portability_pinned_extension_stride_v1"


@dataclass(frozen=True)
class PinnedRange:
    """A Stage-0 window's [start, end) span in absolute valid-row-index
    space (i.e. already including whatever offset Stage-0 used) -- must
    never be selected into, or overlapped by, a new Pilot-V2 window."""
    start: int
    end: int


def _free_intervals(n_valid: int, pinned: List[PinnedRange]) -> List[Tuple[int, int]]:
    """Absolute-valid-row-index free intervals after excising every pinned
    range from [0, n_valid). Pinned ranges may be given in any order and
    must not overlap each other (Stage-0's own 10 windows never do,
    verified by the caller)."""
    intervals: List[Tuple[int, int]] = []
    cursor = 0
    for p in sorted(pinned, key=lambda p: p.start):
        if p.start > cursor:
            intervals.append((cursor, p.start))
        cursor = max(cursor, p.end)
    if cursor < n_valid:
        intervals.append((cursor, n_valid))
    return intervals


def _compute_extension_start_indices(
    free_intervals: List[Tuple[int, int]],
    *,
    window_size: int,
    n_new_windows: int,
    seed: int,
) -> Tuple[List[int], int]:
    """Deterministically choose `n_new_windows` absolute start indices,
    each yielding a `window_size`-row span that fits entirely within ONE
    free interval (never spanning an excised pinned range). Stride buckets
    are defined over total FREE length (not raw valid-row-index space), so
    bucket width is unaffected by how many/large the pinned exclusions
    are. Raises ValueError if free space is insufficient -- never silently
    reduces window count or reuses a pinned range."""
    usable = [(lo, hi) for lo, hi in free_intervals if hi - lo >= window_size]
    total_free = sum(hi - lo for lo, hi in usable)
    needed = n_new_windows * window_size
    if total_free < needed or not usable:
        raise ValueError(
            f"Not enough free (non-pinned) valid-row space to place "
            f"{n_new_windows} new windows of {window_size}: {total_free} usable "
            f"free rows available across {len(usable)} interval(s), need {needed}."
        )

    stride = total_free // n_new_windows
    rng = np.random.default_rng(seed)

    # Map a "free position" (0..total_free) to (interval_lo, interval_hi).
    cum: List[Tuple[int, int, int, int]] = []  # (free_lo, free_hi, abs_lo, abs_hi)
    running = 0
    for lo, hi in usable:
        cum.append((running, running + (hi - lo), lo, hi))
        running += hi - lo

    def _containing_interval(free_pos: int) -> Tuple[int, int, int, int]:
        for entry in cum:
            if entry[0] <= free_pos < entry[1]:
                return entry
        return cum[-1]

    starts: List[int] = []
    for i in range(n_new_windows):
        bucket_lo = i * stride
        bucket_hi = bucket_lo + stride if i < n_new_windows - 1 else total_free
        max_free_start = bucket_hi - window_size
        free_start = (
            int(rng.integers(bucket_lo, max_free_start + 1))
            if max_free_start > bucket_lo else bucket_lo
        )
        free_lo, free_hi, abs_lo, abs_hi = _containing_interval(free_start)
        abs_start = abs_lo + (free_start - free_lo)
        # Clamp so the whole window_size span stays within this ONE
        # interval (never crosses into the next free segment, which could
        # otherwise straddle a pinned/excised range).
        max_abs_start_in_interval = abs_hi - window_size
        if max_abs_start_in_interval < abs_lo:
            raise ValueError(
                f"Free interval [{abs_lo},{abs_hi}) is smaller than window_size="
                f"{window_size} -- should have been filtered out of `usable`."
            )
        abs_start = min(max(abs_start, abs_lo), max_abs_start_in_interval)
        starts.append(abs_start)
    return starts, stride


def select_extension_stride_windows(
    record_source: Callable[[], Iterable[ExternalWorkloadRecord]],
    *,
    window_size: int,
    n_new_windows: int,
    offset_valid_rows: int,
    seed: int,
    pinned_ranges: List[PinnedRange],
) -> Tuple[List[List[ExternalWorkloadRecord]], dict]:
    """Two-pass streaming, same peak-memory discipline as
    `select_stride_windows` (O(n_new_windows * window_size), never O(file
    size)). `pinned_ranges` must be given in absolute valid-row-index
    space (i.e. already offset-adjusted, exactly as
    `stage0_windows.json`'s `start_index_in_valid_rows` values are)."""
    n_seen = 0
    n_valid = 0
    for r in record_source():
        n_seen += 1
        if _is_valid_for_windowing(r):
            n_valid += 1
    n_dropped = n_seen - n_valid

    free = _free_intervals(n_valid, pinned_ranges)
    # Respect offset_valid_rows: never place a new window before it, even
    # if technically "free" (keeps the same documented offset convention
    # Stage-0 used, for every source).
    free = [
        (max(lo, offset_valid_rows), hi)
        for lo, hi in free
        if hi > offset_valid_rows
    ]
    free = [(lo, hi) for lo, hi in free if hi > lo]

    starts, stride = _compute_extension_start_indices(
        free, window_size=window_size, n_new_windows=n_new_windows, seed=seed,
    )

    ranges = sorted((s, s + window_size, i) for i, s in enumerate(starts))
    windows: List[List[ExternalWorkloadRecord]] = [[] for _ in range(n_new_windows)]
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
                f"New window {i} materialized {len(block)} rows, expected "
                f"{window_size} (record_source() likely did not return a stable, "
                "repeatable stream across the two passes)"
            )

    report = {
        "selection_algorithm_version": SELECTION_ALGORITHM_VERSION,
        "n_records_seen": n_seen,
        "n_records_valid": n_valid,
        "n_records_dropped_invalid": n_dropped,
        "offset_valid_rows": offset_valid_rows,
        "window_size": window_size,
        "n_new_windows_requested": n_new_windows,
        "n_new_windows_selected": len(windows),
        "stride_free_rows": stride,
        "seed": seed,
        "pinned_ranges": [asdict(p) for p in pinned_ranges],
        "free_intervals_used": [{"start": lo, "end": hi} for lo, hi in free],
        "window_start_indices": starts,
    }
    return windows, report


def assert_no_overlap(ranges: List[Tuple[int, int]]) -> None:
    """Hard-fails (raises AssertionError) on any pairwise overlap. Used by
    both the builder script and tests -- never silently tolerates overlap
    or logs-and-continues."""
    ordered = sorted(ranges)
    for (s1, e1), (s2, e2) in zip(ordered, ordered[1:]):
        if s2 < e1:
            raise AssertionError(f"overlapping ranges detected: [{s1},{e1}) and [{s2},{e2})")
