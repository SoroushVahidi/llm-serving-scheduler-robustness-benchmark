"""Mooncake (FAST'25 release) adapter.

Source: https://github.com/kvcache-ai/Mooncake, `FAST25-release/traces/`.
The repository carries Apache-2.0 via `LICENSE-APACHE`, but no trace-specific
data-license statement has been identified; public Benchmark v2 releases therefore
exclude raw Mooncake JSONL rows and raw `hash_ids`. Paper arXiv:2407.00079 /
USENIX FAST'25 Best Paper. See
docs/PUBLIC_TRACE_PRIMARY_SOURCE_AUDIT.md §C for the verified field list: JSONL with
`input_length`, `output_length`, `hash_ids` (remapped 512-token prefix-block hashes --
the one source in this project's candidate set with genuine KV-reuse ground truth).
The exact timestamp field name was NOT independently confirmed in the primary-source
audit (marked UNVERIFIED there) -- this adapter accepts a `timestamp_field` name at
construction so the caller states explicitly which key it is, rather than the adapter
guessing; if the field is absent from a row, arrival timing stays UNAVAILABLE rather
than silently defaulting to 0 or the row index. No tenant, model, SLO, or latency
field is confirmed present in this source -- all stay UNAVAILABLE.

Validated only against the small synthetic, schema-equivalent fixture at
configs/external_workloads/fixtures/mooncake_sample.jsonl, not the real trace files.
"""
from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from ..registry import register
from ..schema import (
    PROVENANCE_SOURCE_OBSERVED,
    PROVENANCE_UNAVAILABLE,
    ExternalWorkloadRecord,
)
from .base import TraceAdapter

SOURCE_URL = "https://github.com/kvcache-ai/Mooncake"
SOURCE_LICENSE = "Apache-2.0 repository license; no separate trace-specific license found"


@register("mooncake")
class MooncakeAdapter(TraceAdapter):
    source_dataset = "mooncake"
    source_version = "fast25-release"
    source_license = SOURCE_LICENSE
    source_url = SOURCE_URL
    conversion_version = "mooncake_adapter_v1"

    def __init__(self, timestamp_field: str | None = "timestamp"):
        self.timestamp_field = timestamp_field

    def inspect_source(self, path: Path) -> dict[str, Any]:
        with open(path) as f:
            first_line = f.readline()
        first_row = json.loads(first_line) if first_line else None
        return {"format": "jsonl", "first_row_keys": list(first_row.keys()) if first_row else [], "first_row": first_row}

    def convert_record(self, raw_row: dict[str, Any], index: int) -> ExternalWorkloadRecord:
        prov: dict[str, str] = {}

        def observed(field_name: str, value: Any) -> Any:
            if value is None:
                prov[field_name] = PROVENANCE_UNAVAILABLE
                return None
            prov[field_name] = PROVENANCE_SOURCE_OBSERVED
            return value

        arrival = observed("arrival_time_s", raw_row.get(self.timestamp_field) if self.timestamp_field else None)
        hash_ids = raw_row.get("hash_ids")
        reuse_group_id = observed("reuse_group_id", ",".join(str(h) for h in hash_ids) if hash_ids else None)
        source_record_id = str(raw_row.get("_natural_key", index))
        rec = ExternalWorkloadRecord(
            source_dataset=self.source_dataset,
            source_version=self.source_version,
            source_record_id=source_record_id,
            derived_record_id=self.derived_record_id(raw_row, index),
            source_license=self.source_license,
            source_url=self.source_url,
            conversion_version=self.conversion_version,
            arrival_time_s=float(arrival) / 1000.0 if arrival is not None else None,  # ms -> s
            timestamp_provenance_kind="real" if arrival is not None else None,
            input_tokens=int(v) if (v := observed("input_tokens", raw_row.get("input_length"))) is not None else None,
            output_tokens=int(v) if (v := observed("output_tokens", raw_row.get("output_length"))) is not None else None,
            reuse_group_id=reuse_group_id,
            reuse_confidence_source="mooncake_block_hash" if reuse_group_id is not None else None,
            interaction_category="agent" if hash_ids is not None else None,
        )
        if rec.timestamp_provenance_kind is not None:
            prov["timestamp_provenance_kind"] = PROVENANCE_SOURCE_OBSERVED
        prov["reuse_confidence_source"] = PROVENANCE_SOURCE_OBSERVED if reuse_group_id is not None else PROVENANCE_UNAVAILABLE
        prov["interaction_category"] = PROVENANCE_SOURCE_OBSERVED if rec.interaction_category is not None else PROVENANCE_UNAVAILABLE
        for f in (
            "interarrival_time_s", "session_relative_time_s", "total_tokens",
            "context_growth_tokens", "sequence_position", "session_id", "tenant_id",
            "model_class", "prefix_reuse_info", "kv_block_hash", "task_category", "model_family",
        ):
            prov[f] = PROVENANCE_UNAVAILABLE
        rec.field_provenance = prov
        return rec

    def stream_records(self, path: Path) -> Iterator[ExternalWorkloadRecord]:
        with open(path) as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                raw_row = json.loads(line)
                raw_row["_natural_key"] = f"{path.name}:{i}"
                yield self.convert_record(raw_row, i)
