"""Deterministic unit tests for the ranking-portability mechanism-telemetry
instrumentation (docs/RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md section 8,
docs/RANKING_PORTABILITY_TELEMETRY_IMPLEMENTATION.md). No Stage-0/Pilot-V2
real windows are used -- every scenario is a small, hand-constructed toy
trace, run through the actual `Simulator`, never a fabricated/stubbed
telemetry value.

Some scenarios (contention, token-budget saturation, KV occupancy, queue
buildup) assert a directional/bound property (mechanism activated, and
within its valid range) rather than a single hand-derived magic number --
the exact per-step interaction in Phase-1.5 mode is intricate enough that a
bound check on a deliberately-constructed scenario is the more robust,
honestly-labeled test. Scenarios with simple, fully-traceable mechanics
(idle, full-batch saturation, admission control, preemption, mechanism
absence) assert exact values.
"""
from __future__ import annotations

import math

from robustbench.core.action import Action
from robustbench.core.types import GPUConfig, Request
from robustbench.policies.base import BasePolicy
from robustbench.policies.fifo import FIFOPolicy
from robustbench.policies.admission_control import AdmissionControlPolicy
from robustbench.simulator.service_model import ServiceModel
from robustbench.simulator.simulator import Simulator, SimulatorConfig
from robustbench.simulator.telemetry import TelemetrySummary, validate_telemetry


def _req(rid, arrival=0.0, prompt=10, predicted_out=1, actual_out=1,
         deadline=1000.0, priority=1.0):
    return Request(
        request_id=rid, arrival_time=arrival, prompt_tokens=prompt,
        predicted_output_tokens=predicted_out, actual_output_tokens=actual_out,
        slo_deadline=deadline, priority=priority, class_id="t",
    )


def _gpu(max_active=8, max_batch=4096, max_kv=131072):
    return GPUConfig(gpu_id=0, max_active_sequences=max_active,
                      max_batch_tokens=max_batch, max_kv_tokens=max_kv)


def _run(requests, policy, gpu_configs, service_model=None, drain_steps=50):
    sim = Simulator(SimulatorConfig(
        gpu_configs=gpu_configs, service_model=service_model or ServiceModel(),
        drain_steps=drain_steps,
    ))
    sim.load_trace(requests)
    policy.reset()
    sim.run(policy, workload_tag="telemetry_test", seed=0)
    return sim.telemetry_summary()


# --- 1. EMPTY/IDLE -----------------------------------------------------

def test_empty_idle_all_zero():
    t = _run([], FIFOPolicy(), [_gpu()])
    assert t.queue_depth_mean == 0.0
    assert t.queue_depth_max == 0
    assert t.batch_saturation_mean == 0.0
    assert t.batch_saturation_max == 0.0
    assert t.prefill_decode_contention_fraction == 0.0
    assert t.kv_occupancy_mean == 0.0
    assert t.kv_occupancy_max == 0.0
    assert t.admission_control_activations == 0
    assert t.preemption_or_reorder_events == 0
    assert t.token_budget_saturation_fraction == 0.0
    assert validate_telemetry(t) == []


# --- 2. QUEUE BUILDUP ----------------------------------------------------

def test_queue_buildup_tracks_capacity_constrained_backlog():
    """3 simultaneous arrivals, capacity for only 1 at a time -- queue depth
    must peak at 3 (the full burst) and never exceed it."""
    reqs = [_req(i, arrival=0.0, actual_out=2, predicted_out=2) for i in range(3)]
    t = _run(reqs, FIFOPolicy(), [_gpu(max_active=1)])
    assert t.queue_depth_max == 3
    assert t.queue_depth_mean > 0.0
    assert validate_telemetry(t) == []


# --- 3. FULL BATCH (exact saturation = 1.0) -------------------------------

def test_full_batch_saturation_reaches_exactly_one():
    reqs = [_req(0, actual_out=3, predicted_out=3), _req(1, actual_out=3, predicted_out=3)]
    t = _run(reqs, FIFOPolicy(), [_gpu(max_active=2)])
    assert t.batch_saturation_max == 1.0
    assert 0.0 < t.batch_saturation_mean <= 1.0
    assert validate_telemetry(t) == []


# --- 4. PREFILL + DECODE CONTENTION (bound: constructed to co-occur) -----

