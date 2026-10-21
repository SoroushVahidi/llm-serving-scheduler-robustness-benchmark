import asyncio
from dataclasses import asdict, replace
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from robustbench.mgpu00.metadata import RequestMetadata
from robustbench.mgpu00.provenance import ExperimentIdentity, verify_full_a100
from robustbench.mgpu00.replay import PreparedRequest, make_client, replay
from robustbench.mgpu00.slai import Candidate, SlaiCore, UnsupportedSemantics, validate_deployment


def meta(i=0, cls="tight", arrival=0.):
    return RequestMetadata(f"r{i}", i, cls, arrival, arrival + 10., 1.)


@pytest.mark.parametrize("bad", [None, {}, {"lssp_schema": "mgpu00-v1"}])
def test_metadata_missing_is_not_a_loose_request(bad):
    with pytest.raises(ValueError):
        RequestMetadata.from_xargs(bad)


def test_class_validation_and_ordering():
    with pytest.raises(ValueError):
        meta(cls="invented")
    assert meta().admission_key(99999) < meta(1, "loose").admission_key(1)
    assert RequestMetadata.from_xargs(meta().xargs()) == meta()


def test_actual_vllm_protocol_preserves_metadata_and_affects_decision():
    # Actual installed OpenAI schema -> actual SamplingParams -> the same
    # scheduler decoder/core used by the compute-node adapter. No CUDA calls.
    from vllm.entrypoints.openai.completion.protocol import CompletionRequest
    candidates = []
    for i, cls in enumerate(["loose", "tight", "medium"]):
        body = PreparedRequest(meta(i, cls), (12, 13, 14), 8).payload("model")
        api = CompletionRequest(**body)
        sampling = api.to_sampling_params(max_tokens=8)
        received = RequestMetadata.from_request(SimpleNamespace(sampling_params=sampling))
        assert received == meta(i, cls)
        candidates.append(Candidate(str(i), received, 3))
    core = SlaiCore(1)
    core.batch_completed(start_s=1., end_s=1.001, progressed=candidates, kv_utilization=.1)
    plan, _, held = core.plan(now_s=1.002, decoding=candidates, waiting=[], token_budget=10,
                               active_count=3, max_active=3)
    assert plan == {"1": 1}  # tight request, not the earliest loose request
    assert {c.engine_id for c in held} == {"0", "2"}


def test_clock_uses_measured_completion_and_hold_does_not_refresh():
    candidates = [Candidate(str(i), meta(i, cls), 3) for i, cls in enumerate(["tight", "loose"])]
    core = SlaiCore(1)
    core.batch_completed(start_s=100., end_s=100.002, progressed=candidates, kv_utilization=.1)
    assert core.lst["0"] == pytest.approx(100.092)
    held_lst = core.lst["1"]
    plan, _, held = core.plan(now_s=100.003, decoding=candidates, waiting=[], token_budget=10,
                              active_count=2, max_active=2)
    core.batch_completed(start_s=100.003, end_s=100.007, progressed=[candidates[0]], kv_utilization=.1)
    assert core.lst["1"] == held_lst
    assert core.mean_batch_s == pytest.approx(.003)
    assert core.lst["0"] == pytest.approx(100.092)
    # More scheduling calls without completed GPU work cannot change the clock/LST.
    before = dict(core.lst)
    for _ in range(10):
        core.plan(now_s=100.008, decoding=candidates, waiting=[], token_budget=10, active_count=2, max_active=2)
    assert core.lst == before


def test_mixed_prefill_consumes_budget_before_noncritical_decodes():
    running = [Candidate(str(i), meta(i), 3) for i in range(2)]
    waiting = [Candidate("2", meta(2), 3)]
    core = SlaiCore(2)
    core.batch_completed(start_s=0., end_s=.001, progressed=running, kv_utilization=0.)
    tokens, admitted, held = core.plan(now_s=.002, decoding=running, waiting=waiting,
                                       token_budget=3, active_count=2, max_active=4)
    assert tokens == {"2": 3}
    assert len(held) == 2
    # The historical adapter instead spent this budget on decodes before prefills.


