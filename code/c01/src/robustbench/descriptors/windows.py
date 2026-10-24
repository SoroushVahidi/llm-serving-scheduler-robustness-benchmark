"""Minimal, source-agnostic workload-window construction.

Deliberately simple for the bootstrap: fixed-count and fixed-duration
chunking of a chronologically sorted record stream. The frozen splitting
policy used for confirmatory analysis (source-ID / source-OOD / temporal-OOD)
lives in docs/SPLIT_PROTOCOL.md and configs/splits/*.yaml, not here -- this
module only turns a record stream into windows, it does not decide which
windows go into which split.
"""
from __future__ import annotations

from typing import List, Sequence

from ..workloads.external.schema import ExternalWorkloadRecord


def fixed_count_windows(
    records: Sequence[ExternalWorkloadRecord], window_size: int
) -> List[List[ExternalWorkloadRecord]]:
    """Chunk records (assumed already sorted by arrival time) into
    non-overlapping windows of `window_size` records. The final partial
    window is dropped so every window has an identical, comparable size."""
    if window_size <= 0:
        raise ValueError("window_size must be positive")
    n_full = len(records) // window_size
    return [
        list(records[i * window_size : (i + 1) * window_size]) for i in range(n_full)
    ]


def fixed_duration_windows(
    records: Sequence[ExternalWorkloadRecord], duration_s: float
) -> List[List[ExternalWorkloadRecord]]:
    """Chunk records into non-overlapping windows spanning `duration_s`
    seconds of arrival time each. Records with arrival_time_s=None are
    dropped (a window requires known arrival timing to have a duration)."""
    if duration_s <= 0:
        raise ValueError("duration_s must be positive")
    timed = sorted(
        (r for r in records if r.arrival_time_s is not None),
        key=lambda r: r.arrival_time_s,
    )
    if not timed:
        return []
    windows: List[List[ExternalWorkloadRecord]] = []
    start = timed[0].arrival_time_s
    current: List[ExternalWorkloadRecord] = []
    for r in timed:
        if r.arrival_time_s - start >= duration_s:
            if current:
                windows.append(current)
            start = r.arrival_time_s
            current = [r]
        else:
            current.append(r)
    if current and (timed[-1].arrival_time_s - start) >= duration_s * 0.999:
        windows.append(current)
    return windows
