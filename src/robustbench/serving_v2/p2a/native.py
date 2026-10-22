"""Strict native-FCFS CPU gate, NOT a policy injection or physical ACK bridge.

Scheduler.schedule mutates native state even on disagreement. Every refusal or
invalid ACK therefore stops this instance permanently; no rollback or retry.
Only explicitly synthetic, complete, quiescent ACKs are supported. Native KV
observations are read, not allocated by this adapter. No P1 code is modified.
"""
from copy import deepcopy
from dataclasses import asdict
import hashlib
import importlib.metadata
import json
from pathlib import Path

from ..ledger import (Ledger, RequestSpec, ClockStamp, AllocationObservation,
                      Plan, Acknowledgment)
from .types import (Span, Proposal, Acceptance, Rejection, RunnerAck, Reason,
                    BoundaryError)
from .pins import PINS


def require(condition, message):
    if not condition:
        raise BoundaryError(message)


def verify_sources():
    require(importlib.metadata.version('vllm') == '0.27.1', 'vLLM version')
    import vllm
    root = Path(vllm.__file__).parent
    for name, digest in PINS.items():
        require(hashlib.sha256((root/name).read_bytes()).hexdigest() == digest,
                'source mismatch: '+name)
    return dict(PINS)


def _nat(x, minimum=0):
    return type(x) is int and x >= minimum


