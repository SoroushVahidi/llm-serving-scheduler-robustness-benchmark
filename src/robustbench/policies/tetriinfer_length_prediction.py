"""
Length prediction abstraction for `tetriinfer_paper_reimplementation`.

TetriInfer's own length predictor is a fine-tuned OPT-125M sequence
classifier trained on 75K ShareGPT prompt/response pairs (see
docs/tetriinfer_reference.md section E.1) -- an ML model whose learned
weights and training run cannot be reproduced. This module implements the
REPRODUCIBLE part of the paper's design (fixed-size bucket labeling of a
token-count range; using the predicted range's lower bound for resource
estimates) on top of this project's own existing
`ObservableRequest.predicted_output_tokens` field, with no external LLM or
paid API dependency anywhere in this module.

Strict no-leakage boundary
--------------------------
Every function/method here accepts a `predicted_output_tokens` value
(this project's existing non-oracle prediction field) -- never
`actual_output_tokens`. `actual_output_tokens` is not even present on
`ObservableRequest` (see core/types.py's `ObservableRequest` vs. `Request`
docstrings), so accidental access from inside a policy's `select_action`
is structurally impossible. Tests that deliberately want to compare
against ground truth (an oracle upper bound) pass `actual_output_tokens`
into `LengthPredictor.predict` explicitly and only from test code, never
from `tetriinfer_paper_reimplementation.py` itself -- mirroring this
project's existing `policies/oracle.py` convention of keeping oracle
access textually separate from every deployable policy.
"""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class LengthPrediction:
    """A predicted output-length range, mirroring TetriInfer's own
    bucket-based predictor output (paper §3.3.2): a request's predicted
    length is used only as a `[lower_bound, upper_bound)` range by
    callers, never as a false-precision point estimate -- matching the
    paper's own "regardless of granularity, it's easy to calculate
    resource usage's upper and lower bound" design.
    """
    lower_bound: int
    upper_bound: int
    bucket_index: int

    @property
    def point_estimate(self) -> int:
        """Paper §5.2.3: reserve-static/reserve-dynamic resource estimates
        use the predicted range's LOWER bound, not the midpoint or upper
        bound -- this property exists so callers never have to re-derive
        that choice themselves."""
        return self.lower_bound


class LengthPredictor:
    """Deterministic, non-ML length predictor.

    Reproduces the paper's bucket-labeling math exactly: granularity `g`
    buckets a token count `t` into bucket index `t // g`, covering the
    range `[bucket_index * g, (bucket_index + 1) * g)` -- identical to the
    paper's own description ("using a granularity of 100, responses with
    token lengths between 0-200 are labeled with 0, 200-400 are labeled
    with 1, and so on" -- example uses 2x granularity boundaries per label
    for that specific granularity=100 illustration; the general rule
    reproduced here, `[i*g, (i+1)*g)`, matches the paper's own general
    definition).

    `granularity=0` disables bucketing (the prediction IS the point
    estimate; `lower_bound == upper_bound`) -- useful for oracle-style
    tests. The paper itself notes granularity=1 degenerates to "predicting
    an exact number of tokens, which is not practical" -- granularity=0 is
    this project's own explicit "no bucketing" sentinel, not a value the
    paper discusses.

    mode="exact": use the given `predicted_output_tokens` source value
        as-is before bucketing (this project's own existing non-oracle
        prediction field, or -- only in oracle-comparison tests --
        `actual_output_tokens` passed in explicitly by the test).
    mode="noisy": apply a bounded, seeded perturbation to the source value
        before bucketing, to study TetriInfer's own explicitly-discussed
        sensitivity to prediction error (the paper itself compares
        "actual accuracy" (74.9%) against "ideal accuracy" (100%) for
        reserve-static/reserve-dynamic in Figure 18).
    """

    def __init__(
        self,
        granularity: int = 200,
        mode: str = "exact",
        noise_std_tokens: float = 0.0,
        seed: int = 0,
    ) -> None:
        if granularity < 0:
            raise ValueError(f"granularity must be non-negative, got {granularity}")
        if mode not in ("exact", "noisy"):
            raise ValueError(f"mode must be 'exact' or 'noisy', got {mode!r}")
        if noise_std_tokens < 0:
            raise ValueError(f"noise_std_tokens must be non-negative, got {noise_std_tokens}")
        self.granularity = granularity
        self.mode = mode
        self.noise_std_tokens = noise_std_tokens
        self._rng = random.Random(seed)

    def predict(self, source_tokens: int) -> LengthPrediction:
        """`source_tokens` must be a non-oracle prediction source (this
        project's `predicted_output_tokens`), except in tests that
        deliberately pass `actual_output_tokens` to construct an oracle
        comparison baseline."""
        estimate = source_tokens
        if self.mode == "noisy" and self.noise_std_tokens > 0:
            noise = self._rng.gauss(0.0, self.noise_std_tokens)
            estimate = max(1, round(source_tokens + noise))

        if self.granularity <= 0:
            return LengthPrediction(lower_bound=estimate, upper_bound=estimate, bucket_index=estimate)

        bucket_index = estimate // self.granularity
        lower_bound = bucket_index * self.granularity
        upper_bound = lower_bound + self.granularity
        return LengthPrediction(lower_bound=lower_bound, upper_bound=upper_bound, bucket_index=bucket_index)
