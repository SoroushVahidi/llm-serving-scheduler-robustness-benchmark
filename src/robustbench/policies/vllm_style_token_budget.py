"""
vLLM-inspired token-budget and paged-KV proxy policy.

Manuscript label: "vLLM-inspired token-budget / paged-KV proxy baseline"
NOT a vLLM reproduction or vLLM performance benchmark.

Reference: Kwon et al., "Efficient Memory Management for Large Language
Model Serving with PagedAttention," SOSP 2023.

Key ideas reproduced here
--------------------------
1. Per-step token budget: the scheduler caps the total number of active
   sequences to a configurable `max_batch_tokens` budget (proxy for vLLM's
   per-iteration token limit).
2. KV-block proxy: KV cache is approximated as a flat token budget (rather
   than page-granular blocks).  A request is admitted only when enough "KV
   blocks" are available (proxy: prompt_tokens free in KV budget).
3. Preemption-free in Phase 1: admitted requests are never evicted.  Full
   preemption/recompute logic is deferred to Phase 2.
4. Priority: prefer requests with shortest predicted remaining work
   (shortest_output_first as the inner ranking), consistent with vLLM's
   scheduler defaulting to continuous batching + FCFS but compatible with
   priority extensions.

Phase 1 approximations
-----------------------
- Page granularity is not modelled (KV is tracked in tokens, not blocks).
- No preemption, swap-in, or recompute.
- Prefill is instantaneous (see docs/simulator_design.md).
"""
from __future__ import annotations

from ..core.action import Action
from ..core.types import ObservableState
from .base import BasePolicy
from .tie_breaking import output_asc_then_arrival


class VLLMStyleTokenBudgetPolicy(BasePolicy):
    """vLLM-inspired policy using token budget + KV proxy + shortest-output priority."""

    name = "vllm_style_token_budget"

    def __init__(self, kv_block_size: int = 16) -> None:
        # kv_block_size: granularity of KV allocation (proxy for page size).
        # Admission is rounded up to nearest block.  Default 16 ≈ vLLM default.
        self.kv_block_size = max(1, kv_block_size)

    def _kv_blocks_needed(self, prompt_tokens: int) -> int:
        import math
        return math.ceil(prompt_tokens / self.kv_block_size) * self.kv_block_size

    def select_action(self, state: ObservableState) -> Action:
        admit: dict[int, list[int]] = {g.gpu_id: [] for g in state.gpu_states}

        # Prefer shortest predicted output (SJF inner policy)
        queue = sorted(state.waiting_queue, key=output_asc_then_arrival)

        gpu_idx = 0
        n_gpus = len(state.gpu_states)

        for req in queue:
            kv_needed = self._kv_blocks_needed(req.prompt_tokens)
            for offset in range(n_gpus):
                gpu = state.gpu_states[(gpu_idx + offset) % n_gpus]
                # Standard feasibility plus block-granular KV check
                new_seq = len(gpu.active_request_ids) + 1
                new_kv  = gpu.current_kv_tokens + kv_needed
                if (
                    new_seq <= gpu.max_active_sequences
                    and new_kv <= gpu.max_kv_tokens
                    and new_seq <= gpu.max_batch_tokens
                ):
                    admit[gpu.gpu_id].append(req.request_id)
                    gpu.active_request_ids.append(req.request_id)
                    gpu.current_kv_tokens += kv_needed   # round-up allocation
                    gpu_idx = (gpu_idx + offset + 1) % n_gpus
                    break

        return Action(admit=admit)
