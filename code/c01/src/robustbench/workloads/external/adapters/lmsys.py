"""LMSYS-Chat-1M adapter (SECONDARY, INTERNAL-ANALYSIS-ONLY source -- see
docs/BENCHMARK_V2_PUBLIC_TRACE_SELECTION.md and
docs/API_PROVIDER_DATA_USE_AUDIT.md-style legal caveats).

Source: https://huggingface.co/datasets/lmsys/lmsys-chat-1m. Per
docs/PUBLIC_TRACE_PRIMARY_SOURCE_AUDIT.md §E, the dataset's own license explicitly
PROHIBITS redistributing the dataset (or, by the agreement's plain language, its
content) to third parties. This adapter and any output it produces MUST NOT be
published or embedded in a redistributed derived benchmark -- it exists only to
support internal workload-SHAPE analysis (turn-count/session-length statistics), per
the license's own scope. Enforced practically here by never carrying conversation
TEXT into `ExternalWorkloadRecord` at all (the schema has no text field), and never
storing an `input_tokens`/`output_tokens` value derived from that text with a specific
tokenizer choice -- doing so would be a Layer 2 derivation with an undisclosed
tokenizer parameter, which this Layer-1-only adapter deliberately does not attempt.
No timestamp field was confirmed present in the source (per the audit), so all TIMING
fields stay UNAVAILABLE -- this source cannot drive an arrival process on its own.

Validated only against a small synthetic, schema-equivalent fixture at
configs/external_workloads/fixtures/lmsys_sample.jsonl containing fabricated,
non-sensitive placeholder conversations -- never real LMSYS-Chat-1M rows.
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

SOURCE_URL = "https://huggingface.co/datasets/lmsys/lmsys-chat-1m"
SOURCE_LICENSE = "LMSYS-Chat-1M Dataset License Agreement (custom, gated, no redistribution)"


@register("lmsys_chat_1m")
class LMSYSAdapter(TraceAdapter):
    source_dataset = "lmsys_chat_1m"
    source_version = "1.0"
    source_license = SOURCE_LICENSE
    source_url = SOURCE_URL
    conversion_version = "lmsys_adapter_v1"

    def inspect_source(self, path: Path) -> dict[str, Any]:
        with open(path) as f:
            first_line = f.readline()
        first_row = json.loads(first_line) if first_line else None
        return {
            "format": "jsonl",
            "first_row_keys": list(first_row.keys()) if first_row else [],
            "first_row_redacted": first_row is not None,
            "conversation_turns": len(first_row.get("conversation", [])) if first_row else None,
        }

    def convert_record(self, raw_row: dict[str, Any], index: int) -> ExternalWorkloadRecord:
        """One ExternalWorkloadRecord per conversation, carrying turn count only and
        never holding the conversation text."""
        prov: dict[str, str] = {}

        def observed(field_name: str, value: Any) -> Any:
            if value is None:
                prov[field_name] = PROVENANCE_UNAVAILABLE
                return None
            prov[field_name] = PROVENANCE_SOURCE_OBSERVED
            return value

        conversation = raw_row.get("conversation", [])
        source_record_id = str(raw_row.get("conversation_id", raw_row.get("_natural_key", index)))
        rec = ExternalWorkloadRecord(
            source_dataset=self.source_dataset,
            source_version=self.source_version,
            source_record_id=source_record_id,
            derived_record_id=self.derived_record_id(raw_row, index),
            source_license=self.source_license,
            source_url=self.source_url,
            conversion_version=self.conversion_version,
            session_id=observed("session_id", raw_row.get("conversation_id")),
            sequence_position=observed("sequence_position", len(conversation) if conversation else None),
            model_class=observed("model_class", raw_row.get("model")),
            interaction_category="conversation",
        )
        prov["interaction_category"] = PROVENANCE_SOURCE_OBSERVED
        # No timestamp confirmed present in the source schema; no token-length column;
        # deliberately never derived from text here (see module docstring).
        for f in (
            "arrival_time_s", "interarrival_time_s", "session_relative_time_s",
            "timestamp_provenance_kind", "input_tokens", "output_tokens", "total_tokens",
            "context_growth_tokens", "tenant_id", "prefix_reuse_info", "kv_block_hash",
            "reuse_group_id", "reuse_confidence_source", "task_category", "model_family",
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
