"""Bootstrap smoke test for the new Bailian/Qwen adapter (Layer 1 only).

Runs only against a small synthetic, schema-equivalent fixture -- never the
real anonymized trace release. See docs/PROVENANCE.md and
src/robustbench/workloads/external/adapters/bailian.py's module docstring.
"""
from __future__ import annotations

from pathlib import Path

from robustbench.workloads.external import registry
from robustbench.workloads.external.adapters import bailian
from robustbench.workloads.external.schema import PROVENANCE_UNAVAILABLE

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "configs" / "external_workloads" / "fixtures"


def _bailian_records():
    adapter = bailian.BailianAdapter()
    return list(adapter.stream_records(FIXTURES / "bailian_sample.jsonl"))


def test_registry_has_bailian_adapter():
    assert "bailian_qwen" in registry.registered_names()


def test_bailian_adapter_parses_fixture_and_flags_provenance():
    records = _bailian_records()
    assert len(records) == 4
    r0 = records[0]
    assert r0.arrival_time_s == 0.0
    assert r0.input_tokens == 210
    assert r0.output_tokens == 88
    assert r0.session_id == "c0001"
    assert r0.field_provenance["arrival_time_s"] != PROVENANCE_UNAVAILABLE
    # No native SLO/priority/predicted-output-tokens field on this schema.
    assert r0.field_provenance.get("tenant_id", PROVENANCE_UNAVAILABLE) == PROVENANCE_UNAVAILABLE
    assert r0.validate() == []


def test_bailian_adapter_never_synthesizes_slo_or_priority():
    """This adapter is Layer 1 only -- it must never invent SLO/priority/
    predicted-output-token fields itself (that would be a Layer 3 concern,
    performed by a separate, later step -- see the module docstring)."""
    records = _bailian_records()
    for r in records:
        assert r.extra.get("slo_deadline") is None
        assert r.extra.get("priority") is None
        assert r.extra.get("predicted_output_tokens") is None


def test_bailian_adapter_handles_missing_parent_chat_id():
    records = _bailian_records()
    r_no_parent = records[0]
    assert r_no_parent.field_provenance["reuse_group_id"] == PROVENANCE_UNAVAILABLE


def test_deterministic_record_ids_across_reparse():
    ids_a = [r.derived_record_id for r in _bailian_records()]
    ids_b = [r.derived_record_id for r in _bailian_records()]
    assert ids_a == ids_b