def test_unsupported_partial_prefill_is_rejected_not_approximated():
    with pytest.raises(UnsupportedSemantics, match="partial-prefill"):
        SlaiCore(2).plan(now_s=0., decoding=[], waiting=[Candidate("0", meta(), 10)],
                         token_budget=5, active_count=0, max_active=4)


def test_tp_cannot_be_mistaken_for_validated_single_gpu():
    cfg = SimpleNamespace(parallel_config=SimpleNamespace(tensor_parallel_size=2,
                          pipeline_parallel_size=1, data_parallel_size=1))
    cfg.scheduler_config = SimpleNamespace(async_scheduling=False, enable_chunked_prefill=False)
    with pytest.raises(UnsupportedSemantics, match="TP/PP/DP"):
        validate_deployment(cfg)


def full_device():
    from test_gpu_probe import full_device as fixture
    return fixture()


def test_parent_80gb_does_not_verify_a_10gb_cuda_device():
    value = full_device()
    assert verify_full_a100(value) == "FULL_GPU_VERIFIED"
    value["devices"][0]["cuda_memory_bytes"] = 10 * 1024**3
    with pytest.raises(ValueError):
        verify_full_a100(value)
    value = full_device()
    value["devices"][0]["mig_mode_current"] = 1
    with pytest.raises(ValueError):
        verify_full_a100(value)


def identity():
    return ExperimentIdentity("m", "a"*40, "m", "b"*40, "bfloat16", 1024, "A100", "FULL_GPU_VERIFIED",
           1, 1, 1, 1, 1, "slai", {"decode_limit": 2}, "c"*64, "d"*64, 0, "e"*40,
           {k: "version" for k in ["cuda", "driver", "torch", "vllm", "nccl"]}, "engineering")


def test_identity_has_no_cross_deployment_collisions():
    original = identity()
    variants = [original, replace(original, repetition=1), replace(original, gpu_model="L40"),
                replace(original, gpu_count=2, tensor_parallel=2),
                replace(original, gpu_count=2, data_parallel=2), replace(original, model_revision="f"*40),
                replace(original, policy_parameters={"decode_limit": 128})]
    assert len({x.experiment_id for x in variants}) == len(variants)
    with pytest.raises(ValueError):
        replace(original, model_revision="main")
    with pytest.raises(ValueError):
        replace(original, gpu_count=2)


