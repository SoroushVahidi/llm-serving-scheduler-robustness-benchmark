"""EARLY / MIDDLE / LATE time-stratum tagging for chronologically-sorted
window selections (section 4 / section 6C of
docs/WORKLOAD_DISTRIBUTION_CHARACTERIZATION_PROTOCOL.md).

A window's stratum is determined by where its start position falls within
the source's *valid-row* range (post-offset), split into three equal
thirds -- not by wall-clock date, since not every source has an absolute
calendar timestamp (Bailian/Qwen and TraceLab are relative/pseudonymized).
This keeps the stratification rule identical and auditable across every
source.
"""
from __future__ import annotations

from typing import List


def assign_time_buckets(
    window_start_indices: List[int], offset_valid_rows: int, n_available: int
) -> List[str]:
    """Returns one of "EARLY"/"MIDDLE"/"LATE" per window, in the same order
    as `window_start_indices`. `n_available` is the count of valid rows
    available for windowing past `offset_valid_rows` (i.e.
    WindowSelectionReport.n_records_valid - offset_valid_rows)."""
    if n_available <= 0:
        raise ValueError("n_available must be positive")
    third = n_available / 3.0
    buckets: List[str] = []
    for start in window_start_indices:
        rel = start - offset_valid_rows
        if rel < third:
            buckets.append("EARLY")
        elif rel < 2 * third:
            buckets.append("MIDDLE")
        else:
            buckets.append("LATE")
    return buckets
