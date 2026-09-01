from __future__ import annotations

from pathlib import Path

from robustbench.descriptors.window_descriptors import compute_window_descriptor
from robustbench.workloads.external.adapters import burstgpt

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "configs" / "external_workloads" / "fixtures"


def _burstgpt_records():
    adapter = burstgpt.BurstGPTAdapter()
    return list(adapter.stream_records(FIXTURES / "burstgpt_sample.csv"))


def test_descriptor_basic_fields():
    records = _burstgpt_records()
    d = compute_window_descriptor(records, source_family="burstgpt", window_id="w0")
    assert d.request_count == len(records)
    assert d.prompt_tokens_mean is not None
    assert d.output_tokens_mean is not None
    assert 0.0 <= (d.long_context_fraction or 0.0) <= 1.0


def test_descriptor_never_fabricates_native_priority_for_burstgpt():
    records = _burstgpt_records()
    d = compute_window_descriptor(records, source_family="burstgpt", window_id="w0")
    assert d.has_native_priority is False
    assert d.has_native_slo is False


def test_descriptor_provenance_counts_are_consistent():
    records = _burstgpt_records()
    d = compute_window_descriptor(records, source_family="burstgpt", window_id="w0")
    total = d.n_synthesized_fields + d.n_source_observed_fields + d.n_unavailable_fields
    assert total == sum(d.field_provenance_summary.values())
    assert total > 0


def test_descriptor_handles_single_record_without_crashing():
    records = _burstgpt_records()[:1]
    d = compute_window_descriptor(records, source_family="burstgpt", window_id="w_single")
    assert d.request_count == 1
    assert d.duration_s is None  # cannot compute a span from one arrival
    assert d.burstiness_b is None
