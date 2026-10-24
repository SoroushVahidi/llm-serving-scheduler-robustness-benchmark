"""Stage-0 load calibration: policy-independent capacity search, then a
single frozen reference policy (`fifo`) to translate offered load into
observed saturation -- per docs/LOAD_CALIBRATION_PROTOCOL.md.

Procedure (matches the frozen protocol exactly, not re-derived here):

1. For each frozen Stage-0 window, binary-search the inter-arrival
   compression factor lambda at which `fifo`'s `slo_violation_rate` crosses
   a fixed 0.5% threshold, against one documented single-`GPUConfig`
   capacity reference (`STAGE0_REFERENCE_GPU_CONFIG`) used identically for
   every window and every source.
2. Call that lambda the window's reference capacity `lambda_ref`.
3. Define three Stage-0 operating regions (Stage-0 deliberately excludes
   `LOW`, per docs/STAGE0_DISCRIMINABILITY_PROTOCOL.md):
   - `PRE_KNEE` = 0.8 * lambda_ref
   - `KNEE`     = 1.0 * lambda_ref
   - `OVERLOAD` = 1.2 * lambda_ref

No policy under Stage-0 study (`fifo`, `edf`, `kv_constrained_online`,
`vllm_faithful`, `sarathi_faithful`, `vllm_style_token_budget`) is used for
calibration itself -- only `fifo`, exactly as the protocol requires. The
per-source multiplier table (0.8/1.0/1.2) is used unmodified for every
source; per docs/LOAD_CALIBRATION_PROTOCOL.md item 4, any per-source
adjustment must be frozen *before* any policy-under-study result is
observed and documented in this module -- no such adjustment was made or
needed for the Stage-0 pilot.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import List, Sequence

from ..core.types import GPUConfig, Request
from ..evaluation.run_policy import run_policy
from ..policies.registry import make_policy

SLO_VIOLATION_THRESHOLD = 0.005  # 0.5%, frozen before any policy-under-study run
LOAD_REGION_MULTIPLIERS = {"PRE_KNEE": 0.8, "KNEE": 1.0, "OVERLOAD": 1.2}
REFERENCE_POLICY = "fifo"
BISECTION_ITERATIONS = 30
BISECTION_LOG_LO = -2.0   # compression factor lower bound: 10^-2 = 0.01x
BISECTION_LOG_HI = 4.0    # compression factor upper bound: 10^4 = 10,000x

# A single, documented single-GPU capacity reference used identically for
# every Stage-0 window and every source -- not tuned per window or per
# source. Values are a plausible-order-of-magnitude proxy for one modern
# accelerator's serving capacity, not a hardware-validated number (see
# docs/LOAD_CALIBRATION_PROTOCOL.md: KV-pressure/concurrency proxies are
# documented proxies only, never real backend measurements).
STAGE0_REFERENCE_GPU_CONFIG = GPUConfig(
    gpu_id=0,
    max_active_sequences=64,
    max_batch_tokens=4096,
    max_kv_tokens=131072,
)


def _rebase_and_scale(requests: Sequence[Request], compression_factor: float) -> List[Request]:
    """Compress inter-arrival gaps by `compression_factor` (>1 = denser
    arrivals), rebasing the first arrival to t=0 and scaling each request's
    SLO slack by the same factor (a documented, monotonic convention: this
    project always divides slack by compression_factor, unlike the
    asymmetric "only scale down when factor>1" rule seen in prior-repo code
    -- chosen for a single easily-audited rule at any factor value)."""
    if not requests:
        return []
    ordered = sorted(requests, key=lambda r: r.arrival_time)
    t0 = ordered[0].arrival_time
    out: List[Request] = []
    prev_scaled = 0.0
    prev_raw = t0
    for i, r in enumerate(ordered):
        raw = r.arrival_time
        if i == 0:
            arr = 0.0
        else:
            gap = max(0.0, raw - prev_raw)
            arr = prev_scaled + gap / compression_factor
        slack = max(0.0, r.slo_deadline - raw)
        out.append(
            Request(
                request_id=i,
                arrival_time=arr,
                prompt_tokens=r.prompt_tokens,
                predicted_output_tokens=r.predicted_output_tokens,
                actual_output_tokens=r.actual_output_tokens,
                slo_deadline=arr + slack / compression_factor,
                priority=r.priority,
                class_id=r.class_id,
            )
        )
        prev_scaled = arr
        prev_raw = raw
    return out


def _slo_violation_rate_at(compression_factor: float, requests: Sequence[Request]) -> float:
    scaled = _rebase_and_scale(requests, compression_factor)
    policy = make_policy(REFERENCE_POLICY)
    metrics = run_policy(
        policy, scaled, [STAGE0_REFERENCE_GPU_CONFIG], workload_tag="stage0_calibration", seed=0
    )
    if metrics.num_completed == 0:
        return 1.0
    return metrics.slo_violation_rate


@dataclass
class CalibrationSanityCheck:
    pre_knee_completion_fraction: float
    pre_knee_slo_violation_rate: float
    knee_completion_fraction: float
    knee_slo_violation_rate: float
    overload_completion_fraction: float
    overload_slo_violation_rate: float
    plausible: bool
    notes: List[str]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class WindowCalibration:
    window_id: str
    source_family: str
    reference_policy: str
    slo_violation_threshold: float
    lambda_ref: float
    bisection_lo: float
    bisection_hi: float
    bisection_iterations: int
    load_regions: dict  # {"PRE_KNEE": float, "KNEE": float, "OVERLOAD": float}
    sanity: dict

    def to_dict(self) -> dict:
        return asdict(self)


def _classify_sanity_notes(m_pre, m_over, lambda_ref: float) -> tuple[List[str], List[str]]:
    """Pure classification of the calibration sanity conditions, split into
    (blocking_notes, informational_notes) -- `plausible` is gated only by
    `blocking_notes`. `m_pre`/`m_over` need only duck-type
    `completion_fraction`/`slo_violation_rate`/`num_completed`/`num_dropped`
    (a `RunMetrics` instance in production; any object with those attributes
    in tests).

    PRE_KNEE is *supposed* to sit below the violation-crossing point, so a
    near-zero PRE_KNEE violation rate is the CORRECT, expected outcome of a
    properly calibrated window, not a symptom of a broken one. With
    `window_size` requests, `slo_violation_rate` can only take values that
    are multiples of `1/window_size`; `SLO_VIOLATION_THRESHOLD` (0.005) is
    itself exactly one such step for the frozen Stage-0 window size (200),
    so PRE_KNEE landing at exactly 0 violations is close to mathematically
    guaranteed for any reasonably monotonic response curve, regardless of
    whether the calibration is good or bad. This condition therefore cannot
    discriminate a real problem and is INFORMATIONAL ONLY -- it does not
    gate `plausible` (see docs/STAGE0_LOAD_CALIBRATION_AUDIT_20260901.md
    section A4/A6, derived entirely from this reference-calibration
    mechanism, before any Stage-0-study policy was ever run)."""
    blocking: List[str] = []
    informational: List[str] = []

    if m_pre.completion_fraction >= 0.999 and m_pre.slo_violation_rate < 1e-6:
        informational.append(
            "PRE_KNEE looks trivially underloaded (completion_fraction~=1.0, slo_violation_rate~=0) "
            "-- informational only, not a plausibility failure (see STAGE0_LOAD_CALIBRATION_AUDIT_20260901.md)."
        )
    if m_over.slo_violation_rate < SLO_VIOLATION_THRESHOLD * 2:
        blocking.append("OVERLOAD shows little more pressure than the calibration threshold itself.")
    if math.isnan(m_over.completion_fraction) or m_over.num_completed == 0 and m_over.num_dropped == 0:
        blocking.append("OVERLOAD produced no completions and no drops -- possible simulator malfunction.")
    if lambda_ref in (10 ** BISECTION_LOG_LO, 10 ** BISECTION_LOG_HI):
        blocking.append("lambda_ref pinned to a search-range bound rather than a genuine interior crossing.")

    return blocking, informational


def calibrate_window(requests: Sequence[Request], *, window_id: str, source_family: str) -> WindowCalibration:
    """Binary-searches lambda_ref for one window, then derives and sanity-checks
    the three Stage-0 load regions. Never adjusts the search or the
    multiplier table based on the outcome -- if the result looks degenerate,
    that is recorded in `sanity.notes`, not silently corrected."""
    lo, hi = BISECTION_LOG_LO, BISECTION_LOG_HI
    f_lo = _slo_violation_rate_at(10 ** lo, requests)
    f_hi = _slo_violation_rate_at(10 ** hi, requests)

    notes: List[str] = []
    if f_lo >= SLO_VIOLATION_THRESHOLD:
        notes.append(
            f"slo_violation_rate at the lowest search bound (factor=10^{lo}) is already "
            f"{f_lo:.4f} >= threshold {SLO_VIOLATION_THRESHOLD} -- lambda_ref pinned to the "
            "lower search bound; window may be pathologically hard even near-unscaled."
        )
        lambda_ref = 10 ** lo
    elif f_hi < SLO_VIOLATION_THRESHOLD:
        notes.append(
            f"slo_violation_rate at the highest search bound (factor=10^{hi}) is still "
            f"{f_hi:.4f} < threshold {SLO_VIOLATION_THRESHOLD} -- lambda_ref pinned to the "
            "upper search bound; window may never saturate the reference GPU config within "
            "the search range."
        )
        lambda_ref = 10 ** hi
    else:
        for _ in range(BISECTION_ITERATIONS):
            mid = (lo + hi) / 2.0
            f_mid = _slo_violation_rate_at(10 ** mid, requests)
            if f_mid < SLO_VIOLATION_THRESHOLD:
                lo = mid
            else:
                hi = mid
        lambda_ref = 10 ** ((lo + hi) / 2.0)

    regions = {name: lambda_ref * mult for name, mult in LOAD_REGION_MULTIPLIERS.items()}

    def _metrics_at(factor: float):
        scaled = _rebase_and_scale(requests, factor)
        policy = make_policy(REFERENCE_POLICY)
        return run_policy(policy, scaled, [STAGE0_REFERENCE_GPU_CONFIG], workload_tag="stage0_calibration", seed=0)

    m_pre = _metrics_at(regions["PRE_KNEE"])
    m_knee = _metrics_at(regions["KNEE"])
    m_over = _metrics_at(regions["OVERLOAD"])

    blocking_notes, informational_notes = _classify_sanity_notes(m_pre, m_over, lambda_ref)
    notes.extend(blocking_notes)

    sanity = CalibrationSanityCheck(
        pre_knee_completion_fraction=m_pre.completion_fraction,
        pre_knee_slo_violation_rate=m_pre.slo_violation_rate,
        knee_completion_fraction=m_knee.completion_fraction,
        knee_slo_violation_rate=m_knee.slo_violation_rate,
        overload_completion_fraction=m_over.completion_fraction,
        overload_slo_violation_rate=m_over.slo_violation_rate,
        plausible=len(notes) == 0,
        notes=notes + informational_notes,
    )

    return WindowCalibration(
        window_id=window_id,
        source_family=source_family,
        reference_policy=REFERENCE_POLICY,
        slo_violation_threshold=SLO_VIOLATION_THRESHOLD,
        lambda_ref=lambda_ref,
        bisection_lo=10 ** BISECTION_LOG_LO,
        bisection_hi=10 ** BISECTION_LOG_HI,
        bisection_iterations=BISECTION_ITERATIONS,
        load_regions=regions,
        sanity=sanity.to_dict(),
    )
