"""Frozen RQ3 synthetic stress panel.

Four families, each a single, already-existing, already-parameterized
generator preset from `robustbench.workloads.synthetic` -- none of these
parameters were changed for RQ3; they were frozen in that module before
this analysis existed (Phase 1 engineering presets), which is exactly why
none of them can have been tuned to produce an RQ3 outcome.

Each family is chosen to represent one clear, source-native mechanism
(docs/RQ3_SYNTHETIC_TO_REAL_PROTOCOL_20260903.md section on family
selection), not an arbitrary parameter sweep:

- ``burst_arrival``          -- arrival-process burstiness/clustering.
- ``heavy_tail_service``     -- heavy-tailed prompt+output service demand.
- ``decode_length_skew``     -- short-prompt/long-output length skew.
- ``priority_slo_heterogeneity`` -- spread of the synthesized SLO/priority
  class distribution (the same class-based synthesis scheme used for the
  real Phase-12 windows' scheduler-facing fields).

"Correlated long prompts + tight deadlines" (a fifth candidate mechanism
named in the task) was deliberately NOT added: no existing frozen preset
implements it, and adding one now would require choosing new parameters
after this task already exists -- exactly what section D of the protocol
forbids. Logged here, not silently dropped.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Tuple

from ..core.types import Request
from ..workloads.synthetic import (
    make_bursty_trace,
    make_decode_heavy_trace,
    make_heavy_tail_trace,
    make_mixed_slo_trace,
)

#: (family_id, generator_callable, mechanism, one-line rationale) -- frozen
#: order, frozen membership. Do not add/remove/reorder after seeing outcomes.
SYNTHETIC_FAMILIES: List[Tuple[str, Callable[[int], List[Request]], str, str]] = [
    (
        "burst_arrival",
        make_bursty_trace,
        "burst_arrival",
        "Bursty Poisson-mixture arrivals (burst_factor=8.0, burst_fraction=0.15) "
        "stress arrival-process clustering, independent of token-length effects.",
    ),
    (
        "heavy_tail_service",
        make_heavy_tail_trace,
        "heavy_tailed_service_demand",
        "Pareto prompt+output token distributions stress heavy-tailed per-request "
        "service demand, independent of arrival-process shape (kept Poisson).",
    ),
    (
        "decode_length_skew",
        make_decode_heavy_trace,
        "prompt_output_length_skew",
        "Short prompts (mean 32) / long outputs (mean 512) stress decode-time "
        "scheduling order and KV growth, the opposite skew direction from "
        "prefill-heavy traffic.",
    ),
    (
        "priority_slo_heterogeneity",
        make_mixed_slo_trace,
        "priority_slo_heterogeneity",
        "Three-class (tight/medium/loose) SLO-slack and priority mixture stresses "
        "deadline/priority-aware scheduling order, independent of token-length or "
        "arrival-process shape (both kept at Stage-0-typical moderate values).",
    ),
]

FAMILY_IDS: List[str] = [f[0] for f in SYNTHETIC_FAMILIES]
FAMILY_BY_ID = {f[0]: f for f in SYNTHETIC_FAMILIES}

#: Frozen before any cell was executed (docs/RQ3_SYNTHETIC_TO_REAL_PROTOCOL_20260903.md).
N_SEEDS_PER_FAMILY = 5
SEEDS: List[int] = list(range(N_SEEDS_PER_FAMILY))  # [0, 1, 2, 3, 4]

#: Minimal pair per the protocol -- KNEE (policy-neutral saturation onset) and
#: HIGH_PRESSURE (1.5x lambda_ref, the same multiplier RQ6 and
#: ranking_portability.calibration use for their own HIGH_PRESSURE region).
LOAD_REGIONS = ("KNEE", "HIGH_PRESSURE")
REGION_MULTIPLIERS = {"KNEE": 1.0, "HIGH_PRESSURE": 1.5}

#: The 11 PRIMARY ranking-portability policies (docs/RANKING_PORTABILITY_POLICY_PANEL.md),
#: used verbatim -- no smaller "pilot panel" substitution (the pilot uses this
#: same panel, just fewer seeds/cells; see the protocol doc).
PRIMARY_POLICIES = (
    "fifo",
    "edf",
    "least_laxity_first",
    "estimated_service_time_first",
    "weighted_fair_share",
    "kv_constrained_online",
    "vllm_faithful",
    "vllm_chunked_prefill_faithful",
    "sarathi_faithful",
    "slai_faithful",
    "admission_control",
)

PRIMARY_METRIC = "arrival_normalized_weighted_goodput"

#: Frozen before any cell was executed -- a metric pair/region-condition is
#: skipped (never zero-imputed) when fewer than this many PRIMARY policies
#: have a defined value on both sides of a comparison.
MIN_COMMON_POLICIES = 6


def generate_family_window(family_id: str, seed: int) -> List[Request]:
    """Generate one synthetic replicate for `family_id` at `seed`.

    Deterministic: same (family_id, seed) always returns bit-identical
    requests, because `robustbench.workloads.synthetic.generate_workload`
    seeds a fresh `numpy.random.default_rng(seed)` and every family here is
    a plain call to one existing preset generator with no external state.
    """
    if family_id not in FAMILY_BY_ID:
        raise KeyError(f"Unknown RQ3 synthetic family: {family_id!r}")
    _, generator, _, _ = FAMILY_BY_ID[family_id]
    return generator(seed=seed)
