"""Pure-algorithm tests for the Pilot-V2 window-extension sampler
(docs/RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md section 4). No real trace
file is touched -- every scenario uses a small, synthetic, in-memory
record stream, so these tests run anywhere, including without Wulver
access. No scheduler policy is imported anywhere in this module or the
code it tests.
"""
from __future__ import annotations

import pytest

from robustbench.ranking_portability.window_sampling import (
    PinnedRange,
    SELECTION_ALGORITHM_VERSION,
    _compute_extension_start_indices,
    _free_intervals,
    assert_no_overlap,
    select_extension_stride_windows,
)
from robustbench.workloads.external.schema import ExternalWorkloadRecord


def _fake_records(n: int) -> list[ExternalWorkloadRecord]:
    return [
        ExternalWorkloadRecord(
            source_dataset="fixture", source_version="v0", source_record_id=str(i),
            derived_record_id=str(i), source_license="test", source_url="",
            conversion_version="test_v1",
            arrival_time_s=float(i), input_tokens=10 + (i % 5), output_tokens=5 + (i % 3),
        )
        for i in range(n)
    ]


def _source(records):
    return lambda: iter(records)


# --- _free_intervals ------------------------------------------------------

def test_free_intervals_no_pinned():
    assert _free_intervals(100, []) == [(0, 100)]


def test_free_intervals_single_pinned_in_middle():
    assert _free_intervals(100, [PinnedRange(40, 60)]) == [(0, 40), (60, 100)]


def test_free_intervals_multiple_pinned_sorted_input_order():
    # Given out of order -- must still produce correctly ordered gaps.
    pinned = [PinnedRange(60, 70), PinnedRange(10, 20)]
    assert _free_intervals(100, pinned) == [(0, 10), (20, 60), (70, 100)]


def test_free_intervals_pinned_at_boundaries():
    pinned = [PinnedRange(0, 10), PinnedRange(90, 100)]
    assert _free_intervals(100, pinned) == [(10, 90)]


def test_free_intervals_adjacent_pinned_ranges_merge_gap_to_nothing():
    pinned = [PinnedRange(10, 20), PinnedRange(20, 30)]
    assert _free_intervals(100, pinned) == [(0, 10), (30, 100)]


# --- _compute_extension_start_indices -------------------------------------

def test_extension_starts_never_overlap_free_interval_boundaries():
    free = [(0, 1000), (2000, 3000)]
    starts, stride = _compute_extension_start_indices(
        free, window_size=50, n_new_windows=10, seed=42,
    )
    assert len(starts) == 10
    for s in starts:
        assert (0 <= s and s + 50 <= 1000) or (2000 <= s and s + 50 <= 3000), (
            f"start {s} produces a window spanning outside a single free interval"
        )


def test_extension_starts_deterministic_across_calls():
    free = [(0, 1000)]
    starts1, _ = _compute_extension_start_indices(free, window_size=20, n_new_windows=5, seed=7)
    starts2, _ = _compute_extension_start_indices(free, window_size=20, n_new_windows=5, seed=7)
    assert starts1 == starts2


def test_extension_starts_different_seed_differs():
    free = [(0, 1000)]
    starts1, _ = _compute_extension_start_indices(free, window_size=20, n_new_windows=5, seed=1)
    starts2, _ = _compute_extension_start_indices(free, window_size=20, n_new_windows=5, seed=2)
    assert starts1 != starts2


def test_extension_raises_when_insufficient_free_space():
    free = [(0, 50)]
    with pytest.raises(ValueError, match="Not enough free"):
        _compute_extension_start_indices(free, window_size=20, n_new_windows=10, seed=0)


def test_extension_filters_intervals_smaller_than_window_size():
    # A tiny free sliver (5 rows) must never be selected into for a
    # window_size=20 request -- only the large interval should be used.
    free = [(0, 5), (100, 10000)]
    starts, _ = _compute_extension_start_indices(free, window_size=20, n_new_windows=20, seed=3)
    for s in starts:
        assert not (0 <= s < 5)


# --- select_extension_stride_windows (end-to-end, synthetic stream) ------

def test_extension_windows_avoid_pinned_ranges_and_deduplicate():
    records = _fake_records(2000)
    pinned = [PinnedRange(500, 700), PinnedRange(1000, 1200)]
    windows, report = select_extension_stride_windows(
        _source(records), window_size=50, n_new_windows=10,
        offset_valid_rows=0, seed=99, pinned_ranges=pinned,
    )
    assert len(windows) == 10
    for w in windows:
        assert len(w) == 50
        ids = [int(r.source_record_id) for r in w]
        # window content must be within a single contiguous, non-pinned span
        lo, hi = min(ids), max(ids)
        assert not (lo < 700 and hi >= 500), "window overlaps first pinned range"
        assert not (lo < 1200 and hi >= 1000), "window overlaps second pinned range"
        # chronologically contiguous / strictly increasing arrival order preserved
        assert ids == sorted(ids)

    starts = report["window_start_indices"]
    assert_no_overlap([(s, s + 50) for s in starts] + [(p.start, p.end) for p in pinned])


def test_extension_respects_offset_valid_rows():
    records = _fake_records(2000)
    windows, report = select_extension_stride_windows(
        _source(records), window_size=50, n_new_windows=5,
        offset_valid_rows=1000, seed=1, pinned_ranges=[],
    )
    for w in windows:
        ids = [int(r.source_record_id) for r in w]
        assert min(ids) >= 1000


def test_extension_deterministic_rerun_identical_windows():
    records = _fake_records(2000)
    pinned = [PinnedRange(500, 700)]

    def run():
        windows, report = select_extension_stride_windows(
            _source(records), window_size=40, n_new_windows=8,
            offset_valid_rows=0, seed=555, pinned_ranges=pinned,
        )
        return [[r.source_record_id for r in w] for w in windows], report["window_start_indices"]

    result1 = run()
    result2 = run()
    assert result1 == result2


def test_extension_raises_when_source_stream_unstable():
    """If record_source() returns a DIFFERENT stream on its second call
    (simulating a non-repeatable/corrupt source), materialization must
    fail loudly, never silently emit a short/wrong window."""
    records = _fake_records(500)
    calls = {"n": 0}

    def flaky_source():
        calls["n"] += 1
        if calls["n"] == 1:
            return iter(records)
        return iter(records[:100])  # second pass truncated -- unstable stream

    with pytest.raises(ValueError, match="materialized"):
        select_extension_stride_windows(
            flaky_source, window_size=50, n_new_windows=5,
            offset_valid_rows=0, seed=0, pinned_ranges=[],
        )


def test_algorithm_version_string_is_distinct_from_stage0():
    from robustbench.workloads.external.stage0_window_selection import (
        SELECTION_ALGORITHM_VERSION as STAGE0_VERSION,
    )
    assert SELECTION_ALGORITHM_VERSION != STAGE0_VERSION


# --- assert_no_overlap -----------------------------------------------------

def test_assert_no_overlap_passes_for_disjoint_ranges():
    assert_no_overlap([(0, 10), (10, 20), (30, 40)])


def test_assert_no_overlap_raises_for_overlapping_ranges():
    with pytest.raises(AssertionError):
        assert_no_overlap([(0, 10), (5, 15)])
