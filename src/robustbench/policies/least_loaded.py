"""
Least Loaded: dispatch each admitted request to the GPU with the fewest
active sequences (or lowest KV utilization as a tiebreaker).
"""
from __future__ import annotations

from ..core.action import Action
from ..core.types import ObservableState
from .base import BasePolicy


class LeastLoadedPolicy(BasePolicy):
    name = "least_loaded"

    def select_action(self, state: ObservableState) -> Action:
        admit: dict[int, list[int]] = {g.gpu_id: [] for g in state.gpu_states}

        queue = list(state.waiting_queue)  # FIFO order for waiting requests

        for req in queue:
            # Pick GPU with fewest active sequences that can still accept req
            best_gpu = None
            best_load = float("inf")
            for gpu in state.gpu_states:
                if self._feasible_on_gpu(gpu, req):
                    load = len(gpu.active_request_ids)
                    kv_tie = gpu.current_kv_tokens / max(gpu.max_kv_tokens, 1)
                    score = load + kv_tie * 0.01   # kv as tiebreaker
                    if score < best_load:
                        best_load = score
                        best_gpu = gpu
            if best_gpu is not None:
                admit[best_gpu.gpu_id].append(req.request_id)
                best_gpu.active_request_ids.append(req.request_id)
                best_gpu.current_kv_tokens += req.prompt_tokens

        return Action(admit=admit)
