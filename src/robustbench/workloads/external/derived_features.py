"""Layer 2: deterministic scheduler-pressure derivatives computed FROM Layer-1
`ExternalWorkloadRecord`s. See docs/WORKLOAD_PROVENANCE_LAYERS.md.

These are proxies for benchmark pressure axes, not the axes themselves -- computing
one does not mean the source trace actually exercises that axis meaningfully (see
docs/PUBLIC_TRACE_PRESSURE_AXIS_MAPPING.md for the DIRECT/DERIVABLE/SYNTHETIC_ONLY/
UNAVAILABLE classification per trace). Every value here is UNAVAILABLE (None) rather
than guessed when its required Layer-1 inputs are missing.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .schema import (
    PROVENANCE_DETERMINISTIC_DERIVED,
    PROVENANCE_UNAVAILABLE,
    ExternalWorkloadRecord,
)

DERIVATION_VERSION = "derived_features_v1"

# request_size_category thresholds (input_tokens), a fixed documented convention --
# not tuned against any scheduler outcome.
_SIZE_SMALL_MAX = 256
_SIZE_MEDIUM_MAX = 2048
LONG_CONTEXT_TOKEN_THRESHOLD = 8192


@dataclass
class PressureDerivatives:
    derived_record_id: str
    derivation_version: str = DERIVATION_VERSION

    arrival_pressure_proxy: float | None = None  # 1 / interarrival_time_s
    request_size_category: str | None = None  # small / medium / large / unavailable
    prefill_pressure_proxy: float | None = None  # normalized input_tokens
    decode_pressure_proxy: float | None = None  # normalized output_tokens
    kv_reuse_proxy: float | None = None  # 1.0 if a reuse_group_id repeats in-session, else 0.0
    tenant_skew_proxy: float | None = None  # requires a tenant/session distribution, computed at corpus level
    burstiness_feature: float | None = None  # coefficient of variation of interarrival times within a session
    long_context_flag: bool | None = None  # total_tokens >= LONG_CONTEXT_TOKEN_THRESHOLD

    field_provenance: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _mark(pd: PressureDerivatives, field_name: str, value: Any, kind: str) -> None:
    setattr(pd, field_name, value)
    pd.field_provenance[field_name] = kind


def derive_record_pressure_features(record: ExternalWorkloadRecord) -> PressureDerivatives:
    """Per-record derivations that don't require corpus-level context (session
    grouping is handled separately by derive_session_pressure_features)."""
    pd = PressureDerivatives(derived_record_id=record.derived_record_id)

    if record.interarrival_time_s is not None and record.interarrival_time_s > 0:
        _mark(pd, "arrival_pressure_proxy", 1.0 / record.interarrival_time_s, PROVENANCE_DETERMINISTIC_DERIVED)
    else:
        _mark(pd, "arrival_pressure_proxy", None, PROVENANCE_UNAVAILABLE)

    if record.input_tokens is not None:
        if record.input_tokens <= _SIZE_SMALL_MAX:
            category = "small"
        elif record.input_tokens <= _SIZE_MEDIUM_MAX:
            category = "medium"
        else:
            category = "large"
        _mark(pd, "request_size_category", category, PROVENANCE_DETERMINISTIC_DERIVED)
        _mark(pd, "prefill_pressure_proxy", float(record.input_tokens) / _SIZE_MEDIUM_MAX, PROVENANCE_DETERMINISTIC_DERIVED)
    else:
        _mark(pd, "request_size_category", None, PROVENANCE_UNAVAILABLE)
        _mark(pd, "prefill_pressure_proxy", None, PROVENANCE_UNAVAILABLE)

    if record.output_tokens is not None:
        _mark(pd, "decode_pressure_proxy", float(record.output_tokens) / _SIZE_MEDIUM_MAX, PROVENANCE_DETERMINISTIC_DERIVED)
    else:
        _mark(pd, "decode_pressure_proxy", None, PROVENANCE_UNAVAILABLE)

    total = record.total_tokens
    if total is None and record.input_tokens is not None and record.output_tokens is not None:
        total = record.input_tokens + record.output_tokens
    if total is not None:
        _mark(pd, "long_context_flag", total >= LONG_CONTEXT_TOKEN_THRESHOLD, PROVENANCE_DETERMINISTIC_DERIVED)
    else:
        _mark(pd, "long_context_flag", None, PROVENANCE_UNAVAILABLE)

    if record.reuse_group_id is not None:
        _mark(pd, "kv_reuse_proxy", 1.0, PROVENANCE_DETERMINISTIC_DERIVED)
    else:
        _mark(pd, "kv_reuse_proxy", None, PROVENANCE_UNAVAILABLE)

    # Corpus-level derivations (tenant_skew_proxy, session-grouped burstiness) are
    # intentionally left UNAVAILABLE here -- see derive_session_pressure_features.
    _mark(pd, "tenant_skew_proxy", None, PROVENANCE_UNAVAILABLE)
    _mark(pd, "burstiness_feature", None, PROVENANCE_UNAVAILABLE)

    return pd


def derive_corpus_pressure_features(records: list[ExternalWorkloadRecord]) -> list[PressureDerivatives]:
    """Computes per-record derivations, then fills in the corpus-level ones
    (burstiness within a session, tenant skew across the corpus) deterministically
    from the same input list -- order of `records` does not affect the result."""
    by_id = {r.derived_record_id: derive_record_pressure_features(r) for r in records}

    sessions: dict[str, list[ExternalWorkloadRecord]] = {}
    for r in records:
        if r.session_id is not None:
            sessions.setdefault(r.session_id, []).append(r)
    for recs in sessions.values():
        interarrivals = [r.interarrival_time_s for r in recs if r.interarrival_time_s is not None]
        if len(interarrivals) >= 2:
            mean = sum(interarrivals) / len(interarrivals)
            if mean > 0:
                var = sum((x - mean) ** 2 for x in interarrivals) / len(interarrivals)
                cv = (var ** 0.5) / mean
                for r in recs:
                    _mark(by_id[r.derived_record_id], "burstiness_feature", cv, PROVENANCE_DETERMINISTIC_DERIVED)

    tenants: dict[str, int] = {}
    for r in records:
        if r.tenant_id is not None:
            tenants[r.tenant_id] = tenants.get(r.tenant_id, 0) + 1
    total_tenant_requests = sum(tenants.values())
    if total_tenant_requests > 0:
        for r in records:
            if r.tenant_id is not None:
                share = tenants[r.tenant_id] / total_tenant_requests
                _mark(by_id[r.derived_record_id], "tenant_skew_proxy", share, PROVENANCE_DETERMINISTIC_DERIVED)

    return [by_id[r.derived_record_id] for r in records]
