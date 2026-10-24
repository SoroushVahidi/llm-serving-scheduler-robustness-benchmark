"""
Aggregate metrics across multiple seeds for each policy.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional, Union

import pandas as pd

from ..core.metrics import RunMetrics, metrics_to_dict


def metrics_to_dataframe(results: List[RunMetrics]) -> pd.DataFrame:
    """Convert a list of RunMetrics to a pandas DataFrame."""
    rows = [metrics_to_dict(m) for m in results]
    return pd.DataFrame(rows)


def aggregate_by_policy(df: pd.DataFrame) -> pd.DataFrame:
    """Compute mean ± std across seeds, grouped by policy."""
    numeric_cols = df.select_dtypes(include=[float, int]).columns.tolist()
    # Exclude seed and step-count columns from aggregation
    exclude = {"seed", "total_gpu_busy_steps", "num_completed", "num_dropped",
               "num_slo_violated"}
    agg_cols = [c for c in numeric_cols if c not in exclude]

    agg = df.groupby("policy")[agg_cols].agg(["mean", "std"]).reset_index()
    agg.columns = [
        "_".join(filter(None, col)).strip("_") if isinstance(col, tuple) else col
        for col in agg.columns
    ]
    return agg


_PHASE1_COLS = [
    "mean_latency",
    "p95_latency",
    "p99_latency",
    "mean_queuing_delay",
    "slo_violation_rate",
    "weighted_goodput",
    "request_throughput",
    "mean_gpu_utilization",
    "mean_active_batch_size",
    "num_completed",
]

_PHASE15_EXTRA_COLS = [
    "mean_ttft",
    "p95_ttft",
    "mean_tpot",
    "p95_tpot",
    "mean_prefill_delay",
]


def make_summary_table(
    df: pd.DataFrame,
    cols: Optional[List[str]] = None,
    include_phase15: bool = False,
) -> pd.DataFrame:
    """Return a pivoted summary table with mean values for key metrics."""
    if cols is None:
        cols = list(_PHASE1_COLS)
        if include_phase15:
            cols = cols + _PHASE15_EXTRA_COLS
    available = [c for c in cols if c in df.columns]
    pivot = (
        df.groupby("policy")[available]
        .mean()
        .reset_index()
        .sort_values("mean_latency", ascending=True)
    )
    return pivot


def save_results(
    results: List[RunMetrics],
    out_dir: Union[str, Path],
) -> None:
    """Save per-run CSV, per-run JSONL, and aggregated summary to out_dir."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    df = metrics_to_dataframe(results)
    df.to_csv(out / "per_run.csv", index=False)

    with open(out / "per_run.jsonl", "w") as f:
        for m in results:
            f.write(json.dumps(metrics_to_dict(m)) + "\n")

    summary = make_summary_table(df, include_phase15=True)
    summary.to_csv(out / "summary.csv", index=False)

    with open(out / "summary.json", "w") as f:
        json.dump(summary.to_dict(orient="records"), f, indent=2)


def print_summary_table(df: pd.DataFrame, include_phase15: bool = False) -> None:
    """Pretty-print a summary table to stdout."""
    summary = make_summary_table(df, include_phase15=include_phase15)
    try:
        print(summary.to_string(index=False, float_format="%.4f"))
    except Exception:
        print(summary)
