"""Canonical external-workload record schema (Layer 1: source observations).

Design doc: docs/EXTERNAL_WORKLOAD_CANONICAL_SCHEMA.md,
docs/WORKLOAD_PROVENANCE_LAYERS.md.

`ExternalWorkloadRecord` is the ONE normalized representation every public-trace or
API-derived-workload adapter converts into. It holds only what an adapter directly
read or trivially reshaped from its source (Layer 1) -- never a scheduler-pressure
derivative (Layer 2) and never a benchmark-synthesized field like an assigned SLO or
tenant class (Layer 3). Every field that is not directly observed from the source
must be `None`, and its provenance must be recorded honestly in `field_provenance` --
never silently inferred or fabricated. See PROVENANCE_* constants below.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# Field-provenance vocabulary. Every field on ExternalWorkloadRecord that is
# non-None must have a matching entry in `field_provenance` using one of these.
PROVENANCE_SOURCE_OBSERVED = "SOURCE_OBSERVED"
PROVENANCE_DETERMINISTIC_DERIVED = "DETERMINISTIC_DERIVED"
PROVENANCE_SYNTHESIZED_IMPUTED = "SYNTHESIZED_IMPUTED"
PROVENANCE_UNAVAILABLE = "UNAVAILABLE"

VALID_PROVENANCE_VALUES = frozenset({
    PROVENANCE_SOURCE_OBSERVED,
    PROVENANCE_DETERMINISTIC_DERIVED,
    PROVENANCE_SYNTHESIZED_IMPUTED,
    PROVENANCE_UNAVAILABLE,
})

SCHEMA_VERSION = 1


@dataclass
class ExternalWorkloadRecord:
    # --- IDENTITY ---
    source_dataset: str
    source_version: str
    source_record_id: str
    derived_record_id: str
    source_license: str
    source_url: str
    conversion_version: str

    # --- TIMING ---
    arrival_time_s: float | None = None
    interarrival_time_s: float | None = None
    session_relative_time_s: float | None = None
    # one of "real", "anonymized_shifted", "synthetic"
    timestamp_provenance_kind: str | None = None

    # --- REQUEST SHAPE ---
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    context_growth_tokens: int | None = None
    sequence_position: int | None = None

    # --- SESSION / TENANT ---
    session_id: str | None = None
    tenant_id: str | None = None
    synthetic_tenant_assigned: bool = False
    model_class: str | None = None

    # --- KV / REUSE ---
    prefix_reuse_info: str | None = None
    kv_block_hash: str | None = None
    reuse_group_id: str | None = None
    reuse_confidence_source: str | None = None

    # --- TASK ---
    task_category: str | None = None
    interaction_category: str | None = None  # conversation / api / agent / tool
    model_family: str | None = None

    # Free-form source-specific extras that don't map to a canonical field, plus
    # per-field provenance. Both are always present (possibly empty).
    extra: dict[str, Any] = field(default_factory=dict)
    field_provenance: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def validate(self) -> list[str]:
        """Returns a list of validation problems (empty if valid). Does not raise --
        callers decide whether a problem is fatal for their use case."""
        problems: list[str] = []
        for f in (
            "source_dataset", "source_version", "source_record_id", "derived_record_id",
            "source_license", "source_url", "conversion_version",
        ):
            if not getattr(self, f):
                problems.append(f"identity field '{f}' must be non-empty")
        for name, value in asdict(self).items():
            if name in ("extra", "field_provenance"):
                continue
            if value is None:
                continue
            if name in ("source_dataset", "source_version", "source_record_id", "derived_record_id",
                        "source_license", "source_url", "conversion_version", "synthetic_tenant_assigned"):
                continue
            if name not in self.field_provenance:
                problems.append(f"field '{name}' is set but has no field_provenance entry")
            elif self.field_provenance[name] not in VALID_PROVENANCE_VALUES:
                problems.append(f"field '{name}' has invalid provenance '{self.field_provenance[name]}'")
        for name, prov in self.field_provenance.items():
            if prov not in VALID_PROVENANCE_VALUES:
                problems.append(f"field_provenance['{name}']='{prov}' is not a valid provenance value")
        if self.timestamp_provenance_kind is not None and self.timestamp_provenance_kind not in (
            "real", "anonymized_shifted", "synthetic",
        ):
            problems.append(f"invalid timestamp_provenance_kind: {self.timestamp_provenance_kind!r}")
        if self.arrival_time_s is not None and self.timestamp_provenance_kind is None:
            problems.append("arrival_time_s is set but timestamp_provenance_kind is missing")
        for name in ("arrival_time_s", "interarrival_time_s", "session_relative_time_s"):
            value = getattr(self, name)
            if value is not None and value < 0:
                problems.append(f"field '{name}' must be non-negative")
        for name in ("input_tokens", "output_tokens", "total_tokens", "context_growth_tokens", "sequence_position"):
            value = getattr(self, name)
            if value is not None and value < 0:
                problems.append(f"field '{name}' must be non-negative")
        return problems