def test_prefill_decode_contention_activates_when_constructed_to_overlap():
    """Request A (tiny prompt, long decode) and B (huge prompt, needs many
    prefill chunks) admitted together: once A starts decoding, B is still
    prefilling for several more steps -- a real, non-trivial contention
    window, not a default-zero."""
    a = _req(0, prompt=1, actual_out=5, predicted_out=5)
    b = _req(1, prompt=100, actual_out=1, predicted_out=1)
    sm = ServiceModel(
        enable_prefill_modeling=True, enable_decode_prefill_contention=True,
        decode_first=False, step_token_budget=1000, max_prefill_chunk_tokens=10,
        prefill_cost_per_token=1.0,
    )
    t = _run([a, b], FIFOPolicy(), [_gpu(max_active=2)], service_model=sm)
    assert 0.0 < t.prefill_decode_contention_fraction <= 1.0
    assert validate_telemetry(t) == []


def test_prefill_decode_contention_absent_in_phase1_mode():
    """Mechanism absent (no separate prefill phase modeled): must be
    exactly 0.0, not NaN or undefined."""
    t = _run([_req(0, actual_out=2, predicted_out=2)], FIFOPolicy(), [_gpu()])
    assert t.prefill_decode_contention_fraction == 0.0


# --- 5. KV PRESSURE (bound: deliberately large prompt vs. small capacity) -

def test_kv_occupancy_tracks_deliberate_pressure():
    t = _run(
        [_req(0, prompt=80, actual_out=3, predicted_out=3)],
        FIFOPolicy(), [_gpu(max_active=1, max_kv=100)],
    )
    assert t.kv_occupancy_max >= 0.8
    assert 0.0 < t.kv_occupancy_mean <= 1.0
    assert validate_telemetry(t) == []


# --- 6. ADMISSION CONTROL (exact known activation count) -----------------

def test_admission_control_exact_activation_count():
    """A request whose deadline is already unmeetable is filtered by
    AdmissionControlPolicy's laxity threshold every step it waits, despite
    spare capacity -- drain_steps bounds the run to exactly 5 telemetry
    steps (steps_since_last_arrival reaches drain_steps=5 with a single
    t=0 arrival and nothing ever admitted)."""
    req = _req(0, arrival=0.0, prompt=1000, predicted_out=1000, deadline=0.0001)
    policy = AdmissionControlPolicy(laxity_threshold=0.0)
    t = _run([req], policy, [_gpu(max_active=5)], drain_steps=5)
    assert t.n_steps == 5
    assert t.admission_control_activations == 5
    assert validate_telemetry(t) == []


def test_admission_control_zero_when_no_spare_capacity():
    """If capacity is already full at the moment a request is waiting,
    declining to admit it is not "activation" -- there was nothing spare
    to decline. `active_req` (arrival=0) occupies the sole slot for its
    whole 10-step decode; `waiting_req` arrives at step 2 (step_size=1.0s),
    once that slot is already taken, and drain_steps=3 (counted from the
    LAST arrival, step 2) ends the run at step 5 -- well before
    `active_req` frees the slot at step 10 -- so capacity is observably
    full for every step `waiting_req` is ever in the queue."""
    sm = ServiceModel(step_size=1.0)
    active_req = _req(0, arrival=0.0, actual_out=10, predicted_out=10)
    waiting_req = _req(1, arrival=2.0, prompt=1000, predicted_out=1000, deadline=0.0001)
    policy = AdmissionControlPolicy(laxity_threshold=0.0, step_size=1.0)
    t = _run([active_req, waiting_req], policy, [_gpu(max_active=1)],
             service_model=sm, drain_steps=3)
    assert t.admission_control_activations == 0


# --- 7. PREEMPTION (exact known count via a scripted test-only policy) ---

class _ScriptedPreemptPolicy(BasePolicy):
    """Test-only: admits everything at step 0, preempts everything active
    at step 1 (exactly once), then admits again from step 2 onward. Never
    registered in the real policy registry -- exists only to give this
    unit test an exact, known preemption count."""

    name = "scripted_preempt_test_only"

    def __init__(self):
        self._step = 0

    def reset(self) -> None:
        self._step = 0

    def select_action(self, state) -> Action:
        admit: dict = {g.gpu_id: [] for g in state.gpu_states}
        preempt: dict = {}
        if state.gpu_states:
            gpu = state.gpu_states[0]
            if self._step == 0:
                admit[gpu.gpu_id] = [r.request_id for r in state.waiting_queue]
            elif self._step == 1:
                if gpu.active_request_ids:
                    preempt[gpu.gpu_id] = list(gpu.active_request_ids)
            else:
                admit[gpu.gpu_id] = [r.request_id for r in state.waiting_queue]
        self._step += 1
        return Action(admit=admit, preempt=preempt)


