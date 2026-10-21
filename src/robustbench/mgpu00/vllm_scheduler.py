"""Version-pinned vLLM 0.27.1 adapter. Import only in a vLLM server.

Every batch is checked against the decision core. A mismatch aborts validation;
it is never reported as faithful SLAI or a completed scientific observation.
"""
import importlib.metadata
import hashlib
import inspect
import json
import os
import sys
import time

from vllm.v1.core.sched.scheduler import Scheduler

from .metadata import RequestMetadata, TBT
from .slai import Candidate, SlaiCore, UnsupportedSemantics, validate_deployment


class InstrumentedNativeScheduler(Scheduler):
    mechanism = "native_fcfs"

    def __init__(self, *args, **kwargs):
        if importlib.metadata.version("vllm") != "0.27.1":
            raise UnsupportedSemantics("Adapter is pinned to vLLM 0.27.1")
        with open(inspect.getfile(Scheduler), "rb") as stream:
            if hashlib.sha256(stream.read()).hexdigest() != "c67bda2886b52865ddafabaae7d797c359e930752f374421a33e537d94a5f45a":
                raise UnsupportedSemantics("Installed vLLM scheduler source differs from the inspected build")
        super().__init__(*args, **kwargs)
        self.mgpu_metadata = {}
        self.mgpu_admitted = set()
        self.mgpu_clock = time.monotonic

    def event(self, kind, **fields):
        print("MGPU00_EVENT " + json.dumps({"event": kind, "mechanism": self.mechanism,
              "monotonic_s": self.mgpu_clock(), "pid": os.getpid(), **fields}, sort_keys=True),
              file=sys.stderr, flush=True)

    def candidate(self, request):
        return Candidate(request.request_id, self.mgpu_metadata[request.request_id], request.num_prompt_tokens)

    def add_request(self, request):
        metadata = RequestMetadata.from_request(request)
        if any(m.request_id == metadata.request_id for m in self.mgpu_metadata.values()):
            raise ValueError("Duplicate MGPU00 request identity")
        self.mgpu_metadata[request.request_id] = metadata
        super().add_request(request)
        self.event("received", engine_id=request.request_id, metadata=metadata.xargs())

    def record_output(self, output):
        for rid, tokens in output.num_scheduled_tokens.items():
            m = self.mgpu_metadata[rid]
            if rid not in self.mgpu_admitted:
                self.mgpu_admitted.add(rid)
                self.event("admitted", engine_id=rid, request_id=m.request_id, class_id=m.class_id)
        self.event("scheduled", tokens=output.num_scheduled_tokens,
                   request_ids={rid: self.mgpu_metadata[rid].request_id for rid in output.num_scheduled_tokens})

    def schedule(self, throttle_prefills=False):
        output = super().schedule(throttle_prefills=throttle_prefills)
        self.record_output(output)
        return output


