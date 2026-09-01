"""Standardized per-window workload descriptor extractor (new for this project).

Computes a fixed set of source-agnostic descriptors from a window of
`ExternalWorkloadRecord`s (see `robustbench.workloads.external.schema`, reused
from the module-intervention-benchmark ingestion layer). Descriptors are used
downstream to (a) characterize each workload window independently of any
scheduler outcome, and (b) explain observed rank reversals (RQ4) without
turning the explanation into an online selector.

Design rule (non-negotiable): every descriptor must say, honestly, whether it
was computed from source-observed fields or from synthesized/overlaid ones.
We never silently treat a synthetic overlay as a source-native signal -- see
`field_provenance_summary` on `WindowDescriptor`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

import numpy as np

from ..workloads.external.schema import ExternalWorkloadRecord

#: Requests with total_tokens at or above this threshold count toward
#: long_context_fraction. Matches derived_features.LONG_CONTEXT_TOKEN_THRESHOLD
#: so descriptors and Layer-2 pressure derivatives stay consistent.
LONG_CONTEXT_TOKEN_THRESHOLD = 8192

PERCENTILES = (50, 90, 95, 99)


@dataclass
class WindowDescriptor:
    source_family: str
    window_id: str
    time_bucket: Optional[str]

    request_count: int
    duration_s: Optional[float]
    arrival_rate_rps: Optional[float]

    interarrival_mean_s: Optional[float]
    interarrival_cv: Optional[float]
    burstiness_b: Optional[float]  # Goh-Barabasi burstiness parameter in [-1, 1]

    prompt_tokens_mean: Optional[float]
    prompt_tokens_p50: Optional[float]
    prompt_tokens_p90: Optional[float]
    prompt_tokens_p95: Optional[float]
    prompt_tokens_p99: Optional[float]
    prompt_tokens_cv: Optional[float]

    output_tokens_mean: Optional[float]
    output_tokens_p50: Optional[float]
    output_tokens_p90: Optional[float]
    output_tokens_p95: Optional[float]
    output_tokens_p99: Optional[float]
    output_tokens_cv: Optional[float]

    prompt_output_correlation: Optional[float]
    long_context_fraction: Optional[float]

    concurrency_proxy: Optional[float]
    kv_pressure_proxy: Optional[float]

    has_native_priority: bool
    has_native_slo: bool

    n_synthesized_fields: int
    n_source_observed_fields: int
    n_unavailable_fields: int
    field_provenance_summary: dict = field(default_factory=dict)


def _percentiles(values: np.ndarray) -> dict:
    if values.size == 0:
        return {p: None for p in PERCENTILES} | {"mean": None, "cv": None}
    out: dict[str, Any] = {"mean": float(np.mean(values))}
    for p in PERCENTILES:
        out[p] = float(np.percentile(values, p))
    std = float(np.std(values))
    out["cv"] = std / out["mean"] if out["mean"] not in (0, None) else None
    return out


def _burstiness_b(interarrivals: np.ndarray) -> Optional[float]:
    """Goh-Barabasi burstiness parameter B = (sigma - mu) / (sigma + mu).

    B in (-1, 0): more regular than Poisson. B = 0: Poisson-like.
    B in (0, 1): bursty. Undefined (None) for fewer than 2 interarrivals.
    """
    if interarrivals.size < 2:
        return None
    mu = float(np.mean(interarrivals))
    sigma = float(np.std(interarrivals))
    denom = sigma + mu
    if denom == 0:
        return None
    return (sigma - mu) / denom


def compute_window_descriptor(
    records: Sequence[ExternalWorkloadRecord],
    source_family: str,
    window_id: str,
    time_bucket: Optional[str] = None,
) -> WindowDescriptor:
    """Compute one WindowDescriptor from a window's worth of Layer-1 records.

    Records are assumed to already belong to a single window (window
    construction / manifest membership is a separate, frozen step -- see
    docs/SPLIT_PROTOCOL.md); this function performs no filtering itself.
    """
    n = len(records)

    arrivals = np.array(
        sorted(r.arrival_time_s for r in records if r.arrival_time_s is not None),
        dtype=float,
    )
    duration = float(arrivals[-1] - arrivals[0]) if arrivals.size >= 2 else None
    arrival_rate = (n / duration) if duration and duration > 0 else None
    interarrivals = np.diff(arrivals) if arrivals.size >= 2 else np.array([])
    interarrival_mean = float(np.mean(interarrivals)) if interarrivals.size else None
    interarrival_cv = (
        float(np.std(interarrivals) / interarrival_mean)
        if interarrival_mean and interarrival_mean > 0
        else None
    )
    burstiness = _burstiness_b(interarrivals)

    prompt_tokens = np.array(
        [r.input_tokens for r in records if r.input_tokens is not None], dtype=float
    )
    output_tokens = np.array(
        [r.output_tokens for r in records if r.output_tokens is not None], dtype=float
    )
    prompt_stats = _percentiles(prompt_tokens)
    output_stats = _percentiles(output_tokens)

    paired = [
        (r.input_tokens, r.output_tokens)
        for r in records
        if r.input_tokens is not None and r.output_tokens is not None
    ]
    if len(paired) >= 2:
        p_arr, o_arr = zip(*paired)
        p_arr, o_arr = np.array(p_arr, dtype=float), np.array(o_arr, dtype=float)
        prompt_output_corr = (
            float(np.corrcoef(p_arr, o_arr)[0, 1]) if np.std(p_arr) > 0 and np.std(o_arr) > 0 else None
        )
    else:
        prompt_output_corr = None

    totals = np.array(
        [
            r.total_tokens
            if r.total_tokens is not None
            else (
                (r.input_tokens or 0) + (r.output_tokens or 0)
                if r.input_tokens is not None or r.output_tokens is not None
                else None
            )
            for r in records
        ],
        dtype=object,
    )
    totals_known = np.array([t for t in totals if t is not None], dtype=float)
    long_context_fraction = (
        float(np.mean(totals_known >= LONG_CONTEXT_TOKEN_THRESHOLD)) if totals_known.size else None
    )

    # Documented proxies, not measured backend quantities (no real service-time
    # or KV-block accounting exists at the Layer-1 ingestion stage).
    concurrency_proxy = (
        arrival_rate * output_stats["mean"]
        if arrival_rate is not None and output_stats["mean"] is not None
        else None
    )
    kv_pressure_proxy = float(np.mean(totals_known)) if totals_known.size else None

    has_native_priority = any(
        r.extra.get("priority") is not None or r.field_provenance.get("priority") == "SOURCE_OBSERVED"
        for r in records
    )
    has_native_slo = any(
        r.extra.get("slo") is not None or r.field_provenance.get("slo") == "SOURCE_OBSERVED"
        for r in records
    )

    provenance_counts: dict[str, int] = {}
    for r in records:
        for kind in r.field_provenance.values():
            provenance_counts[kind] = provenance_counts.get(kind, 0) + 1

    return WindowDescriptor(
        source_family=source_family,
        window_id=window_id,
        time_bucket=time_bucket,
        request_count=n,
        duration_s=duration,
        arrival_rate_rps=arrival_rate,
        interarrival_mean_s=interarrival_mean,
        interarrival_cv=interarrival_cv,
        burstiness_b=burstiness,
        prompt_tokens_mean=prompt_stats["mean"],
        prompt_tokens_p50=prompt_stats[50],
        prompt_tokens_p90=prompt_stats[90],
        prompt_tokens_p95=prompt_stats[95],
        prompt_tokens_p99=prompt_stats[99],
        prompt_tokens_cv=prompt_stats["cv"],
        output_tokens_mean=output_stats["mean"],
        output_tokens_p50=output_stats[50],
        output_tokens_p90=output_stats[90],
        output_tokens_p95=output_stats[95],
        output_tokens_p99=output_stats[99],
        output_tokens_cv=output_stats["cv"],
        prompt_output_correlation=prompt_output_corr,
        long_context_fraction=long_context_fraction,
        concurrency_proxy=concurrency_proxy,
        kv_pressure_proxy=kv_pressure_proxy,
        has_native_priority=has_native_priority,
        has_native_slo=has_native_slo,
        n_synthesized_fields=provenance_counts.get("SYNTHESIZED_IMPUTED", 0),
        n_source_observed_fields=provenance_counts.get("SOURCE_OBSERVED", 0),
        n_unavailable_fields=provenance_counts.get("UNAVAILABLE", 0),
        field_provenance_summary=provenance_counts,
    )
