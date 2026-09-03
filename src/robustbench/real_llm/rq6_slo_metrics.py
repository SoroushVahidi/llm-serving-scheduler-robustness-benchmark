"""RQ6 real-vLLM SLO/weight metric pipeline.

Implements the concrete, scoped engineering prerequisite named in
docs/RQ6_REAL_VLLM_CALIBRATION_PROTOCOL_20260902.md ("What is frozen now vs.
what remains open"): `calibration_common`/`vllm_openai_client` do not attach
a per-request `slo_deadline`/`weight` or compute `t_done`-vs-`slo_deadline`
client-side, so `slo_violation_rate_real` (and, downstream,
`arrival_normalized_weighted_goodput`) is `UNAVAILABLE` from the real
collection layer today (docs/REAL_SYSTEM_METRIC_MAPPING.md). This module
attaches those fields and computes the metric -- reusing the exact frozen
`slo_deadline`/`weight` (=`priority`) values already carried through into
each RQ6 workload manifest request (`stage0_synthesis_v1`,
docs/DATA_FIELD_PROVENANCE.md), never resynthesizing them.

Calibration population (2026-09-03, frozen): forensic inspection of
Phase-12's own `execute_cell.py` (fresh `Simulator` + `policy.reset()` per
cell) and `ranking_portability/analysis/ranking_analysis.py` ("(policy,
window) rows treated as independent", bootstrap-resampled over windows)
established that each of the 120 frozen windows (40/source x 3 sources) is
an independent unit in Phase-12's own methodology, each with its own
`lambda_ref`. The real-vLLM calibration bisection therefore runs per
window (200 requests/candidate, 120 independent calibrations total), never
against a concatenated per-source trace -- see
docs/RQ6_REAL_VLLM_SCIENTIFIC_PROTOCOL_20260902.md's "Execution unit"
section.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence


def scale_request_timing(
    base_relative_arrival_s: float, base_slo_deadline_s: float, candidate_scale: float,
) -> tuple[float, float]:
    """Applies the real-engine candidate timing scale `s` to one request's
    frozen (already 1.5x-that-window's-own-lambda_ref-scaled) trace-shape
    arrival/deadline, per docs/RQ6_REAL_VLLM_SCIENTIFIC_PROTOCOL_20260902.md
    and the workload manifest's own `timing_transform_formula` field:

        real_arrival = base_relative_arrival / s
        real_slo_deadline = real_arrival + (base_slo_deadline - base_relative_arrival) / s

    This is exactly `_rebase_and_scale`'s "arr + slack / compression_factor"
    convention (src/robustbench/calibration/stage0_load_calibration.py)
    applied a second time, with `s` playing the role of `compression_factor`
    and the manifest's `base_*` fields playing the role of that function's
    `raw` input -- never the simulator's own absolute `lambda_ref` reused as
    a real-engine rate.
    """
    if candidate_scale <= 0:
        raise ValueError(f"candidate_scale must be > 0, got {candidate_scale}")
    real_arrival = base_relative_arrival_s / candidate_scale
    slack = base_slo_deadline_s - base_relative_arrival_s
    real_slo_deadline = real_arrival + slack / candidate_scale
    return real_arrival, real_slo_deadline


@dataclass
class RequestOutcome:
    """One request's real-engine completion outcome, for
    `real_slo_violation_rate`. `t_done_s` is the request's completion time,
    in the same time base as `slo_deadline_s` (both relative to the same
    run-start reference); `None` means the request never completed
    (dispatch failure, timeout, server crash) and is fail-closed per
    `_slo_violation_rate_at`'s `num_completed == 0 -> 1.0` convention below.
    """

    weight: float
    slo_deadline_s: float
    t_done_s: Optional[float]


def real_slo_violation_rate(outcomes: Sequence[RequestOutcome]) -> float:
    """`1 - (weighted count of requests with t_done <= slo_deadline) /
    (weighted count of completed requests)`, per
    docs/REAL_SYSTEM_METRIC_MAPPING.md and
    docs/RQ6_REAL_VLLM_CALIBRATION_PROTOCOL_20260902.md's
    `slo_violation_rate_real_definition`.

    Fail-closed: a candidate factor with zero completed requests (server
    crash, timeout) returns 1.0, mirroring
    `stage0_load_calibration._slo_violation_rate_at`'s
    `num_completed == 0 -> return 1.0` fallback (never a divide-by-zero, and
    never silently treated as 0% violation).
    """
    completed = [o for o in outcomes if o.t_done_s is not None]
    if not completed:
        return 1.0
    total_weight = sum(o.weight for o in completed)
    if total_weight <= 0:
        return 1.0
    met_weight = sum(o.weight for o in completed if o.t_done_s <= o.slo_deadline_s)
    return 1.0 - (met_weight / total_weight)
