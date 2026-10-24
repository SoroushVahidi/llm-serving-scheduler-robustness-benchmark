"""
Dynamic-SplitFuse-style policy inspired by DeepSpeed-FastGen.

Manuscript label: "Dynamic-SplitFuse-style chunked-prefill baseline
inspired by DeepSpeed-FastGen"
NOT an official DeepSpeed-FastGen reproduction.

Reference: Holmes et al., "DeepSpeed-FastGen: High-Throughput Text Generation
for LLMs via MII and DeepSpeed-Inference," arXiv 2024.

Key idea reproduced here
------------------------
Dynamic SplitFuse composes each forward pass to exactly fill a fixed token
budget (`step_token_budget`):
  1. Allocate 1 token for each active decode request.
  2. With the remaining budget, admit a chunk of one or more new prefill requests
     (or a partial chunk of a single large request — "split" a long prefill).
  3. Maximise GPU utilisation by ensuring the forward pass is always full.

Phase 1 approximation
---------------------
True token-level chunking requires the simulator to track partial prefill
state.  In Phase 1 we approximate by:
  - Computing available budget = step_token_budget - n_active_decode.
  - Admitting new requests greedily until budget is exhausted (by prompt_tokens).
  - Requests with prompt_tokens > available budget are skipped (not split),
    unless they are the only waiting request (then admit anyway up to capacity).

This captures the budget-filling spirit without per-token prefill chunking.
Full chunked-prefill support is deferred to Phase 2.
"""
from __future__ import annotations

from ..core.action import Action
from ..core.types import ObservableState
from .base import BasePolicy
from .tie_breaking import arrival_then_id


class SplitFuseStylePolicy(BasePolicy):
    """Dynamic-SplitFuse-style: fill a fixed token budget each step."""

    name = "splitfuse_style"

    def __init__(self, step_token_budget: int = 512) -> None:
        self.step_token_budget = step_token_budget

    def select_action(self, state: ObservableState) -> Action:
        admit: dict[int, list[int]] = {g.gpu_id: [] for g in state.gpu_states}

        queue = sorted(state.waiting_queue, key=arrival_then_id)
        if not queue:
            return Action(admit=admit)

        admitted_ids: set[int] = set()

        for gpu in state.gpu_states:
            n_active = len(gpu.active_request_ids)
            # Budget: total tokens this step = step_token_budget
            # Decode requests consume 1 each; remaining is for new prefill
            remaining_budget = self.step_token_budget - n_active
            if remaining_budget <= 0:
                continue  # GPU is fully utilised; don't admit new requests

            local_kv = gpu.current_kv_tokens
            local_seq = n_active
            local_admitted = 0

            for req in queue:
                if req.request_id in admitted_ids:
                    continue

                fits_budget   = req.prompt_tokens <= remaining_budget
                fits_capacity = (
                    local_seq + 1 <= gpu.max_active_sequences
                    and local_kv + req.prompt_tokens <= gpu.max_kv_tokens
                    and local_seq + 1 <= gpu.max_batch_tokens
                )

                if fits_capacity and (fits_budget or local_admitted == 0):
                    # Admit (allow oversized prefill only if nothing else fits)
                    admit[gpu.gpu_id].append(req.request_id)
                    admitted_ids.add(req.request_id)
                    remaining_budget -= req.prompt_tokens
                    local_kv  += req.prompt_tokens
                    local_seq += 1
                    local_admitted += 1
                    gpu.active_request_ids.append(req.request_id)
                    gpu.current_kv_tokens += req.prompt_tokens

                    if remaining_budget <= 0:
                        break  # budget exhausted

        return Action(admit=admit)
