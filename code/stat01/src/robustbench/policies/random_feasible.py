"""Random Feasible: admit a random subset of waiting requests, deterministic under seed."""
from __future__ import annotations

import numpy as np

from ..core.action import Action
from ..core.types import ObservableState
from .base import BasePolicy


class RandomFeasiblePolicy(BasePolicy):
    name = "random_feasible"

    def __init__(self, seed: int = 0) -> None:
        self._rng = np.random.default_rng(seed)
        self._seed = seed

    def reset(self) -> None:
        self._rng = np.random.default_rng(self._seed)

    def select_action(self, state: ObservableState) -> Action:
        admit: dict[int, list[int]] = {g.gpu_id: [] for g in state.gpu_states}

        queue = list(state.waiting_queue)
        if not queue:
            return Action(admit=admit)

        # Shuffle waiting requests randomly
        indices = self._rng.permutation(len(queue))
        shuffled = [queue[i] for i in indices]

        gpu_idx = 0
        n_gpus = len(state.gpu_states)

        for req in shuffled:
            for offset in range(n_gpus):
                gpu = state.gpu_states[(gpu_idx + offset) % n_gpus]
                if self._feasible_on_gpu(gpu, req):
                    admit[gpu.gpu_id].append(req.request_id)
                    gpu.active_request_ids.append(req.request_id)
                    gpu.current_kv_tokens += req.prompt_tokens
                    gpu_idx = (gpu_idx + offset + 1) % n_gpus
                    break

        return Action(admit=admit)
