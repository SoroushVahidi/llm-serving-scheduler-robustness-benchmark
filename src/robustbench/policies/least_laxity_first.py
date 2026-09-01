"""
Least Laxity First (LLF) scheduling policy.

Laxity measures how much slack a request has relative to its estimated
remaining service time:

    laxity_i = deadline_i − current_time − estimated_remaining_service_time_i

A request with low (or negative) laxity is close to missing its SLO even if
admitted immediately.  LLF always prefers the request with the lowest laxity,
making it strictly more urgent than EDF under service-time uncertainty.

Estimated service time uses online-observable proxies only:
    estimated_prefill_cost = α × prompt_tokens
    estimated_decode_cost  = β × predicted_output_tokens
    estimated_service_time = estimated_prefill_cost + estimated_decode_cost

actual_output_tokens is never accessed.

Tie-breaking (deterministic, in order):
    1. lower laxity (primary)
    2. earlier deadline (slo_deadline)
    3. higher priority
    4. lower request_id (arrival proxy)
"""
from __future__ import annotations

from ..core.action import Action
from ..core.types import ObservableState
from .base import BasePolicy
from .scoring import DEFAULT_ALPHA, DEFAULT_BETA, predicted_service_proxy


class LeastLaxityFirstPolicy(BasePolicy):
    """Greedy admission of requests with smallest laxity first.

    Parameters
    ----------
    alpha : float
        Weight on prompt_tokens in the service-time proxy (default 0.5).
    beta : float
        Weight on predicted_output_tokens in the service-time proxy (default 1.0).
    """

    name = "least_laxity_first"

    def __init__(
        self,
        alpha: float = DEFAULT_ALPHA,
        beta: float = DEFAULT_BETA,
    ) -> None:
        self.alpha = alpha
        self.beta = beta

    def _laxity(self, req, now: float) -> float:
        service_est = predicted_service_proxy(req, alpha=self.alpha, beta=self.beta)
        return req.slo_deadline - now - service_est

    def _sort_key(self, req, now: float):
        # Lower laxity first, then earlier deadline, then higher priority (neg),
        # then lower request_id for full determinism.
        return (
            self._laxity(req, now),
            req.slo_deadline,
            -req.priority,
            req.request_id,
        )

    def select_action(self, state: ObservableState) -> Action:
        admit: dict[int, list[int]] = {g.gpu_id: [] for g in state.gpu_states}
        if not state.waiting_queue:
            return Action(admit=admit)

        now = state.time
        queue = sorted(state.waiting_queue, key=lambda r: self._sort_key(r, now))

        gpu_idx = 0
        n_gpus = len(state.gpu_states)

        for req in queue:
            for offset in range(n_gpus):
                gpu = state.gpu_states[(gpu_idx + offset) % n_gpus]
                if self._feasible_on_gpu(gpu, req):
                    admit[gpu.gpu_id].append(req.request_id)
                    gpu.active_request_ids.append(req.request_id)
                    gpu.current_kv_tokens += req.prompt_tokens
                    gpu_idx = (gpu_idx + offset + 1) % n_gpus
                    break

        return Action(admit=admit)