def test_preemption_exact_single_event():
    req = _req(0, actual_out=5, predicted_out=5)
    t = _run([req], _ScriptedPreemptPolicy(), [_gpu(max_active=1)])
    assert t.preemption_or_reorder_events == 1
    assert validate_telemetry(t) == []


def test_preemption_zero_for_non_preempting_policy():
    reqs = [_req(i, actual_out=2, predicted_out=2) for i in range(3)]
    t = _run(reqs, FIFOPolicy(), [_gpu(max_active=2)])
    assert t.preemption_or_reorder_events == 0


# --- 8. TOKEN-BUDGET SATURATION (bound: deliberately starved budget) -----

def test_token_budget_saturation_activates_under_tight_budget():
    reqs = [_req(0, prompt=1, actual_out=4, predicted_out=4),
            _req(1, prompt=1, actual_out=4, predicted_out=4)]
    sm = ServiceModel(
        enable_prefill_modeling=True, enable_decode_prefill_contention=True,
        decode_first=False, step_token_budget=1, max_prefill_chunk_tokens=10,
        prefill_cost_per_token=1.0,
    )
    t = _run(reqs, FIFOPolicy(), [_gpu(max_active=2)], service_model=sm)
    assert t.token_budget_saturation_fraction > 0.5
    assert validate_telemetry(t) == []


def test_token_budget_saturation_absent_in_phase1_mode():
    t = _run([_req(0, actual_out=2, predicted_out=2)], FIFOPolicy(), [_gpu()])
    assert t.token_budget_saturation_fraction == 0.0


# --- 9. MECHANISM ABSENT -> 0, never NaN ---------------------------------

def test_all_mechanism_absent_fields_are_zero_not_nan():
    t = _run([_req(0, actual_out=2, predicted_out=2)], FIFOPolicy(), [_gpu()])
    for field_name in ("prefill_decode_contention_fraction",
                        "token_budget_saturation_fraction"):
        v = getattr(t, field_name)
        assert v == 0.0
        assert not math.isnan(v)
    assert t.admission_control_activations == 0
    assert t.preemption_or_reorder_events == 0


# --- 10. INSTRUMENTATION FAILURE -> validator rejects, never silent 0 ----

def test_validator_rejects_zero_steps_as_instrumentation_failure():
    bad = TelemetrySummary(
        schema_version="ranking_portability_telemetry_v1",
        queue_depth_mean=0.0, queue_depth_max=0, batch_saturation_mean=0.0,
        batch_saturation_max=0.0, prefill_decode_contention_fraction=0.0,
        kv_occupancy_mean=0.0, kv_occupancy_max=0.0,
        admission_control_activations=0, preemption_or_reorder_events=0,
        token_budget_saturation_fraction=0.0, n_steps=0,
    )
    problems = validate_telemetry(bad)
    assert any("n_steps" in p for p in problems)


def test_validator_rejects_nan_fraction():
    bad = TelemetrySummary(
        schema_version="ranking_portability_telemetry_v1",
        queue_depth_mean=0.0, queue_depth_max=0, batch_saturation_mean=0.0,
        batch_saturation_max=0.0, prefill_decode_contention_fraction=float("nan"),
        kv_occupancy_mean=0.0, kv_occupancy_max=0.0,
        admission_control_activations=0, preemption_or_reorder_events=0,
        token_budget_saturation_fraction=0.0, n_steps=5,
    )
    problems = validate_telemetry(bad)
    assert any("prefill_decode_contention_fraction" in p for p in problems)


def test_validator_rejects_out_of_range_fraction():
    bad = TelemetrySummary(
        schema_version="ranking_portability_telemetry_v1",
        queue_depth_mean=0.0, queue_depth_max=0, batch_saturation_mean=1.5,
        batch_saturation_max=1.5, prefill_decode_contention_fraction=0.0,
        kv_occupancy_mean=0.0, kv_occupancy_max=0.0,
        admission_control_activations=0, preemption_or_reorder_events=0,
        token_budget_saturation_fraction=0.0, n_steps=5,
    )
    problems = validate_telemetry(bad)
    assert any("batch_saturation_mean" in p for p in problems)


