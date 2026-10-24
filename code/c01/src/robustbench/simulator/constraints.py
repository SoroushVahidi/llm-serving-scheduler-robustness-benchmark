"""
Constraint checking for request admission.

A policy action is valid only if every admitted request satisfies the GPU
capacity constraints.  The simulator calls these checks before applying any
admission; invalid admissions are silently dropped with a warning.
"""
from __future__ import annotations

from typing import List

from ..core.types import GPUConfig
from .request import InternalRequest


class ConstraintViolation(Exception):
    pass


def check_admission(
    gpu_config: GPUConfig,
    current_active: List[InternalRequest],
    candidates: List[InternalRequest],
) -> List[str]:
    """Return list of violation messages, empty if feasible.

    Checks are applied cumulatively so that adding `candidates` one-by-one
    in order remains feasible.  The full set is checked here at once.
    """
    violations: List[str] = []

    # Evaluate cumulative state after all candidates admitted
    new_count = len(current_active) + len(candidates)
    new_kv = (
        sum(r.kv_tokens for r in current_active if getattr(r, "current_tier", "kv") == "kv")
        + sum(c.request.prompt_tokens for c in candidates)  # initial KV for new reqs
    )
    # In Phase 1, batch_tokens = total active requests (1 decode token each per step)
    new_batch_tokens = new_count

    if new_count > gpu_config.max_active_sequences:
        violations.append(
            f"max_active_sequences exceeded: {new_count} > {gpu_config.max_active_sequences}"
        )
    if new_kv > gpu_config.max_kv_tokens:
        violations.append(
            f"max_kv_tokens exceeded: {new_kv} > {gpu_config.max_kv_tokens}"
        )
    if new_batch_tokens > gpu_config.max_batch_tokens:
        violations.append(
            f"max_batch_tokens exceeded: {new_batch_tokens} > {gpu_config.max_batch_tokens}"
        )

    return violations


def incremental_feasible(
    gpu_config: GPUConfig,
    current_active: List[InternalRequest],
    candidate: InternalRequest,
) -> bool:
    """Return True if adding one more request is feasible given current state."""
    new_count = len(current_active) + 1
    new_kv = (
        sum(r.kv_tokens for r in current_active if getattr(r, "current_tier", "kv") == "kv")
        + candidate.request.prompt_tokens
    )
    new_batch_tokens = new_count
    return (
        new_count <= gpu_config.max_active_sequences
        and new_kv <= gpu_config.max_kv_tokens
        and new_batch_tokens <= gpu_config.max_batch_tokens
    )
