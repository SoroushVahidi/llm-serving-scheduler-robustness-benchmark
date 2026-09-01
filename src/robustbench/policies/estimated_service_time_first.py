"""
Estimated Service Time First (ESTF) — prompt-and-prediction-aware SJF proxy.

This policy ranks requests by estimated total service time, preferring shorter
jobs.  It is a PARS-inspired, prompt-and-prediction-aware SJF proxy.

Estimated service time uses online-observable proxies only:

    estimated_service_time_i =
        α × prompt_tokens_i + β × predicted_output_tokens_i

where α and β are the service-model prefill/decode cost coefficients (defaulting
to the shared scoring.py constants).

IMPORTANT: This is NOT a reproduction of PARS.  PARS uses prompt-aware
learning-to-rank to predict service time from prompt semantics.  This policy
uses only token-length estimates and does not learn from data.

actual_output_tokens is never accessed.

Tie-breaking (deterministic, in order):
    1. lower estimated service time (primary)
    2. earlier deadline (slo_deadline)
    3. higher priority
    4. lower request_id (arrival proxy)
"""
from __future__ import annotations

from ..core.action import Action
from ..core.types import ObservableState
from .base import BasePolicy
from .scoring import DEFAULT_ALPHA, DEFAULT_BETA, predicted_service_proxy


class EstimatedServiceTimeFirstPolicy(BasePolicy):
    """Admit requests with the lowest estimated (prefill + decode) service time.

    Parameters
    ----------
    alpha : float
        Weight on prompt_tokens in the service-time proxy (default 0.5).
    beta : float
        Weight on predicted_output_tokens in the service-time proxy (default 1.0).
    """

    name = "estimated_service_time_first"

    def __init__(
        self,
        alpha: float = DEFAULT_ALPHA,
        beta: float = DEFAULT_BETA,
    ) -> None:
        self.alpha = alpha
        self.beta = beta

    def _sort_key(self, req):
        est = predicted_service_proxy(req, alpha=self.alpha, beta=self.beta)
        return (
            est,
            req.slo_deadline,
            -req.priority,
            req.request_id,
        )

    def select_action(self, state: ObservableState) -> Action:
        admit: dict[int, list[int]] = {g.gpu_id: [] for g in state.gpu_states}
        if not state.waiting_queue:
            return Action(admit=admit)

        queue = sorted(state.waiting_queue, key=self._sort_key)

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
