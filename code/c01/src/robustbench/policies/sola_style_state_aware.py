"""SOLA-style state-aware scheduler approximation.

This is not a reproduction of SOLA. It is a faithful simulator-level
approximation of the implementable behavior: causal state-aware ranking that
combines estimated service, laxity, priority, queue pressure, and KV pressure.
"""
from __future__ import annotations

from ..core.action import Action
from ..core.types import ObservableRequest, ObservableState
from .base import BasePolicy
from .policy_library_v2_helpers import deterministic_place, est_steps, gpu_pressure, laxity_seconds, system_pressure
from .scoring import DEFAULT_ALPHA, DEFAULT_BETA

_EPS = 1e-9


class SolaStyleStateAwarePolicy(BasePolicy):
    name = "sola_style_state_aware"

    def __init__(self, step_size: float = 0.001, alpha: float = DEFAULT_ALPHA, beta: float = DEFAULT_BETA) -> None:
        self.step_size = step_size
        self.alpha = alpha
        self.beta = beta

    def _score(self, req: ObservableRequest, state: ObservableState) -> float:
        laxity = laxity_seconds(req, state.time, self.step_size, self.alpha, self.beta)
        urgency = 1.0 / max(laxity, _EPS)
        service = est_steps(req, self.alpha, self.beta)
        load = system_pressure(state)
        kv_cost = req.prompt_tokens + req.predicted_output_tokens
        return (
            1.8 * req.priority
            + 1.2 * urgency
            - (0.004 + 0.008 * load) * service
            - 0.00015 * load * kv_cost
            + 0.04 * max(0.0, state.time - req.arrival_time)
        )

    def select_action(self, state: ObservableState) -> Action:
        ranked = sorted(
            state.waiting_queue,
            key=lambda r: (-self._score(r, state), laxity_seconds(r, state.time, self.step_size, self.alpha, self.beta), r.arrival_time, r.request_id),
        )
        return deterministic_place(state, ranked, gpu_key=lambda g, r: (gpu_pressure(g), g.current_kv_tokens + r.prompt_tokens, g.gpu_id))
