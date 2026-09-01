"""
WSPT: Weighted Shortest Processing Time.

Sort by predicted_service_proxy / priority_weight (ascending).
Balances urgency (priority) with predicted work length.
"""
from __future__ import annotations

from ..core.action import Action
from ..core.types import ObservableState
from .base import BasePolicy
from .scoring import weighted_shortest_processing_score, DEFAULT_ALPHA, DEFAULT_BETA


class WeightedShortestProcessingPolicy(BasePolicy):
    name = "weighted_shortest_processing"

    def __init__(self, alpha: float = DEFAULT_ALPHA, beta: float = DEFAULT_BETA) -> None:
        self.alpha = alpha
        self.beta = beta

    def select_action(self, state: ObservableState) -> Action:
        admit: dict[int, list[int]] = {g.gpu_id: [] for g in state.gpu_states}

        queue = sorted(
            state.waiting_queue,
            key=lambda r: (
                weighted_shortest_processing_score(r, self.alpha, self.beta),
                r.arrival_time,
                r.request_id,
            ),
        )

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
