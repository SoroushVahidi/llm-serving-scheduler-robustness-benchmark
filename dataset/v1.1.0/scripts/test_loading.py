#!/usr/bin/env python3
"""Smoke-test all declared local HF configurations and the documented pandas path."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
from datasets import load_dataset

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "scheduler_outcomes": 18720,
    "unique_configurations": 9360,
    "workload_windows": 120,
    "load_region_assignments": 720,
    "policy_registry": 13,
    "pairwise_reversals": 10890,
    "ranking_correlations": 198,
    "sample_complexity": 33,
    "telemetry_explanation": 990,
    "temporal_robustness": 36,
    "topk_overlap": 198,
}


def main() -> None:
    os.environ.setdefault("HF_DATASETS_DISABLE_PROGRESS_BARS", "1")
    loaded = {}
    for name, expected in EXPECTED.items():
        ds = load_dataset(str(ROOT), name=name, split="train")
        assert len(ds) == expected, (name, len(ds), expected)
        loaded[name] = ds
    frame = loaded["scheduler_outcomes"].to_pandas()
    assert isinstance(frame, pd.DataFrame)
    assert frame.cell_id.is_unique
    assert set(frame.repetition.unique()) == {0, 1}
    key = ["source_family", "window_id", "load_region", "policy_id"]
    assert frame.groupby(key).size().eq(2).all()
    selection = frame.loc[(frame.policy_id == "fifo") & (frame.load_region == "KNEE")]
    assert len(selection) == 240  # 120 windows, two deterministic passes each
    assert selection.groupby("source_family")["arrival_normalized_weighted_goodput"].mean().shape[0] == 3
    configs = loaded["unique_configurations"].to_pandas()
    assert configs.deterministic_passes_equal.all()
    assert len(configs) == 9360
    assert set(configs.cell_id_rep0).isdisjoint(set(configs.cell_id_rep1))
    for name, key_name in (
        ("pairwise_reversals", "records"),
        ("ranking_correlations", "comparisons"),
        ("sample_complexity", "per_source_metric"),
        ("telemetry_explanation", "records"),
        ("temporal_robustness", "records"),
        ("topk_overlap", "comparisons"),
    ):
        source = json.loads((ROOT / "scientific" / "analysis" / f"{name}.json").read_text())
        value = source[key_name]
        original_count = sum(len(rows) for rows in value.values()) if isinstance(value, dict) else len(value)
        assert len(loaded[name]) == original_count
    print(json.dumps({
        "pass": True, "loaded_configs": EXPECTED,
        "pandas_outcome_rows": len(frame), "selected_fifo_knee_rows": len(selection),
        "unique_configurations": len(configs), "canonical_analysis_files_read": 6,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
