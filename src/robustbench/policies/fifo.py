"""FIFO: admit oldest-arrived requests first, round-robin across GPUs."""
from __future__ import annotations

from ..core.action import Action
from ..core.types import ObservableState
from .base import BasePolicy


class FIFOPolicy(BasePolicy):
    name = "fifo"

    def select_action(self, state: ObservableState) -> Action:
        admit: dict[int, list[int]] = {g.gpu_id: [] for g in state.gpu_states}

        # Waiting queue is already ordered by arrival time (simulator preserves order)
        queue = list(state.waiting_queue)  # oldest first

        gpu_idx = 0
        n_gpus = len(state.gpu_states)

        for req in queue:
            for offset in range(n_gpus):
                gpu = state.gpu_states[(gpu_idx + offset) % n_gpus]
                if self._feasible_on_gpu(gpu, req):
                    admit[gpu.gpu_id].append(req.request_id)
                    # Update local count to avoid over-admission in same action
                    gpu.active_request_ids.append(req.request_id)
                    gpu.current_kv_tokens += req.prompt_tokens
                    gpu_idx = (gpu_idx + offset + 1) % n_gpus
                    break
            # If no GPU is feasible, this request is skipped for this step

        return Action(admit=admit)
