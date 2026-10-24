"""Adaptive chunked-prefill controller approximation.

The monolithic simulator cannot choose actual chunk sizes per request through
Action. This policy faithfully implements the representable part: admission
control that limits long-prompt prefill concurrency under pressure and admits
short/decode-friendly requests around those long prompts.
"""
from __future__ import annotations

from ..core.action import Action
from ..core.types import ObservableRequest, ObservableState
from .base import BasePolicy
from .policy_library_v2_helpers import deterministic_place, laxity_seconds, system_pressure
from .scoring import DEFAULT_ALPHA, DEFAULT_BETA


class AdaptiveChunkedPrefillPolicy(BasePolicy):
    name = "adaptive_chunked_prefill"

    def __init__(
        self,
        step_size: float = 0.001,
        alpha: float = DEFAULT_ALPHA,
        beta: float = DEFAULT_BETA,
        long_prompt_threshold: int = 2048,
        pressure_threshold: float = 0.55,
    ) -> None:
        self.step_size = step_size
        self.alpha = alpha
        self.beta = beta
        self.long_prompt_threshold = long_prompt_threshold
        self.pressure_threshold = pressure_threshold

    def _score(self, req: ObservableRequest, state: ObservableState) -> tuple:
        pressure = system_pressure(state)
        long_prompt_penalty = 1 if pressure >= self.pressure_threshold and req.prompt_tokens >= self.long_prompt_threshold else 0
        return (
            long_prompt_penalty,
            laxity_seconds(req, state.time, self.step_size, self.alpha, self.beta),
            req.predicted_output_tokens,
            req.request_id,
        )

    def select_action(self, state: ObservableState) -> Action:
        pressure = system_pressure(state)
        active_long_prefill = sum(1 for g in state.gpu_states for r in g.active_requests_info if r.prompt_tokens >= self.long_prompt_threshold)
        max_long = 1 if pressure >= self.pressure_threshold else None

        def admit_filter(req: ObservableRequest, _gpu, admitted: list[ObservableRequest]) -> bool:
            if max_long is None or req.prompt_tokens < self.long_prompt_threshold:
                return True
            return active_long_prefill + sum(1 for r in admitted if r.prompt_tokens >= self.long_prompt_threshold) < max_long

        ranked = sorted(state.waiting_queue, key=lambda r: self._score(r, state))
        return deterministic_place(state, ranked, admit_filter=admit_filter)
