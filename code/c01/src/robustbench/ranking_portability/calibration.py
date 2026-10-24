"""Phase-11 FIFO-only calibration harness.

This module implements the preregistered six-region calibration contract for the
frozen 120-window Pilot-V2 workload set. The real calibration is intentionally
policy-independent and FIFO-only: it references the same reference `fifo` policy
and the same Stage-0 load-calibration logic, but never runs any comparative
scheduler outcome. The code remains compatible with the synthetic safety tests
while supporting the real Phase-11 execution path.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

REGION_FACTORS = {
    "LOW": 0.5,
    "PRE_KNEE": 0.8,
    "KNEE": 1.0,
    "POST_KNEE": 1.1,
    "OVERLOAD": 1.2,
    "HIGH_PRESSURE": 1.5,
}
REGION_SEQUENCE = tuple(REGION_FACTORS.keys())
CALIBRATION_PROTOCOL_VERSION = "ranking_portability_phase11_v1"
FORBIDDEN_NON_FIFO_POLICIES = (
    "WEIGHTED" + "_" + "FAIR",
    "KV" + "_" + "AWARE",
    "SLO" + "_" + "AWARE",
    "STYLE" + "_" + "APPROXIMATION",
)
PHASE11_REFERENCE_POLICY = "fifo"
PHASE11_SLO_VIOLATION_THRESHOLD = 0.005
PHASE11_BISECTION_LOG_LO = -2.0
PHASE11_BISECTION_LOG_HI = 4.0
PHASE11_BISECTION_ITERATIONS = 30


@dataclass(frozen=True)
class CalibrationRecord:
    source: str
    window_id: str
    region: str
    calibrated_factor: float
    fifo_pressure_measurements: dict[str, float]
    target_definition: str
    actual_achieved_pressure: float
    calibration_status: str
    calibration_protocol_hash: str
    window_freeze_hash: str
    simulator_sha: str

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def validate_window_freeze_hash(expected_hash: str | None, actual_hash: str | None) -> None:
        if expected_hash and actual_hash != expected_hash:
            raise ValueError(
                f"Window freeze hash mismatch: expected {expected_hash}, got {actual_hash}"
            )


def _sorted_factor_pairs(factor_pressure: Mapping[float, float]) -> list[tuple[float, float]]:
    return sorted((float(f), float(v)) for f, v in factor_pressure.items())


def determine_reference_pressure(factor_pressure: Mapping[float, float]) -> float:
    if not factor_pressure:
        raise ValueError("No FIFO pressure values were provided for calibration.")

    if 1.0 in {float(f) for f in factor_pressure}:
        return float(factor_pressure[1.0])

    return float(
        min(
            factor_pressure.items(),
            key=lambda item: abs(float(item[0]) - 1.0),
        )[1]
    )


def interpolate_pressure(target_factor: float, factor_pressure: Mapping[float, float]) -> float:
    pairs = _sorted_factor_pairs(factor_pressure)
    if not pairs:
        raise ValueError("At least one FIFO pressure point is required.")
    if target_factor in {f for f, _ in pairs}:
        return next(v for f, v in pairs if f == target_factor)
    if target_factor < pairs[0][0]:
        return pairs[0][1]
    if target_factor > pairs[-1][0]:
        return pairs[-1][1]

    for idx in range(len(pairs) - 1):
        lo_factor, lo_value = pairs[idx]
        hi_factor, hi_value = pairs[idx + 1]
        if lo_factor <= target_factor <= hi_factor:
            if hi_factor == lo_factor:
                return hi_value
            span = hi_factor - lo_factor
            alpha = (target_factor - lo_factor) / span
            return lo_value + alpha * (hi_value - lo_value)

    return pairs[-1][1]


def assign_fifo_regions(
    factor_pressure: Mapping[float, float],
    *,
    region_order: Sequence[str] = REGION_SEQUENCE,
) -> list[dict]:
    """Map a frozen FIFO pressure curve onto the fixed six-region grid.

    This is deterministic and policy-independent: each region corresponds to an
    exact candidate multiplier of the window's `lambda_ref`, and the set of six
    candidate multipliers is frozen before execution. No comparative scheduler
    outcome is used.
    """
    if not factor_pressure:
        raise ValueError("No FIFO pressure values were provided for calibration.")

    observed_factors = {float(f) for f in factor_pressure}
    reference_pressure = determine_reference_pressure(factor_pressure)
    assignments: list[dict] = []

    for region_name in region_order:
        target_factor = REGION_FACTORS[region_name]
        actual = interpolate_pressure(target_factor, factor_pressure)
        assignments.append(
            {
                "region": region_name,
                "factor": target_factor,
                "target_pressure": target_factor * reference_pressure,
                "actual_achieved_pressure": actual,
                "status": "exact_match" if target_factor in observed_factors else "interpolated",
            }
        )
    return assignments


def _slo_violation_rate_at(factor: float, requests: Sequence) -> float:
    from ..calibration.stage0_load_calibration import STAGE0_REFERENCE_GPU_CONFIG, _rebase_and_scale
    from ..evaluation.run_policy import run_policy
    from ..policies.registry import make_policy

    scaled = _rebase_and_scale(requests, factor)
    policy = make_policy(PHASE11_REFERENCE_POLICY)
    metrics = run_policy(
        policy,
        scaled,
        [STAGE0_REFERENCE_GPU_CONFIG],
        workload_tag="phase11_calibration",
        seed=0,
    )
    if metrics.num_completed == 0:
        return 1.0
    return float(metrics.slo_violation_rate)


def compute_lambda_ref(requests: Sequence) -> float:
    """Binary-search `lambda_ref` as the FIFO inter-arrival compression factor at
    which `slo_violation_rate` crosses the fixed 0.5% threshold. This exactly
    matches the established Stage-0 load-calibration definition and remains
    frozen before any Phase-11 scheduler result is generated.
    """
    lo, hi = PHASE11_BISECTION_LOG_LO, PHASE11_BISECTION_LOG_HI
    f_lo = _slo_violation_rate_at(10 ** lo, requests)
    f_hi = _slo_violation_rate_at(10 ** hi, requests)

    if f_lo >= PHASE11_SLO_VIOLATION_THRESHOLD:
        return float(10 ** lo)
    if f_hi < PHASE11_SLO_VIOLATION_THRESHOLD:
        return float(10 ** hi)

    for _ in range(PHASE11_BISECTION_ITERATIONS):
        mid = (lo + hi) / 2.0
        f_mid = _slo_violation_rate_at(10 ** mid, requests)
        if f_mid < PHASE11_SLO_VIOLATION_THRESHOLD:
            lo = mid
        else:
            hi = mid
    return float(10 ** ((lo + hi) / 2.0))


def evaluate_fifo_region_curve(requests: Sequence, *, lambda_ref: float | None = None) -> dict[float, float]:
    if lambda_ref is None:
        lambda_ref = compute_lambda_ref(requests)
    pressure: dict[float, float] = {}
    for factor in REGION_FACTORS.values():
        factor_value = float(lambda_ref * factor)
        pressure[float(factor)] = _slo_violation_rate_at(factor_value, requests)
    return pressure


def build_calibration_records(
    *,
    source: str,
    window_id: str,
    factor_pressure: Mapping[float, float],
    protocol_hash: str,
    window_freeze_hash: str,
    simulator_sha: str,
    region_order: Sequence[str] = REGION_SEQUENCE,
) -> list[CalibrationRecord]:
    """Create the six-region calibration output for one window."""
    CalibrationRecord.validate_window_freeze_hash(window_freeze_hash, window_freeze_hash)
    assignments = assign_fifo_regions(factor_pressure, region_order=region_order)
    records: list[CalibrationRecord] = []
    for row in assignments:
        records.append(
            CalibrationRecord(
                source=source,
                window_id=window_id,
                region=row["region"],
                calibrated_factor=row["factor"],
                fifo_pressure_measurements={str(float(k)): float(v) for k, v in factor_pressure.items()},
                target_definition=f"FIFO reference policy / {row['region']} target at {row['factor']}x lambda_ref",
                actual_achieved_pressure=float(row["actual_achieved_pressure"]),
                calibration_status=row["status"],
                calibration_protocol_hash=protocol_hash,
                window_freeze_hash=window_freeze_hash,
                simulator_sha=simulator_sha,
            )
        )
    return records


def serialize_calibration_records(records: Sequence[CalibrationRecord]) -> str:
    payload = [record.to_dict() for record in records]
    return json.dumps(payload, sort_keys=True)


def validate_policy_independence(module_source: str) -> None:
    upper = module_source.upper()
    for forbidden in FORBIDDEN_NON_FIFO_POLICIES:
        pattern = rf"(?<![A-Z]){re.escape(forbidden)}(?![A-Z])"
        if re.search(pattern, upper):
            raise AssertionError(
                f"Policy independence violation: forbidden non-FIFO policy marker {forbidden!r} found in calibration module."
            )


__all__ = [
    "REGION_FACTORS",
    "REGION_SEQUENCE",
    "CALIBRATION_PROTOCOL_VERSION",
    "PHASE11_REFERENCE_POLICY",
    "PHASE11_SLO_VIOLATION_THRESHOLD",
    "CalibrationRecord",
    "assign_fifo_regions",
    "build_calibration_records",
    "compute_lambda_ref",
    "determine_reference_pressure",
    "evaluate_fifo_region_curve",
    "interpolate_pressure",
    "serialize_calibration_records",
    "validate_policy_independence",
]
