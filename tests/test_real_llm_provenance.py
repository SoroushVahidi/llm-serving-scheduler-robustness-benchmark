import pytest

from robustbench.real_llm.provenance import PROVENANCE_SCHEMA_VERSION, RealRunProvenance


def _valid_kwargs(**overrides):
    base = dict(
        repository_sha="a" * 40,
        validation_protocol_sha="b" * 40,
        hardware_manifest_hash="c" * 64,
        gpu_model="NVIDIA A100",
        gpu_driver_version="580.173.02",
        cuda_version="12.6",
        python_version="3.12.3",
        pytorch_version="2.13.0+cu130",
        vllm_version="0.27.1",
        model_id="Qwen/Qwen2.5-0.5B-Instruct",
        model_revision=None,
        dtype="bfloat16",
        tensor_parallel_size=1,
        max_model_len=2048,
        gpu_memory_utilization=0.5,
        scheduler_mechanism="fifo",
        scheduler_config="scheduling_policy=fcfs",
        workload_manifest_sha256="d" * 64,
        run_order_seed=42,
        run_order_scheme="deterministic_random",
        repetition_index=0,
        warmup_request_count=2,
        measurement_request_count=4,
        server_command="vllm serve Qwen/Qwen2.5-0.5B-Instruct",
        client_command="python smoke_client.py",
        start_time_iso="2026-09-02T18:00:00Z",
        end_time_iso="2026-09-02T18:01:00Z",
        exit_status=0,
    )
    base.update(overrides)
    return base


def test_valid_provenance_passes_validate():
    p = RealRunProvenance(**_valid_kwargs())
    p.validate()  # must not raise


def test_to_dict_includes_schema_version():
    p = RealRunProvenance(**_valid_kwargs())
    d = p.to_dict()
    assert d["provenance_schema_version"] == PROVENANCE_SCHEMA_VERSION
    assert d["model_id"] == "Qwen/Qwen2.5-0.5B-Instruct"


@pytest.mark.parametrize(
    "field_name",
    [
        "repository_sha", "validation_protocol_sha", "hardware_manifest_hash",
        "gpu_model", "scheduler_mechanism", "workload_manifest_sha256",
        "server_command", "client_command",
    ],
)
def test_empty_required_field_rejected(field_name):
    kwargs = _valid_kwargs(**{field_name: ""})
    p = RealRunProvenance(**kwargs)
    with pytest.raises(ValueError, match=field_name):
        p.validate()


def test_negative_repetition_index_rejected():
    p = RealRunProvenance(**_valid_kwargs(repetition_index=-1))
    with pytest.raises(ValueError, match="repetition_index"):
        p.validate()


def test_zero_tensor_parallel_size_rejected():
    p = RealRunProvenance(**_valid_kwargs(tensor_parallel_size=0))
    with pytest.raises(ValueError, match="tensor_parallel_size"):
        p.validate()


def test_optional_model_revision_may_be_none():
    p = RealRunProvenance(**_valid_kwargs(model_revision=None))
    p.validate()
