"""BurstGPT adapter.

Source: https://github.com/HPMLL/BurstGPT (CC-BY-4.0), paper arXiv:2401.17644 /
ACM SIGKDD 2025. See docs/PUBLIC_TRACE_PRIMARY_SOURCE_AUDIT.md §A for the verified
field list this adapter relies on: `Timestamp`, `Model`, `Request tokens`,
`Response tokens`, `Total tokens`, `Session ID`, `Elapsed time` (CSV columns).
BurstGPT has no tenant/user, KV-reuse, SLO, or explicit failure-code field in the
documented schema -- those stay `None`/`UNAVAILABLE` here, never invented.

This adapter has been validated only against the small synthetic, schema-equivalent
fixture at configs/external_workloads/fixtures/burstgpt_sample.csv (see
tests/test_external_workload_adapters.py) -- it has NOT been run against the real ~10M-row
BurstGPT files, which are not downloaded in this task.
"""
from __future__ import annotations

import csv
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

SOURCE_URL = "https://github.com/HPMLL/BurstGPT"
SOURCE_LICENSE = "CC-BY-4.0"


@register("burstgpt")
class BurstGPTAdapter(TraceAdapter):
    source_dataset = "burstgpt"
    source_version = "v2.0"
    source_license = SOURCE_LICENSE
    source_url = SOURCE_URL
    conversion_version = "burstgpt_adapter_v1"

    def __init__(self, source_version: str = "v2.0"):
        self.source_version = source_version

    def inspect_source(self, path: Path) -> dict[str, Any]:
        with open(path, newline="") as f:
            reader = csv.reader(f)
            header = next(reader)
            first_row = next(reader, None)
        return {"format": "csv", "columns": header, "first_row": first_row}

    def convert_record(self, raw_row: dict[str, Any], index: int) -> ExternalWorkloadRecord:
        source_record_id = str(raw_row.get("_natural_key", index))
        prov: dict[str, str] = {}

        def observed(field_name: str, value: Any) -> Any:
            if value is None or value == "":
                prov[field_name] = PROVENANCE_UNAVAILABLE
                return None
            prov[field_name] = PROVENANCE_SOURCE_OBSERVED
            return value

        arrival = observed("arrival_time_s", raw_row.get("Timestamp"))
        rec = ExternalWorkloadRecord(
            source_dataset=self.source_dataset,
            source_version=self.source_version,
            source_record_id=source_record_id,
            derived_record_id=self.derived_record_id(raw_row, index),
            source_license=self.source_license,
            source_url=self.source_url,
            conversion_version=self.conversion_version,
            arrival_time_s=float(arrival) if arrival is not None else None,
            timestamp_provenance_kind="real" if arrival is not None else None,
            input_tokens=int(v) if (v := observed("input_tokens", raw_row.get("Request tokens"))) is not None else None,
            output_tokens=int(v) if (v := observed("output_tokens", raw_row.get("Response tokens"))) is not None else None,
            total_tokens=int(v) if (v := observed("total_tokens", raw_row.get("Total tokens"))) is not None else None,
            session_id=observed("session_id", raw_row.get("Session ID")),
            model_class=observed("model_class", raw_row.get("Model")),
            interaction_category="api",
        )
        if rec.timestamp_provenance_kind is not None:
            prov["timestamp_provenance_kind"] = PROVENANCE_SOURCE_OBSERVED
        if rec.interaction_category is not None:
            prov["interaction_category"] = PROVENANCE_SOURCE_OBSERVED
        # Fields BurstGPT's documented schema does not contain -- explicitly UNAVAILABLE.
        for f in (
            "interarrival_time_s", "session_relative_time_s", "context_growth_tokens",
            "sequence_position", "tenant_id", "prefix_reuse_info", "kv_block_hash",
            "reuse_group_id", "reuse_confidence_source", "task_category", "model_family",
        ):
            prov[f] = PROVENANCE_UNAVAILABLE
        rec.field_provenance = prov
        return rec

    def stream_records(self, path: Path) -> Iterator[ExternalWorkloadRecord]:
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                raw_row = dict(row)
                raw_row["_natural_key"] = f"{path.name}:{i}"
                yield self.convert_record(raw_row, i)
