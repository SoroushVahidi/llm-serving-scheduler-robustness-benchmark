"""RQ6 real-vLLM per-window calibration: the live bisection runner.

Calibration population (frozen 2026-09-03, per
docs/RQ6_REAL_VLLM_SCIENTIFIC_PROTOCOL_20260902.md's "Calibration
population" section): each of the 120 frozen windows (3 sources x 40
windows/source) is calibrated INDEPENDENTLY against exactly its own 200
frozen requests -- never a concatenated per-source trace, never a subset
of windows, never SLAI. Reference policy is always `vllm_faithful`
(vLLM's native FCFS scheduling, no custom scheduler class).

Reuses, rather than duplicates:
- `robustbench.real_llm.rq6_slo_metrics` for the timing-scale formula and
  the frozen SLO-violation-rate definition.
- `robustbench.real_llm.vllm_openai_client.call_non_streaming` for the
  actual HTTP call against vLLM's OpenAI-compatible endpoint.
- `robustbench.real_llm.calibration_common.build_exact_length_prompt` for
  deterministic prompt reconstruction.
- The exact bisection search shape (log10 bounds, iteration count,
  threshold, tie behavior) already frozen in
  `robustbench.ranking_portability.calibration.compute_lambda_ref` --
  mirrored here as a search-shape definition only, never reusing the
  simulator's own numeric `lambda_ref` result.
"""
from __future__ import annotations

import concurrent.futures
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

from .calibration_common import build_exact_length_prompt
from .rq6_slo_metrics import RequestOutcome, real_slo_violation_rate, scale_request_timing

# Mirrors src/robustbench/ranking_portability/calibration.py's frozen
# bisection constants exactly (search-shape only, never the numeric result).
BISECTION_LOG_LO = -2.0
BISECTION_LOG_HI = 4.0
BISECTION_ITERATIONS = 30
SLO_VIOLATION_THRESHOLD = 0.005

REFERENCE_POLICY = "vllm_faithful"


@dataclass
class EpisodeResetReport:
    """Result of the reset barrier checked between window episodes (and,
    within a window, between bisection candidates). See
    docs/RQ6_REAL_VLLM_SCIENTIFIC_PROTOCOL_20260902.md's "Episode reset"
    section for the full invariant list -- this reports the two directly
    server-observable ones (running/waiting queue depth from vLLM's own
    `/metrics`); the remaining invariants (held requests, KV release,
    request-ID isolation) hold by construction of the sequential
    wait-for-all-responses replay design used here, not by a separate
    server-side check.
    """

    num_requests_running: Optional[float]
    num_requests_waiting: Optional[float]
    metrics_available: bool
    passed: bool
    elapsed_s: float


def _parse_prometheus_gauge(metrics_text: str, name: str) -> Optional[float]:
    """Sums all time series for a Prometheus gauge line (there is normally
    exactly one, labeled by model_name). Returns None if the metric is
    absent (older vLLM version, or /metrics disabled)."""
    total = 0.0
    found = False
    for line in metrics_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if not line.startswith(name):
            continue
        # "metric_name{labels} value" or "metric_name value"
        parts = line.rsplit(" ", 1)
        if len(parts) != 2:
            continue
        key, value = parts
        if key == name or key.startswith(f"{name}{{"):
            try:
                total += float(value)
                found = True
            except ValueError:
                continue
    return total if found else None


def check_reset_barrier(
    fetch_metrics: Callable[[], str], *, timeout_s: float = 30.0, poll_interval_s: float = 0.2,
) -> EpisodeResetReport:
    """Polls `fetch_metrics()` (a callable returning vLLM's `/metrics` text
    body, injected so this is unit-testable without a live server) until
    both `vllm:num_requests_running` and `vllm:num_requests_waiting` read
    0, or `timeout_s` elapses. In this runner's sequential design (a window
    episode only ends after every one of its 200 dispatched requests has
    already returned an HTTP response), this should pass immediately on
    the first poll -- the barrier exists as a defense-in-depth check, not
    the primary isolation mechanism.
    """
    deadline = time.monotonic() + timeout_s
    start = time.monotonic()
    last_running: Optional[float] = None
    last_waiting: Optional[float] = None
    metrics_available = False
    while True:
        text = fetch_metrics()
        running = _parse_prometheus_gauge(text, "vllm:num_requests_running")
        waiting = _parse_prometheus_gauge(text, "vllm:num_requests_waiting")
        last_running, last_waiting = running, waiting
        if running is not None or waiting is not None:
            metrics_available = True
        if (running is None or running == 0) and (waiting is None or waiting == 0):
            return EpisodeResetReport(
                num_requests_running=running, num_requests_waiting=waiting,
                metrics_available=metrics_available, passed=True,
                elapsed_s=time.monotonic() - start,
            )
        if time.monotonic() >= deadline:
            return EpisodeResetReport(
                num_requests_running=last_running, num_requests_waiting=last_waiting,
                metrics_available=metrics_available, passed=False,
                elapsed_s=time.monotonic() - start,
            )
        time.sleep(poll_interval_s)


@dataclass
class WindowRequestReplayResult:
    slo_violation_rate: float
    n_completed: int
    n_total: int
    outcomes: List[RequestOutcome] = field(default_factory=list)


