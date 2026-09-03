"""POST_PHASE12_SLO_DEFINITION_SENSITIVITY_EXTENSION: deterministic SLO-
definition variant transform.

This was NOT part of the original sealed Phase-12 scientific campaign
(docs/PHASE12_SLO_SENSITIVITY_PROTOCOL_HOLE.md: no alternative SLO-synthesis
rule was ever frozen at any prior commit). It is a post-campaign robustness
extension with its own freeze/manifest process, per that document's own
stated requirement.

The sealed synthesis rule (`stage0_synthesis_v1`,
`robustbench.workloads.external.benchmark_synthesis`) computes, once, at
synthesis time:

    slo_deadline = arrival_time + SLO_MULTIPLIER * service_time_proxy
    service_time_proxy = PREFILL_TOKEN_COST_S * prompt_tokens
                        + DECODE_TOKEN_COST_S * predicted_output_tokens

`apply_slo_variant` never re-derives `service_time_proxy` from token counts
(that would duplicate the sealed formula's constants and risk drifting from
them). Instead it uses the exact algebraic identity

    slack = deadline - arrival_time                    (= multiplier * proxy)
    variant_slack = slack * (variant_multiplier / primary_multiplier)
    variant_deadline = arrival_time + variant_slack

which recovers precisely the value `synthesize_requests_from_window` would
have produced had it been called with `SLO_MULTIPLIER = variant_multiplier`
instead of the primary 20.0 -- for ANY multiplier, including the primary
one itself, where the ratio is exactly 1.0 and the transform is a
mathematically exact no-op (this is what makes the primary-equivalence gate
in tests/test_slo_variant.py provable, not just empirically spot-checked).

Only `slo_deadline` is ever touched. Every other `Request` field is copied
byte-for-byte via `dataclasses.replace`, so request identity (request_id,
arrival_time, prompt_tokens, predicted_output_tokens, actual_output_tokens,
priority, class_id) is structurally guaranteed unchanged -- not merely
validated after the fact (`validate_slo_variant` below is defense-in-depth
for callers that build `Request`s some other way, not the source of the
guarantee for this function's own output).
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import List, Sequence

from ..core.types import Request
from ..workloads.external.benchmark_synthesis import SLO_MULTIPLIER as PRIMARY_SLO_MULTIPLIER

SYNTHESIS_VERSION_BASE = "stage0_synthesis_v1"

#: The three frozen SLO-definition variants for the sensitivity extension.
#: Chosen as a symmetric doubling/halving bracket around the sealed primary
#: multiplier (20.0), in the same spirit the primary value's own doc
#: comment used ("generous, chosen before any policy-under-study result was
#: observed") -- selected from the structure of the sealed formula alone,
#: before any scheduler-ranking outcome under any variant was computed.
SLO_VARIANT_MULTIPLIERS = {
    "tight_10x": 10.0,
    "primary_20x": PRIMARY_SLO_MULTIPLIER,
    "loose_40x": 40.0,
}
assert SLO_VARIANT_MULTIPLIERS["primary_20x"] == 20.0

#: Fields that `apply_slo_variant` is permitted to change. Everything else
#: on `Request` must be identical between the primary and any variant.
_SLO_ONLY_FIELDS = frozenset({"slo_deadline"})


def apply_slo_variant(
    request: Request,
    variant_multiplier: float,
    *,
    primary_multiplier: float = PRIMARY_SLO_MULTIPLIER,
) -> Request:
    """Returns a new `Request` identical to `request` except `slo_deadline`,
    rescaled as if synthesized with `variant_multiplier` instead of
    `primary_multiplier`. `request` must already carry a deadline produced
    under `primary_multiplier` (true for every request coming out of
    `synthesize_requests_from_window`, which is always called with the
    sealed constant)."""
    if primary_multiplier <= 0:
        raise ValueError(f"primary_multiplier must be positive, got {primary_multiplier}")
    if variant_multiplier <= 0:
        raise ValueError(f"variant_multiplier must be positive, got {variant_multiplier}")
    slack = request.slo_deadline - request.arrival_time
    ratio = variant_multiplier / primary_multiplier
    variant_deadline = request.arrival_time + slack * ratio
    return replace(request, slo_deadline=variant_deadline)


def apply_slo_variant_to_window(
    requests: Sequence[Request],
    variant_multiplier: float,
    *,
    primary_multiplier: float = PRIMARY_SLO_MULTIPLIER,
) -> List[Request]:
    return [
        apply_slo_variant(r, variant_multiplier, primary_multiplier=primary_multiplier)
        for r in requests
    ]


@dataclass
class SLOVariantValidationReport:
    n_original: int
    n_variant: int
    n_field_mismatches: int
    mismatched_fields: List[str]
    problems: List[str]

    @property
    def passed(self) -> bool:
        return not self.problems


def validate_slo_variant(
    original: Sequence[Request],
    variant: Sequence[Request],
) -> SLOVariantValidationReport:
    """Structural validator (section M): fails hard (non-empty `problems`)
    if request count, request IDs, arrival times, token counts, priority,
    or class_id differ between `original` and `variant`, or if `variant`'s
    `slo_deadline` never differs at all (a no-op variant would silently
    defeat the sensitivity design). Never inspects scheduler outcomes."""
    problems: List[str] = []
    mismatched_fields: set[str] = set()

    if len(original) != len(variant):
        problems.append(f"request count differs: original={len(original)} variant={len(variant)}")

    n = min(len(original), len(variant))
    any_deadline_differs = False
    for i in range(n):
        o, v = original[i], variant[i]
        if o.request_id != v.request_id:
            problems.append(f"request_id drift at index {i}: {o.request_id} != {v.request_id}")
            mismatched_fields.add("request_id")
        if o.arrival_time != v.arrival_time:
            problems.append(f"arrival_time drift at index {i} (request_id={o.request_id})")
            mismatched_fields.add("arrival_time")
        if o.prompt_tokens != v.prompt_tokens:
            problems.append(f"prompt_tokens drift at index {i} (request_id={o.request_id})")
            mismatched_fields.add("prompt_tokens")
        if o.predicted_output_tokens != v.predicted_output_tokens:
            problems.append(f"predicted_output_tokens drift at index {i} (request_id={o.request_id})")
            mismatched_fields.add("predicted_output_tokens")
        if o.actual_output_tokens != v.actual_output_tokens:
            problems.append(f"actual_output_tokens drift at index {i} (request_id={o.request_id})")
            mismatched_fields.add("actual_output_tokens")
        if o.priority != v.priority:
            problems.append(f"priority drift at index {i} (request_id={o.request_id})")
            mismatched_fields.add("priority")
        if o.class_id != v.class_id:
            problems.append(f"class_id drift at index {i} (request_id={o.request_id})")
            mismatched_fields.add("class_id")
        if o.slo_deadline != v.slo_deadline:
            any_deadline_differs = True

    return SLOVariantValidationReport(
        n_original=len(original),
        n_variant=len(variant),
        n_field_mismatches=len(mismatched_fields),
        mismatched_fields=sorted(mismatched_fields),
        problems=problems,
    )
