from __future__ import annotations

import pytest

from robustbench.characterization.chronology import assign_time_buckets


def test_assign_time_buckets_basic_thirds():
    # n_available=300 -> thirds at 100/200
    starts = [0, 50, 99, 100, 150, 199, 200, 250, 299]
    buckets = assign_time_buckets(starts, offset_valid_rows=0, n_available=300)
    assert buckets == [
        "EARLY", "EARLY", "EARLY",
        "MIDDLE", "MIDDLE", "MIDDLE",
        "LATE", "LATE", "LATE",
    ]


def test_assign_time_buckets_respects_offset():
    # offset shifts the origin; n_available describes the post-offset range
    starts = [1000, 1099, 1100, 1199, 1200]
    buckets = assign_time_buckets(starts, offset_valid_rows=1000, n_available=300)
    assert buckets == ["EARLY", "EARLY", "MIDDLE", "MIDDLE", "LATE"]


def test_assign_time_buckets_rejects_nonpositive_available():
    with pytest.raises(ValueError):
        assign_time_buckets([0], offset_valid_rows=0, n_available=0)
