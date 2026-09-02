"""Mechanism-activation telemetry for the ranking-portability pilot
(`docs/RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md` section 8,
`docs/RANKING_PORTABILITY_TELEMETRY_IMPLEMENTATION.md`).

Purely observational, computed post-hoc from state the simulator already
records for its own execution/metrics purposes (`Simulator._waiting_queue_history`,
`GPUState.step_active_counts`/`step_kv_used`/`step_contention_diagnostics`)
plus two small new counters (`Simulator._admission_control_activations`,
`Simulator._preemption_reorder_events`) that are written once, from
already-computed values, and never read back by `compute_metrics()` or any
policy -- see `docs/RANKING_PORTABILITY_TELEMETRY_IMPLEMENTATION.md`'s
non-interference argument. Never consulted by any policy or by
`compute_metrics()`; this module only reads a `Simulator` after `run()`
returns, exactly like the existing `contention_diagnostics_summary()`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class TelemetrySummary:
    schema_version: str
    queue_depth_mean: float
    queue_depth_max: int
    batch_saturation_mean: float
    batch_saturation_max: float
    prefill_decode_contention_fraction: float
    kv_occupancy_mean: float
    kv_occupancy_max: float
    admission_control_activations: int
    preemption_or_reorder_events: int
    token_budget_saturation_fraction: float
    n_steps: int

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "queue_depth_mean": self.queue_depth_mean,
            "queue_depth_max": self.queue_depth_max,
            "batch_saturation_mean": self.batch_saturation_mean,
            "batch_saturation_max": self.batch_saturation_max,
            "prefill_decode_contention_fraction": self.prefill_decode_contention_fraction,
            "kv_occupancy_mean": self.kv_occupancy_mean,
            "kv_occupancy_max": self.kv_occupancy_max,
            "admission_control_activations": self.admission_control_activations,
            "preemption_or_reorder_events": self.preemption_or_reorder_events,
            "token_budget_saturation_fraction": self.token_budget_saturation_fraction,
            "n_steps": self.n_steps,
        }


TELEMETRY_SCHEMA_VERSION = "ranking_portability_telemetry_v1"


def compute_telemetry_summary(simulator) -> TelemetrySummary:
    """`simulator` is a `Simulator` after `run()`/`continue_run()` has
    completed. Reads only already-recorded, per-step histories -- computes
    no new simulator state and never re-invokes a policy."""
    n_steps = len(simulator._waiting_queue_history)

    queue_depth_mean = (
        sum(simulator._waiting_queue_history) / n_steps if n_steps else 0.0
    )
    queue_depth_max = max(simulator._waiting_queue_history, default=0)

    gpus = simulator._gpus
    batch_ratios: list[float] = []
    kv_ratios: list[float] = []
    for step_idx in range(n_steps):
        step_batch_vals = []
        step_kv_vals = []
        for g in gpus:
            max_active = g.config.max_active_sequences
            max_kv = g.config.max_kv_tokens
            active = g.step_active_counts[step_idx] if step_idx < len(g.step_active_counts) else 0
            kv_used = g.step_kv_used[step_idx] if step_idx < len(g.step_kv_used) else 0
            step_batch_vals.append(active / max_active if max_active > 0 else 0.0)
            step_kv_vals.append(kv_used / max_kv if max_kv > 0 else 0.0)
        if step_batch_vals:
            batch_ratios.append(sum(step_batch_vals) / len(step_batch_vals))
        if step_kv_vals:
            kv_ratios.append(sum(step_kv_vals) / len(step_kv_vals))

    batch_saturation_mean = sum(batch_ratios) / len(batch_ratios) if batch_ratios else 0.0
    batch_saturation_max = max(batch_ratios, default=0.0)
    kv_occupancy_mean = sum(kv_ratios) / len(kv_ratios) if kv_ratios else 0.0
    kv_occupancy_max = max(kv_ratios, default=0.0)

    # Pooled across GPUs, same convention as Simulator.contention_diagnostics_summary().
    combined_contention = [d for g in gpus for d in g.step_contention_diagnostics]
    if combined_contention:
        n_c = len(combined_contention)
        prefill_decode_contention_fraction = sum(
            1 for d in combined_contention if d.num_decoding > 0 and d.num_prefilling > 0
        ) / n_c
        token_budget_saturation_fraction = sum(
            1 for d in combined_contention if d.budget_saturated
        ) / n_c
    else:
        # Mechanism absent (Phase-1 instant-prefill mode has no separate
        # prefill phase / no token-budget model): defined 0.0, not NaN.
        prefill_decode_contention_fraction = 0.0
        token_budget_saturation_fraction = 0.0

    return TelemetrySummary(
        schema_version=TELEMETRY_SCHEMA_VERSION,
        queue_depth_mean=queue_depth_mean,
        queue_depth_max=queue_depth_max,
        batch_saturation_mean=batch_saturation_mean,
        batch_saturation_max=batch_saturation_max,
        prefill_decode_contention_fraction=prefill_decode_contention_fraction,
        kv_occupancy_mean=kv_occupancy_mean,
        kv_occupancy_max=kv_occupancy_max,
        admission_control_activations=simulator._admission_control_activations,
        preemption_or_reorder_events=simulator._preemption_reorder_events,
        token_budget_saturation_fraction=token_budget_saturation_fraction,
        n_steps=n_steps,
    )


def validate_telemetry(t: TelemetrySummary) -> list[str]:
    """Returns a list of validation problems (empty = valid). Never raises.
    Distinguishes genuine instrumentation failure (n_steps <= 0, a
    non-finite value, an out-of-range fraction) from a mechanism simply
    not activating (which is a valid 0, already handled by
    `compute_telemetry_summary` -- this function does not special-case
    zeros)."""
    problems: list[str] = []

    def _check_fraction(name: str, v: float) -> None:
        if not math.isfinite(v):
            problems.append(f"{name} is not finite: {v}")
        elif not (0.0 <= v <= 1.0 + 1e-9):
            problems.append(f"{name} out of [0,1]: {v}")

    def _check_kv_occupancy(name: str, v: float) -> None:
        """`kv_occupancy_{mean,max}` is `kv_used / max_kv_tokens` per step
        (`compute_telemetry_summary` above). Unlike `batch_saturation`
        (bounded at 1.0 by every panel policy's shared `max_active_sequences`
        admission check, `policies/feasibility.py`), `max_kv_tokens` is only
        enforced as a hard admission constraint by KV-aware policies
        (`kv_constrained_online`, the `*_faithful` block-manager policies,
        `vllm_style_token_budget`) -- discovered via the Phase-12A
        engineering smoke (docs/RANKING_PORTABILITY_PHASE12_SMOKE_FREEZE.md):
        several PRIMARY-panel policies (fifo, edf, least_laxity_first,
        estimated_service_time_first, weighted_fair_share, admission_control,
        slai_faithful) admit purely on concurrency count, so aggregate KV
        demand from their active requests can genuinely exceed the
        configured `max_kv_tokens` by a small amount on some (window,
        region) combinations (observed: up to ~1.3% over, never more). This
        is real simulator state -- a meaningful "demand exceeded nominal KV
        capacity" signal for non-KV-aware policies -- not an instrumentation
        failure, so it must not be rejected as invalid the way the other,
        genuinely admission-bounded fractions are. A generous upper bound
        (2.0x) still catches an actual instrumentation bug (e.g. a unit
        mismatch or an unbounded runaway) without rejecting the small,
        real, policy-dependent overshoot this smoke found."""
        if not math.isfinite(v):
            problems.append(f"{name} is not finite: {v}")
        elif not (0.0 <= v <= 2.0):
            problems.append(f"{name} out of [0,2.0] (genuine-overshoot-tolerant bound): {v}")

    def _check_nonneg_finite(name: str, v: float) -> None:
        if not math.isfinite(v) or v < 0:
            problems.append(f"{name} invalid (must be finite, >= 0): {v}")

    def _check_nonneg_int(name: str, v) -> None:
        if not isinstance(v, int) or isinstance(v, bool) or v < 0:
            problems.append(f"{name} invalid (must be a non-negative int): {v}")

    if t.n_steps <= 0:
        problems.append(
            "n_steps <= 0 -- telemetry unavailable (instrumentation failure or "
            "a degenerate zero-step run), not genuine zero mechanism activity"
        )

    _check_nonneg_finite("queue_depth_mean", t.queue_depth_mean)
    _check_nonneg_int("queue_depth_max", t.queue_depth_max)
    _check_fraction("batch_saturation_mean", t.batch_saturation_mean)
    _check_fraction("batch_saturation_max", t.batch_saturation_max)
    _check_fraction("prefill_decode_contention_fraction", t.prefill_decode_contention_fraction)
    _check_kv_occupancy("kv_occupancy_mean", t.kv_occupancy_mean)
    _check_kv_occupancy("kv_occupancy_max", t.kv_occupancy_max)
    _check_fraction("token_budget_saturation_fraction", t.token_budget_saturation_fraction)
    _check_nonneg_int("admission_control_activations", t.admission_control_activations)
    _check_nonneg_int("preemption_or_reorder_events", t.preemption_or_reorder_events)

    if t.batch_saturation_max < t.batch_saturation_mean - 1e-9:
        problems.append("batch_saturation_max < batch_saturation_mean")
    if t.kv_occupancy_max < t.kv_occupancy_mean - 1e-9:
        problems.append("kv_occupancy_max < kv_occupancy_mean")
    if t.queue_depth_max < t.queue_depth_mean - 1e-9:
        problems.append("queue_depth_max < queue_depth_mean")

    return problems
