from __future__ import annotations

from pathlib import Path

from robustbench.characterization.descriptors import (
    COMMON_NUMERIC_FEATURES,
    compute_characterization_descriptor,
)
from robustbench.workloads.external.adapters import burstgpt, tracelab
from robustbench.workloads.external.schema import ExternalWorkloadRecord

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "configs" / "external_workloads" / "fixtures"


def _burstgpt_records():
    adapter = burstgpt.BurstGPTAdapter()
    return list(adapter.stream_records(FIXTURES / "burstgpt_sample.csv"))


def _tracelab_records():
    adapter = tracelab.TraceLabAdapter()
    return list(adapter.stream_records(FIXTURES / "tracelab_sample.jsonl"))


def test_descriptor_basic_shape_on_real_adapter_fixture():
    records = _burstgpt_records()
    d = compute_characterization_descriptor(
        records, source_family="burstgpt", window_id="w0", window_size_requested=len(records)
    )
    assert d.request_count == len(records)
    assert d.prompt_tokens_mean is not None
    assert d.output_tokens_mean is not None
    for thr_field in (
        "long_prompt_fraction_512", "long_prompt_fraction_2048",
        "long_prompt_fraction_8192", "long_prompt_fraction_32768",
    ):
        v = getattr(d, thr_field)
        assert v is None or 0.0 <= v <= 1.0


def test_descriptor_handles_tracelab_missing_arrival_time_gracefully():
    records = _tracelab_records()
    d = compute_characterization_descriptor(
        records, source_family="tracelab", window_id="w0", window_size_requested=len(records)
    )
    # one record has no timing_events -> n_with_arrival_time < request_count
    assert d.n_with_arrival_time < d.request_count
    assert d.request_count == len(records)


def test_descriptor_single_record_does_not_crash():
    records = _burstgpt_records()[:1]
    d = compute_characterization_descriptor(
        records, source_family="burstgpt", window_id="w_single", window_size_requested=1
    )
    assert d.request_count == 1
    assert d.duration_s is None
    assert d.burstiness_b is None
    assert d.peak_short_window_arrival_rate_rps is None
    assert d.idle_gap_fraction is None


def test_descriptor_empty_window_all_none_no_crash():
    d = compute_characterization_descriptor(
        [], source_family="burstgpt", window_id="w_empty", window_size_requested=0
    )
    assert d.request_count == 0
    assert d.prompt_tokens_mean is None
    assert d.total_tokens_gini is None


def _synthetic_uniform_arrivals(n: int, gap: float, base_id: str) -> list[ExternalWorkloadRecord]:
    records = []
    for i in range(n):
        rec = ExternalWorkloadRecord(
            source_dataset="synthetic",
            source_version="v0",
            source_record_id=f"{base_id}:{i}",
            derived_record_id=f"{base_id}:{i}",
            source_license="synthetic",
            source_url="synthetic://test",
            conversion_version="test_v1",
            arrival_time_s=float(i) * gap,
            timestamp_provenance_kind="real",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
        )
        rec.field_provenance = {
            "arrival_time_s": "SOURCE_OBSERVED",
            "timestamp_provenance_kind": "SOURCE_OBSERVED",
            "input_tokens": "SOURCE_OBSERVED",
            "output_tokens": "SOURCE_OBSERVED",
            "total_tokens": "SOURCE_OBSERVED",
        }
        records.append(rec)
    return records


def test_burstiness_near_zero_for_perfectly_regular_arrivals():
    records = _synthetic_uniform_arrivals(50, gap=1.0, base_id="regular")
    d = compute_characterization_descriptor(
        records, source_family="synthetic", window_id="w_regular", window_size_requested=50
    )
    assert d.burstiness_b is not None
    assert abs(d.burstiness_b - (-1.0)) < 1e-6  # zero-variance interarrivals -> B = -1


def test_gini_zero_for_identical_total_tokens():
    records = _synthetic_uniform_arrivals(20, gap=1.0, base_id="const")
    d = compute_characterization_descriptor(
        records, source_family="synthetic", window_id="w_const", window_size_requested=20
    )
    assert d.total_tokens_gini is not None
    assert abs(d.total_tokens_gini) < 1e-9


def test_common_numeric_features_all_exist_on_dataclass():
    records = _synthetic_uniform_arrivals(20, gap=1.0, base_id="feat")
    d = compute_characterization_descriptor(
        records, source_family="synthetic", window_id="w_feat", window_size_requested=20
    )
    d_dict = d.to_dict()
    for feat in COMMON_NUMERIC_FEATURES:
        assert feat in d_dict, f"missing common feature: {feat}"
