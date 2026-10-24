"""
Fit simple prefill and decode service curves from raw measurements.

Fits:
    prefill_time = a0 + a1 * prompt_tokens          (per batch_size group)
    decode_time_per_token = b0 + b1 * batch_size + b2 * context_tokens

Also computes empirical lookup tables for interpolation.
Reports fit quality metrics.

Uses only numpy for linear algebra (no sklearn dependency).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class FitResult:
    """Result of a single curve fit."""

    params: dict          # named coefficients
    rmse: float
    mape: float           # mean absolute percentage error (%)
    max_error: float      # max absolute error
    r_squared: float
    n_samples: int
    fit_method: str = "linear"


@dataclass
class ServiceCurves:
    """Container for all fitted service curves."""

    prefill: FitResult
    decode: FitResult
    lookup_tables: dict     # dict of pandas-style records for interpolation
    step_size: float
    model_name: str
    fit_timestamp: str


def _linear_fit_numpy(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """OLS fit using numpy's least-squares solver. X should include bias column."""
    coeffs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    return coeffs


def _r_squared(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Coefficient of determination."""
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - y_true.mean()) ** 2)
    if ss_tot == 0:
        return 1.0
    return float(1.0 - ss_res / ss_tot)


def _mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean absolute percentage error, skipping near-zero actuals."""
    mask = np.abs(y_true) > 1e-10
    if mask.sum() == 0:
        return 0.0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100.0)


def fit_prefill_curve(df: Any) -> FitResult:
    """
    Fit a linear model: prefill_time ~ a0 + a1 * prompt_tokens.

    Uses only batch_size=1 rows (where prefill_time_s reflects actual single-request
    prefill+1-decode, not total batch time). Batch rows have inflated prefill_time_s
    (= total_time_s) which would corrupt the fit.

    Parameters
    ----------
    df : pandas.DataFrame with columns [prompt_tokens, prefill_time_s, batch_size, skipped]

    Returns
    -------
    FitResult
    """

    # Only use single-request rows for prefill fit
    if "batch_size" in df.columns:
        df_single = df[df["batch_size"] == 1].copy()
    else:
        df_single = df.copy()

    df_ok = df_single[(df_single["skipped"] == False) & (df_single["prefill_time_s"].notna())].copy()  # noqa: E712
    df_ok = df_ok[df_ok["prefill_time_s"] > 0]

    if len(df_ok) < 2:
        raise ValueError(f"Not enough valid samples for prefill fit: {len(df_ok)}")

    X = np.column_stack([
        np.ones(len(df_ok)),
        df_ok["prompt_tokens"].values.astype(float),
    ])
    y = df_ok["prefill_time_s"].values.astype(float)

    coeffs = _linear_fit_numpy(X, y)
    y_pred = X @ coeffs

    rmse = float(np.sqrt(np.mean((y - y_pred) ** 2)))
    return FitResult(
        params={"a0": float(coeffs[0]), "a1": float(coeffs[1])},
        rmse=rmse,
        mape=_mape(y, y_pred),
        max_error=float(np.max(np.abs(y - y_pred))),
        r_squared=_r_squared(y, y_pred),
        n_samples=len(df_ok),
        fit_method="linear",
    )


def fit_decode_curve(df: Any) -> FitResult:
    """
    Fit: decode_time_per_token ~ b0 + b1 * batch_size + b2 * (prompt_tokens + output_tokens).

    context_tokens = prompt_tokens + output_tokens (approximate average KV cache size).

    Parameters
    ----------
    df : pandas.DataFrame with columns:
        [prompt_tokens, output_tokens, batch_size, decode_time_per_token_s, skipped]

    Returns
    -------
    FitResult
    """
    df_ok = df[
        (df["skipped"] == False)  # noqa: E712
        & (df["decode_time_per_token_s"].notna())
        & (df["decode_time_per_token_s"] > 0)
    ].copy()

    if len(df_ok) < 3:
        raise ValueError(f"Not enough valid samples for decode fit: {len(df_ok)}")

    context_tokens = df_ok["prompt_tokens"].values + df_ok["output_tokens"].values

    X = np.column_stack([
        np.ones(len(df_ok)),
        df_ok["batch_size"].values.astype(float),
        context_tokens.astype(float),
    ])
    y = df_ok["decode_time_per_token_s"].values.astype(float)

    coeffs = _linear_fit_numpy(X, y)
    y_pred = X @ coeffs

    rmse = float(np.sqrt(np.mean((y - y_pred) ** 2)))
    return FitResult(
        params={
            "b0": float(coeffs[0]),
            "b1": float(coeffs[1]),
            "b2": float(coeffs[2]),
        },
        rmse=rmse,
        mape=_mape(y, y_pred),
        max_error=float(np.max(np.abs(y - y_pred))),
        r_squared=_r_squared(y, y_pred),
        n_samples=len(df_ok),
        fit_method="linear",
    )


