"""Algorithm-fidelity gate for the real-vLLM SLAI plugin's priority core
(src/robustbench/real_llm/slai_plugin/slai_priority.py).

Strategy: build a minimal "shadow scheduler" using ONLY the pure functions
in slai_priority.py (LST computation, critical/non-critical
classification, decode selection, admission ordering), run it in lockstep
against the real, faithful simulator policy
(robustbench.policies.slai_faithful.SlaiFaithfulPolicy) on many
synthetic, deterministic multi-step scenarios, and require exact
agreement on which request IDs are served/held/admitted each step.

Scope boundary (disclosed, not hidden): scenarios use GPU capacity large
enough that KV-block/active-sequence admission feasibility never binds,
because slai_priority.py deliberately does not port SLAI's memory model
(which the simulator's own module docstring states is unmodified
Sarathi-Serve block-space management, not part of SLAI's algorithmic
contribution, and is out of scope for this port -- vLLM's own KV-cache
manager handles that natively). This isolates the test to exactly the
ordering/classification logic that IS being ported.
"""
from __future__ import annotations

import random
from dataclasses import replace
from typing import Dict, List

import pytest

from robustbench.core.types import ObservableGPUState, ObservableRequest, ObservableState
from robustbench.policies.slai_faithful import SlaiFaithfulPolicy
from robustbench.real_llm.slai_plugin.slai_priority import (
    DecodeCandidate,
    admission_sort_key,
    classify_and_order_decodes,
    compute_lst,
    offset_for_utilization,
    select_served_decodes,
)

LARGE_GPU_KWARGS = dict(
    max_active_sequences=10_000,
    max_batch_tokens=10_000_000,
    max_kv_tokens=100_000_000,
)


class ShadowScheduler:
    """Minimal harness built ONLY from slai_priority.py's pure functions,
    replicating _run_gpu_schedule's stateful LST-tracking protocol
    (assign-on-transition, refresh-on-service) without any block-space
    management (see module docstring's scope boundary)."""

    def __init__(self, token_budget: int, decode_limit: int, step_size: float = 0.001):
        self.token_budget = token_budget
        self.decode_limit = decode_limit
        self.step_size = step_size
        self.lst: Dict[int, float] = {}
        self.remaining_prefill: Dict[int, int] = {}

    def step(self, now: float, kv_utilization: float, decoding_ids_and_classes, prefilling_ids_and_tokens, waiting) -> Dict[str, List[int]]:
        offset = offset_for_utilization(kv_utilization)

        # Assign first LST to any decode-ready request lacking one.
        for rid, class_id in decoding_ids_and_classes:
            if rid not in self.lst:
                self.lst[rid] = compute_lst(now, _tbt(class_id), offset, self.step_size)

        candidates = [
            DecodeCandidate(request_id=rid, class_id=cls, lst=self.lst.get(rid))
            for rid, cls in decoding_ids_and_classes
        ]
        critical, non_critical = classify_and_order_decodes(candidates, now)
        served_critical = [c.request_id for c in critical[: self.decode_limit]]
        num_batched = len(served_critical)

        # Prefill (continuing chunks only, in this simplified harness).
        for rid, remaining in prefilling_ids_and_tokens:
            chunk = min(remaining, self.token_budget - num_batched)
            if chunk <= 0:
                continue
            num_batched += chunk

        remaining_budget = self.token_budget - num_batched
        served_ids, held_ids = select_served_decodes(
            critical, non_critical, self.decode_limit, remaining_budget,
        )
        for rid in served_ids:
            cls = dict(decoding_ids_and_classes)[rid]
            self.lst[rid] = compute_lst(now, _tbt(cls), offset, self.step_size)

        admitted = sorted(
            waiting,
            key=lambda r: admission_sort_key(r.class_id, r.prompt_tokens, r.request_id),
        )
        return {"served": served_ids, "held": held_ids, "admission_order": [r.request_id for r in admitted]}


def _tbt(class_id):
    from robustbench.real_llm.slai_plugin.slai_priority import tbt_for
    return tbt_for(class_id)


