"""
Multi-Bin-style Batching (approximate baseline).

Inspired by the Multi-Bin Batching idea from the LLM scheduling literature:
group requests by predicted output length into bins, then fill batches from
a single bin to reduce length mismatch and padding overhead.

IMPORTANT: This is our own simplified adaptation of the Multi-Bin Batching
idea for use as a research baseline.  It is NOT the official implementation
of any published work.  See docs/baselines.md for provenance notes.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List


from ..core.action import Action
from ..core.types import ObservableRequest, ObservableState
from .base import BasePolicy


class MultiBinBatchingPolicy(BasePolicy):
    name = "multi_bin_batching"

    def __init__(self, n_bins: int = 4, bin_edges: list | None = None) -> None:
        self.n_bins = n_bins
        # Default bin edges for predicted output tokens
        self.bin_edges = bin_edges or [32, 64, 128, 256]

    def _bin_id(self, predicted_output: int) -> int:
        for i, edge in enumerate(self.bin_edges):
            if predicted_output <= edge:
                return i
        return len(self.bin_edges)  # last bin = long outputs

    def select_action(self, state: ObservableState) -> Action:
        admit: dict[int, list[int]] = {g.gpu_id: [] for g in state.gpu_states}

        if not state.waiting_queue:
            return Action(admit=admit)

        # Group waiting requests into bins
        bins: Dict[int, List[ObservableRequest]] = defaultdict(list)
        for req in state.waiting_queue:
            bins[self._bin_id(req.predicted_output_tokens)].append(req)

        # Sort bins by bin_id (shorter outputs first)
        sorted_bin_ids = sorted(bins.keys())

        # Fill GPUs bin by bin: prefer to fill a GPU entirely from one bin
        for bin_id in sorted_bin_ids:
            bin_reqs = bins[bin_id]
            for req in bin_reqs:
                best_gpu = None
                best_score = float("inf")
                for gpu in state.gpu_states:
                    if self._feasible_on_gpu(gpu, req):
                        # Prefer GPU that already has requests from this bin
                        # (reduces length variance within the batch)
                        load = len(gpu.active_request_ids)
                        score = load
                        if score < best_score:
                            best_score = score
                            best_gpu = gpu
                if best_gpu is not None:
                    admit[best_gpu.gpu_id].append(req.request_id)
                    best_gpu.active_request_ids.append(req.request_id)
                    best_gpu.current_kv_tokens += req.prompt_tokens

        return Action(admit=admit)
