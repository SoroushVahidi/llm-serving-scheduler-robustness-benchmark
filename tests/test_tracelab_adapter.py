"""Bootstrap smoke test for the new TraceLab adapter (Layer 1 only).

Runs only against a small synthetic, schema-equivalent fixture -- never the
real acquired release asset. See docs/DATA_ACQUISITION_STATUS.md and
src/robustbench/workloads/external/adapters/tracelab.py's module docstring.
"""
from __future__ import annotations

from pathlib import Path

from robustbench.workloads.external import registry
from robustbench.workloads.external.adapters import tracelab
from robustbench.workloads.external.schema import PROVENANCE_UNAVAILABLE

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "configs" / "external_workloads" / "fixtures"


def _tracelab_records():
    adapter = tracelab.TraceLabAdapter()
    return list(adapter.stream_records(FIXTURES / "tracelab_sample.jsonl"))


def test_registry_has_tracelab_adapter():
    assert "tracelab" in registry.registered_names()


def test_tracelab_adapter_parses_fixture_and_flags_provenance():
    records = _tracelab_records()
    assert len(records) == 5
    r0 = records[0]
    assert r0.input_tokens == 1000
    assert r0.output_tokens == 120
    assert r0.total_tokens == 1120
    assert r0.session_id == "claude:demo-session-0001"
    assert r0.model_family == "claude"
    assert r0.field_provenance["arrival_time_s"] == PROVENANCE_UNAVAILABLE or r0.arrival_time_s is not None
    assert r0.validate() == []


def test_tracelab_adapter_derives_arrival_from_earliest_timing_event():
    records = _tracelab_records()
    r1 = records[1]
    # earliest timing_events timestamp is 2026-01-01T00:00:05.000Z
    assert r1.arrival_time_s is not None
    assert r1.timestamp_provenance_kind == "anonymized_shifted"


def test_tracelab_adapter_handles_empty_timing_events_without_fabricating():
    records = _tracelab_records()
    r_no_events = records[-1]
    assert r_no_events.arrival_time_s is None
    assert r_no_events.timestamp_provenance_kind is None
    assert r_no_events.field_provenance["arrival_time_s"] == PROVENANCE_UNAVAILABLE
    assert r_no_events.validate() == []


def test_tracelab_adapter_handles_zero_output_tokens_as_observed_not_missing():
    records = _tracelab_records()
    codex_tool_only = records[3]
    assert codex_tool_only.output_tokens == 0
    assert codex_tool_only.field_provenance["output_tokens"] != PROVENANCE_UNAVAILABLE


def test_tracelab_adapter_never_synthesizes_kv_reuse_fields():
    records = _tracelab_records()
    for r in records:
        assert r.field_provenance.get("kv_block_hash") == PROVENANCE_UNAVAILABLE
        assert r.field_provenance.get("prefix_reuse_info") == PROVENANCE_UNAVAILABLE
        assert r.kv_block_hash is None


def test_deterministic_record_ids_across_reparse():
    ids_a = [r.derived_record_id for r in _tracelab_records()]
    ids_b = [r.derived_record_id for r in _tracelab_records()]
    assert ids_a == ids_b


def test_provider_captured_as_model_family_for_both_agent_types():
    records = _tracelab_records()
    families = {r.model_family for r in records}
    assert families == {"claude", "codex"}