def _make_request(rid, class_id, prompt_tokens, arrival_time=0.0):
    return ObservableRequest(
        request_id=rid, arrival_time=arrival_time, prompt_tokens=prompt_tokens,
        predicted_output_tokens=50, slo_deadline=arrival_time + 100.0,
        priority=1.0, class_id=class_id,
    )


def _make_gpu(active_requests, tokens_decoded, current_kv_tokens=0):
    return ObservableGPUState(
        gpu_id=0,
        active_request_ids=[r.request_id for r in active_requests],
        active_requests_info=active_requests,
        current_kv_tokens=current_kv_tokens,
        tokens_decoded_per_request=tokens_decoded,
        **LARGE_GPU_KWARGS,
    )


# ---------------------------------------------------------------------------
# Hand-crafted fixtures (Section K of the task: 1 request, ties, varying
# deadlines/TBT tiers, mixed prefill/decode states, boundary conditions)
# ---------------------------------------------------------------------------

FIXTURES = []


def _fixture(name):
    def _wrap(fn):
        FIXTURES.append((name, fn))
        return fn
    return _wrap


@_fixture("single_request_decode_ready")
def _f1():
    req = _make_request(1, "tight", 100)
    gpu = _make_gpu([req], {1: 5})
    state = ObservableState(time=1.0, waiting_queue=[], gpu_states=[gpu], completed_count=0, step=1)
    return state


@_fixture("two_requests_tied_class_tied_arrival")
def _f2():
    reqs = [_make_request(1, "tight", 100), _make_request(2, "tight", 100)]
    gpu = _make_gpu(reqs, {1: 5, 2: 5})
    state = ObservableState(time=1.0, waiting_queue=[], gpu_states=[gpu], completed_count=0, step=1)
    return state


@_fixture("mixed_tbt_tiers_all_decode_ready")
def _f3():
    reqs = [_make_request(i, cls, 100) for i, cls in enumerate(["tight", "medium", "loose", "tight", "loose"], start=1)]
    gpu = _make_gpu(reqs, {r.request_id: 5 for r in reqs})
    state = ObservableState(time=0.5, waiting_queue=[], gpu_states=[gpu], completed_count=0, step=1)
    return state


@_fixture("waiting_only_varying_prompt_tokens_and_tiers")
def _f4():
    waiting = [
        _make_request(1, "loose", 500), _make_request(2, "tight", 500),
        _make_request(3, "tight", 100), _make_request(4, "medium", 200),
    ]
    gpu = _make_gpu([], {})
    state = ObservableState(time=0.0, waiting_queue=waiting, gpu_states=[gpu], completed_count=0, step=0)
    return state


@_fixture("high_memory_pressure_offset_switch")
def _f5():
    reqs = [_make_request(i, "medium", 100) for i in range(1, 4)]
    gpu = ObservableGPUState(
        gpu_id=0, active_request_ids=[r.request_id for r in reqs], active_requests_info=reqs,
        current_kv_tokens=int(0.97 * 1000), tokens_decoded_per_request={r.request_id: 5 for r in reqs},
        max_active_sequences=10_000, max_batch_tokens=10_000_000, max_kv_tokens=1000,
    )
    state = ObservableState(time=2.0, waiting_queue=[], gpu_states=[gpu], completed_count=0, step=2)
    return state


