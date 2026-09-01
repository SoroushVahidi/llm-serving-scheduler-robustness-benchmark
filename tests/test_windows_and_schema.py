from __future__ import annotations

from pathlib import Path

from robustbench.descriptors.windows import fixed_count_windows, fixed_duration_windows
from robustbench.schemas.policy_outcome import PolicyOutcomeRow, validate_policy_outcome_row
from robustbench.workloads.external.adapters import burstgpt

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "configs" / "external_workloads" / "fixtures"


def _burstgpt_records():
    adapter = burstgpt.BurstGPTAdapter()
    return list(adapter.stream_records(FIXTURES / "burstgpt_sample.csv"))


def test_fixed_count_windows_drops_partial_tail():
    records = _burstgpt_records() * 3  # replicate small fixture to get >1 window
    windows = fixed_count_windows(records, window_size=4)
    assert all(len(w) == 4 for w in windows)
    assert sum(len(w) for w in windows) <= len(records)


def test_fixed_duration_windows_never_crashes_on_small_input():
    records = _burstgpt_records()
    windows = fixed_duration_windows(records, duration_s=1.0)
    assert isinstance(windows, list)


def test_policy_outcome_row_schema_round_trip():
    row = PolicyOutcomeRow(
        workload_window_id="w0",
        source_family="burstgpt",
        load_level="PRE_KNEE",
        policy_id="fifo",
        seed=0,
        experiment_version="bootstrap-v0",
        code_sha="deadbeef",
        config_hash="abc123",
        num_completed=10,
        num_dropped=0,
        request_throughput=1.0,
        token_throughput=100.0,
        mean_latency=0.5,
        p95_latency=0.9,
        slo_violation_rate=0.0,
    )
    assert validate_policy_outcome_row(row.to_dict()) == []


def test_policy_outcome_row_schema_flags_missing_fields():
    problems = validate_policy_outcome_row({"workload_window_id": "w0"})
    assert len(problems) > 0