class NativeBoundary:
    """Owns an initially empty native Scheduler and private P1 ledger.

    Callers must surrender mutation of the scheduler. Each boundary checks live
    state against its ledger; journal exports are detached. This is diagnostic
    instrumentation, not a timed-serving integration or a security sandbox.
    """
    def __init__(self, scheduler, run_id, *, enabled=False):
        require(enabled is True, 'explicit CPU opt-in required')
        self.source_hashes = verify_sources()
        from vllm.v1.core.sched.scheduler import Scheduler
        require(type(scheduler) is Scheduler, 'unmodified native Scheduler required')
        self.s = scheduler
        self._ledger = Ledger(run_id)
        self._ids = {}  # native -> immutable application ID
        self._refs = {}
        self._batches = []
        self._faults = []
        self._used = set()
        self._pending = None
        self._obs = 0
        self._config()
        self._profile = self._configuration()
        require(not scheduler.requests and not scheduler.running and
                not scheduler.waiting and not scheduler.skipped_waiting, 'nonempty scheduler')

    def _config(self):
        s = self.s
        c = s.vllm_config
        sc = c.scheduler_config
        pc = c.parallel_config
        require(str(c.device_config.device) == 'cpu', 'CPU objects only')
        require(sc.policy == 'fcfs' and not sc.async_scheduling and
                sc.enable_chunked_prefill and sc.long_prefill_token_threshold == 0 and
                sc.watermark == 0 and c.max_concurrent_batches == 1,
                'unsupported scheduler configuration')
        require(pc.tensor_parallel_size == pc.pipeline_parallel_size ==
                pc.data_parallel_size == 1, 'distributed unsupported')
        require(c.speculative_config is None and c.lora_config is None and
                c.kv_transfer_config is None and c.ec_transfer_config is None and
                not c.model_config.is_multimodal_model and not c.model_config.is_encoder_decoder,
                'unsupported model/connector/speculation')
        require(c.use_v2_model_runner and not c.cache_config.enable_prefix_caching and
                len(s.kv_cache_config.kv_cache_groups) == 1, 'unsupported runner/KV mode')
        from vllm.v1.kv_cache_interface import FullAttentionSpec
        require(type(s.kv_cache_config.kv_cache_groups[0].kv_cache_spec) is FullAttentionSpec,
                'full attention only')
        require(s.scheduler_reserve_full_isl, 'full input fit required')

    def _configuration(self):
        return dict(token_budget=self.s.max_num_scheduled_tokens,
                    active_limit=self.s.max_num_running_reqs, max_model_len=self.s.max_model_len,
                    block_size=self.s.block_size,
                    total_blocks=self.s.kv_cache_manager.block_pool.num_gpu_blocks,
                    policy='fcfs', runner='v2', device='cpu', prefix_caching=False,
                    reserve_full_input=True, sampling='fixed-output-synthetic',
                    parallelism=[1, 1, 1])

    def _stamp(self, stamp):
        require(type(stamp) is ClockStamp, 'clock type')
        stamp.validate()
        require(stamp.category == 'host_control', 'host control observation only')

    def _live(self):
        require(not self._faults, 'boundary stopped')
        self._config()
        require(self._configuration() == self._profile, 'configuration drift')

    def _stop(self, reason, detail):
        self._faults.append({'reason': reason.value, 'detail': str(detail)})

    def enqueue(self, spec, prompt_ids, *, stamp):
        """Fixed-output synthetic request. No EOS/model/tokenizer policy is chosen."""
        try:
            self._live()
            require(self._pending is None, 'inflight batch')
            self._stamp(stamp)
            require(type(spec) is RequestSpec, 'spec type')
            spec.validate()
            require(type(prompt_ids) is tuple and len(prompt_ids) == spec.prompt_tokens and
                    all(_nat(x) for x in prompt_ids), 'prompt identity')
            digest = hashlib.sha256(json.dumps(list(prompt_ids), separators=(',', ':')).encode()).hexdigest()
            require(digest == spec.prompt_digest, 'prompt digest')
            require(spec.prompt_tokens+spec.output_limit <= self.s.max_model_len,
                    'context limit')
            staged = deepcopy(self._ledger)
            staged.enqueue(spec, stamp=stamp)
            from vllm.v1.request import Request
            from vllm.sampling_params import SamplingParams
            r = Request(request_id=spec.engine_id, prompt_token_ids=list(prompt_ids),
                        pooling_params=None, arrival_time=spec.arrival.seconds,
                        sampling_params=SamplingParams(max_tokens=spec.output_limit, ignore_eos=True))
            self.s.add_request(r)
            self._ledger = staged
            self._ids[spec.engine_id] = spec.request_id
            self._refs[spec.engine_id] = r
        except Exception as e:
            self._stop(Reason.INVALID, e)
            raise BoundaryError(str(e)) from e

    def _snapshot(self):
        s = self.s
        pool = s.kv_cache_manager.block_pool
        rows = {}
        for rid, r in self._refs.items():
            rows[rid] = dict(prompt=r.num_prompt_tokens, limit=r.max_tokens,
                computed=r.num_computed_tokens, inflight=r.num_in_flight_tokens,
                output=list(r.output_token_ids), status=r.status.name,
                arrival=r.arrival_time,
                blocks=list(s.kv_cache_manager.get_block_ids(rid)[0]),
                preemptions=r.num_preemptions)
        return dict(rows=rows, running=[r.request_id for r in s.running],
                    waiting=[r.request_id for r in s.waiting],
                    live=list(s.requests), skipped=[r.request_id for r in s.skipped_waiting],
                    total_blocks=pool.num_gpu_blocks, system_blocks=1,
                    free_blocks=pool.get_num_free_blocks(), block_size=s.block_size)

    def _observation(self, rid, snapshot):
        self._obs += 1
        owned = tuple(snapshot['rows'][rid]['blocks'])
        return AllocationObservation(f'obs-{self._obs}', 'native-pool-0',
            snapshot['total_blocks'], 1, snapshot['free_blocks'], owned,
            snapshot['total_blocks']-1-snapshot['free_blocks']-len(owned))

    def _wire(self, output):
        cached = output.scheduled_cached_reqs
        return dict(counts=dict(output.num_scheduled_tokens), total=output.total_num_scheduled_tokens,
            new=[dict(id=r.req_id, start=r.num_computed_tokens) for r in output.scheduled_new_reqs],
            cached=[dict(id=rid, start=start) for rid, start in
                    zip(cached.req_ids, cached.num_computed_tokens, strict=True)],
            resumed=sorted(cached.resumed_req_ids), preempted=sorted(output.preempted_req_ids or []),
            speculative=bool(output.scheduled_spec_decode_tokens),
            encoder=bool(output.scheduled_encoder_inputs),
            connector=output.kv_connector_metadata is not None)

    def _accepted(self, proposal, before, after, wire):
        require(not any(wire[k] for k in ('resumed','preempted','speculative','encoder','connector')),
                'unsupported native action')
        raw = wire['new']+wire['cached']
        require(len(raw) == len(wire['counts']) and len({r['id'] for r in raw}) == len(raw),
                'native request identity')
        require({r['id'] for r in raw} == set(wire['counts']), 'missing native request')
        starts = {r['id']:r['start'] for r in raw}
        spans = tuple(Span(rid, 0, starts[rid], starts[rid]+n) for rid,n in wire['counts'].items())
        require(spans == proposal.spans, 'native differs from proposed work')
        require(wire['total'] == sum(x.end-x.start for x in spans) <= proposal.token_budget,
                'native budget')
        require(len(after['running']) <= proposal.active_limit, 'active slots')
        for span in spans:
            b, a = before['rows'][span.request_id], after['rows'][span.request_id]
            require(b['computed'] == span.start and a['computed'] == span.end and
                    a['inflight'] == span.end-span.start and a['output'] == b['output'],
                    'native position/progress mismatch')
        mask = tuple(x.end == before['rows'][x.request_id]['prompt']+
                     len(before['rows'][x.request_id]['output']) for x in spans)
        return Acceptance(proposal.batch_id, self.s.current_step, spans,
                          wire['total'], len(after['running']), mask)

    def schedule(self, proposal, *, stamp):
        called = False
        record = None
        reason = Reason.INVALID
        try:
            self._live()
            self._stamp(stamp)
            require(self._pending is None, 'previous batch not acknowledged')
            require(type(proposal) is Proposal and type(proposal.batch_id) is str and
                    bool(proposal.batch_id.strip()) and proposal.batch_id not in self._used,
                    'batch identity')
            require(type(proposal.spans) is tuple and bool(proposal.spans) and
                    all(type(x) is Span for x in proposal.spans), 'span types')
            require(_nat(proposal.token_budget,1) and _nat(proposal.active_limit,1) and
                    proposal.token_budget == self.s.max_num_scheduled_tokens and
                    proposal.active_limit == self.s.max_num_running_reqs, 'budget/slot configuration')
            require(len({x.request_id for x in proposal.spans}) == len(proposal.spans), 'duplicate span')
            before = self._snapshot()
            require(not before['skipped'], 'skipped waiting unsupported')
            for rid in before['live']:
                r = before['rows'][rid]
                snap = self._ledger.snapshot(self._ids[rid])
                require(hashlib.sha256(json.dumps(list(self._refs[rid].prompt_token_ids),
                    separators=(',', ':')).encode()).hexdigest() == snap.spec.prompt_digest and
                    r['prompt'] == snap.spec.prompt_tokens and r['limit'] == snap.spec.output_limit and
                    r['arrival'] == snap.spec.arrival.seconds, 'immutable request drift')
                require(r['computed'] == snap.acknowledged and r['output'] == list(snap.generated)
                        and r['inflight'] == 0 and r['preemptions'] == 0, 'native/ledger drift')
            for x in proposal.spans:
                require(x.request_id in before['live'] and _nat(x.epoch) and x.epoch == 0 and
                        _nat(x.start) and _nat(x.end,1) and x.start < x.end, 'span binding')
                r = before['rows'][x.request_id]
                require(x.start == r['computed'] and x.end <= r['prompt']+len(r['output']), 'span extent')
            require(sum(x.end-x.start for x in proposal.spans) <= proposal.token_budget, 'proposal budget')
            reason = Reason.CAPACITY
            size = before['block_size']
            bound = sum((r['prompt']+r['limit']+size-1)//size for rid,r in before['rows'].items()
                        if rid in before['live'])
            require(bound <= before['total_blocks']-1, 'lifetime no-pressure bound')
            reason = Reason.MODIFIED
            record = dict(proposal=asdict(proposal), before=before,
                          ledger_start=len(self._ledger.export()['events']))
            self._batches.append(record)
            self._used.add(proposal.batch_id)
            called = True
            output = self.s.schedule()
            after = self._snapshot()
            wire = self._wire(output)
            record.update(native=wire, scheduled=after, step=self.s.current_step)
            accepted = self._accepted(proposal, before, after, wire)
            staged = deepcopy(self._ledger)
            for x in accepted.spans:
                app = self._ids[x.request_id]
                if staged.snapshot(app).state == 'WAITING':
                    staged.admit(app, self._observation(x.request_id, after), stamp=stamp)
                staged.plan(app, Plan(f'{proposal.batch_id}/{x.request_id}', proposal.batch_id,
                                     x.epoch,x.start,x.end), stamp=stamp)
            self._ledger = staged
            record['acceptance'] = asdict(accepted)
            record['ledger_planned'] = len(staged.export()['events'])
            self._pending = (accepted, output, record)
            return accepted
        except Exception as e:
            rejection = Rejection(getattr(proposal,'batch_id',''), reason, str(e), called)
            if record is not None:
                record['rejection'] = asdict(rejection)
            self._stop(reason, e)
            return rejection

    def acknowledge(self, ack, runner_output, *, stamp):
        """Consume actual native output type + explicit SYNTHETIC span attestation.

        No plan-derived ACK helper is supplied. Failed/nonquiescent/partial work
        is retained as an invalid record and stops the batch without P1 commits.
        """
        record = None
        try:
            self._live()
            self._stamp(stamp)
            require(self._pending is not None, 'missing accepted batch')
            accepted, native, record = self._pending
            require(type(ack) is RunnerAck, 'ACK type')
            record['ack_attempt'] = asdict(ack)
            require(type(ack.spans) is tuple and all(type(x) is Span and
                    type(x.request_id) is str and _nat(x.epoch) and _nat(x.start) and
                    _nat(x.end,1) for x in ack.spans), 'ACK span types')
            require(ack.provenance == 'synthetic_cpu' and ack.success is True and
                    ack.quiescent is True, 'unsupported/partial/nonquiescent ACK')
            require(type(ack.native_step) is int and ack.batch_id == accepted.batch_id and
                    ack.native_step == accepted.native_step and ack.spans == accepted.spans and
                    type(ack.sample_mask) is tuple and all(type(v) is bool for v in ack.sample_mask)
                    and ack.sample_mask == accepted.sample_mask, 'ACK batch/span/mask binding')
            from vllm.v1.outputs import ModelRunnerOutput
            require(type(runner_output) is ModelRunnerOutput, 'native runner output type')
            ids = [x.request_id for x in accepted.spans]
            runner_ids = runner_output.req_ids
            require(type(runner_ids) is list and all(type(r) is str for r in runner_ids) and
                    len(runner_ids) == len(ids) and len(set(runner_ids)) == len(ids) and
                    set(runner_ids) == set(ids) and type(runner_output.req_id_to_index) is dict and
                    all(_nat(i) for i in runner_output.req_id_to_index.values()) and
                    runner_output.req_id_to_index == {rid:i for i,rid in enumerate(runner_ids)},
                    'runner identities')
            raw_samples = runner_output.sampled_token_ids
            record['runner'] = dict(ids=list(runner_ids),
                                   index=dict(runner_output.req_id_to_index), samples=deepcopy(raw_samples))
            require(type(raw_samples) is list and len(raw_samples) == len(ids), 'runner row count')
            # V2 sorts query rows; ID/index binding, not row position, identifies work.
            samples = [raw_samples[runner_output.req_id_to_index[rid]] for rid in ids]
            require(all(type(row) is list and len(row) == int(mask) and all(_nat(t) for t in row)
                        for row,mask in zip(samples,accepted.sample_mask,strict=True)), 'runner sampling mask')
            require(not runner_output.kv_connector_output and not runner_output.ec_connector_output
                    and not runner_output.pooler_output and not runner_output.num_nans_in_logits,
                    'unsupported runner diagnostics')
            staged = deepcopy(self._ledger)
            for x,tokens in zip(accepted.spans,samples,strict=True):
                staged.acknowledge(self._ids[x.request_id], Acknowledgment(
                    f'{accepted.batch_id}/{x.request_id}', x.epoch,x.start,x.end,tuple(tokens),
                    allocation=self._observation(x.request_id, record['scheduled'])), stamp=stamp)
            self.s.update_from_output(native,runner_output)
            after = self._snapshot()
            record['executed'] = after
            for x in accepted.spans:
                rid = x.request_id
                app = self._ids[rid]
                snap = staged.snapshot(app)
                r = after['rows'][x.request_id]
                require(hashlib.sha256(json.dumps(list(self._refs[rid].prompt_token_ids),
                    separators=(',', ':')).encode()).hexdigest() == snap.spec.prompt_digest and
                    r['prompt'] == snap.spec.prompt_tokens and r['limit'] == snap.spec.output_limit and
                    r['arrival'] == snap.spec.arrival.seconds, 'immutable request drift')
                require(r['computed'] == snap.acknowledged and r['inflight'] == 0 and
                        r['output'] == list(snap.generated), 'native update disagreement')
                if snap.state == 'TERMINAL':
                    require(x.request_id not in after['live'] and not r['blocks'], 'native completion mismatch')
                    staged.release(app,self._observation(x.request_id,after),stamp=stamp)
            self._ledger = staged
            record['ack'] = asdict(ack)
            record['ledger_end'] = len(staged.export()['events'])
            self._pending = None
        except Exception as e:
            self._stop(Reason.ACK,e)
            raise BoundaryError(str(e)) from e

    def export(self):
        return json.loads(json.dumps(dict(schema='lssp-p2a-boundary/0.1.0', provenance='synthetic_cpu',
            source_hashes=self.source_hashes, configuration=self._profile, registry=dict(self._ids),
            batches=self._batches, faults=self._faults, ledger=self._ledger.export()), allow_nan=False))