def build_lookup_table(df: Any) -> dict:
    """
    Build empirical lookup tables for direct interpolation.

    Returns a dict with:
        prefill_table: list of {prompt_tokens, batch_size, prefill_time_s_mean}
        decode_table:  list of {prompt_tokens, output_tokens, batch_size, decode_time_per_token_s_mean}
    """

    df_ok = df[df["skipped"] == False].copy()  # noqa: E712

    # Prefill lookup: group by (prompt_tokens, batch_size)
    prefill_grouped = (
        df_ok.groupby(["prompt_tokens", "batch_size"])["prefill_time_s"]
        .mean()
        .reset_index()
        .rename(columns={"prefill_time_s": "prefill_time_s_mean"})
    )

    # Decode lookup: group by (prompt_tokens, output_tokens, batch_size)
    decode_grouped = (
        df_ok.groupby(["prompt_tokens", "output_tokens", "batch_size"])["decode_time_per_token_s"]
        .mean()
        .reset_index()
        .rename(columns={"decode_time_per_token_s": "decode_time_per_token_s_mean"})
    )

    return {
        "prefill_table": prefill_grouped.to_dict(orient="records"),
        "decode_table": decode_grouped.to_dict(orient="records"),
    }


def save_service_curves(curves: ServiceCurves, path: str | Path) -> None:
    """Serialize ServiceCurves to JSON."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "prefill": asdict(curves.prefill),
        "decode": asdict(curves.decode),
        "lookup_tables": curves.lookup_tables,
        "step_size": curves.step_size,
        "model_name": curves.model_name,
        "fit_timestamp": curves.fit_timestamp,
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_service_curves(path: str | Path) -> ServiceCurves:
    """Load ServiceCurves from JSON."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Service curves file not found: {path}\n"
            "Run 'python scripts/run_gpu_calibration.py' then "
            "'python scripts/fit_service_curves.py' to generate it."
        )
    with open(path) as f:
        data = json.load(f)

    return ServiceCurves(
        prefill=FitResult(**data["prefill"]),
        decode=FitResult(**data["decode"]),
        lookup_tables=data.get("lookup_tables", {}),
        step_size=data["step_size"],
        model_name=data["model_name"],
        fit_timestamp=data["fit_timestamp"],
    )


def generate_fit_report(curves: ServiceCurves) -> dict:
    """
    Generate a comprehensive fit report dict ready for JSON serialization.
    """
    report = {
        "model_name": curves.model_name,
        "fit_timestamp": curves.fit_timestamp,
        "step_size": curves.step_size,
        "prefill": {
            "formula": "prefill_time_s = a0 + a1 * prompt_tokens",
            "params": curves.prefill.params,
            "rmse_s": curves.prefill.rmse,
            "mape_pct": curves.prefill.mape,
            "max_error_s": curves.prefill.max_error,
            "r_squared": curves.prefill.r_squared,
            "n_samples": curves.prefill.n_samples,
            "fit_method": curves.prefill.fit_method,
        },
        "decode": {
            "formula": "decode_time_per_token_s = b0 + b1*batch_size + b2*(prompt_tokens+output_tokens)",
            "params": curves.decode.params,
            "rmse_s": curves.decode.rmse,
            "mape_pct": curves.decode.mape,
            "max_error_s": curves.decode.max_error,
            "r_squared": curves.decode.r_squared,
            "n_samples": curves.decode.n_samples,
            "fit_method": curves.decode.fit_method,
        },
        "lookup_tables_prefill_rows": len(curves.lookup_tables.get("prefill_table", [])),
        "lookup_tables_decode_rows": len(curves.lookup_tables.get("decode_table", [])),
    }
    return report
