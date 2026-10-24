"""
Shared feasibility helpers for scheduling policies.

These functions mirror the simulator-side constraint checks but operate on
ObservableGPUState so that policies can perform look-ahead without
touching simulator internals.
"""
from __future__ import annotations

from ..core.types import ObservableGPUState, ObservableRequest


def can_admit(
    gpu: ObservableGPUState,
    req: ObservableRequest,
    extra_seq: int = 0,
    extra_kv: int = 0,
) -> bool:
    """Return True if `req` can be admitted to `gpu`.

    `extra_seq` and `extra_kv` account for other requests already chosen
    for this GPU in the same action (within-step look-ahead).
    """
    new_seq   = len(gpu.active_request_ids) + extra_seq + 1
    new_kv    = gpu.current_kv_tokens + extra_kv + req.prompt_tokens
    new_batch = new_seq   # Phase 1: 1 batch token per sequence
    return (
        new_seq   <= gpu.max_active_sequences
        and new_kv    <= gpu.max_kv_tokens
        and new_batch <= gpu.max_batch_tokens
    )


def max_additional_reqs(gpu: ObservableGPUState, prompt_tokens: int = 0) -> int:
    """Upper bound on how many more requests (each with `prompt_tokens`) fit."""
    seq_free = gpu.max_active_sequences - len(gpu.active_request_ids)
    if prompt_tokens > 0:
        kv_free = (gpu.max_kv_tokens - gpu.current_kv_tokens) // max(prompt_tokens, 1)
    else:
        kv_free = seq_free
    batch_free = gpu.max_batch_tokens - len(gpu.active_request_ids)
    return max(0, min(seq_free, kv_free, batch_free))


def token_budget_remaining(gpu: ObservableGPUState) -> int:
    """Batch tokens available for new requests this step (Phase 1 model)."""
    return gpu.max_batch_tokens - len(gpu.active_request_ids)


def fits_in_token_budget(
    gpu: ObservableGPUState,
    req: ObservableRequest,
    already_admitted_batch: int = 0,
) -> bool:
    """Return True if req's prefill fits within remaining token budget."""
    used = len(gpu.active_request_ids) + already_admitted_batch
    remaining = gpu.max_batch_tokens - used
    # In Phase 1, each request needs exactly 1 batch token slot (decode phase).
    # Sarathi/SplitFuse extend this to include prompt tokens; approximated here.
    return remaining >= 1
