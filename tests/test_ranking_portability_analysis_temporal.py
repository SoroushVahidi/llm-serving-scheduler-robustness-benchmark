"""Temporal split fixtures (BurstGPT tercile/bisect, Bailian
relative-only labeling, Azure calendar split) -- fixture case 18
(temporal split edge cases: odd window counts, empty tail)."""
from __future__ import annotations

from robustbench.ranking_portability.analysis.contract import BAILIAN_TEMPORAL_LABEL
from robustbench.ranking_portability.analysis.temporal_analysis import (
    filter_rows_to_windows,
    split_azure_calendar,
    split_bailian_relative,
    split_burstgpt_bisect,
    split_burstgpt_tercile,
)


def test_tercile_split_covers_all_windows_exactly_once():
    ts = {f"w{i}": float(i) for i in range(9)}
    groups = split_burstgpt_tercile(ts)
    all_windows = groups["EARLY"] + groups["MIDDLE"] + groups["LATE"]
    assert sorted(all_windows) == sorted(ts.keys())
    assert len(groups["EARLY"]) == len(groups["MIDDLE"]) == len(groups["LATE"]) == 3


def test_case18_tercile_split_odd_count_edge_case():
    ts = {f"w{i}": float(i) for i in range(10)}  # not divisible by 3
    groups = split_burstgpt_tercile(ts)
    all_windows = groups["EARLY"] + groups["MIDDLE"] + groups["LATE"]
    assert sorted(all_windows) == sorted(ts.keys())
    assert len(all_windows) == 10


def test_case18_bisect_split_odd_count_edge_case():
    ts = {f"w{i}": float(i) for i in range(7)}
    groups = split_burstgpt_bisect(ts)
    assert sorted(groups["EARLY"] + groups["LATE"]) == sorted(ts.keys())
    assert abs(len(groups["EARLY"]) - len(groups["LATE"])) <= 1


def test_case18_single_window_edge_case():
    ts = {"w0": 1.0}
    groups = split_burstgpt_bisect(ts)
    assert sorted(groups["EARLY"] + groups["LATE"]) == ["w0"]


def test_bisect_is_time_ordered():
    ts = {"w2": 20.0, "w0": 0.0, "w1": 10.0, "w3": 30.0}
    groups = split_burstgpt_bisect(ts)
    assert groups["EARLY"] == ["w0", "w1"]
    assert groups["LATE"] == ["w2", "w3"]


def test_bailian_relative_split_labeled_relative_only():
    order = {"w0": 3, "w1": 1, "w2": 2, "w3": 0}
    result = split_bailian_relative(order)
    assert result.chronology_type == BAILIAN_TEMPORAL_LABEL
    assert result.groups["EARLY_RELATIVE"] == ["w3", "w1"]
    assert result.groups["LATE_RELATIVE"] == ["w2", "w0"]


def test_azure_calendar_split_uses_explicit_boundary():
    ts = {"w0": 100.0, "w1": 200.0, "w2": 300.0}
    groups = split_azure_calendar(ts, boundary_epoch_seconds=200.0)
    assert groups["BEFORE_BOUNDARY"] == ["w0"]
    assert groups["AT_OR_AFTER_BOUNDARY"] == ["w1", "w2"]


def test_filter_rows_to_windows():
    rows = [{"window_id": "w0"}, {"window_id": "w1"}, {"window_id": "w2"}]
    filtered = filter_rows_to_windows(rows, ["w0", "w2"])
    assert [r["window_id"] for r in filtered] == ["w0", "w2"]
