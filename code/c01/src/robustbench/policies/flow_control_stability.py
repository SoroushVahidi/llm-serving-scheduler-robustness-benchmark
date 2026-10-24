"""Flow-control stability scheduler.

This policy deliberately throttles admissions when queue and load pressure are
high. It models a causal overload-stability behavior that was missing from the
historical ranking-heavy library.
"""
from __future__ import annotations

from ..core.action import Action
from ..core.types import ObservableRequest, ObservableState
from .base import BasePolicy
from .policy_library_v2_helpers import arrival_rate_recent, deterministic_place, est_steps, laxity_seconds, system_pressure
from .scoring import DEFAULT_ALPHA, DEFAULT_BETA


class FlowControlStabilityPolicy(BasePolicy):
    name = "flow_control_stability"

    def __init__(
        self,
        step_size: float = 0.001,
        alpha: float = DEFAULT_ALPHA,
        beta: float = DEFAULT_BETA,
        budget_refill: float = 1.5,
        budget_max: float = 8.0,
        overload_threshold: float = 0.62,
    ) -> None:
        self.step_size = step_size
        self.alpha = alpha
        self.beta = beta
        self.budget_refill = budget_refill
        self.budget_max = budget_max
        self.overload_threshold = overload_threshold
        self._budget = budget_max

    def reset(self) -> None:
        self._budget = self.budget_max

    def _score(self, req: ObservableRequest, state: ObservableState) -> tuple:
        laxity = laxity_seconds(req, state.time, self.step_size, self.alpha, self.beta)
        return (laxity, est_steps(req, self.alpha, self.beta) / max(req.priority, 1e-9), req.arrival_time, req.request_id)

    def select_action(self, state: ObservableState) -> Action:
        self._budget = min(self.budget_max, self._budget + self.budget_refill)
        pressure = system_pressure(state)
        arrival_slope = arrival_rate_recent(state, 2.0) - arrival_rate_recent(state, 20.0)
        overload = pressure >= self.overload_threshold or arrival_slope > 0.5
        max_admits = max(1, int(self._budget)) if overload else None
        ranked = sorted(state.waiting_queue, key=lambda r: self._score(r, state))
        action = deterministic_place(state, ranked, max_admits=max_admits)
        admitted = sum(len(v) for v in action.admit.values())
        if overload:
            self._budget = max(0.0, self._budget - admitted)
        return action
