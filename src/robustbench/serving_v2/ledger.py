"""P1/0.1.0: request-local evidence ledger, not a scheduler or an allocator.

All times and execution facts are caller-supplied. Invalid calls poison the
ledger, preserve the last accepted state and prohibit further transitions.
Allocation observations describe one non-sharing pool; no capacity decisions
are inferred. This module intentionally depends only on the standard library.
"""
from dataclasses import asdict, dataclass, replace
import json
import math

SCHEMA = 'lssp-p1-ledger/0.1.0'


class ContractError(ValueError):
    """Invalid evidence or transition; the affected run must not continue."""


def _require(condition, reason):
    if not condition:
        raise ContractError(reason)


def _integer(value, minimum=0):
    _require(type(value) is int and value >= minimum, 'INVALID_INTEGER')


def _text(value):
    _require(type(value) is str and bool(value.strip()), 'INVALID_TEXT')


def _tokens(value):
    _require(type(value) is tuple, 'TOKENS_NOT_IMMUTABLE')
    for token in value:
        _integer(token)


@dataclass(frozen=True)
class ClockStamp:
    domain: str  # host + boot/time-namespace + clock identifier
    seconds: float
    category: str  # explicit boundary, never inferred from event kind

    def validate(self):
        _text(self.domain)
        _require(type(self.seconds) in (int, float) and
                 math.isfinite(self.seconds) and self.seconds >= 0, 'INVALID_TIME')
        _require(self.category in ('host_control', 'host_policy_feedback',
                 'gpu_execution', 'client_observation', 'server_observation'),
                 'UNKNOWN_CLOCK_CATEGORY')


@dataclass(frozen=True)
class TimingInterval:
    start: ClockStamp
    end: ClockStamp

    def validate(self):
        _require(type(self.start) is ClockStamp and type(self.end) is ClockStamp, 'INVALID_INTERVAL')
        self.start.validate()
        self.end.validate()
        _require(self.start.domain == self.end.domain and
                 self.start.category == self.end.category and
                 self.start.category in ('host_policy_feedback', 'gpu_execution') and
                 self.start.seconds <= self.end.seconds, 'INCOMPARABLE_INTERVAL')


@dataclass(frozen=True)
class RequestSpec:
    request_id: str
    engine_id: str
    prompt_tokens: int
    output_limit: int
    prompt_digest: str
    arrival: ClockStamp
    metadata: tuple[tuple[str, str], ...] = ()

    def validate(self):
        for value in (self.request_id, self.engine_id, self.prompt_digest):
            _text(value)
        _integer(self.prompt_tokens, 1)
        _integer(self.output_limit, 1)
        _require(type(self.arrival) is ClockStamp, 'INVALID_ARRIVAL')
        self.arrival.validate()
        _require(type(self.metadata) is tuple, 'MUTABLE_METADATA')
        keys = []
        for item in self.metadata:
            _require(type(item) is tuple and len(item) == 2, 'INVALID_METADATA')
            for value in item:
                _text(value)
            keys.append(item[0])
        _require(len(keys) == len(set(keys)), 'DUPLICATE_METADATA_KEY')


@dataclass(frozen=True)
class AllocationObservation:
    observation_id: str
    pool_id: str
    total_blocks: int
    system_blocks: int
    free_blocks: int
    owned_blocks: tuple[int, ...]
    other_allocated_blocks: int

    def validate(self):
        _text(self.observation_id)
        _text(self.pool_id)
        for value in (self.total_blocks, self.system_blocks,
                      self.free_blocks, self.other_allocated_blocks):
            _integer(value)
        _tokens(self.owned_blocks)
        _require(len(set(self.owned_blocks)) == len(self.owned_blocks), 'DUPLICATE_BLOCK')
        _require(all(b < self.total_blocks for b in self.owned_blocks), 'INVALID_BLOCK_ID')
        _require(self.total_blocks == self.system_blocks + self.free_blocks +
                 len(self.owned_blocks) + self.other_allocated_blocks,
                 'BLOCK_COUNTS_DO_NOT_RECONCILE')


