"""Shared test-only helpers for SLAI plugin fidelity tests. Not part of
the shipped plugin (src/robustbench/real_llm/slai_plugin/) -- this is
test scaffolding only."""
from __future__ import annotations

from typing import Dict, List

from robustbench.core.types import ObservableGPUState, ObservableRequest
from robustbench.real_llm.slai_plugin.slai_priority import (
    DecodeCandidate,
    admission_sort_key,
    classify_and_order_decodes,
    compute_lst,
    offset_for_utilization,
    select_served_decodes,
    tbt_for,
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
    management (block-space management is explicitly out of scope -- see
    slai_priority.py's module docstring)."""

    def __init__(self, token_budget: int, decode_limit: int, step_size: float = 0.001):
        self.token_budget = token_budget
        self.decode_limit = decode_limit
        self.step_size = step_size
        self.lst: Dict[int, float] = {}
        self.remaining_prefill: Dict[int, int] = {}

    def step(self, now: float, kv_utilization: float, decoding_ids_and_classes, prefilling_ids_and_tokens, waiting) -> Dict[str, List[int]]:
        offset = offset_for_utilization(kv_utilization)

        for rid, class_id in decoding_ids_and_classes:
            if rid not in self.lst:
                self.lst[rid] = compute_lst(now, tbt_for(class_id), offset, self.step_size)

        candidates = [
            DecodeCandidate(request_id=rid, class_id=cls, lst=self.lst.get(rid))
            for rid, cls in decoding_ids_and_classes
        ]
        critical, non_critical = classify_and_order_decodes(candidates, now)
        served_critical = [c.request_id for c in critical[: self.decode_limit]]
        num_batched = len(served_critical)

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
            self.lst[rid] = compute_lst(now, tbt_for(cls), offset, self.step_size)

        admitted = sorted(
            waiting,
            key=lambda r: admission_sort_key(r.class_id, r.prompt_tokens, r.request_id),
        )
        return {"served": served_ids, "held": held_ids, "admission_order": [r.request_id for r in admitted]}


def make_request(rid, class_id, prompt_tokens, arrival_time=0.0):
    return ObservableRequest(
        request_id=rid, arrival_time=arrival_time, prompt_tokens=prompt_tokens,
        predicted_output_tokens=50, slo_deadline=arrival_time + 100.0,
        priority=1.0, class_id=class_id,
    )


def make_gpu(active_requests, tokens_decoded, current_kv_tokens=0, max_kv_tokens=None):
    kwargs = dict(LARGE_GPU_KWARGS)
    if max_kv_tokens is not None:
        kwargs["max_kv_tokens"] = max_kv_tokens
    return ObservableGPUState(
        gpu_id=0,
        active_request_ids=[r.request_id for r in active_requests],
        active_requests_info=active_requests,
        current_kv_tokens=current_kv_tokens,
        tokens_decoded_per_request=tokens_decoded,
        **kwargs,
    )
