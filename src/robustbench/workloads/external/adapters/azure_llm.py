"""Azure LLM Inference Dataset adapter.

Sources:
- Azure LLM Inference Dataset 2023 (Splitwise / ISCA 2024).
- Azure LLM Inference Dataset 2024 (DynamoLLM / HPCA 2025).

Both use `TIMESTAMP`, `ContextTokens`, and `GeneratedTokens` CSV columns. There are
two released splits (code, conversation); which split a file belongs to is passed in
by the caller as `split_name` at adapter construction time -- it is NOT invented by
parsing the file itself, since no split-identifying column is in the source schema.
No session ID, tenant ID, model ID, KV-reuse, SLO, or server-latency field is
confirmed present -- all stay UNAVAILABLE.

Validated only against the small synthetic, schema-equivalent fixture at
configs/external_workloads/fixtures/azure_llm_sample.csv, not the real dataset.
"""
from __future__ import annotations

import csv
import calendar
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

from ..registry import register
from ..schema import (
    PROVENANCE_SOURCE_OBSERVED,
    PROVENANCE_SYNTHESIZED_IMPUTED,
    PROVENANCE_UNAVAILABLE,
    ExternalWorkloadRecord,
)
from .base import TraceAdapter

SOURCE_LICENSE = "CC-BY"
SOURCE_URLS = {
    "2023": "https://github.com/Azure/AzurePublicDataset/blob/master/AzureLLMInferenceDataset2023.md",
    "2024": "https://github.com/Azure/AzurePublicDataset/blob/master/AzureLLMInferenceDataset2024.md",
}
SOURCE_VERSIONS = {
    "2023": "2023-11-11",
    "2024": "2024-05-10_to_2024-05-19",
}


def _timestamp_to_seconds(value: Any) -> float:
    """Parse Azure TIMESTAMP values without using local timezone state."""
    try:
        return float(value)
    except (TypeError, ValueError):
        pass
    text = str(value).strip().replace(" ", "T")
    if "." in text:
        head, tail = text.split(".", 1)
        digits = "".join(ch for ch in tail if ch.isdigit())
        text = f"{head}.{digits[:6].ljust(6, '0')}"
    dt = datetime.fromisoformat(text)
    return float(calendar.timegm(dt.timetuple())) + dt.microsecond / 1_000_000.0


@register("azure_llm_2023")
class AzureLLMAdapter(TraceAdapter):
    source_dataset = "azure_llm_2023"
    source_version = SOURCE_VERSIONS["2023"]
    source_license = SOURCE_LICENSE
    source_url = SOURCE_URLS["2023"]
    conversion_version = "azure_llm_adapter_v1"

    def __init__(self, split_name: str, dataset_year: str = "2023"):
        if split_name not in ("code", "conversation"):
            raise ValueError(f"split_name must be 'code' or 'conversation', got {split_name!r}")
        if dataset_year not in SOURCE_VERSIONS:
            raise ValueError(f"dataset_year must be one of {sorted(SOURCE_VERSIONS)}, got {dataset_year!r}")
        self.split_name = split_name
        self.dataset_year = dataset_year
        self.source_dataset = f"azure_llm_{dataset_year}"
        self.source_version = SOURCE_VERSIONS[dataset_year]
        self.source_url = SOURCE_URLS[dataset_year]

    def inspect_source(self, path: Path) -> dict[str, Any]:
        with open(path, newline="") as f:
            reader = csv.reader(f)
            header = next(reader)
            first_row = next(reader, None)
        return {"format": "csv", "columns": header, "first_row": first_row, "split_name": self.split_name}

    def convert_record(self, raw_row: dict[str, Any], index: int) -> ExternalWorkloadRecord:
        prov: dict[str, str] = {}

        def observed(field_name: str, value: Any) -> Any:
            if value is None or value == "":
                prov[field_name] = PROVENANCE_UNAVAILABLE
                return None
            prov[field_name] = PROVENANCE_SOURCE_OBSERVED
            return value

        arrival = observed("arrival_time_s", raw_row.get("TIMESTAMP"))
        source_record_id = str(raw_row.get("_natural_key", index))
        rec = ExternalWorkloadRecord(
            source_dataset=self.source_dataset,
            source_version=self.source_version,
            source_record_id=source_record_id,
            derived_record_id=self.derived_record_id(raw_row, index),
            source_license=self.source_license,
            source_url=self.source_url,
            conversion_version=self.conversion_version,
            arrival_time_s=_timestamp_to_seconds(arrival) if arrival is not None else None,
            timestamp_provenance_kind="real" if arrival is not None else None,
            input_tokens=int(v) if (v := observed("input_tokens", raw_row.get("ContextTokens"))) is not None else None,
            output_tokens=int(v) if (v := observed("output_tokens", raw_row.get("GeneratedTokens"))) is not None else None,
            # task_category is NOT a source-observed field -- it is imputed from which
            # release split the file belongs to (a caller-supplied fact about the
            # source file, not something invented from row content), so this is marked
            # SYNTHESIZED_IMPUTED rather than SOURCE_OBSERVED, per the honesty rule in
            # docs/EXTERNAL_WORKLOAD_CANONICAL_SCHEMA.md.
            task_category=self.split_name,
            interaction_category="api",
        )
        if rec.timestamp_provenance_kind is not None:
            prov["timestamp_provenance_kind"] = PROVENANCE_SOURCE_OBSERVED
        prov["task_category"] = PROVENANCE_SYNTHESIZED_IMPUTED
        prov["interaction_category"] = PROVENANCE_SOURCE_OBSERVED
        for f in (
            "interarrival_time_s", "session_relative_time_s", "total_tokens",
            "context_growth_tokens", "sequence_position", "session_id", "tenant_id",
            "model_class", "prefix_reuse_info", "kv_block_hash", "reuse_group_id",
            "reuse_confidence_source", "model_family",
        ):
            prov[f] = PROVENANCE_UNAVAILABLE
        rec.field_provenance = prov
        return rec

    def stream_records(self, path: Path) -> Iterator[ExternalWorkloadRecord]:
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                raw_row = dict(row)
                raw_row["_natural_key"] = f"{self.split_name}:{path.name}:{i}"
                yield self.convert_record(raw_row, i)
