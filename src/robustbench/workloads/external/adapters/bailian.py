"""Bailian / Qwen anonymized serving-trace adapter.

Source: https://github.com/alibaba-edu/qwen-bailian-usagetraces-anon
(Apache-2.0, per repository LICENSE and README section on data licensing).
Pinned tip inspected 2026-07-24 (per llm-serving-heuristic-evolution's own
loader docstring): commit 5f7439c51ec248a0c585f7d90a41a6f57773b912 -- this
adapter has not independently re-verified that pin; treat it as inherited,
unverified provenance until re-checked against the live upstream repo.

This is a NEW implementation for this project's Layer-1 `TraceAdapter`
interface, informed by (not copied from) the pre-existing
`llmserveopt/workloads/bailian.py` loader in `llm-serving-heuristic-evolution`
(see docs/PROVENANCE.md) -- that loader mixes Layer-1 parsing with Layer-3 SLO/
priority/predicted-output-token synthesis in one function, which this
project's schema explicitly forbids for a `TraceAdapter` (see
`workloads/external/schema.py`: every synthesized field must be added by a
separate, later step, never baked into ingestion). Only the *field mapping
knowledge* (which raw keys exist, which are synthesized) is reused; the code
itself is new.

Observed fields (per the source loader's docstring): `timestamp` (seconds,
relative to trace start -- NOT an absolute wall-clock timestamp),
`input_length`, `output_length`, `chat_id` / `parent_chat_id` (session
lineage), `type`, `turn`, `hash_ids` (16-token KV/prefix blocks). No native
SLO, priority, or predicted-output-token field exists in this source; a
downstream project step may synthesize those (and must mark them
SYNTHESIZED_IMPUTED, never SOURCE_OBSERVED, if it does).

Validated only against the small synthetic, schema-equivalent fixture at
configs/external_workloads/fixtures/bailian_sample.jsonl -- NOT against the
real anonymized trace release, which is not downloaded in this project.
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

SOURCE_URL = "https://github.com/alibaba-edu/qwen-bailian-usagetraces-anon"
SOURCE_LICENSE = "Apache-2.0"
SOURCE_VERSION = "commit-5f7439c5-unverified-pin"


@register("bailian_qwen")
class BailianAdapter(TraceAdapter):
    source_dataset = "bailian_qwen"
    source_version = SOURCE_VERSION
    source_license = SOURCE_LICENSE
    source_url = SOURCE_URL
    conversion_version = "bailian_adapter_v1"

    def inspect_source(self, path: Path) -> dict[str, Any]:
        with open(path) as f:
            first_line = f.readline()
        keys = sorted(json.loads(first_line).keys()) if first_line.strip() else []
        return {"format": "jsonl", "keys": keys}

    def convert_record(self, raw_row: dict[str, Any], index: int) -> ExternalWorkloadRecord:
        source_record_id = str(raw_row.get("_natural_key", index))
        prov: dict[str, str] = {}

        def observed(field_name: str, value: Any) -> Any:
            if value is None or value == "":
                prov[field_name] = PROVENANCE_UNAVAILABLE
                return None
            prov[field_name] = PROVENANCE_SOURCE_OBSERVED
            return value

        arrival = observed("arrival_time_s", raw_row.get("timestamp"))
        hash_ids = raw_row.get("hash_ids") or []
        kv_hash = hash_ids[0] if isinstance(hash_ids, list) and hash_ids else None

        rec = ExternalWorkloadRecord(
            source_dataset=self.source_dataset,
            source_version=self.source_version,
            source_record_id=source_record_id,
            derived_record_id=self.derived_record_id(raw_row, index),
            source_license=self.source_license,
            source_url=self.source_url,
            conversion_version=self.conversion_version,
            arrival_time_s=float(arrival) if arrival is not None else None,
            # Relative-to-trace-start, not an absolute wall-clock timestamp --
            # still a real observed value, so "real" per the vocabulary in
            # ExternalWorkloadRecord, not "synthetic".
            timestamp_provenance_kind="real" if arrival is not None else None,
            input_tokens=int(v) if (v := observed("input_tokens", raw_row.get("input_length"))) is not None else None,
            output_tokens=int(v) if (v := observed("output_tokens", raw_row.get("output_length"))) is not None else None,
            session_id=str(v) if (v := observed("session_id", raw_row.get("chat_id"))) is not None else None,
            reuse_group_id=str(v) if (v := observed("reuse_group_id", raw_row.get("parent_chat_id"))) is not None else None,
            sequence_position=int(v) if (v := observed("sequence_position", raw_row.get("turn"))) is not None else None,
            interaction_category=observed("interaction_category", raw_row.get("type")),
            kv_block_hash=observed("kv_block_hash", kv_hash),
        )
        if rec.timestamp_provenance_kind is not None:
            prov["timestamp_provenance_kind"] = PROVENANCE_SOURCE_OBSERVED
        for f in (
            "interarrival_time_s", "session_relative_time_s", "total_tokens",
            "context_growth_tokens", "tenant_id", "model_class", "model_family",
            "prefix_reuse_info", "reuse_confidence_source", "task_category",
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
