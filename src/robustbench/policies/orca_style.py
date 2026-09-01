"""
Orca-style iteration-level scheduling policy.

Manuscript label: "Orca-style iteration-level scheduler"
NOT an official Orca reproduction.

Reference: Yu et al., "Orca: A Distributed Serving System for
Transformer-Based Generative Models," OSDI 2022.

Key idea reproduced here
------------------------
At every decode iteration the scheduler:
  1. Retires all requests that completed their last decode step (handled by simulator).
  2. Inspects the waiting queue and admits as many requests as fit within the
     step's capacity budget (max_active_sequences, max_batch_tokens, max_kv_tokens).
  3. Uses FCFS (arrival-time order) as the base selection policy, with class-level
     priority as a secondary sort key (higher-priority class first).
  4. All active requests (old + newly admitted) run together in the next step.

This is the "selective batching" variant from the Orca paper where the scheduler
selects a subset of waiting requests to add to the running batch.

Phase 1 approximations
----------------------
- Prefill is not separately modeled; see docs/simulator_design.md.
- Token budget is modelled as max_active_sequences (1 token per decode request).
- No memory paging or eviction.
"""
from __future__ import annotations

from ..core.action import Action
from ..core.types import ObservableState
from .base import BasePolicy
from .tie_breaking import priority_desc_then_arrival


class OrcaStylePolicy(BasePolicy):
    """Orca-style iteration-level scheduler (FCFS within priority class)."""

    name = "orca_style"

    def select_action(self, state: ObservableState) -> Action:
        admit: dict[int, list[int]] = {g.gpu_id: [] for g in state.gpu_states}

        # Sort: highest priority first, then FCFS, then id
        queue = sorted(state.waiting_queue, key=priority_desc_then_arrival)

        # Round-robin GPU assignment to balance load
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
