"""
Oracle policy (non-deployable, hindsight upper bound).

Uses actual_output_tokens to make optimal admit-order decisions.  This is
NOT a real online policy — it requires future information and cannot be
deployed in production.

IMPORTANT: The oracle is included only as a benchmark ceiling for small
traces.  Claims like "our method matches the oracle" would require
careful qualification.  See docs/result_claims.md.

The oracle implemented here is a greedy hindsight oracle, not necessarily
globally optimal.  It schedules requests by shortest actual job first (SRTF),
which is optimal for minimizing mean completion time in single-machine
scheduling but only approximately optimal in the multi-GPU batched setting.
"""
from __future__ import annotations

import warnings

from ..core.action import Action
from ..core.types import ObservableState
from .base import BasePolicy


class OracleShortestJobFirstPolicy(BasePolicy):
    """Hindsight greedy SRTF oracle.  Uses actual_output_tokens if provided."""

    name = "oracle_srtf"

    def __init__(self, actual_output_map: dict[int, int]) -> None:
        """
        Parameters
        ----------
        actual_output_map : dict[int, int]
            Maps request_id -> actual_output_tokens (ground truth).
            Obtained from the trace before simulation; NOT available to
            real online policies.
        """
        self._actual = actual_output_map
        warnings.warn(
            "OracleShortestJobFirstPolicy uses future information (actual_output_tokens). "
            "It is NOT a deployable policy.  Use only as a benchmark ceiling.",
            UserWarning,
            stacklevel=2,
        )

    def select_action(self, state: ObservableState) -> Action:
        admit: dict[int, list[int]] = {g.gpu_id: [] for g in state.gpu_states}

        # Sort by actual output tokens (true SRTF) — oracle knowledge
        queue = sorted(
            state.waiting_queue,
            key=lambda r: self._actual.get(r.request_id, r.predicted_output_tokens),
        )

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


def build_oracle(requests: list) -> OracleShortestJobFirstPolicy:
    """Convenience constructor from a list of Request objects."""
    actual_map = {r.request_id: r.actual_output_tokens for r in requests}
    return OracleShortestJobFirstPolicy(actual_output_map=actual_map)