class LSSPSlaiVLLMScheduler(InstrumentedNativeScheduler):
    mechanism = "slai_mgpu00_checked"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        validate_deployment(self.vllm_config)
        if self.scheduler_config.policy != "priority":
            raise UnsupportedSemantics("SLAI requires priority admission")
        if "LSSP_MGPU00_DECODE_LIMIT" not in os.environ:
            raise ValueError("Explicit, recorded decode limit required; no implicit default")
        self.mgpu_core = SlaiCore(int(os.environ["LSSP_MGPU00_DECODE_LIMIT"]))
        self.mgpu_batch = None

    def add_request(self, request):
        metadata = RequestMetadata.from_request(request)
        if metadata.ordinal >= 1_000_000 or request.num_prompt_tokens > self.max_model_len:
            raise ValueError("Admission key outside explicitly supported bounds")
        tier = sorted(set(TBT.values())).index(TBT[metadata.class_id])
        # Exact bounded integer encoding of (tier, prompt length, original ordinal).
        request.priority = ((tier * (self.max_model_len + 1) + request.num_prompt_tokens) *
                            1_000_000 + metadata.ordinal)
        super().add_request(request)
        self.event("priority_set", request_id=metadata.request_id, class_id=metadata.class_id,
                   tbt_seconds=TBT[metadata.class_id], priority=request.priority,
                   admission_key=metadata.admission_key(request.num_prompt_tokens))

    def schedule(self, throttle_prefills=False):
        if self.mgpu_batch is not None:
            raise UnsupportedSemantics("Overlapping batches violate the synchronous timing contract")
        if self.skipped_waiting:
            raise UnsupportedSemantics("Skipped/resumable waiting state outside checked domain")
        if any(r.num_computed_tokens < r.num_prompt_tokens for r in self.running):
            raise UnsupportedSemantics("Continuing partial prefill is not supported")
        if any(r.num_tokens_with_spec - r.num_computed_tokens != 1 for r in self.running):
            raise UnsupportedSemantics("Expected one-token autoregressive decode")
        decoding = [self.candidate(r) for r in self.running]
        waiting = [self.candidate(r) for r in self.waiting]
        now = self.mgpu_clock()
        expected, admitted, held = self.mgpu_core.plan(
            now_s=now, decoding=decoding, waiting=waiting,
            token_budget=self.max_num_scheduled_tokens, active_count=len(self.running),
            max_active=self.max_num_running_reqs)
        held_ids = {r.engine_id for r in held}
        admitted_ids = {r.engine_id for r in admitted}
        deferred_waiting = [r for r in self.waiting if r.request_id not in admitted_ids]
        self.waiting.remove_requests(deferred_waiting)
        gates = {r.request_id: r.next_decode_eligible_step for r in self.running if r.request_id in held_ids}
        # Preserve held requests in running/KV state and active capacity. Use the
        # installed scheduler's explicit skip-without-eviction eligibility gate.
        for r in self.running:
            if r.request_id in held_ids:
                r.next_decode_eligible_step = self.current_step + 2
        try:
            output = Scheduler.schedule(self, throttle_prefills=throttle_prefills)
        finally:
            for r in self.running:
                if r.request_id in gates:
                    r.next_decode_eligible_step = gates[r.request_id]
            for r in deferred_waiting:
                self.waiting.add_request(r)
        if output.preempted_req_ids or output.num_scheduled_tokens != expected:
            self.event("semantic_mismatch", expected=expected, actual=output.num_scheduled_tokens)
            raise UnsupportedSemantics("Native KV/token scheduling deviated from SLAI plan; no result is valid")
        self.event("decision_verified", now_s=now, expected_tokens=expected,
                   decoding=[{"request_id": r.metadata.request_id, "class_id": r.metadata.class_id,
                              "lst_s": self.mgpu_core.lst[r.engine_id], "scheduled": r.engine_id in expected}
                             for r in decoding])
        for r in held:
            self.event("held", engine_id=r.engine_id, request_id=r.metadata.request_id,
                       class_id=r.metadata.class_id, lst_s=self.mgpu_core.lst[r.engine_id],
                       now_s=now, decode_limit=self.mgpu_core.decode_limit)
        self.record_output(output)
        if expected:
            self.mgpu_batch = (now, [self.candidate(self.requests[rid]) for rid in expected])
        return output

    def update_from_output(self, scheduler_output, model_runner_output):
        output = super().update_from_output(scheduler_output, model_runner_output)
        if self.mgpu_batch is not None:
            start, progressed = self.mgpu_batch
            self.mgpu_core.batch_completed(start_s=start, end_s=self.mgpu_clock(), progressed=progressed,
                                            kv_utilization=self.get_kv_cache_usage())
            self.event("batch_completed", batch_seconds=self.mgpu_core.total_batch_s / self.mgpu_core.batches,
                       clock_contract="monotonic batch completion; cumulative observed batch duration")
            self.mgpu_batch = None
        return output
