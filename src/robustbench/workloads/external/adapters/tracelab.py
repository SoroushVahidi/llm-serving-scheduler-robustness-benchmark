"""TraceLab adapter (coding-agent LLM-invocation traces).

Source: https://github.com/uw-syfi/TraceLab, paper arXiv:2606.30560
("TraceLab: Characterizing Coding Agent Workloads for LLM Serving").
Code license Apache-2.0; trace dataset license CC BY 4.0 per the repository's
own README/LICENSE-DATASET.md badges (re-verify directly from the live repo
before any redistribution decision -- this adapter only records what was
observed in the acquired release asset).

This is a NEW, independent Layer-1 ingestion of the *raw* official release
asset (`syfi_coding_trace.jsonl.gz`, GitHub release `v0.0.1`,
sha256 recorded in `configs/workloads/source_registry.yaml`) -- it does
**not** reuse or wrap the pre-existing HF `tracelab_scheduler_ood_policy_sweep`
512-window config. Per `docs/TRACELAB_PROVENANCE_RESOLUTION.md`, that existing
config is near-saturated, sqrt-compresses prompt tokens, and overlays
synthetic neutral SLO labels -- unsuitable as a source-native characterization
input. Re-deriving directly from the raw asset with this project's own
`TraceAdapter` is the resolution's explicit recommendation.

Raw schema (one JSON object per line = one LLM-invocation "round" within a
coding-agent session; verified 2026-09-01 against a live sample of the
acquired asset, both `provider` values):

    provider            "claude" | "codex"
    session_id          str, stable per coding-agent session
    round_index         int, 0-based position of this round within its session
    round_id / turn_id  str identifiers (codex additionally has `turn_id`)
    model               str, e.g. "claude-haiku-4-5-20251001", "gpt-5.4"
    input_tokens_total  int, full context size sent to the model this round
                         (includes any reused/cached prefix -- the semantic
                         analog of Azure's `ContextTokens`, not a fresh-prompt
                         count)
    prefix_tokens       int, portion of input_tokens_total that is a reused
                         prefix from a prior round in the same session
    newly_append_tokens int, input_tokens_total - prefix_tokens
    output_tokens       int
    reasoning_output_tokens  int | null (only populated for reasoning models)
    timing_events       list of {event_type, timestamp (ISO-8601 UTC), ...};
                         may be empty for a degenerate/truncated round
    user                str, pseudonymized per-developer identifier
    store               ".claude" | ".codex"
    trace_key           str, globally unique across the whole release

There is no per-round top-level timestamp; this adapter derives
`arrival_time_s` as the earliest `timing_events[*].timestamp` (the moment the
round's triggering input -- a user message or a completed tool result --
became available), which is the closest source-native analog to "when this
request arrived at a serving system." A round with an empty `timing_events`
list has no derivable arrival time and is correctly left `UNAVAILABLE`, never
imputed.

Per the source's own documentation the dataset is a *sanitized/pseudonymized*
release (developer identity replaced by `user`, session IDs replaced), so
`timestamp_provenance_kind="anonymized_shifted"` is used rather than "real"
-- this adapter cannot itself confirm whether calendar time was shifted
per-developer, only that pseudonymization was applied; treat any absolute-
calendar-date claim from this source as provisional.

`prefix_tokens` and the raw cache-accounting fields (`claude_cache_read_input_tokens`,
etc.) are retained in `extra` for secondary source-specific analysis, not
mapped onto the canonical `kv_block_hash`/`prefix_reuse_info` fields -- this
source has no block-hash-level KV-reuse ground truth, only a coarser
round-level reused-token count, and inventing a qualitative KV-reuse category
from a raw count would not be honest per `docs/DATA_FIELD_PROVENANCE.md`.

Validated only against the small synthetic, schema-equivalent fixture at
configs/external_workloads/fixtures/tracelab_sample.jsonl in unit tests;
smoke-tested separately against a real slice of the acquired release asset
(see docs/DATA_ACQUISITION_STATUS.md) -- not embedded in this repo.
"""
from __future__ import annotations

import calendar
import gzip
import json
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

from ..registry import register
from ..schema import (
    PROVENANCE_DETERMINISTIC_DERIVED,
    PROVENANCE_SOURCE_OBSERVED,
    PROVENANCE_SYNTHESIZED_IMPUTED,
    PROVENANCE_UNAVAILABLE,
    ExternalWorkloadRecord,
)
from .base import TraceAdapter

SOURCE_URL = "https://github.com/uw-syfi/TraceLab"
SOURCE_LICENSE = "CC-BY-4.0"
SOURCE_VERSION = "release_tag:v0.0.1"


def _iso_to_epoch_seconds(text: str) -> float:
    """Parse a UTC ISO-8601 timestamp (with 'Z' suffix) to epoch seconds
    without using local timezone state (matches azure_llm.py's approach)."""
    cleaned = text.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is not None:
        return float(calendar.timegm(dt.utctimetuple())) + dt.microsecond / 1_000_000.0
    return float(calendar.timegm(dt.timetuple())) + dt.microsecond / 1_000_000.0


