"""Adapter interface every external-workload source adapter implements.

An adapter converts one public trace / API-derived source into
`ExternalWorkloadRecord`s (Layer 1 only -- see docs/WORKLOAD_PROVENANCE_LAYERS.md).
It must never compute a scheduler-pressure derivative or synthesize a missing field;
those are Layer 2/3 concerns handled elsewhere (`derived_features.py`, and the
not-yet-implemented benchmark-synthesis step described in
docs/BENCHMARK_V2_PUBLIC_TRACE_REPLAY_PROTOCOL.md).
"""
from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from ..schema import ExternalWorkloadRecord


class TraceAdapter(ABC):
    """Base class for a single source's adapter. Subclasses must be deterministic:
    the same source file(s) must always yield the same records in the same order."""

    source_dataset: str
    source_version: str
    source_license: str
    source_url: str
    conversion_version: str

    @abstractmethod
    def inspect_source(self, path: Path) -> dict[str, Any]:
        """Read only metadata/header/first few rows of `path` -- must not require
        loading the full file into memory. Returns a dict describing what was found
        (columns/keys present, row-count estimate if cheap, detected format)."""

    @abstractmethod
    def stream_records(self, path: Path) -> Iterator[ExternalWorkloadRecord]:
        """Yields ExternalWorkloadRecord objects one at a time (streaming, not
        loading the whole file into a list) by calling convert_record per raw row."""

    @abstractmethod
    def convert_record(self, raw_row: dict[str, Any], index: int) -> ExternalWorkloadRecord:
        """Converts exactly one raw source row into an ExternalWorkloadRecord. Must
        never silently invent a value for a field the source doesn't provide -- set
        it to None and mark field_provenance as UNAVAILABLE instead."""

    def derived_record_id(self, raw_row: dict[str, Any], index: int) -> str:
        """Stable, deterministic derived ID: sha256 of (source_dataset, source_version,
        a source-provided natural key if present, else the row index) -- so re-running
        the same conversion always yields the same IDs (required for idempotent,
        resumable, duplicate-free conversion)."""
        key = raw_row.get("_natural_key") or str(index)
        digest = hashlib.sha256(f"{self.source_dataset}|{self.source_version}|{key}".encode()).hexdigest()
        return digest[:32]

    def validate(self, records: list[ExternalWorkloadRecord]) -> dict[str, Any]:
        """Runs ExternalWorkloadRecord.validate() over every record and returns an
        aggregate report -- does not raise, so a caller can decide what's fatal."""
        problems_by_index: dict[int, list[str]] = {}
        for i, rec in enumerate(records):
            problems = rec.validate()
            if problems:
                problems_by_index[i] = problems
        return {
            "n_records": len(records),
            "n_with_problems": len(problems_by_index),
            "problems_by_index": problems_by_index,
        }

    def provenance(self) -> dict[str, str]:
        return {
            "source_dataset": self.source_dataset,
            "source_version": self.source_version,
            "source_license": self.source_license,
            "source_url": self.source_url,
            "conversion_version": self.conversion_version,
        }

    def summarize(self, records: list[ExternalWorkloadRecord]) -> dict[str, Any]:
        """Small, cheap summary statistics -- never a full copy of the records."""
        n = len(records)
        if n == 0:
            return {"n_records": 0}
        n_with_tokens = sum(1 for r in records if r.input_tokens is not None)
        n_with_timestamps = sum(1 for r in records if r.arrival_time_s is not None)
        n_with_session = sum(1 for r in records if r.session_id is not None)
        provenance_kinds: dict[str, int] = {}
        for r in records:
            for kind in r.field_provenance.values():
                provenance_kinds[kind] = provenance_kinds.get(kind, 0) + 1
        return {
            "n_records": n,
            "n_with_input_tokens": n_with_tokens,
            "n_with_arrival_time": n_with_timestamps,
            "n_with_session_id": n_with_session,
            "field_provenance_kind_counts": provenance_kinds,
        }
