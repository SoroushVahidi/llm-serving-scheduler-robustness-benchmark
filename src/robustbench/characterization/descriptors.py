"""Per-window workload-characterization descriptors (outcome-blind).

Computes a wide, fixed, predeclared set of descriptors from a window of
`ExternalWorkloadRecord`s (see `robustbench.workloads.external.schema`).
This module is a sibling of, not a replacement for,
`robustbench.descriptors.window_descriptors` (which backs the RQ4
explanatory analysis in the main scheduler-comparison paper) -- it is kept
entirely separate so this outcome-blind characterization experiment cannot
accidentally couple to, or be coupled to by, that pipeline.

Every descriptor is either:
  - computed only from SOURCE_OBSERVED / DETERMINISTIC_DERIVED fields
    (see field_provenance on ExternalWorkloadRecord), or
  - explicitly None when the underlying field is missing for enough of the
    window that the statistic is not meaningful (never imputed).

No descriptor here depends on a scheduler-synthesized field (SLO, priority,
predicted_output_tokens) -- see docs/WORKLOAD_DISTRIBUTION_CHARACTERIZATION_PROTOCOL.md
"Source-native feature rule".
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional, Sequence

import numpy as np
from scipy import stats as scipy_stats

from ..workloads.external.schema import ExternalWorkloadRecord

#: Predeclared long-prompt thresholds (tokens). Fixed before any result was
#: inspected -- see docs/WORKLOAD_DISTRIBUTION_CHARACTERIZATION_PROTOCOL.md.
LONG_PROMPT_THRESHOLDS = (512, 2048, 8192, 32768)

#: Number of equal-width sub-bins used for the peak short-window arrival
#: rate proxy (20 bins -> each bin covers 5% of the window's duration).
_N_SUBBINS_FOR_PEAK_RATE = 20

#: A gap between consecutive arrivals longer than this multiple of the
#: window's mean interarrival time counts toward idle_gap_fraction.
_IDLE_GAP_MULTIPLE = 3.0

DESCRIPTOR_SCHEMA_VERSION = "workload_characterization_descriptors_v1"


@dataclass
class WorkloadCharacterizationDescriptor:
    source_family: str
    window_id: str
    window_size_requested: int
    time_bucket: Optional[str]  # "EARLY" | "MIDDLE" | "LATE" | None

    # --- identity / integrity ---
    request_count: int
    n_with_arrival_time: int
    n_with_input_tokens: int
    n_with_output_tokens: int

    # --- arrival structure ---
    duration_s: Optional[float]
    mean_arrival_rate_rps: Optional[float]
    interarrival_mean_s: Optional[float]
    interarrival_std_s: Optional[float]
    interarrival_cv: Optional[float]
    interarrival_p50_s: Optional[float]
    interarrival_p90_s: Optional[float]
    interarrival_p95_s: Optional[float]
    interarrival_p99_s: Optional[float]
    burstiness_b: Optional[float]
    peak_short_window_arrival_rate_rps: Optional[float]
    idle_gap_fraction: Optional[float]

    # --- prompt (input token) structure ---
    prompt_tokens_mean: Optional[float]
    prompt_tokens_median: Optional[float]
    prompt_tokens_std: Optional[float]
    prompt_tokens_cv: Optional[float]
    prompt_tokens_p90: Optional[float]
    prompt_tokens_p95: Optional[float]
    prompt_tokens_p99: Optional[float]
    prompt_tokens_max: Optional[float]

    # --- output token structure ---
    output_tokens_mean: Optional[float]
    output_tokens_median: Optional[float]
    output_tokens_std: Optional[float]
    output_tokens_cv: Optional[float]
    output_tokens_p90: Optional[float]
    output_tokens_p95: Optional[float]
    output_tokens_p99: Optional[float]
    output_tokens_max: Optional[float]

    # --- joint length structure ---
    prompt_output_pearson_r: Optional[float]
    prompt_output_spearman_r: Optional[float]
    total_tokens_mean: Optional[float]
    total_tokens_median: Optional[float]
    total_tokens_std: Optional[float]
    total_tokens_p90: Optional[float]
    total_tokens_p95: Optional[float]
    total_tokens_p99: Optional[float]
    prompt_output_ratio_mean: Optional[float]
    prompt_output_ratio_median: Optional[float]
    prompt_output_ratio_p90: Optional[float]

    # --- long-prompt fractions (one field per predeclared threshold) ---
    long_prompt_fraction_512: Optional[float]
    long_prompt_fraction_2048: Optional[float]
    long_prompt_fraction_8192: Optional[float]
    long_prompt_fraction_32768: Optional[float]

    # --- pressure proxies (documented approximations, never modeled backend values) ---
    approx_token_arrival_rate_tps: Optional[float]
    approx_concurrent_request_proxy: Optional[float]
    approx_kv_demand_proxy_tokens: Optional[float]

    # --- heavy-tail / inequality statistics (computed on total_tokens) ---
    total_tokens_tail_ratio_p99_p50: Optional[float]
    total_tokens_excess_kurtosis: Optional[float]
    total_tokens_gini: Optional[float]

    # --- provenance honesty ---
    n_source_observed_fields: int
    n_deterministic_derived_fields: int
    n_synthesized_fields: int
    n_unavailable_fields: int
    field_provenance_summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _safe_float_array(values: Sequence) -> np.ndarray:
    return np.array([v for v in values if v is not None], dtype=float)


def _percentile_block(values: np.ndarray, prefix: str) -> dict:
    """Returns mean/median/std/cv/p90/p95/p99/max keyed by `{prefix}_*`."""
    if values.size == 0:
        keys = ("mean", "median", "std", "cv", "p90", "p95", "p99", "max")
        return {f"{prefix}_{k}": None for k in keys}
    mean = float(np.mean(values))
    std = float(np.std(values))
    return {
        f"{prefix}_mean": mean,
        f"{prefix}_median": float(np.median(values)),
        f"{prefix}_std": std,
        f"{prefix}_cv": (std / mean) if mean > 0 else None,
        f"{prefix}_p90": float(np.percentile(values, 90)),
        f"{prefix}_p95": float(np.percentile(values, 95)),
        f"{prefix}_p99": float(np.percentile(values, 99)),
        f"{prefix}_max": float(np.max(values)),
    }


def _burstiness_b(interarrivals: np.ndarray) -> Optional[float]:
    """Goh-Barabasi burstiness parameter B = (sigma - mu) / (sigma + mu)."""
    if interarrivals.size < 2:
        return None
    mu = float(np.mean(interarrivals))
    sigma = float(np.std(interarrivals))
    denom = sigma + mu
    if denom == 0:
        return None
    return (sigma - mu) / denom


def _peak_short_window_rate(arrivals: np.ndarray, duration: Optional[float]) -> Optional[float]:
    """Max request rate (req/s) across N equal-width sub-bins of the window's
    duration. Returns None if duration is unknown/degenerate."""
    if arrivals.size < 2 or not duration or duration <= 0:
        return None
    bin_width = duration / _N_SUBBINS_FOR_PEAK_RATE
    if bin_width <= 0:
        return None
    start = arrivals[0]
    bin_idx = np.minimum(
        ((arrivals - start) / bin_width).astype(int), _N_SUBBINS_FOR_PEAK_RATE - 1
    )
    counts = np.bincount(bin_idx, minlength=_N_SUBBINS_FOR_PEAK_RATE)
    return float(np.max(counts) / bin_width)


def _idle_gap_fraction(interarrivals: np.ndarray, duration: Optional[float]) -> Optional[float]:
    if interarrivals.size == 0 or not duration or duration <= 0:
        return None
    mean_ia = float(np.mean(interarrivals))
    if mean_ia <= 0:
        return None
    idle_time = float(np.sum(interarrivals[interarrivals > _IDLE_GAP_MULTIPLE * mean_ia]))
    return min(idle_time / duration, 1.0)


def _gini(values: np.ndarray) -> Optional[float]:
    """Gini coefficient over non-negative values. None if fewer than 2
    positive values or all values are identical (undefined/degenerate)."""
    v = values[values >= 0]
    if v.size < 2:
        return None
    total = float(np.sum(v))
    if total == 0:
        return None
    sorted_v = np.sort(v)
    n = sorted_v.size
    cum = np.cumsum(sorted_v)
    # Standard discrete Gini via the Lorenz-curve trapezoid formula.
    gini = (n + 1 - 2 * float(np.sum(cum)) / total) / n
    return float(gini)


def compute_characterization_descriptor(
    records: Sequence[ExternalWorkloadRecord],
    *,
    source_family: str,
    window_id: str,
    window_size_requested: int,
    time_bucket: Optional[str] = None,
) -> WorkloadCharacterizationDescriptor:
    """Compute one WorkloadCharacterizationDescriptor from a window's worth
    of Layer-1 records. Performs no filtering/selection itself -- window
    membership is decided upstream (see
    `scripts/characterization/build_characterization_windows.py`)."""
    n = len(records)

    arrivals = np.sort(_safe_float_array(r.arrival_time_s for r in records))
    n_with_arrival = int(arrivals.size)
    duration = float(arrivals[-1] - arrivals[0]) if arrivals.size >= 2 else None
    arrival_rate = (n_with_arrival / duration) if duration and duration > 0 else None
    interarrivals = np.diff(arrivals) if arrivals.size >= 2 else np.array([])
    interarrival_mean = float(np.mean(interarrivals)) if interarrivals.size else None
    interarrival_std = float(np.std(interarrivals)) if interarrivals.size else None
    interarrival_cv = (
        interarrival_std / interarrival_mean
        if interarrival_mean and interarrival_mean > 0
        else None
    )
    ia_percentiles = (
        {p: float(np.percentile(interarrivals, p)) for p in (50, 90, 95, 99)}
        if interarrivals.size
        else {p: None for p in (50, 90, 95, 99)}
    )
    burstiness = _burstiness_b(interarrivals)
    peak_rate = _peak_short_window_rate(arrivals, duration)
    idle_frac = _idle_gap_fraction(interarrivals, duration)

    prompt_tokens = _safe_float_array(r.input_tokens for r in records)
    output_tokens = _safe_float_array(r.output_tokens for r in records)
    prompt_block = _percentile_block(prompt_tokens, "prompt_tokens")
    output_block = _percentile_block(output_tokens, "output_tokens")

    paired = [
        (r.input_tokens, r.output_tokens)
        for r in records
        if r.input_tokens is not None and r.output_tokens is not None
    ]
    if len(paired) >= 2:
        p_arr = np.array([p for p, _ in paired], dtype=float)
        o_arr = np.array([o for _, o in paired], dtype=float)
        pearson_r = (
            float(np.corrcoef(p_arr, o_arr)[0, 1])
            if np.std(p_arr) > 0 and np.std(o_arr) > 0
            else None
        )
        if np.std(p_arr) > 0 and np.std(o_arr) > 0:
            spearman_r = float(scipy_stats.spearmanr(p_arr, o_arr).statistic)
        else:
            spearman_r = None
        # Ratio uses +1 smoothing to avoid division by zero for legitimate
        # zero-output-token rounds (e.g. tool-call-only turns); documented,
        # not a fabricated value.
        ratios = (p_arr + 1.0) / (o_arr + 1.0)
        ratio_block = {
            "prompt_output_ratio_mean": float(np.mean(ratios)),
            "prompt_output_ratio_median": float(np.median(ratios)),
            "prompt_output_ratio_p90": float(np.percentile(ratios, 90)),
        }
    else:
        pearson_r = None
        spearman_r = None
        ratio_block = {
            "prompt_output_ratio_mean": None,
            "prompt_output_ratio_median": None,
            "prompt_output_ratio_p90": None,
        }

    totals = _safe_float_array(
        (
            r.total_tokens
            if r.total_tokens is not None
            else (
                (r.input_tokens + r.output_tokens)
                if r.input_tokens is not None and r.output_tokens is not None
                else None
            )
        )
        for r in records
    )
    total_block_full = _percentile_block(totals, "total_tokens")
    total_block = {
        k: total_block_full[k]
        for k in ("total_tokens_mean", "total_tokens_median", "total_tokens_std",
                  "total_tokens_p90", "total_tokens_p95", "total_tokens_p99")
    }

    long_prompt_fractions = {}
    for thr in LONG_PROMPT_THRESHOLDS:
        long_prompt_fractions[f"long_prompt_fraction_{thr}"] = (
            float(np.mean(prompt_tokens >= thr)) if prompt_tokens.size else None
        )

    total_tokens_mean = total_block_full["total_tokens_mean"]
    output_tokens_mean = output_block["output_tokens_mean"]
    prompt_tokens_mean = prompt_block["prompt_tokens_mean"]

    token_arrival_rate = (
        arrival_rate * total_tokens_mean
        if arrival_rate is not None and total_tokens_mean is not None
        else None
    )
    # Little's-law-style standing-request-count proxy: arrival_rate (req/s) *
    # a service-time proxy (mean output tokens, since decode length dominates
    # serving time far more than the prefill step for typical LLM serving).
    concurrent_request_proxy = (
        arrival_rate * output_tokens_mean
        if arrival_rate is not None and output_tokens_mean is not None
        else None
    )
    # Standing-KV-token proxy: (concurrent request count) * (mean context
    # size per request) -- an approximation of aggregate KV footprint, not a
    # measured value from any real KV-cache manager.
    kv_demand_proxy = (
        concurrent_request_proxy * prompt_tokens_mean
        if concurrent_request_proxy is not None and prompt_tokens_mean is not None
        else None
    )

    tail_ratio = None
    excess_kurtosis = None
    gini = None
    if totals.size >= 2:
        p50 = float(np.percentile(totals, 50))
        p99 = float(np.percentile(totals, 99))
        tail_ratio = (p99 / p50) if p50 > 0 else None
        excess_kurtosis = float(scipy_stats.kurtosis(totals, fisher=True, bias=False)) if totals.size >= 4 else None
        gini = _gini(totals)

    provenance_counts: dict[str, int] = {}
    for r in records:
        for kind in r.field_provenance.values():
            provenance_counts[kind] = provenance_counts.get(kind, 0) + 1

    return WorkloadCharacterizationDescriptor(
        source_family=source_family,
        window_id=window_id,
        window_size_requested=window_size_requested,
        time_bucket=time_bucket,
        request_count=n,
        n_with_arrival_time=n_with_arrival,
        n_with_input_tokens=int(prompt_tokens.size),
        n_with_output_tokens=int(output_tokens.size),
        duration_s=duration,
        mean_arrival_rate_rps=arrival_rate,
        interarrival_mean_s=interarrival_mean,
        interarrival_std_s=interarrival_std,
        interarrival_cv=interarrival_cv,
        interarrival_p50_s=ia_percentiles[50],
        interarrival_p90_s=ia_percentiles[90],
        interarrival_p95_s=ia_percentiles[95],
        interarrival_p99_s=ia_percentiles[99],
        burstiness_b=burstiness,
        peak_short_window_arrival_rate_rps=peak_rate,
        idle_gap_fraction=idle_frac,
        prompt_tokens_mean=prompt_block["prompt_tokens_mean"],
        prompt_tokens_median=prompt_block["prompt_tokens_median"],
        prompt_tokens_std=prompt_block["prompt_tokens_std"],
        prompt_tokens_cv=prompt_block["prompt_tokens_cv"],
        prompt_tokens_p90=prompt_block["prompt_tokens_p90"],
        prompt_tokens_p95=prompt_block["prompt_tokens_p95"],
        prompt_tokens_p99=prompt_block["prompt_tokens_p99"],
        prompt_tokens_max=prompt_block["prompt_tokens_max"],
        output_tokens_mean=output_block["output_tokens_mean"],
        output_tokens_median=output_block["output_tokens_median"],
        output_tokens_std=output_block["output_tokens_std"],
        output_tokens_cv=output_block["output_tokens_cv"],
        output_tokens_p90=output_block["output_tokens_p90"],
        output_tokens_p95=output_block["output_tokens_p95"],
        output_tokens_p99=output_block["output_tokens_p99"],
        output_tokens_max=output_block["output_tokens_max"],
        prompt_output_pearson_r=pearson_r,
        prompt_output_spearman_r=spearman_r,
        total_tokens_mean=total_block["total_tokens_mean"],
        total_tokens_median=total_block["total_tokens_median"],
        total_tokens_std=total_block["total_tokens_std"],
        total_tokens_p90=total_block["total_tokens_p90"],
        total_tokens_p95=total_block["total_tokens_p95"],
        total_tokens_p99=total_block["total_tokens_p99"],
        prompt_output_ratio_mean=ratio_block["prompt_output_ratio_mean"],
        prompt_output_ratio_median=ratio_block["prompt_output_ratio_median"],
        prompt_output_ratio_p90=ratio_block["prompt_output_ratio_p90"],
        long_prompt_fraction_512=long_prompt_fractions["long_prompt_fraction_512"],
        long_prompt_fraction_2048=long_prompt_fractions["long_prompt_fraction_2048"],
        long_prompt_fraction_8192=long_prompt_fractions["long_prompt_fraction_8192"],
        long_prompt_fraction_32768=long_prompt_fractions["long_prompt_fraction_32768"],
        approx_token_arrival_rate_tps=token_arrival_rate,
        approx_concurrent_request_proxy=concurrent_request_proxy,
        approx_kv_demand_proxy_tokens=kv_demand_proxy,
        total_tokens_tail_ratio_p99_p50=tail_ratio,
        total_tokens_excess_kurtosis=excess_kurtosis,
        total_tokens_gini=gini,
        n_source_observed_fields=provenance_counts.get("SOURCE_OBSERVED", 0),
        n_deterministic_derived_fields=provenance_counts.get("DETERMINISTIC_DERIVED", 0),
        n_synthesized_fields=provenance_counts.get("SYNTHESIZED_IMPUTED", 0),
        n_unavailable_fields=provenance_counts.get("UNAVAILABLE", 0),
        field_provenance_summary=provenance_counts,
    )


#: The subset of descriptor fields used as the common cross-source numeric
#: feature matrix for the multivariate distance / separability analyses
#: (section 6B/6E of the protocol). Deliberately excludes identity/count
#: fields and provenance-bookkeeping fields.
COMMON_NUMERIC_FEATURES = (
    "mean_arrival_rate_rps",
    "interarrival_cv",
    "interarrival_p50_s",
    "interarrival_p90_s",
    "interarrival_p99_s",
    "burstiness_b",
    "peak_short_window_arrival_rate_rps",
    "idle_gap_fraction",
    "prompt_tokens_mean",
    "prompt_tokens_cv",
    "prompt_tokens_p90",
    "prompt_tokens_p99",
    "output_tokens_mean",
    "output_tokens_cv",
    "output_tokens_p90",
    "output_tokens_p99",
    "prompt_output_pearson_r",
    "prompt_output_spearman_r",
    "total_tokens_mean",
    "total_tokens_p90",
    "total_tokens_p99",
    "prompt_output_ratio_mean",
    "long_prompt_fraction_512",
    "long_prompt_fraction_2048",
    "long_prompt_fraction_8192",
    "approx_token_arrival_rate_tps",
    "approx_concurrent_request_proxy",
    "approx_kv_demand_proxy_tokens",
    "total_tokens_tail_ratio_p99_p50",
    "total_tokens_excess_kurtosis",
    "total_tokens_gini",
)
