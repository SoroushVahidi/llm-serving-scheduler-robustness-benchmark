"""
Base class for all scheduling policies.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..core.action import Action
from ..core.types import ObservableGPUState, ObservableRequest, ObservableState


class BasePolicy(ABC):
    """Abstract base for scheduling policies.

    Policies are stateless between calls unless they explicitly maintain
    internal state.  They must NOT access Request.actual_output_tokens;
    that field is hidden in ObservableRequest and ObservableState.
    """

    #: Human-readable identifier used in tables and logs.
    name: str = "base"

    @abstractmethod
    def select_action(self, state: ObservableState) -> Action:
        """Given the current observable state, return an admission action."""
        ...

    def reset(self) -> None:
        """Optional hook called by the simulator before each run."""
        pass

    # ------------------------------------------------------------------
    # Shared utility helpers available to all subclasses
    # ------------------------------------------------------------------

    @staticmethod
    def _feasible_on_gpu(gpu: ObservableGPUState, req: ObservableRequest) -> bool:
        """Check if req can be admitted to gpu without violating capacity."""
        new_count = len(gpu.active_request_ids) + 1
        new_kv = gpu.current_kv_tokens + req.prompt_tokens
        new_batch = new_count  # 1 token per decode request in Phase 1
        return (
            new_count <= gpu.max_active_sequences
            and new_kv <= gpu.max_kv_tokens
            and new_batch <= gpu.max_batch_tokens
        )

    @staticmethod
    def _remaining_kv(gpu: ObservableGPUState) -> int:
        return gpu.max_kv_tokens - gpu.current_kv_tokens

    @staticmethod
    def _remaining_sequences(gpu: ObservableGPUState) -> int:
        return gpu.max_active_sequences - len(gpu.active_request_ids)
