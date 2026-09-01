"""Aging-priority scheduler.

Adds explicit fairness/aging behavior missing from pure WSP/SLO policies by
increasing priority as a request waits. Uses only arrival_time, now, predicted
lengths, and deadline.
"""
from __future__ import annotations

from ..core.action import Action
from ..core.types import ObservableRequest, ObservableState
from .base import BasePolicy
from .policy_library_v2_helpers import deterministic_place, est_steps, laxity_seconds
from .scoring import DEFAULT_ALPHA, DEFAULT_BETA


class AgingPriorityPolicy(BasePolicy):
    name = "aging_priority"

    def __init__(self, step_size: float = 0.001, alpha: float = DEFAULT_ALPHA, beta: float = DEFAULT_BETA, aging_rate: float = 0.15) -> None:
        self.step_size = step_size
        self.alpha = alpha
        self.beta = beta
        self.aging_rate = aging_rate

    def _score(self, req: ObservableRequest, state: ObservableState) -> float:
        wait = max(0.0, state.time - req.arrival_time)
        aged_priority = req.priority + self.aging_rate * wait
        service = est_steps(req, self.alpha, self.beta)
        laxity = laxity_seconds(req, state.time, self.step_size, self.alpha, self.beta)
        return aged_priority / max(service, 1e-9) + 0.2 / max(laxity, 1e-9)

    def select_action(self, state: ObservableState) -> Action:
        ranked = sorted(state.waiting_queue, key=lambda r: (-self._score(r, state), r.arrival_time, r.request_id))
        return deterministic_place(state, ranked)