def _earliest_timestamp(timing_events: Any) -> str | None:
    if not isinstance(timing_events, list) or not timing_events:
        return None
    timestamps = [
        e.get("timestamp") for e in timing_events if isinstance(e, dict) and e.get("timestamp")
    ]
    if not timestamps:
        return None
    return min(timestamps)


@register("tracelab")
class TraceLabAdapter(TraceAdapter):
    source_dataset = "tracelab"
    source_version = SOURCE_VERSION
    source_license = SOURCE_LICENSE
    source_url = SOURCE_URL
    conversion_version = "tracelab_adapter_v1"

    def inspect_source(self, path: Path) -> dict[str, Any]:
        opener = gzip.open if str(path).endswith(".gz") else open
        with opener(path, "rt") as f:
            first_line = f.readline()
        keys = sorted(json.loads(first_line).keys()) if first_line.strip() else []
        return {"format": "jsonl(.gz)", "keys": keys}

    def convert_record(self, raw_row: dict[str, Any], index: int) -> ExternalWorkloadRecord:
        source_record_id = str(raw_row.get("trace_key") or raw_row.get("_natural_key", index))
        prov: dict[str, str] = {}

        def observed(field_name: str, value: Any) -> Any:
            if value is None or value == "":
                prov[field_name] = PROVENANCE_UNAVAILABLE
                return None
            prov[field_name] = PROVENANCE_SOURCE_OBSERVED
            return value

        arrival_iso = observed("arrival_time_s", _earliest_timestamp(raw_row.get("timing_events")))
        arrival_s = _iso_to_epoch_seconds(arrival_iso) if arrival_iso is not None else None

        input_tokens = observed("input_tokens", raw_row.get("input_tokens_total"))
        output_tokens_raw = raw_row.get("output_tokens")
        # output_tokens=0 is a legitimate observed value (e.g. a round that
        # only emits tool calls with no assistant text), not a missing field.
        if output_tokens_raw is None:
            prov["output_tokens"] = PROVENANCE_UNAVAILABLE
            output_tokens = None
        else:
            prov["output_tokens"] = PROVENANCE_SOURCE_OBSERVED
            output_tokens = output_tokens_raw

        total_tokens = None
        if input_tokens is not None and output_tokens is not None:
            total_tokens = int(input_tokens) + int(output_tokens)
            prov["total_tokens"] = PROVENANCE_DETERMINISTIC_DERIVED
        else:
            prov["total_tokens"] = PROVENANCE_UNAVAILABLE

        context_growth = observed("context_growth_tokens", raw_row.get("newly_append_tokens"))

        rec = ExternalWorkloadRecord(
            source_dataset=self.source_dataset,
            source_version=self.source_version,
            source_record_id=source_record_id,
            derived_record_id=self.derived_record_id(raw_row, index),
            source_license=self.source_license,
            source_url=self.source_url,
            conversion_version=self.conversion_version,
            arrival_time_s=arrival_s,
            timestamp_provenance_kind="anonymized_shifted" if arrival_s is not None else None,
            input_tokens=int(input_tokens) if input_tokens is not None else None,
            output_tokens=int(output_tokens) if output_tokens is not None else None,
            total_tokens=total_tokens,
            context_growth_tokens=int(context_growth) if context_growth is not None else None,
            sequence_position=int(v) if (v := observed("sequence_position", raw_row.get("round_index"))) is not None else None,
            session_id=observed("session_id", raw_row.get("session_id")),
            tenant_id=observed("tenant_id", raw_row.get("user")),
            model_class=observed("model_class", raw_row.get("model")),
            model_family=observed("model_family", raw_row.get("provider")),
            interaction_category="agent",
        )
        if rec.timestamp_provenance_kind is not None:
            prov["timestamp_provenance_kind"] = PROVENANCE_SOURCE_OBSERVED
        prov["interaction_category"] = PROVENANCE_SYNTHESIZED_IMPUTED
        for f in (
            "interarrival_time_s", "session_relative_time_s", "prefix_reuse_info",
            "kv_block_hash", "reuse_group_id", "reuse_confidence_source", "task_category",
        ):
            prov[f] = PROVENANCE_UNAVAILABLE
        rec.field_provenance = prov
        rec.extra = {
            "prefix_tokens": raw_row.get("prefix_tokens"),
            "reasoning_output_tokens": raw_row.get("reasoning_output_tokens"),
            "claude_cache_read_input_tokens": raw_row.get("claude_cache_read_input_tokens"),
            "claude_cache_creation_input_tokens": raw_row.get("claude_cache_creation_input_tokens"),
            "store": raw_row.get("store"),
            "project": raw_row.get("project"),
        }
        return rec

    def stream_records(self, path: Path) -> Iterator[ExternalWorkloadRecord]:
        opener = gzip.open if str(path).endswith(".gz") else open
        with opener(path, "rt") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                raw_row = json.loads(line)
                raw_row["_natural_key"] = raw_row.get("trace_key", f"{path.name}:{i}")
                yield self.convert_record(raw_row, i)