def test_validator_rejects_negative_count():
    bad = TelemetrySummary(
        schema_version="ranking_portability_telemetry_v1",
        queue_depth_mean=0.0, queue_depth_max=0, batch_saturation_mean=0.0,
        batch_saturation_max=0.0, prefill_decode_contention_fraction=0.0,
        kv_occupancy_mean=0.0, kv_occupancy_max=0.0,
        admission_control_activations=-1, preemption_or_reorder_events=0,
        token_budget_saturation_fraction=0.0, n_steps=5,
    )
    problems = validate_telemetry(bad)
    assert any("admission_control_activations" in p for p in problems)


def test_validator_tolerates_small_kv_occupancy_overshoot_above_one():
    """Regression test for the Phase-12A engineering-smoke finding
    (docs/RANKING_PORTABILITY_PHASE12_SMOKE_FREEZE.md): several PRIMARY-
    panel policies (fifo, edf, least_laxity_first, estimated_service_time_first,
    weighted_fair_share, admission_control, slai_faithful) do not enforce
    `max_kv_tokens` as a hard admission constraint, so real aggregate KV
    demand can slightly exceed nominal capacity (observed up to ~1.3% over
    on a real azure_llm_2024 window) -- a genuine simulator state, not an
    instrumentation failure, and must not be rejected."""
    ok = TelemetrySummary(
        schema_version="ranking_portability_telemetry_v1",
        queue_depth_mean=0.0, queue_depth_max=0, batch_saturation_mean=0.5,
        batch_saturation_max=0.5, prefill_decode_contention_fraction=0.0,
        kv_occupancy_mean=0.5, kv_occupancy_max=1.0125503540039062,
        admission_control_activations=0, preemption_or_reorder_events=0,
        token_budget_saturation_fraction=0.0, n_steps=5,
    )
    assert validate_telemetry(ok) == []


def test_validator_accepts_large_kv_occupancy_no_arbitrary_ceiling():
    """Corrected semantics (docs/RANKING_PORTABILITY_PHASE12_TELEMETRY_SEMANTIC_AMENDMENT.md):
    `kv_occupancy` is normalized KV demand relative to nominal capacity for
    policies that never enforce `max_kv_tokens` at admission -- there is no
    simulator/config invariant bounding how far demand can exceed nominal
    capacity, so no arbitrary numeric ceiling (e.g. a "2.0x" cutoff) is
    imposed. A large but finite, non-negative value with max >= mean is
    valid telemetry, not a rejected one."""
    ok = TelemetrySummary(
        schema_version="ranking_portability_telemetry_v1",
        queue_depth_mean=0.0, queue_depth_max=0, batch_saturation_mean=0.0,
        batch_saturation_max=0.0, prefill_decode_contention_fraction=0.0,
        kv_occupancy_mean=1.0, kv_occupancy_max=5.0,
        admission_control_activations=0, preemption_or_reorder_events=0,
        token_budget_saturation_fraction=0.0, n_steps=5,
    )
    assert validate_telemetry(ok) == []


def test_validator_still_rejects_kv_occupancy_max_below_mean():
    """No numeric ceiling is imposed, but internal self-consistency (max >=
    mean) is still a structural invariant of any per-step max/mean pair,
    and is still checked."""
    bad = TelemetrySummary(
        schema_version="ranking_portability_telemetry_v1",
        queue_depth_mean=0.0, queue_depth_max=0, batch_saturation_mean=0.0,
        batch_saturation_max=0.0, prefill_decode_contention_fraction=0.0,
        kv_occupancy_mean=2.0, kv_occupancy_max=1.0,
        admission_control_activations=0, preemption_or_reorder_events=0,
        token_budget_saturation_fraction=0.0, n_steps=5,
    )
    problems = validate_telemetry(bad)
    assert any("kv_occupancy_max < kv_occupancy_mean" in p for p in problems)


def test_validator_still_rejects_negative_or_nonfinite_kv_occupancy():
    bad = TelemetrySummary(
        schema_version="ranking_portability_telemetry_v1",
        queue_depth_mean=0.0, queue_depth_max=0, batch_saturation_mean=0.0,
        batch_saturation_max=0.0, prefill_decode_contention_fraction=0.0,
        kv_occupancy_mean=-0.1, kv_occupancy_max=float("nan"),
        admission_control_activations=0, preemption_or_reorder_events=0,
        token_budget_saturation_fraction=0.0, n_steps=5,
    )
    problems = validate_telemetry(bad)
    assert any("kv_occupancy_mean" in p for p in problems)
    assert any("kv_occupancy_max" in p for p in problems)