@dataclass(frozen=True)
class Plan:
    plan_id: str
    batch_id: str
    epoch: int
    start: int
    end: int


@dataclass(frozen=True)
class Acknowledgment:
    plan_id: str
    epoch: int
    start: int
    executed_end: int  # confirmed contiguous prefix; may be short on failure
    samples: tuple[int, ...] = ()  # valid samples, not raw sampler padding
    success: bool = True
    quiescent: bool = True  # executor attests outstanding use has ended
    allocation: AllocationObservation | None = None


@dataclass(frozen=True)
class Snapshot:
    spec: RequestSpec
    state: str = 'WAITING'
    epoch: int = 0
    acknowledged: int = 0
    planned: int = 0
    pending: Plan | None = None
    generated: tuple[int, ...] = ()
    emitted: int = 0
    observed: int = 0
    resident: bool = False
    allocation: AllocationObservation | None = None
    replay_until: int = 0
    seen_prompt: tuple[int, ...] = ()
    prompt_work: int = 0
    repeated_prompt_work: int = 0
    retained_output_work: int = 0
    decode_work: int = 0
    discarded_samples: tuple[int, ...] = ()
    first_sample: ClockStamp | None = None
    disposition: str | None = None
    pending_disposition: str | None = None


class Ledger:
    """Synchronous request-local ledger; export() returns detached JSON data.

    Admission/preemption are external facts, not decisions. Successful final
    sampling reaches COMPLETE at the immutable output cap; early external
    completion is labeled STOPPED without assuming an approved EOS policy.
    Terminal resources remain visible until an explicit empty observation.
    """
    def __init__(self, run_id: str, provenance: str = 'cpu_fixture'):
        _text(run_id)
        _require(provenance in ('cpu_fixture', 'simulated', 'physical'), 'BAD_PROVENANCE')
        self._run_id = run_id
        self._provenance = provenance
        self._requests = {}
        self._engines = set()
        self._plan_ids = {}
        self._observations = set()
        self._clocks = {}
        self._events = []
        self._faults = []

    @property
    def run_id(self):
        return self._run_id

    @property
    def provenance(self):
        return self._provenance

    def snapshot(self, request_id: str) -> Snapshot:
        return self._requests[request_id]

    def export(self):
        return json.loads(json.dumps(dict(schema=SCHEMA, run_id=self.run_id,
            provenance=self.provenance, events=self._events, faults=self._faults),
            allow_nan=False))

    def enqueue(self, spec: RequestSpec, *, stamp: ClockStamp):
        return self._apply('enqueue', getattr(spec, 'request_id', ''), {'spec': spec}, stamp)

    def admit(self, request_id, allocation: AllocationObservation, *, stamp):
        return self._apply('admit', request_id, {'allocation': allocation}, stamp)

    def plan(self, request_id, plan: Plan, *, stamp):
        return self._apply('plan', request_id, {'plan': plan}, stamp)

    def acknowledge(self, request_id, ack: Acknowledgment, *, stamp):
        return self._apply('ack', request_id, {'ack': ack}, stamp)

    def hold(self, request_id, *, stamp):
        return self._apply('hold', request_id, {}, stamp)

    def wait(self, request_id, reason: str, *, stamp):
        return self._apply('wait', request_id, {'reason': reason}, stamp)

    def preempt(self, request_id, allocation: AllocationObservation, *, stamp):
        return self._apply('preempt', request_id, {'allocation': allocation}, stamp)

    def cancel(self, request_id, reason: str, *, stamp):
        return self._apply('cancel', request_id, {'reason': reason}, stamp)

    def fail(self, request_id, reason: str, *, stamp):
        return self._apply('fail', request_id, {'reason': reason}, stamp)

    def complete(self, request_id, reason: str, *, stamp):
        return self._apply('complete', request_id, {'reason': reason}, stamp)

    def quiesce(self, request_id, allocation: AllocationObservation, *, stamp):
        return self._apply('quiesce', request_id, {'allocation': allocation}, stamp)

    def release(self, request_id, allocation: AllocationObservation, *, stamp):
        return self._apply('release', request_id, {'allocation': allocation}, stamp)

    def emit(self, request_id, start: int, tokens: tuple[int, ...], *, stamp):
        return self._apply('emit', request_id, {'start': start, 'tokens': tokens}, stamp)

    def observe(self, request_id, start: int, tokens: tuple[int, ...], *, stamp):
        return self._apply('observe', request_id, {'start': start, 'tokens': tokens}, stamp)

    def annotate_interval(self, request_id, plan_id: str, interval: TimingInterval, *, stamp):
        return self._apply('interval', request_id, {'plan_id': plan_id, 'interval': interval}, stamp)

    def _apply(self, kind, rid, data, stamp):
        _require(not self._faults, 'LEDGER_POISONED')
        try:
            _text(rid)
            _require(type(stamp) is ClockStamp, 'INVALID_STAMP')
            stamp.validate()
            allowed = {'emit': ('server_observation',), 'observe': ('client_observation',),
                       'plan': ('host_control', 'host_policy_feedback'),
                       'ack': ('host_control', 'host_policy_feedback', 'server_observation')}
            _require(stamp.category in allowed.get(kind, ('host_control',)), 'WRONG_BOUNDARY_CATEGORY')
            old = self._requests.get(rid)
            clocks = dict(self._clocks)
            if kind == 'enqueue':
                spec = data['spec']
                _require(type(spec) is RequestSpec, 'INVALID_SPEC')
                spec.validate()
                _require(old is None and spec.engine_id not in self._engines, 'DUPLICATE_ID')
                clocks[(rid, spec.arrival.domain)] = spec.arrival.seconds
                new = Snapshot(spec)
            else:
                _require(old is not None, 'UNKNOWN_REQUEST')
                new = self._transition(old, kind, data, stamp)
            key = (rid, stamp.domain)
            _require(stamp.seconds >= clocks.get(key, 0), 'TIMESTAMP_CAUSALITY')
            clocks[key] = stamp.seconds
            # Validate all external objects before touching any ledger state.
            observation = data.get('allocation')
            if kind == 'ack':
                observation = data['ack'].allocation
            if observation is not None:
                _require(type(observation) is AllocationObservation, 'INVALID_ALLOCATION')
                observation.validate()
                _require(observation.observation_id not in self._observations, 'REUSED_OBSERVATION')
                if old and old.allocation:
                    previous = old.allocation
                    _require((observation.pool_id, observation.total_blocks, observation.system_blocks) ==
                             (previous.pool_id, previous.total_blocks, previous.system_blocks),
                             'POOL_IDENTITY_CHANGED')
            payload = {k: asdict(v) if hasattr(v, '__dataclass_fields__') else v
                       for k, v in data.items()}
            record = json.loads(json.dumps(dict(sequence=len(self._events), kind=kind,
                request_id=rid, stamp=asdict(stamp), data=payload, after=asdict(new)),
                allow_nan=False))
        except (ValueError, TypeError, AttributeError, KeyError) as exc:
            reason = str(exc) if isinstance(exc, ContractError) else 'MALFORMED_INPUT'
            self._faults.append(dict(kind=kind, request_id=rid if type(rid) is str else None,
                                    reason=reason, after_sequence=len(self._events)-1))
            raise ContractError(reason) from exc
        self._requests[rid] = new
        self._engines.add(new.spec.engine_id)
        self._clocks = clocks
        if kind == 'plan':
            self._plan_ids[data['plan'].plan_id] = rid
        if observation is not None:
            self._observations.add(observation.observation_id)
        self._events.append(record)
        return new

    def _transition(self, s, kind, data, stamp):
        if kind == 'interval':
            _text(data['plan_id'])
            _require(self._plan_ids.get(data['plan_id']) == s.spec.request_id, 'UNBOUND_INTERVAL')
            interval = data['interval']
            _require(type(interval) is TimingInterval, 'INVALID_INTERVAL')
            interval.validate()
            if stamp.domain == interval.end.domain:
                _require(interval.end.seconds <= stamp.seconds, 'FUTURE_INTERVAL')
            return s
        if kind in ('emit', 'observe'):
            start, tokens = data['start'], data['tokens']
            _integer(start)
            _tokens(tokens)
            _require(bool(tokens), 'EMPTY_TRANSPORT_EVENT')
            offset = s.emitted if kind == 'emit' else s.observed
            ceiling = len(s.generated) if kind == 'emit' else s.emitted
            _require(start == offset and start + len(tokens) <= ceiling and
                     s.generated[start:start+len(tokens)] == tokens, 'PREFIX_MISMATCH')
            if kind == 'emit':
                _require(s.pending_disposition is None and s.disposition not in ('CANCELLED', 'FAILED'),
                         'EMISSION_AFTER_ABORT')
            return replace(s, **{('emitted' if kind == 'emit' else 'observed'): start+len(tokens)})
        if kind == 'release':
            _require(s.state == 'TERMINAL' and s.allocation is not None and
                     bool(s.allocation.owned_blocks), 'ILLEGAL_RELEASE')
            _require(type(data['allocation']) is AllocationObservation and
                     not data['allocation'].owned_blocks, 'NONEMPTY_RELEASE')
            return replace(s, allocation=data['allocation'])
        _require(s.state != 'TERMINAL', 'TERMINAL_TRANSITION')
        if kind == 'admit':
            _require(s.state in ('WAITING', 'RECOMPUTE_WAITING'), 'ILLEGAL_ADMISSION')
            _require(type(data['allocation']) is AllocationObservation, 'INVALID_ALLOCATION')
            return replace(s, state='ADMITTED', resident=True, allocation=data['allocation'])
        if kind == 'wait':
            _require(s.state in ('WAITING', 'RECOMPUTE_WAITING'), 'ILLEGAL_WAIT')
            _text(data['reason'])
            return s
        if kind == 'hold':
            _require(s.state == 'DECODE_READY', 'ILLEGAL_HOLD')
            return s
        if kind == 'plan':
            p = data['plan']
            _require(type(p) is Plan, 'INVALID_PLAN')
            for value in (p.plan_id, p.batch_id):
                _text(value)
            for value in (p.epoch, p.start, p.end):
                _integer(value)
            _require(p.plan_id not in self._plan_ids, 'DUPLICATE_PLAN_ID')
            _require(s.state in ('ADMITTED', 'PREFILL_PAUSED', 'RECOMPUTE_PAUSED', 'DECODE_READY'),
                     'ILLEGAL_PLAN')
            _require(p.epoch == s.epoch and p.start == s.acknowledged and
                     p.start < p.end <= s.spec.prompt_tokens + len(s.generated), 'INVALID_SPAN')
            return replace(s, state='IN_FLIGHT', planned=p.end, pending=p)
        if kind == 'preempt':
            _require(s.state in ('ADMITTED', 'PREFILL_PAUSED', 'RECOMPUTE_PAUSED', 'DECODE_READY'),
                     'ILLEGAL_PREEMPTION')
            _require(type(data['allocation']) is AllocationObservation and
                     not data['allocation'].owned_blocks, 'PREEMPTION_WITH_OWNED_BLOCKS')
            return replace(s, state='RECOMPUTE_WAITING', epoch=s.epoch+1,
                           acknowledged=0, planned=0, resident=False,
                           replay_until=s.spec.prompt_tokens+len(s.generated),
                           allocation=data['allocation'])
        if kind in ('cancel', 'fail', 'complete'):
            _text(data['reason'])
            _require(s.pending_disposition is None, 'DUPLICATE_TERMINAL_INTENT')
            disposition = {'cancel':'CANCELLED', 'fail':'FAILED', 'complete':'STOPPED'}[kind]
            if kind == 'complete':
                _require(s.state == 'DECODE_READY', 'ILLEGAL_EARLY_COMPLETION')
            if s.pending is not None:
                return replace(s, state='CANCEL_PENDING' if kind == 'cancel' else 'FAILED_PENDING',
                               pending_disposition=disposition)
            return replace(s, state='TERMINAL', disposition=disposition, resident=False)
        if kind == 'quiesce':
            _require(s.state in ('CANCEL_PENDING', 'FAILED_PENDING') and s.pending is None,
                     'QUIESCENCE_BEFORE_ACK')
            _require(type(data['allocation']) is AllocationObservation and
                     not data['allocation'].owned_blocks, 'NONEMPTY_RELEASE')
            return replace(s, state='TERMINAL', disposition=s.pending_disposition,
                           pending_disposition=None, resident=False, allocation=data['allocation'])
        _require(kind == 'ack', 'UNKNOWN_EVENT')
        a = data['ack']
        _require(type(a) is Acknowledgment, 'INVALID_ACK')
        _require(type(a.success) is bool and type(a.quiescent) is bool, 'INVALID_ACK_FLAGS')
        _tokens(a.samples)
        for value in (a.epoch, a.start, a.executed_end):
            _integer(value)
        p = s.pending
        _require(p is not None and s.state in ('IN_FLIGHT', 'CANCEL_PENDING', 'FAILED_PENDING'),
                 'UNBOUND_ACK')
        _require((a.plan_id, a.epoch, a.start) == (p.plan_id, p.epoch, p.start) and
                 p.start <= a.executed_end <= p.end, 'ACK_BINDING')
        if a.success:
            _require(a.executed_end == p.end, 'SHORT_SUCCESS_ACK')
        else:
            _require(not a.samples, 'FAILED_ACK_HAS_SAMPLES')
        end_context = s.spec.prompt_tokens + len(s.generated)
        expected_samples = int(a.executed_end == end_context)
        if a.success and s.pending_disposition is None:
            _require(a.quiescent and len(a.samples) == expected_samples, 'INVALID_SAMPLE_COUNT')
        else:
            _require(len(a.samples) <= expected_samples, 'INVALID_DISCARDED_SAMPLES')
        prompt = set(range(p.start, min(a.executed_end, s.spec.prompt_tokens)))
        retained = max(0, min(a.executed_end, s.replay_until) - max(p.start, s.spec.prompt_tokens))
        decode = a.executed_end-p.start-len(prompt)-retained
        updates = dict(acknowledged=a.executed_end, planned=a.executed_end, pending=None,
            seen_prompt=tuple(sorted(set(s.seen_prompt) | prompt)),
            prompt_work=s.prompt_work+len(prompt),
            repeated_prompt_work=s.repeated_prompt_work+len(prompt & set(s.seen_prompt)),
            retained_output_work=s.retained_output_work+retained, decode_work=s.decode_work+decode,
            allocation=a.allocation if a.allocation is not None else s.allocation)
        abort = s.pending_disposition or ('FAILED' if not a.success else None)
        if abort:
            updates.update(discarded_samples=s.discarded_samples+a.samples,
                           state='TERMINAL' if a.quiescent else ('CANCEL_PENDING' if abort == 'CANCELLED' else 'FAILED_PENDING'),
                           disposition=abort if a.quiescent else None,
                           pending_disposition=None if a.quiescent else abort,
                           resident=not a.quiescent)
        else:
            generated = s.generated+a.samples
            _require(len(generated) <= s.spec.output_limit, 'OUTPUT_LIMIT')
            state = ('DECODE_READY' if a.samples else
                     ('RECOMPUTE_PAUSED' if s.epoch else 'PREFILL_PAUSED'))
            done = len(generated) == s.spec.output_limit
            updates.update(generated=generated, state='TERMINAL' if done else state,
                           disposition='COMPLETE' if done else None,
                           resident=not done,
                           first_sample=s.first_sample or (stamp if a.samples else None))
        return replace(s, **updates)