def replay_window_once(
    window_requests: Sequence[Dict[str, Any]],
    *,
    candidate_scale: float,
    tokenizer: Any,
    model: str,
    call_fn: Callable[[str, int, bool], Dict[str, Any]],
    max_workers: int = 32,
    request_timeout_s: int = 120,
) -> WindowRequestReplayResult:
    """Replays exactly one frozen window's 200 requests once, at real-engine
    timing scale `candidate_scale`, and returns the frozen SLO-violation
    rate. `call_fn(prompt_text, max_tokens, ignore_eos) -> {"output_tokens":
    ..., "prompt_tokens": ...}` is injected (production wires it to
    `vllm_openai_client.call_non_streaming` against a live server; tests
    inject a deterministic stub) -- never a mock outcome silently treated
    as real evidence.

    Every request is dispatched at its own scheduled wall-clock offset
    (`real_arrival_s` from `rq6_slo_metrics.scale_request_timing`) relative
    to this call's start, and this function returns only once every
    dispatched request's HTTP call has returned (success or failure) -- by
    construction, the reset barrier's running/waiting queue is therefore
    already empty when this returns.
    """
    run_start = time.monotonic()
    outcomes: List[Optional[RequestOutcome]] = [None] * len(window_requests)

    def _dispatch(i: int, r: Dict[str, Any]) -> None:
        real_arrival, real_deadline = scale_request_timing(
            r["base_relative_arrival_s"], r["base_slo_deadline_s"], candidate_scale,
        )
        sleep_for = run_start + real_arrival - time.monotonic()
        if sleep_for > 0:
            time.sleep(sleep_for)
        prompt_text = build_exact_length_prompt(tokenizer, r["input_tokens"], r["prompt_generation_seed"])
        try:
            out = call_fn(prompt_text, int(r["output_tokens_target"]), True)
            t_done = time.monotonic() - run_start
            outcomes[i] = RequestOutcome(weight=r["weight"], slo_deadline_s=real_deadline, t_done_s=t_done)
        except Exception:
            outcomes[i] = RequestOutcome(weight=r["weight"], slo_deadline_s=real_deadline, t_done_s=None)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_dispatch, i, r) for i, r in enumerate(window_requests)]
        concurrent.futures.wait(futures, timeout=request_timeout_s * 2 + 60)

    final_outcomes = [o if o is not None else RequestOutcome(weight=r["weight"], slo_deadline_s=0.0, t_done_s=None)
                       for o, r in zip(outcomes, window_requests)]
    n_completed = sum(1 for o in final_outcomes if o.t_done_s is not None)
    return WindowRequestReplayResult(
        slo_violation_rate=real_slo_violation_rate(final_outcomes),
        n_completed=n_completed, n_total=len(final_outcomes), outcomes=final_outcomes,
    )


@dataclass
class BisectionCandidateRecord:
    iteration: int
    factor: float
    slo_violation_rate: float
    n_completed: int
    n_total: int
    reset_barrier_passed: bool


@dataclass
class WindowCalibrationResult:
    source: str
    window_id: str
    reference_policy: str
    real_lambda_ref: float
    derived_high_pressure: float
    convergence_status: str
    candidate_history: List[BisectionCandidateRecord]


def bisect_lambda_ref_real(
    window_requests: Sequence[Dict[str, Any]],
    *,
    tokenizer: Any,
    model: str,
    call_fn: Callable[[str, int, bool], Dict[str, Any]],
    fetch_metrics: Callable[[], str],
    source: str,
    window_id: str,
    reset_barrier_timeout_s: float = 30.0,
) -> WindowCalibrationResult:
    """Mirrors `ranking_portability.calibration.compute_lambda_ref`'s exact
    bisection shape (log10 bounds [-2, 4], 30 iterations, 0.5% threshold,
    same lo/hi early-exit and tie behavior) against a live vLLM server
    instead of the simulator, replaying this window's 200 requests once per
    candidate factor. A candidate whose replay completes zero requests is
    fail-closed to `slo_violation_rate = 1.0` (see `rq6_slo_metrics.
    real_slo_violation_rate`), mirroring `_slo_violation_rate_at`'s
    `num_completed == 0 -> 1.0` convention.
    """
    history: List[BisectionCandidateRecord] = []

    def _measure(iteration: int, factor: float) -> float:
        reset = check_reset_barrier(fetch_metrics, timeout_s=reset_barrier_timeout_s)
        result = replay_window_once(
            window_requests, candidate_scale=factor, tokenizer=tokenizer, model=model, call_fn=call_fn,
        )
        history.append(BisectionCandidateRecord(
            iteration=iteration, factor=factor, slo_violation_rate=result.slo_violation_rate,
            n_completed=result.n_completed, n_total=result.n_total, reset_barrier_passed=reset.passed,
        ))
        return result.slo_violation_rate

    lo, hi = BISECTION_LOG_LO, BISECTION_LOG_HI
    f_lo = _measure(0, 10 ** lo)
    f_hi = _measure(1, 10 ** hi)

    if f_lo >= SLO_VIOLATION_THRESHOLD:
        real_lambda_ref = float(10 ** lo)
        status = "LOWER_BOUND_ALREADY_VIOLATING"
    elif f_hi < SLO_VIOLATION_THRESHOLD:
        real_lambda_ref = float(10 ** hi)
        status = "UPPER_BOUND_NEVER_VIOLATING"
    else:
        for i in range(BISECTION_ITERATIONS):
            mid = (lo + hi) / 2.0
            f_mid = _measure(2 + i, 10 ** mid)
            if f_mid < SLO_VIOLATION_THRESHOLD:
                lo = mid
            else:
                hi = mid
        real_lambda_ref = float(10 ** ((lo + hi) / 2.0))
        status = "CONVERGED"

    return WindowCalibrationResult(
        source=source, window_id=window_id, reference_policy=REFERENCE_POLICY,
        real_lambda_ref=real_lambda_ref, derived_high_pressure=1.5 * real_lambda_ref,
        convergence_status=status, candidate_history=history,
    )