def test_historical_classification_needs_cuda_evidence():
    path = Path(__file__).parents[2] / "scripts/mgpu00/audit_rq6.py"
    spec = importlib.util.spec_from_file_location("rq6_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.classify("gres/gpu:a100_10g=1", [9.5]) == "MIG_VERIFIED"
    assert module.classify("gres/gpu:a100_10g=1", []) == "UNVERIFIABLE"
    assert module.classify("gres/gpu:a100_10g=1", [80.]) == "UNVERIFIABLE"


async def controlled_replay(*, count=40, max_inflight=80, service_delay=.06, spacing=.002, incomplete=False):
    received = []
    async def serve(reader, writer):
        header = await reader.readuntil(b"\r\n\r\n")
        length = next(int(line.split(b":")[1]) for line in header.split(b"\r\n") if line.lower().startswith(b"content-length:"))
        body = json.loads(await reader.readexactly(length))
        received.append(RequestMetadata.from_xargs(body["vllm_xargs"]))
        writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nConnection: close\r\n\r\n")
        await writer.drain()
        await asyncio.sleep(service_delay)
        chunk = {"choices": [{"text": "token", "finish_reason": "length"}],
                 "usage": {"prompt_tokens": len(body["prompt"]), "completion_tokens": 0 if incomplete else body["max_tokens"]}}
        writer.write(("data: " + json.dumps(chunk) + "\n\ndata: [DONE]\n\n").encode())
        await writer.drain()
        writer.close()
        await writer.wait_closed()
    server = await asyncio.start_server(serve, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    requests = [PreparedRequest(meta(i, "tight" if i % 2 else "loose", i*spacing), (1, 2, 3), 8)
                for i in range(count)]
    async with server, make_client(f"http://127.0.0.1:{port}", max_inflight) as client:
        result = await replay(requests, model="controlled", client=client, max_inflight=max_inflight,
                              timeout_s=3., max_dispatch_delay_s=.5)
    return result, received


def test_open_loop_more_than_32_and_real_stream_timings():
    result, received = asyncio.run(controlled_replay(service_delay=.2, spacing=.001))
    assert result["valid_replay"] and result["completed"] == 40
    assert result["peak_inflight"] > 32
    assert result["transport_timing_complete"]
    assert len(received) == 40 and {m.class_id for m in received} == {"tight", "loose"}
    assert result["actual_dispatch_rate_rps"] is not None
    for row in result["rows"]:
        assert row["scheduled_arrival_s"] <= row["dispatch_s"] <= row["transport_send_s"] <= row["first_token_s"] <= row["completion_s"]
        assert row["server_admission_s"] is None


def test_capacity_overrun_is_detected_not_rescheduled():
    result, _ = asyncio.run(controlled_replay(count=12, max_inflight=2, service_delay=.2, spacing=.001))
    assert not result["valid_replay"]
    saturated = [r for r in result["rows"] if r["status"] == "CLIENT_SATURATED"]
    assert len(saturated) == 10
    assert all(r["dispatch_s"] is None for r in saturated)


def test_incomplete_token_lengths_invalidate_replay():
    result, _ = asyncio.run(controlled_replay(count=2, incomplete=True))
    assert not result["valid_replay"]
    assert {r["status"] for r in result["rows"]} == {"INCOMPLETE"}


def test_dispatch_lag_is_detected_even_when_every_request_completes():
    import httpx
    import time
    async def run():
        async def handler(request):
            body = json.loads(request.content)
            await request.extensions["trace"]("http11.send_request_headers.started", {})
            # Deliberately block the injection event loop (emulates CPU-bound client work).
            if body["request_id"] == "r0":
                time.sleep(.08)
            chunk = {"choices": [{"text": "x", "finish_reason": "length"}],
                     "usage": {"prompt_tokens": 1, "completion_tokens": 1}}
            return httpx.Response(200, content=("data: " + json.dumps(chunk) + "\n\ndata: [DONE]\n\n").encode())
        async with httpx.AsyncClient(base_url="http://fixture", transport=httpx.MockTransport(handler)) as client:
            return await replay([PreparedRequest(meta(i, arrival=i*.001), (1,), 1) for i in range(3)],
                model="fixture", client=client, max_inflight=3, timeout_s=1., max_dispatch_delay_s=.02)
    result = asyncio.run(run())
    assert result["completed"] == 3 and not result["valid_replay"]
    assert result["dispatch_delay_max_s"] >= .06


def test_decision_sets_match_existing_simulator_in_supported_domain():
    import random
    from robustbench.core.types import ObservableRequest, ObservableGPUState, ObservableState
    from robustbench.policies.slai_faithful import SlaiFaithfulPolicy
    rng = random.Random(1701)
    for _ in range(60):
        running = [Candidate(str(i), meta(i, rng.choice(["tight", "medium", "loose"])), 16) for i in range(6)]
        waiting = [Candidate(str(i), meta(i, rng.choice(["tight", "medium", "loose"])), 16) for i in range(6, 9)]
        limit = rng.randint(1, 6)
        now = 1.
        core = SlaiCore(limit)
        core.lst = {str(i): rng.uniform(.7, 1.3) for i in range(6)}
        def observable(r):
            return ObservableRequest(int(r.engine_id), 0., r.prompt_tokens, 20, 10., 1., r.metadata.class_id)
        gpu = ObservableGPUState(0, 100, 4096, 1000000, list(range(6)),
                  [observable(r) for r in running], 6*16, {i: 1 for i in range(6)})
        policy = SlaiFaithfulPolicy(decode_limit=limit, token_budget=4096)
        policy._lst[0] = {int(k): v for k, v in core.lst.items()}
        action = policy.select_action(ObservableState(now, [observable(r) for r in waiting], [gpu], 0, 1))
        _, admitted, held = core.plan(now_s=now, decoding=running, waiting=waiting,
                                      token_budget=4096, active_count=6, max_active=100)
        assert [int(r.engine_id) for r in admitted] == action.admit[0]
        assert {int(r.engine_id) for r in held} == set(action.hold_decode[0])


def test_adapter_keeps_held_requests_active_and_rejects_native_plan_drift(monkeypatch):
    from vllm.v1.core.sched.request_queue import FCFSRequestQueue
    from robustbench.mgpu00.vllm_scheduler import LSSPSlaiVLLMScheduler, Scheduler
    adapter = object.__new__(LSSPSlaiVLLMScheduler)
    adapter.mgpu_metadata = {str(i): meta(i) for i in range(3)}
    adapter.mgpu_admitted = set()
    adapter.mgpu_clock = lambda: 1.002
    adapter.mgpu_batch = None
    adapter.mgpu_core = SlaiCore(1)
    adapter.running = [SimpleNamespace(request_id=str(i), num_prompt_tokens=3, num_computed_tokens=3,
                                      num_tokens_with_spec=4, next_decode_eligible_step=0) for i in range(3)]
    adapter.requests = {r.request_id: r for r in adapter.running}
    adapter.waiting = FCFSRequestQueue()
    adapter.skipped_waiting = FCFSRequestQueue()
    adapter.current_step = 0
    adapter.max_num_scheduled_tokens = 512
    adapter.max_num_running_reqs = 3
    adapter.mgpu_core.batch_completed(start_s=1., end_s=1.001,
                                     progressed=[adapter.candidate(r) for r in adapter.running], kv_utilization=0.)
    def native(self, **kwargs):
        self.current_step += 1
        assert len(self.running) == 3  # held work still occupies capacity, not evicted
        tokens = {r.request_id: 1 for r in self.running if self.current_step >= r.next_decode_eligible_step}
        return SimpleNamespace(num_scheduled_tokens=tokens, preempted_req_ids=set())
    monkeypatch.setattr(Scheduler, "schedule", native)
    output = adapter.schedule()
    assert len(output.num_scheduled_tokens) == 1
    assert len(adapter.running) == 3 and all(r.next_decode_eligible_step == 0 for r in adapter.running)
    adapter.mgpu_batch = None
    monkeypatch.setattr(Scheduler, "schedule", lambda *a, **k: SimpleNamespace(num_scheduled_tokens={}, preempted_req_ids=set()))
    with pytest.raises(UnsupportedSemantics, match="deviated"):
        adapter.schedule()


def test_workload_preparation_preserves_identity_and_lengths(tmp_path):
    import hashlib
    from robustbench.mgpu00.workload import prepare_window
    class CharacterTokenizer:
        def encode(self, text, **kwargs):
            return list(text.encode())
        def decode(self, ids):
            return bytes(ids).decode()
    records = [{"request_id": f"original-{i}", "request_index": i, "class_id": cls,
                "base_relative_arrival_s": i*.25, "base_slo_deadline_s": 2+i*.25,
                "input_tokens": 13+i, "output_tokens_target": 8+i, "weight": 1+i,
                "prompt_generation_seed": 50+i} for i, cls in enumerate(["tight", "medium", "loose"])]
    manifest = {"source": "fixture", "windows": [{"window_id": "w", "content_sha256": "a"*64, "requests": records}]}
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    prepared, provenance = prepare_window(path, expected_file_sha256=digest, window_id="w", tokenizer=CharacterTokenizer())
    for old, new in zip(records, prepared):
        assert new.metadata.request_id == old["request_id"]
        assert new.metadata.arrival_s == old["base_relative_arrival_s"]
        assert new.metadata.deadline_s == old["base_slo_deadline_s"]
        assert len(new.prompt_token_ids) == old["input_tokens"]
        assert new.output_tokens == old["output_tokens_target"]
        assert new.metadata.weight == old["weight"]
    assert provenance["manifest_file_sha256"] == digest
    with pytest.raises(ValueError, match="hash"):
        prepare_window(path, expected_file_sha256="b"*64, window_id="w", tokenizer=CharacterTokenizer())
