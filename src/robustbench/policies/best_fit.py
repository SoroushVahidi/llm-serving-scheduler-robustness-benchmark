"""
Best Fit: place each request on the GPU with the least remaining KV capacity
that can still admit it (tightest fit).

Analogous to Best Fit bin packing — reduces fragmentation by filling nearly-full
GPUs before using emptier ones.
"""
from __future__ import annotations

from ..core.action import Action
from ..core.types import ObservableState
from .base import BasePolicy
from .scoring import remaining_kv
from .tie_breaking import arrival_then_id


class BestFitPolicy(BasePolicy):
    name = "best_fit"

    def select_action(self, state: ObservableState) -> Action:
        admit: dict[int, list[int]] = {g.gpu_id: [] for g in state.gpu_states}

        queue = sorted(state.waiting_queue, key=arrival_then_id)

        for req in queue:
            best_gpu = None
            best_remaining = float("inf")
            for gpu in state.gpu_states:
                if self._feasible_on_gpu(gpu, req):
                    rem = remaining_kv(gpu)
                    # Best fit = smallest remaining capacity that still fits
                    if rem < best_remaining:
                        best_remaining = rem
                        best_gpu = gpu
            if best_gpu is not None:
                admit[best_gpu.gpu_id].append(req.request_id)
                best_gpu.active_request_ids.append(req.request_id)
                best_gpu.current_kv_tokens += req.prompt_tokens

        return Action(admit=admit)
