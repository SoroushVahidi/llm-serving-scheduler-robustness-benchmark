"""KV-constrained online scheduler.

Admits requests only when their causal predicted KV footprint leaves a reserve
under high KV pressure, while allowing urgent requests to consume the reserve.
"""
from __future__ import annotations

from ..core.action import Action
from ..core.types import ObservableGPUState, ObservableRequest, ObservableState
from .base import BasePolicy
from .policy_library_v2_helpers import deterministic_place, laxity_seconds
from .scoring import DEFAULT_ALPHA, DEFAULT_BETA


class KVConstrainedOnlinePolicy(BasePolicy):
    name = "kv_constrained_online"

    def __init__(
        self,
        step_size: float = 0.001,
        alpha: float = DEFAULT_ALPHA,
        beta: float = DEFAULT_BETA,
        target_kv_utilization: float = 0.82,
        urgent_laxity_seconds: float = 0.25,
    ) -> None:
        self.step_size = step_size
        self.alpha = alpha
        self.beta = beta
        self.target_kv_utilization = target_kv_utilization
        self.urgent_laxity_seconds = urgent_laxity_seconds

    def _score(self, req: ObservableRequest, state: ObservableState) -> tuple:
        laxity = laxity_seconds(req, state.time, self.step_size, self.alpha, self.beta)
        kv_cost = req.prompt_tokens + 0.25 * req.predicted_output_tokens
        return (laxity > self.urgent_laxity_seconds, kv_cost / max(req.priority, 1e-9), laxity, req.request_id)

    def _admit_filter(self, req: ObservableRequest, gpu: ObservableGPUState, admitted: list[ObservableRequest], now: float) -> bool:
        post_util = (gpu.current_kv_tokens + req.prompt_tokens) / max(gpu.max_kv_tokens, 1)
        urgent = laxity_seconds(req, now, self.step_size, self.alpha, self.beta) <= self.urgent_laxity_seconds
        return post_util <= self.target_kv_utilization or urgent

    def select_action(self, state: ObservableState) -> Action:
        ranked = sorted(state.waiting_queue, key=lambda r: self._score(r, state))
        return deterministic_place(
            state,
            ranked,
            gpu_key=lambda g, r: ((g.current_kv_tokens + r.prompt_tokens) / max(g.max_kv_tokens, 1), g.gpu_id),
            admit_filter=lambda r, g, a: self._admit_filter(r, g, a, state.time),
        )
