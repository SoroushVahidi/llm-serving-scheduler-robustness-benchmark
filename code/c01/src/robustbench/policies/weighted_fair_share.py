"""Weighted fair-share scheduler over observable request classes.

The simulator has no tenant ID. This policy uses class_id as the only
observable group label and therefore models class-level fairness, not true
multi-tenant fair sharing.
"""
from __future__ import annotations

from collections import Counter

from ..core.action import Action
from ..core.types import ObservableRequest, ObservableState
from .base import BasePolicy
from .policy_library_v2_helpers import deterministic_place, est_steps, queue_class_counts
from .scoring import DEFAULT_ALPHA, DEFAULT_BETA


class WeightedFairSharePolicy(BasePolicy):
    name = "weighted_fair_share"

    def __init__(self, alpha: float = DEFAULT_ALPHA, beta: float = DEFAULT_BETA) -> None:
        self.alpha = alpha
        self.beta = beta

    def _active_counts(self, state: ObservableState) -> Counter[str]:
        return queue_class_counts(r for g in state.gpu_states for r in g.active_requests_info)

    def _score(self, req: ObservableRequest, state: ObservableState, admitted_counts: Counter[str]) -> float:
        active = self._active_counts(state)
        cls = req.class_id or "unknown"
        served_share = active[cls] + admitted_counts[cls]
        demand = queue_class_counts(state.waiting_queue)[cls]
        deficit = demand / max(1, served_share + 1)
        return deficit * req.priority / max(est_steps(req, self.alpha, self.beta), 1e-9)

    def select_action(self, state: ObservableState) -> Action:
        admitted_counts: Counter[str] = Counter()
        ranked = sorted(
            state.waiting_queue,
            key=lambda r: (-self._score(r, state, admitted_counts), r.arrival_time, r.request_id),
        )

        def admit_filter(req: ObservableRequest, _gpu, _admitted: list[ObservableRequest]) -> bool:
            admitted_counts[req.class_id or "unknown"] += 1
            return True

        return deterministic_place(state, ranked, admit_filter=admit_filter)
