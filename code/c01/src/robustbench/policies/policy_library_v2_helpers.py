"""Shared helpers for Policy Library v2 monolithic schedulers.

These helpers operate only on ObservableState/ObservableRequest fields and
mutate the ObservableGPUState copies in the same style as existing policies.
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Callable, Iterable

from ..core.action import Action
from ..core.types import ObservableGPUState, ObservableRequest, ObservableState
from .base import BasePolicy
from .scoring import DEFAULT_ALPHA, DEFAULT_BETA, predicted_service_proxy

_EPS = 1e-9


def est_steps(
    req: ObservableRequest,
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
) -> float:
    return predicted_service_proxy(req, alpha=alpha, beta=beta)


def est_seconds(
    req: ObservableRequest,
    step_size: float,
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
) -> float:
    return est_steps(req, alpha=alpha, beta=beta) * step_size


def laxity_seconds(
    req: ObservableRequest,
    now: float,
    step_size: float,
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
) -> float:
    return req.slo_deadline - now - est_seconds(req, step_size, alpha, beta)


def gpu_pressure(gpu: ObservableGPUState) -> float:
    seq = len(gpu.active_request_ids) / max(gpu.max_active_sequences, 1)
    kv = gpu.current_kv_tokens / max(gpu.max_kv_tokens, 1)
    phase = gpu.prefilling_count / max(gpu.max_active_sequences, 1)
    return 0.45 * seq + 0.45 * kv + 0.10 * phase


def system_pressure(state: ObservableState) -> float:
    if not state.gpu_states:
        return 0.0
    seq_cap = sum(g.max_active_sequences for g in state.gpu_states) or 1
    kv_cap = sum(g.max_kv_tokens for g in state.gpu_states) or 1
    active = sum(len(g.active_request_ids) for g in state.gpu_states)
    kv = sum(g.current_kv_tokens for g in state.gpu_states)
    queue_pressure = len(state.waiting_queue) / max(seq_cap, 1)
    return 0.35 * active / seq_cap + 0.35 * kv / kv_cap + 0.30 * min(queue_pressure, 3.0) / 3.0


def arrival_rate_recent(state: ObservableState, horizon: float) -> float:
    if horizon <= 0:
        return 0.0
    now = state.time
    return sum(1 for r in state.waiting_queue if now - r.arrival_time <= horizon) / horizon


def queue_class_counts(requests: Iterable[ObservableRequest]) -> Counter[str]:
    return Counter(r.class_id or "unknown" for r in requests)


def deterministic_place(
    state: ObservableState,
    ranked: list[ObservableRequest],
    *,
    gpu_key: Callable[[ObservableGPUState, ObservableRequest], tuple] | None = None,
    admit_filter: Callable[[ObservableRequest, ObservableGPUState, list[ObservableRequest]], bool] | None = None,
    max_admits: int | None = None,
) -> Action:
    """Greedily place ranked requests while respecting observable capacities."""
    admit: dict[int, list[int]] = {g.gpu_id: [] for g in state.gpu_states}
    admitted: list[ObservableRequest] = []
    if not state.gpu_states or not ranked:
        return Action(admit=admit)

    def default_gpu_key(gpu: ObservableGPUState, req: ObservableRequest) -> tuple:
        return (gpu_pressure(gpu), gpu.gpu_id)

    choose_key = gpu_key or default_gpu_key

    for req in ranked:
        if max_admits is not None and len(admitted) >= max_admits:
            break
        feasible = [g for g in state.gpu_states if BasePolicy._feasible_on_gpu(g, req)]
        feasible.sort(key=lambda g: choose_key(g, req))
        for gpu in feasible:
            if admit_filter is not None and not admit_filter(req, gpu, admitted):
                continue
            admit[gpu.gpu_id].append(req.request_id)
            admitted.append(req)
            gpu.active_request_ids.append(req.request_id)
            gpu.current_kv_tokens += req.prompt_tokens
            break
    return Action(admit=admit)


def sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)
