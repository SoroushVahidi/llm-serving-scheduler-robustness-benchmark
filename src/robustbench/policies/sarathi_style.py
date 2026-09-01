"""
Sarathi-style stall-free chunked-prefill policy.

Manuscript label: "Sarathi-style stall-free chunked-prefill baseline"
NOT an official Sarathi-Serve reproduction.

Reference: Agrawal et al., "Sarathi: Efficient LLM Inference by Piggybacking
Decodes with Chunked Prefills," arXiv 2023.  / Sarathi-Serve, OSDI 2024.

Key idea reproduced here
------------------------
Sarathi-Serve avoids decode stalls caused by large prefill batches by:
  1. Running decode-only steps whenever active decode requests are present.
  2. Piggybacking a bounded chunk of prefill alongside ongoing decodes — the
     "stall-free" property: decode throughput is never blocked by prefill.
  3. Limiting admitted prefill work per step to `max_prefill_tokens_per_step`
     (the chunk size).

Phase 1 approximation
---------------------
Because the Phase 1 simulator does not model a separate prefill step, this
policy approximates stall-free chunked prefill as follows:
  - Ongoing decode requests always run (handled by simulator).
  - Each step, the policy only admits requests whose total prompt_tokens sum
    does not exceed `max_prefill_tokens_per_step`.
  - When active decode requests are present (GPU busy), the chunk budget is
    halved to simulate decode-priority scheduling.

This captures the spirit of Sarathi's admission-rate limiting without
full prefill-phase modelling.  See docs/simulator_design.md §extension-points.
"""
from __future__ import annotations

from ..core.action import Action
from ..core.types import ObservableState
from .base import BasePolicy
from .tie_breaking import arrival_then_id


class SarathiStylePolicy(BasePolicy):
    """Sarathi-style: decode-first, bounded chunked-prefill admission."""

    name = "sarathi_style"

    def __init__(self, max_prefill_tokens_per_step: int = 512) -> None:
        self.max_prefill_tokens_per_step = max_prefill_tokens_per_step

    def select_action(self, state: ObservableState) -> Action:
        admit: dict[int, list[int]] = {g.gpu_id: [] for g in state.gpu_states}

        queue = sorted(state.waiting_queue, key=arrival_then_id)
        if not queue:
            return Action(admit=admit)

        # Maintained incrementally — avoids O(N²) set rebuild inside the inner loop.
        admitted_ids: set[int] = set()

        for gpu in state.gpu_states:
            # Reduce chunk budget when GPU already has active decode work
            n_active = len(gpu.active_request_ids)
            if n_active > 0:
                # Decode-priority: give half the prefill budget to new requests
                step_prefill_budget = self.max_prefill_tokens_per_step // 2
            else:
                step_prefill_budget = self.max_prefill_tokens_per_step

            admitted_prefill_tokens = 0
            admitted_seq = 0

            for req in queue:
                if req.request_id in admitted_ids:
                    continue  # already assigned to another GPU

                # Stall-free check: don't exceed prefill chunk budget.
                # Safety valve: always admit at least one request per step
                # (when the first feasible request exceeds the budget, admit
                # it anyway — real Sarathi handles this via chunked prefill;
                # refusing to admit would cause starvation).
                exceeds_budget = (
                    admitted_prefill_tokens + req.prompt_tokens > step_prefill_budget
                )
                if exceeds_budget and admitted_seq > 0:
                    continue   # defer to a future step

                # Standard capacity check (uses updated state with admitted so far)
                new_seq = len(gpu.active_request_ids) + admitted_seq + 1
                new_kv  = gpu.current_kv_tokens + admitted_prefill_tokens + req.prompt_tokens

                if (
                    new_seq <= gpu.max_active_sequences
                    and new_kv  <= gpu.max_kv_tokens
                    and new_seq <= gpu.max_batch_tokens
                ):
                    admit[gpu.gpu_id].append(req.request_id)
                    admitted_ids.add(req.request_id)  # O(1) incremental update
                    admitted_prefill_tokens += req.prompt_tokens
                    admitted_seq += 1
                    gpu.active_request_ids.append(req.request_id)
                    gpu.current_kv_tokens += req.prompt_tokens

        return Action(admit=admit)