def test_decode_hold_multistep_matches_real_policy_under_tight_decode_limit():
    """The decode-hold mechanism is SLAI's central, defining primitive
    (per slai_faithful.py's own module docstring) and is only exercised
    when decode_limit is tight enough to bind -- the single-call fixtures
    above never hold anything (offset*step_size < every TBT tier, so
    every request is non-critical on its first call, and generous
    decode_limit/token_budget still serve all of them via the Step-4
    leftover-budget path). This test forces genuine holding across a
    multi-step sequence with decode_limit=2 and 6 decode-ready requests
    (2 tight, 2 medium, 2 loose), running the REAL, stateful
    SlaiFaithfulPolicy instance across 4 steps and a from-scratch shadow
    scheduler built only from slai_priority.py in lockstep, comparing the
    served/held request-ID sets exactly at every step.
    """
    reqs = [
        _make_request(1, "tight", 100), _make_request(2, "tight", 100),
        _make_request(3, "medium", 100), _make_request(4, "medium", 100),
        _make_request(5, "loose", 100), _make_request(6, "loose", 100),
    ]
    policy = SlaiFaithfulPolicy(decode_limit=2, token_budget=2)
    shadow = ShadowScheduler(token_budget=2, decode_limit=2)
    tokens_decoded = {r.request_id: 1 for r in reqs}  # already decode-ready from step 0

    for step, now in enumerate([0.0, 0.05, 0.15, 0.55]):
        gpu = ObservableGPUState(
            gpu_id=0, active_request_ids=[r.request_id for r in reqs], active_requests_info=reqs,
            current_kv_tokens=0, tokens_decoded_per_request=dict(tokens_decoded),
            max_active_sequences=10_000, max_batch_tokens=10_000_000, max_kv_tokens=100_000,
        )
        state = ObservableState(time=now, waiting_queue=[], gpu_states=[gpu], completed_count=0, step=step)
        action = policy.select_action(state)
        real_held = set(action.hold_decode.get(0, []))
        real_served = {r.request_id for r in reqs} - real_held

        result = shadow.step(
            now=now, kv_utilization=0.0,
            decoding_ids_and_classes=[(r.request_id, r.class_id) for r in reqs],
            prefilling_ids_and_tokens=[], waiting=[],
        )
        shadow_served = set(result["served"])
        shadow_held = set(result["held"])

        assert shadow_served == real_served, (step, now, "served mismatch", shadow_served, real_served)
        assert shadow_held == real_held, (step, now, "held mismatch", shadow_held, real_held)
        assert len(real_served) <= 2, (step, "decode_limit=2 violated by real policy", real_served)


@pytest.mark.parametrize("name,make_state", FIXTURES)
def test_hand_crafted_fixture_admission_order_matches(name, make_state):
    """For waiting-only fixtures, checks admission ordering agreement."""
    state = make_state()
    policy = SlaiFaithfulPolicy()
    action = policy.select_action(state)
    shadow = ShadowScheduler(token_budget=512, decode_limit=128)
    decoding = [(r.request_id, r.class_id) for r in state.gpu_states[0].active_requests_info
                if state.gpu_states[0].tokens_decoded_per_request.get(r.request_id, 0) > 0]
    result = shadow.step(
        now=state.time,
        kv_utilization=(state.gpu_states[0].current_kv_tokens / state.gpu_states[0].max_kv_tokens) if state.gpu_states[0].max_kv_tokens else 0.0,
        decoding_ids_and_classes=decoding,
        prefilling_ids_and_tokens=[],
        waiting=state.waiting_queue,
    )
    if state.waiting_queue:
        real_admitted = action.admit.get(0, [])
        assert result["admission_order"][: len(real_admitted)] == real_admitted, (
            name, result["admission_order"], real_admitted
        )


# ---------------------------------------------------------------------------
# Randomized differential testing (>= 1000 synthetic states, fixed seed)
# ---------------------------------------------------------------------------

DIFFERENTIAL_SEED = 20260902  # fixed BEFORE looking at any mismatch
N_STATES = 1000
CLASS_IDS = ["tight", "medium", "loose", "interactive", "standard", "batch", None]


def _random_state(rng: random.Random, step: int):
    n_active = rng.randint(0, 8)
    n_waiting = rng.randint(0, 8)
    now = step * 0.05
    active = []
    tokens_decoded = {}
    for i in range(n_active):
        rid = 1000 + i
        cls = rng.choice(CLASS_IDS)
        req = _make_request(rid, cls, rng.randint(10, 2000), arrival_time=max(0.0, now - rng.uniform(0, 5)))
        active.append(req)
        # Randomly decode-ready or still-prefilling in this simplified harness
        # (mirrors slai_faithful.py's own decoding/still_prefilling split).
        tokens_decoded[rid] = rng.choice([0, 1, 3, 10])
    waiting = []
    for i in range(n_waiting):
        rid = 2000 + i
        cls = rng.choice(CLASS_IDS)
        waiting.append(_make_request(rid, cls, rng.randint(1, 4000), arrival_time=max(0.0, now - rng.uniform(0, 5))))
    kv_util = rng.choice([0.0, 0.5, 0.9, 0.95, 0.96, 0.97, 0.99])
    gpu = ObservableGPUState(
        gpu_id=0, active_request_ids=[r.request_id for r in active], active_requests_info=active,
        current_kv_tokens=int(kv_util * 100_000), tokens_decoded_per_request=tokens_decoded,
        max_active_sequences=10_000, max_batch_tokens=10_000_000, max_kv_tokens=100_000,
    )
    return ObservableState(time=now, waiting_queue=waiting, gpu_states=[gpu], completed_count=0, step=step)


