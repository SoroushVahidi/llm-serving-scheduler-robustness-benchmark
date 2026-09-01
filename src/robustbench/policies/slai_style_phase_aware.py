"""SLAI-style phase-aware scheduler approximation.

The simulator's monolithic action space cannot implement a full paper system,
but it exposes active prefill/decode counts. This policy uses those causal
phase signals to avoid admitting work that worsens the currently dominant
prefill/decode bottleneck.
"""
from __future__ import annotations

from ..core.action import Action
from ..core.types import ObservableRequest, ObservableState
from .base import BasePolicy
from .policy_library_v2_helpers import deterministic_place, est_steps, laxity_seconds
from .scoring import DEFAULT_ALPHA, DEFAULT_BETA


class SlaiStylePhaseAwarePolicy(BasePolicy):
    name = "slai_style_phase_aware"

    def __init__(self, step_size: float = 0.001, alpha: float = DEFAULT_ALPHA, beta: float = DEFAULT_BETA) -> None:
        self.step_size = step_size
        self.alpha = alpha
        self.beta = beta

    def _phase_pressure(self, state: ObservableState) -> tuple[float, float]:
        cap = sum(g.max_active_sequences for g in state.gpu_states) or 1
        prefill = sum(g.prefilling_count for g in state.gpu_states) / cap
        decode = sum(g.decoding_count for g in state.gpu_states) / cap
        return prefill, decode

    def _score(self, req: ObservableRequest, state: ObservableState) -> float:
        prefill_p, decode_p = self._phase_pressure(state)
        prompt_share = req.prompt_tokens / max(req.prompt_tokens + req.predicted_output_tokens, 1)
        decode_share = 1.0 - prompt_share
        phase_penalty = prefill_p * prompt_share + decode_p * decode_share
        service = est_steps(req, self.alpha, self.beta)
        laxity = laxity_seconds(req, state.time, self.step_size, self.alpha, self.beta)
        return req.priority - 2.5 * phase_penalty - 0.0025 * service - 0.08 * max(laxity, 0.0)

    def select_action(self, state: ObservableState) -> Action:
        ranked = sorted(
            state.waiting_queue,
            key=lambda r: (-self._score(r, state), r.predicted_output_tokens, r.prompt_tokens, r.request_id),
        )
        return deterministic_place(state, ranked)
