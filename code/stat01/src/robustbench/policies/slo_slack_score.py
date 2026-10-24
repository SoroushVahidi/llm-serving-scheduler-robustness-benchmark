"""
SLO-slack composite scoring policy.

Combines urgency (deadline slack), predicted service time, priority, and
waiting time into a single admission-priority score.  Higher score → admit
sooner.  Uses the shared scoring utilities from policies/scoring.py.
"""
from __future__ import annotations

from ..core.action import Action
from ..core.types import ObservableState
from .base import BasePolicy
from .scoring import urgency_score


class SloSlackScorePolicy(BasePolicy):
    """Prioritise requests with the worst deadline slack, weighted by priority."""

    name = "slo_slack_score"

    def __init__(
        self,
        alpha: float = 0.5,     # weight on predicted service proxy in urgency
        beta: float  = 1.0,     # weight on waiting time in urgency
        priority_weight: float = 1.0,  # multiplier for request.priority
    ) -> None:
        self.alpha = alpha
        self.beta  = beta
        self.priority_weight = priority_weight

    def select_action(self, state: ObservableState) -> Action:
        admit: dict[int, list[int]] = {g.gpu_id: [] for g in state.gpu_states}
        if not state.waiting_queue:
            return Action(admit=admit)

        now = state.time

        # Score: higher = more urgent.  urgency_score returns a composite metric
        # that combines (negative) deadline slack, service proxy, and wait time.
        # We additionally weight by priority so high-priority requests with the
        # same deadline urgency get admission preference.
        def _key(req):
            u = urgency_score(req, now, alpha=self.alpha, beta=self.beta)
            p = req.priority * self.priority_weight
            return -(u + p)   # negative → sorted ascending = highest score first

        queue = sorted(state.waiting_queue, key=_key)

        gpu_idx = 0
        n_gpus  = len(state.gpu_states)

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
