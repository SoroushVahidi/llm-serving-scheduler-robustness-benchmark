"""
Greedy Token Fill: fill each GPU's token/KV budget as tightly as possible.

Admits requests in FIFO order but skips ones that would overflow a GPU's
remaining capacity, trying the next GPU before giving up on a request.
"""
from __future__ import annotations

from ..core.action import Action
from ..core.types import ObservableState
from .base import BasePolicy


class GreedyTokenFillPolicy(BasePolicy):
    name = "greedy_token_fill"

    def select_action(self, state: ObservableState) -> Action:
        admit: dict[int, list[int]] = {g.gpu_id: [] for g in state.gpu_states}

        queue = list(state.waiting_queue)  # FIFO order

        for req in queue:
            # Try each GPU, pick the one with most remaining KV (best fit)
            best_gpu = None
            best_remaining = -1
            for gpu in state.gpu_states:
                if self._feasible_on_gpu(gpu, req):
                    remaining = self._remaining_kv(gpu)
                    if remaining > best_remaining:
                        best_remaining = remaining
                        best_gpu = gpu
            if best_gpu is not None:
                admit[best_gpu.gpu_id].append(req.request_id)
                best_gpu.active_request_ids.append(req.request_id)
                best_gpu.current_kv_tokens += req.prompt_tokens

        return Action(admit=admit)
