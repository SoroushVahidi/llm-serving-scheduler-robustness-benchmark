"""Layer 3: benchmark synthesis -- turns a window of Layer-1
`ExternalWorkloadRecord`s into simulator-runnable `Request` objects.

None of this project's three Stage-0 sources (Azure 2024, Bailian/Qwen,
BurstGPT) natively carries `priority`, `slo_deadline`, or
`predicted_output_tokens` (see docs/DATA_FIELD_PROVENANCE.md). Every value
this module adds is a documented, versioned, deterministically-seeded
overlay -- never presented as source-native. Per
docs/DATA_FIELD_PROVENANCE.md item 1, the synthesis rule is documented here
(not just in code comments) and versioned via `SYNTHESIS_VERSION`; per item
3, any headline result depending materially on a synthesized field (e.g.
`edf`, which needs `slo_deadline`) should be checked against an alternative
synthesis rule before being treated as a primary finding -- not done for the
Stage-0 discriminability pilot itself, which only needs the six frozen
policies to execute and produce a primary ANWG metric.

Synthesis rule (`stage0_synthesis_v1`), frozen before any Stage-0 cell is run:

- `predicted_output_tokens`: log-normal multiplicative noise around
  `actual_output_tokens` (reusing `workloads.distributions.prediction_noise`,
  the same mechanism already used for this project's synthetic traces),
  relative error 0.20, seeded per-window so re-running the same window with
  the same seed reproduces byte-identical predictions.
- `priority`: constant 1.0 for every request. None of the three Stage-0
  sources exposes a native tenant/priority signal, and inventing a
  distribution would bias `weighted_fair_share`-style policies in a way this
  project cannot justify from source data; Stage-0's 6-policy panel does not
  include a fairness policy, so uniform priority is a safe, honest default
  for this pilot.
- `slo_deadline`: `arrival_time + slo_multiplier * service_time_proxy`, where
  `service_time_proxy = prefill_token_cost * prompt_tokens +
  decode_token_cost * predicted_output_tokens` (a simple linear proxy, not a
  real backend measurement) and `slo_multiplier = 20.0` (generous, chosen
  before any policy-under-study result was observed, to avoid a trivially
  degenerate SLO regime at PRE_KNEE).
- `class_id`: fixed `"stage0_uniform"` for every request (no native class
  signal; distinguishes these rows from the synthetic generator's
  tight/medium/loose classes at a glance).

Every synthesized field is why this module lives under `workloads.external`
but produces `core.types.Request`, not `ExternalWorkloadRecord` -- it is
explicitly a Layer-1 -> Layer-3 boundary crossing, not a Layer-1 adapter.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import List, Sequence

import numpy as np

from ...core.types import Request
from ..distributions import prediction_noise
from .schema import ExternalWorkloadRecord

SYNTHESIS_VERSION = "stage0_synthesis_v1"

PREDICTION_NOISE_RELATIVE_ERROR = 0.20
UNIFORM_PRIORITY = 1.0
UNIFORM_CLASS_ID = "stage0_uniform"
SLO_MULTIPLIER = 20.0
PREFILL_TOKEN_COST_S = 0.0004   # documented proxy seconds/prompt-token
DECODE_TOKEN_COST_S = 0.02      # documented proxy seconds/output-token


@dataclass
class SynthesisManifestEntry:
    synthesis_version: str
    window_id: str
    seed: int
    n_requests: int
    n_records_dropped_invalid: int
    prediction_noise_relative_error: float
    uniform_priority: float
    uniform_class_id: str
    slo_multiplier: float
    prefill_token_cost_s: float
    decode_token_cost_s: float

    def to_dict(self) -> dict:
        return asdict(self)


def _is_valid_for_synthesis(r: ExternalWorkloadRecord) -> bool:
    return (
        r.arrival_time_s is not None
        and r.input_tokens is not None
        and r.input_tokens > 0
        and r.output_tokens is not None
        and r.output_tokens > 0
    )


def synthesize_requests_from_window(
    records: Sequence[ExternalWorkloadRecord],
    *,
    window_id: str,
    seed: int,
) -> tuple[List[Request], SynthesisManifestEntry]:
    """Converts one window's Layer-1 records into simulator `Request`s.

    Records are re-sorted by `arrival_time_s` and re-based so the window's
    first arrival is at t=0 (matching the convention already used by
    `real_window_construction.apply_load_factor`-style code in the source
    lineage repos). Records failing `_is_valid_for_synthesis` (missing
    arrival time or non-positive token counts) are dropped and counted.
    """
    valid = [r for r in records if _is_valid_for_synthesis(r)]
    n_dropped = len(records) - len(valid)
    valid.sort(key=lambda r: r.arrival_time_s)

    rng = np.random.default_rng(seed)
    if not valid:
        return [], SynthesisManifestEntry(
            synthesis_version=SYNTHESIS_VERSION,
            window_id=window_id,
            seed=seed,
            n_requests=0,
            n_records_dropped_invalid=n_dropped,
            prediction_noise_relative_error=PREDICTION_NOISE_RELATIVE_ERROR,
            uniform_priority=UNIFORM_PRIORITY,
            uniform_class_id=UNIFORM_CLASS_ID,
            slo_multiplier=SLO_MULTIPLIER,
            prefill_token_cost_s=PREFILL_TOKEN_COST_S,
            decode_token_cost_s=DECODE_TOKEN_COST_S,
        )

    t0 = valid[0].arrival_time_s
    actual_output = np.array([r.output_tokens for r in valid], dtype=float)
    predicted_output = prediction_noise(rng, actual_output, PREDICTION_NOISE_RELATIVE_ERROR)

    requests: List[Request] = []
    for i, r in enumerate(valid):
        arrival = float(r.arrival_time_s) - float(t0)
        arrival = max(arrival, 0.0)
        predicted = int(predicted_output[i])
        service_proxy = (
            PREFILL_TOKEN_COST_S * r.input_tokens + DECODE_TOKEN_COST_S * predicted
        )
        req = Request(
            request_id=i,
            arrival_time=arrival,
            prompt_tokens=int(r.input_tokens),
            predicted_output_tokens=predicted,
            actual_output_tokens=int(r.output_tokens),
            slo_deadline=arrival + SLO_MULTIPLIER * service_proxy,
            priority=UNIFORM_PRIORITY,
            class_id=UNIFORM_CLASS_ID,
        )
        requests.append(req)

    manifest = SynthesisManifestEntry(
        synthesis_version=SYNTHESIS_VERSION,
        window_id=window_id,
        seed=seed,
        n_requests=len(requests),
        n_records_dropped_invalid=n_dropped,
        prediction_noise_relative_error=PREDICTION_NOISE_RELATIVE_ERROR,
        uniform_priority=UNIFORM_PRIORITY,
        uniform_class_id=UNIFORM_CLASS_ID,
        slo_multiplier=SLO_MULTIPLIER,
        prefill_token_cost_s=PREFILL_TOKEN_COST_S,
        decode_token_cost_s=DECODE_TOKEN_COST_S,
    )
    return requests, manifest