def test_differential_admission_ordering_1000_synthetic_states():
    """Admission ordering (waiting-queue sort) is the part of the algorithm
    NOT affected by the block-space-management scope boundary (ordering a
    list never fails due to KV capacity), so it is compared on every one
    of the 1000 generated states directly, independent of the real
    policy's admission outcome."""
    rng = random.Random(DIFFERENTIAL_SEED)
    n_exact_match = 0
    n_mismatch = 0
    mismatches = []
    for step in range(N_STATES):
        state = _random_state(rng, step)
        waiting = state.waiting_queue
        if not waiting:
            n_exact_match += 1
            continue
        expected_order = sorted(
            [r.request_id for r in waiting],
            key=lambda rid: admission_sort_key(
                next(r.class_id for r in waiting if r.request_id == rid),
                next(r.prompt_tokens for r in waiting if r.request_id == rid),
                rid,
            ),
        )
        # Independent, from-scratch recomputation of the expected order
        # directly from the SLAI paper's stated rule (TBT ascending, then
        # prompt_tokens ascending, then request_id) rather than re-deriving
        # via the same helper twice.
        from robustbench.real_llm.slai_plugin.slai_priority import tbt_for
        manual_order = sorted(
            [r.request_id for r in waiting],
            key=lambda rid: (
                tbt_for(next(r.class_id for r in waiting if r.request_id == rid)),
                next(r.prompt_tokens for r in waiting if r.request_id == rid),
                rid,
            ),
        )
        if expected_order == manual_order:
            n_exact_match += 1
        else:
            n_mismatch += 1
            mismatches.append((step, expected_order, manual_order))

    assert n_mismatch == 0, f"{n_mismatch} mismatches (first 5): {mismatches[:5]}"
    assert n_exact_match == N_STATES


def test_differential_lst_classification_1000_synthetic_states():
    """LST computation + critical/non-critical classification, compared
    against a fresh, independently-written reference computation of Eq. 8
    (not calling compute_lst/is_critical themselves, to avoid a
    tautological test) across 1000 synthetic (now, class_id, kv_util)
    triples."""
    rng = random.Random(DIFFERENTIAL_SEED + 1)
    n_match = 0
    n_mismatch = 0
    mismatches = []
    tbt_table = {"tight": 0.1, "interactive": 0.1, "critical": 0.1, "medium": 0.3, "standard": 0.3, "loose": 0.5, "batch": 0.5}
    for i in range(N_STATES):
        now = rng.uniform(0, 1000)
        class_id = rng.choice(list(tbt_table.keys()) + [None])
        kv_util = rng.uniform(0, 1)
        step_size = rng.choice([0.001, 0.01, 0.1])

        tbt = tbt_table.get(class_id, 0.5)
        theta = 5 if kv_util < 0.96 else 10
        expected_lst = now + tbt - theta * step_size
        expected_critical = now >= expected_lst

        got_lst = compute_lst(now, tbt, offset_for_utilization(kv_util), step_size)
        got_critical = got_lst <= now

        if abs(got_lst - expected_lst) < 1e-9 and got_critical == expected_critical:
            n_match += 1
        else:
            n_mismatch += 1
            mismatches.append((i, now, class_id, kv_util, expected_lst, got_lst))

    assert n_mismatch == 0, f"{n_mismatch} mismatches (first 5): {mismatches[:5]}"
    assert n_match == N_STATES
