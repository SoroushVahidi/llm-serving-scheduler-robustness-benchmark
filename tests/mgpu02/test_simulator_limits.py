"""Characterize historical simulator limits, NOT physical-fidelity acceptance.

Keep old results reproducible. Any future semantic revision must explicitly
replace these historical expectations and validate against native execution.
"""
from robustbench.core.types import GPUConfig, Request
from robustbench.simulator.gpu import GPUState
from robustbench.simulator.request import InternalRequest
from robustbench.simulator.service_model import ServiceModel


def fixture():
    gpu = GPUState(GPUConfig(gpu_id=0, max_active_sequences=2,
                            max_batch_tokens=128, max_kv_tokens=16))
    model = ServiceModel(enable_prefill_modeling=True,
                         step_token_budget=128, max_prefill_chunk_tokens=128)
    r = InternalRequest(Request(0, 0., 16, 4, 4, 30., 1., 'tight'))
    assert gpu.admit(r, admission_time=0., service_model=model)
    return gpu, model, r


def test_historical_simulator_first_token_requires_extra_step():
    gpu, model, r = fixture()
    gpu.step(1., model)
    assert r.prefill_remaining == 0
    assert r.tokens_decoded == 0 and r.first_token_time == -1.
    gpu.step(2., model)
    assert r.tokens_decoded == 1 and r.first_token_time == 2.


def test_historical_execution_has_no_native_decode_allocation_guard():
    gpu, model, r = fixture()
    gpu.step(1., model)
    assert gpu.current_kv_tokens == 16
    gpu.step(2., model)
    assert gpu.current_kv_tokens == 17 > gpu.config.max_kv_tokens
    # A policy/shadow manager must intervene; GPUState is not a native allocator.
    assert r.tokens_decoded == 1


def test_historical_recompute_discards_output_progress():
    gpu, model, r = fixture()
    gpu.step(1., model)
    gpu.step(2., model)
    assert r.tokens_decoded == 1
    assert gpu.evict(r.request_id) is r
    assert r.tokens_decoded == 0 and r.first_token_time == -1.
