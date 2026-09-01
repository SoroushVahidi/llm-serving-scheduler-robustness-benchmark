from __future__ import annotations

from pathlib import Path

from robustbench.workloads.external.adapters import burstgpt
from robustbench.workloads.external.benchmark_synthesis import (
    SYNTHESIS_VERSION,
    synthesize_requests_from_window,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "configs" / "external_workloads" / "fixtures"


def _records():
    adapter = burstgpt.BurstGPTAdapter()
    return list(adapter.stream_records(FIXTURES / "burstgpt_sample.csv"))


def test_synthesize_drops_invalid_and_rebases_arrival():
    records = _records()
    requests, manifest = synthesize_requests_from_window(records, window_id="w0", seed=0)
    # burstgpt_sample.csv has 4 rows, one with an empty Response tokens field.
    assert manifest.n_records_dropped_invalid == 1
    assert len(requests) == 3
    assert requests[0].arrival_time == 0.0
    assert all(r.arrival_time >= 0.0 for r in requests)
    assert manifest.synthesis_version == SYNTHESIS_VERSION


def test_synthesize_produces_valid_requests():
    records = _records()
    requests, _ = synthesize_requests_from_window(records, window_id="w0", seed=0)
    for r in requests:
        assert r.prompt_tokens > 0
        assert r.actual_output_tokens > 0
        assert r.predicted_output_tokens > 0
        assert r.slo_deadline > r.arrival_time
        assert r.priority == 1.0
        assert r.class_id == "stage0_uniform"


def test_synthesize_deterministic_for_fixed_seed():
    records = _records()
    r1, _ = synthesize_requests_from_window(records, window_id="w0", seed=7)
    r2, _ = synthesize_requests_from_window(records, window_id="w0", seed=7)
    assert [r.predicted_output_tokens for r in r1] == [r.predicted_output_tokens for r in r2]
    assert [r.slo_deadline for r in r1] == [r.slo_deadline for r in r2]


def test_synthesize_empty_window():
    requests, manifest = synthesize_requests_from_window([], window_id="empty", seed=0)
    assert requests == []
    assert manifest.n_requests == 0
