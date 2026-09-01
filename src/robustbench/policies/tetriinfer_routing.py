"""
Inter-instance decode routing for `tetriinfer_paper_reimplementation`: the
"dispatcher" component (paper §3.3.4) that decentralized-ly routes a
freshly-prefilled request to one of potentially many decode-role GPUs.

Algorithm (paper-specified; see docs/tetriinfer_reference.md section A):
  1. Partition decode instances into alpha (enough predicted resources to
     run this request's decode phase) / beta (not enough).
  2. Power-of-two choice: sample exactly two instances from alpha
     (uniformly, without replacement; seeded, deterministic).
  3. Tie-break: pick whichever of the two would leave the LOWER
     heavy:light decode ratio on that instance -- the paper's own stated
     objective ("establish the lowest average ratio of heavy decode:light
     decode... spread heavy decode requests evenly", §5.2.3), used here
     directly as the scoring function since the paper does not give a
     separate closed-form "interference score" formula (see
     docs/tetriinfer_reference.md section E.2 -- this is this project's
     own disclosed operationalization of "least interference," not an
     invented, unrelated criterion).

If |alpha| == 0: no decode instance can currently accept this request; the
caller must leave it in the bridge queue for a later round (mirrors this
project's established "stop at first non-admittable, don't invent
behavior" convention). If |alpha| == 1: no comparison to make, route there
directly (power-of-two needs two candidates).
"""
from __future__ import annotations

import random
from typing import Callable, List, Optional

from ..core.types import ObservableGPUState

# Paper §5 (evaluation setup, consistent with the dispatcher's own stated
# objective in §5.2.3): "Decode requests with more than 128 tokens are
# categorized as heavy as ShareGPT answers' median length is 128."
HEAVY_DECODE_THRESHOLD_TOKENS = 128
# Paper §5 (evaluation setup): "prefill requests that have more than 512
# prompt tokens are categorized as heavy." Not used by any scheduling
# decision in this module -- provided for sanity-check workloads/tests
# that want to replicate the paper's own heavy/light workload taxonomy.
HEAVY_PREFILL_THRESHOLD_TOKENS = 512


def is_heavy_decode(predicted_output_tokens: int) -> bool:
    return predicted_output_tokens > HEAVY_DECODE_THRESHOLD_TOKENS


def _heavy_light_counts(gpu: ObservableGPUState) -> tuple:
    heavy = sum(1 for r in gpu.active_requests_info if is_heavy_decode(r.predicted_output_tokens))
    light = len(gpu.active_requests_info) - heavy
    return heavy, light


def _ratio_if_added(gpu: ObservableGPUState, predicted_heavy: bool) -> float:
    heavy, light = _heavy_light_counts(gpu)
    if predicted_heavy:
        heavy += 1
    else:
        light += 1
    if light == 0:
        # All-heavy instance: maximally imbalanced: treat as the worst
        # (largest) ratio so a router always prefers a mixed instance.
        return float(heavy)
    return heavy / light


class PowerOfTwoDecodeRouter:
    """Stateful only in its own RNG stream (seeded, deterministic) --
    holds no per-request state; callers own request-to-instance
    assignment stickiness (see tetriinfer_paper_reimplementation.py's
    `_decode_assignment`)."""

    def __init__(self, seed: int = 0) -> None:
        self._rng = random.Random(seed)

    def select_decode_gpu(
        self,
        candidate_gpus: List[ObservableGPUState],
        predicted_heavy: bool,
        fits_fn: Callable[[ObservableGPUState], bool],
    ) -> Optional[int]:
        """Returns the chosen gpu_id, or None if no candidate currently
        has enough predicted resources (the alpha set is empty)."""
        alpha = sorted((g for g in candidate_gpus if fits_fn(g)), key=lambda g: g.gpu_id)
        if not alpha:
            return None
        if len(alpha) == 1:
            return alpha[0].gpu_id

        i, j = sorted(self._rng.sample(range(len(alpha)), 2))
        cand_a, cand_b = alpha[i], alpha[j]

        ratio_a = _ratio_if_added(cand_a, predicted_heavy)
        ratio_b = _ratio_if_added(cand_b, predicted_heavy)
        if ratio_a != ratio_b:
            return cand_a.gpu_id if ratio_a < ratio_b else cand_b.gpu_id
        # Deterministic tie-break: lower gpu_id (consistent with this
        # codebase's established tie-breaking convention -- see
        # policies/tie_breaking.py).
        return min(cand_a.gpu_id, cand_b.gpu_id)
