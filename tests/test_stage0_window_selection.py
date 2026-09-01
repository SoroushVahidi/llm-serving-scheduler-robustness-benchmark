from __future__ import annotations

from pathlib import Path

import pytest

from robustbench.workloads.external.adapters import burstgpt
from robustbench.workloads.external.stage0_window_selection import select_stride_windows

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "configs" / "external_workloads" / "fixtures"


def _burstgpt_records(n_repeats: int = 50):
    adapter = burstgpt.BurstGPTAdapter()
    base = list(adapter.stream_records(FIXTURES / "burstgpt_sample.csv"))
    out = []
    for _ in range(n_repeats):
        out.extend(base)
    return out


def test_select_stride_windows_basic_shape():
    records = _burstgpt_records(50)
    windows, report = select_stride_windows(
        records, window_size=3, n_windows=4, offset_valid_rows=10
    )
    assert len(windows) == 4
    assert all(len(w) == 3 for w in windows)
    assert report.n_windows_selected == 4
    assert report.offset_valid_rows == 10
    assert report.n_records_dropped_invalid >= 0
    assert report.n_records_valid + report.n_records_dropped_invalid == report.n_records_seen


def test_select_stride_windows_drops_invalid_rows():
    # burstgpt_sample.csv's 4th row has an empty Response tokens field.
    records = _burstgpt_records(1)
    _, report = select_stride_windows(records, window_size=1, n_windows=1, offset_valid_rows=0)
    assert report.n_records_dropped_invalid >= 1
    assert report.n_records_seen == 4


def test_select_stride_windows_raises_when_not_enough_rows():
    records = _burstgpt_records(1)
    with pytest.raises(ValueError):
        select_stride_windows(records, window_size=200, n_windows=10, offset_valid_rows=0)


def test_select_stride_windows_deterministic_for_fixed_seed():
    records = _burstgpt_records(50)
    w1, r1 = select_stride_windows(
        records, window_size=3, n_windows=4, offset_valid_rows=10, seed=42
    )
    w2, r2 = select_stride_windows(
        records, window_size=3, n_windows=4, offset_valid_rows=10, seed=42
    )
    assert r1.window_start_indices == r2.window_start_indices
    for a, b in zip(w1, w2):
        assert [r.derived_record_id for r in a] == [r.derived_record_id for r in b]


def test_select_stride_windows_different_seeds_can_differ():
    records = _burstgpt_records(200)
    _, r1 = select_stride_windows(
        records, window_size=3, n_windows=4, offset_valid_rows=10, seed=1
    )
    _, r2 = select_stride_windows(
        records, window_size=3, n_windows=4, offset_valid_rows=10, seed=999
    )
    # Not a strict guarantee for all inputs, but true for this fixture/stride size.
    assert r1.window_start_indices != r2.window_start_indices
