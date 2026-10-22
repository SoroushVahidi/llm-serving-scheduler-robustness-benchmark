"""Independent P1 journal referee (stdlib only; NO ledger imports).

Declarative legal-edge table + per-epoch sets of confirmed positions. Output
history and a work-position multiset reconstruct every advertised snapshot.
Input is untrusted JSON, not ledger objects. A valid prefix is not a complete
run, and neither result establishes model-runner or physical execution.
"""
from dataclasses import dataclass
import math
import json

# External observations advance this graph; it contains no scheduler ordering.
EDGES = {
    'admit': {'WAITING', 'RECOMPUTE_WAITING'},
    'wait': {'WAITING', 'RECOMPUTE_WAITING'},
    'plan': {'ADMITTED', 'PREFILL_PAUSED', 'RECOMPUTE_PAUSED', 'DECODE_READY'},
    'hold': {'DECODE_READY'},
    'preempt': {'ADMITTED', 'PREFILL_PAUSED', 'RECOMPUTE_PAUSED', 'DECODE_READY'},
    'ack': {'IN_FLIGHT', 'CANCEL_PENDING', 'FAILED_PENDING'},
    'cancel': {'WAITING', 'RECOMPUTE_WAITING', 'ADMITTED', 'PREFILL_PAUSED',
               'RECOMPUTE_PAUSED', 'DECODE_READY', 'IN_FLIGHT'},
    'fail': {'WAITING', 'RECOMPUTE_WAITING', 'ADMITTED', 'PREFILL_PAUSED',
             'RECOMPUTE_PAUSED', 'DECODE_READY', 'IN_FLIGHT'},
    'complete': {'DECODE_READY'},
    'quiesce': {'CANCEL_PENDING', 'FAILED_PENDING'},
    'release': {'TERMINAL'},
    'emit': {'WAITING', 'RECOMPUTE_WAITING', 'ADMITTED', 'PREFILL_PAUSED',
             'RECOMPUTE_PAUSED', 'DECODE_READY', 'IN_FLIGHT', 'TERMINAL'},
    'observe': {'WAITING', 'RECOMPUTE_WAITING', 'ADMITTED', 'PREFILL_PAUSED',
                'RECOMPUTE_PAUSED', 'DECODE_READY', 'IN_FLIGHT',
                'CANCEL_PENDING', 'FAILED_PENDING', 'TERMINAL'},
}
EDGES['interval'] = set().union(*EDGES.values())
FIELDS = {'interval': {'plan_id', 'interval'}, 'enqueue': {'spec'}, 'admit': {'allocation'}, 'plan': {'plan'},
          'ack': {'ack'}, 'hold': set(), 'wait': {'reason'}, 'preempt': {'allocation'},
          'cancel': {'reason'}, 'fail': {'reason'}, 'complete': {'reason'},
          'quiesce': {'allocation'}, 'release': {'allocation'},
          'emit': {'start', 'tokens'}, 'observe': {'start', 'tokens'}}


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    closed: bool
    events_checked: int
    errors: tuple[str, ...]
    physical_status: str = 'NOT_VERIFIED'


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def natural(x, positive=False):
    need(type(x) is int and x >= int(positive), 'non-integer/negative count')


def text(x):
    need(type(x) is str and bool(x.strip()), 'invalid identifier')


def token_vector(x):
    need(type(x) is list, 'token vector not JSON array')
    for v in x:
        natural(v)


def time_record(x):
    need(type(x) is dict and set(x) == {'domain', 'seconds', 'category'}, 'clock schema')
    text(x['domain'])
    need(type(x['seconds']) in (int, float) and math.isfinite(x['seconds']) and
         x['seconds'] >= 0, 'clock value')
    need(x['category'] in {'host_control', 'host_policy_feedback', 'gpu_execution',
                          'client_observation', 'server_observation'}, 'clock category')


def allocation(x, previous, used):
    need(type(x) is dict and set(x) == {'observation_id', 'pool_id', 'total_blocks',
         'system_blocks', 'free_blocks', 'owned_blocks', 'other_allocated_blocks'}, 'allocation schema')
    text(x['observation_id']); text(x['pool_id'])
    need(x['observation_id'] not in used, 'reused allocation observation')
    for key in ('total_blocks', 'system_blocks', 'free_blocks', 'other_allocated_blocks'):
        natural(x[key])
    token_vector(x['owned_blocks'])
    need(len(set(x['owned_blocks'])) == len(x['owned_blocks']), 'duplicate block')
    need(all(b < x['total_blocks'] for b in x['owned_blocks']), 'block outside pool')
    remaining = x['total_blocks'] - x['system_blocks'] - x['free_blocks'] - x['other_allocated_blocks']
    need(remaining == len(x['owned_blocks']), 'block accounting')
    if previous is not None:
        need(all(x[k] == previous[k] for k in ('pool_id', 'total_blocks', 'system_blocks')),
             'pool changed')
    used.add(x['observation_id'])


class RefRequest:
    def __init__(self, spec):
        self.spec = spec
        self.phase = 'WAITING'
        self.generation = 0
        self.positions = set()
        self.work = []  # (position, is_retained_output), independent of advertised counters
        self.output = []
        self.sent = []
        self.received = []
        self.pending = None
        self.owned = None
        self.active = False
        self.replay_boundary = 0
        self.first = None
        self.discarded = []
        self.terminal = None
        self.aborting = None

    def snapshot(self):
        # Materialize the public schema from independent position/history sets.
        n = self.spec['prompt_tokens']
        prompt_history = [pos for pos, _ in self.work if pos < n]
        progress = len(self.positions)
        return dict(spec=self.spec, state=self.phase, epoch=self.generation,
            acknowledged=progress, planned=self.pending['end'] if self.pending else progress,
            pending=self.pending, generated=list(self.output), emitted=len(self.sent),
            observed=len(self.received), resident=self.active, allocation=self.owned,
            replay_until=self.replay_boundary, seen_prompt=sorted(set(prompt_history)),
            prompt_work=len(prompt_history), repeated_prompt_work=len(prompt_history)-len(set(prompt_history)),
            retained_output_work=sum(retained for _, retained in self.work),
            decode_work=sum(pos >= n and not retained for pos, retained in self.work),
            discarded_samples=list(self.discarded), first_sample=self.first,
            disposition=self.terminal, pending_disposition=self.aborting)

    def step(self, kind, d, timestamp, plans):
        need(self.phase in EDGES[kind], 'forbidden state edge')
        if kind == 'interval':
            need(plans.get(d['plan_id']) == self.spec['request_id'], 'unbound time interval')
            need(set(d['interval']) == {'start', 'end'}, 'interval schema')
            start, end = d['interval']['start'], d['interval']['end']
            time_record(start); time_record(end)
            need(start['domain'] == end['domain'] and start['category'] == end['category'] and
                 start['category'] in {'host_policy_feedback', 'gpu_execution'} and
                 start['seconds'] <= end['seconds'], 'incomparable interval')
            if end['domain'] == timestamp['domain']:
                need(end['seconds'] <= timestamp['seconds'], 'future interval')
        elif kind in ('emit', 'observe'):
            natural(d['start']); token_vector(d['tokens'])
            need(bool(d['tokens']), 'empty transport event')
            target = self.sent if kind == 'emit' else self.received
            source = self.output if kind == 'emit' else self.sent
            need(d['start'] == len(target), 'transport cursor')
            need(source[len(target):len(target)+len(d['tokens'])] == d['tokens'], 'output prefix')
            if kind == 'emit':
                need(self.aborting is None and self.terminal not in ('FAILED', 'CANCELLED'), 'post-abort emit')
            target.extend(d['tokens'])
        elif kind in ('admit', 'preempt', 'quiesce', 'release'):
            if kind != 'admit':
                need(not d['allocation']['owned_blocks'], 'release still owns blocks')
            if kind == 'admit':
                self.phase = 'ADMITTED'; self.active = True
            elif kind == 'preempt':
                self.positions.clear(); self.generation += 1
                self.replay_boundary = self.spec['prompt_tokens'] + len(self.output)
                self.phase = 'RECOMPUTE_WAITING'; self.active = False
            elif kind == 'quiesce':
                need(self.pending is None, 'cannot release outstanding plan')
                self.phase = 'TERMINAL'; self.terminal = self.aborting
                self.aborting = None; self.active = False
            else:
                need(self.owned is not None and bool(self.owned['owned_blocks']), 'duplicate/unneeded release')
            self.owned = d['allocation']
        elif kind in ('wait', 'hold'):
            if kind == 'wait': text(d['reason'])
        elif kind == 'plan':
            p = d['plan']
            need(set(p) == {'plan_id', 'batch_id', 'epoch', 'start', 'end'}, 'plan schema')
            text(p['plan_id']); text(p['batch_id'])
            for key in ('epoch', 'start', 'end'): natural(p[key])
            need(p['plan_id'] not in plans, 'duplicate plan')
            plans[p['plan_id']] = self.spec['request_id']
            need(p['epoch'] == self.generation, 'plan epoch')
            known = set(range(self.spec['prompt_tokens'] + len(self.output)))
            proposed = set(range(p['start'], p['end']))
            need(bool(proposed) and p['start'] == len(self.positions) and
                 proposed <= known - self.positions, 'plan positions')
            self.pending = dict(p); self.phase = 'IN_FLIGHT'
        elif kind in ('cancel', 'fail', 'complete'):
            text(d['reason'])
            need(self.aborting is None, 'duplicate abort')
            outcome = {'cancel': 'CANCELLED', 'fail': 'FAILED', 'complete': 'STOPPED'}[kind]
            if self.pending is None:
                self.phase = 'TERMINAL'; self.terminal = outcome; self.active = False
            else:
                self.aborting = outcome
                self.phase = 'CANCEL_PENDING' if kind == 'cancel' else 'FAILED_PENDING'
        elif kind == 'ack':
            a, p = d['ack'], self.pending
            need(set(a) == {'plan_id', 'epoch', 'start', 'executed_end', 'samples',
                            'success', 'quiescent', 'allocation'}, 'ACK schema')
            need(p is not None, 'ACK without plan')
            for key in ('epoch', 'start', 'executed_end'): natural(a[key])
            need(type(a['success']) is bool and type(a['quiescent']) is bool, 'ACK flags')
            token_vector(a['samples'])
            need(all(a[k] == p[k] for k in ('plan_id', 'epoch', 'start')), 'ACK binding')
            need(p['start'] <= a['executed_end'] <= p['end'], 'ACK range')
            if a['success']: need(a['executed_end'] == p['end'], 'short success')
            else: need(not a['samples'], 'failure samples')
            executed = set(range(a['start'], a['executed_end']))
            need(not (self.positions & executed), 'executed overlap')
            after = self.positions | executed
            known = set(range(self.spec['prompt_tokens'] + len(self.output)))
            catches_up = after == known
            interrupted = self.aborting or ('FAILED' if not a['success'] else None)
            if interrupted:
                need(len(a['samples']) <= int(catches_up), 'invalid discarded sample')
            else:
                need(a['quiescent'] and len(a['samples']) == int(catches_up), 'sample eligibility')
            for pos in sorted(executed):
                self.work.append((pos, self.spec['prompt_tokens'] <= pos < self.replay_boundary))
            self.positions = after
            self.pending = None
            if a['allocation'] is not None: self.owned = a['allocation']
            if interrupted:
                self.discarded.extend(a['samples'])
                if a['quiescent']:
                    self.phase = 'TERMINAL'; self.terminal = interrupted
                    self.aborting = None; self.active = False
                else:
                    self.phase = 'CANCEL_PENDING' if interrupted == 'CANCELLED' else 'FAILED_PENDING'
                    self.aborting = interrupted
            else:
                if a['samples']:
                    self.output.extend(a['samples'])
                    if self.first is None: self.first = timestamp
                    self.phase = 'DECODE_READY'
                else:
                    self.phase = 'RECOMPUTE_PAUSED' if self.generation else 'PREFILL_PAUSED'
                need(len(self.output) <= self.spec['output_limit'], 'output cap')
                if len(self.output) == self.spec['output_limit']:
                    self.phase = 'TERMINAL'; self.terminal = 'COMPLETE'; self.active = False
        else:
            raise ValueError('unknown operation')


def validate(journal, *, require_complete=False):
    """Validate a serialized journal independently, including advertised snapshots.

    `closed` additionally requires terminal dispositions, empty ownership and all
    successful output observed. Prefix validity never establishes serving success.
    Rejected producer calls poison the run even when its accepted prefix is valid.
    """
    count = 0
    try:
        need(type(journal) is dict and set(journal) == {'schema', 'run_id', 'provenance', 'events', 'faults'},
             'journal schema')
        need(journal['schema'] == 'lssp-p1-ledger/0.1.0', 'schema version')
        text(journal['run_id'])
        need(journal['provenance'] in ('cpu_fixture', 'simulated', 'physical'), 'provenance')
        need(type(journal['events']) is list and type(journal['faults']) is list, 'journal arrays')
        requests, engine_ids, plans, observations, clocks = {}, set(), {}, set(), {}
        for index, event in enumerate(journal['events']):
            need(type(event) is dict and set(event) == {'sequence', 'kind', 'request_id', 'stamp', 'data', 'after'},
                 'event schema')
            natural(event['sequence']); need(event['sequence'] == index, 'journal sequence gap')
            rid, kind, d, stamp = event['request_id'], event['kind'], event['data'], event['stamp']
            text(rid); time_record(stamp)
            if kind == 'emit': permitted = {'server_observation'}
            elif kind == 'observe': permitted = {'client_observation'}
            elif kind == 'plan': permitted = {'host_control', 'host_policy_feedback'}
            elif kind == 'ack': permitted = {'host_control', 'host_policy_feedback', 'server_observation'}
            else: permitted = {'host_control'}
            need(stamp['category'] in permitted, 'wrong observation boundary')
            need(kind in FIELDS and type(d) is dict and set(d) == FIELDS[kind], 'event payload schema')
            if kind == 'enqueue':
                spec = d['spec']
                need(type(spec) is dict and set(spec) == {'request_id', 'engine_id', 'prompt_tokens',
                     'output_limit', 'prompt_digest', 'arrival', 'metadata'}, 'request schema')
                need(spec['request_id'] == rid and rid not in requests and
                     spec['engine_id'] not in engine_ids, 'duplicate/mismatched identity')
                for key in ('request_id', 'engine_id', 'prompt_digest'): text(spec[key])
                natural(spec['prompt_tokens'], True); natural(spec['output_limit'], True)
                time_record(spec['arrival'])
                need(type(spec['metadata']) is list, 'metadata array')
                keys = set()
                for pair in spec['metadata']:
                    need(type(pair) is list and len(pair) == 2, 'metadata pair')
                    text(pair[0]); text(pair[1]); need(pair[0] not in keys, 'duplicate metadata')
                    keys.add(pair[0])
                clocks[rid, spec['arrival']['domain']] = spec['arrival']['seconds']
                requests[rid] = RefRequest(spec); engine_ids.add(spec['engine_id'])
            else:
                need(rid in requests, 'unknown request')
                a = d['ack'].get('allocation') if kind == 'ack' else d.get('allocation')
                if a is not None: allocation(a, requests[rid].owned, observations)
                requests[rid].step(kind, d, stamp, plans)
            key = rid, stamp['domain']
            need(stamp['seconds'] >= clocks.get(key, 0), 'causal clock reversal')
            clocks[key] = stamp['seconds']
            need(json.dumps(requests[rid].snapshot(), sort_keys=True, allow_nan=False) ==
                 json.dumps(event['after'], sort_keys=True, allow_nan=False),
                 'advertised snapshot disagrees with reference')
            count += 1
        need(not journal['faults'], 'producer contract failure (accepted prefix checked)')
        closed = bool(requests) and all(r.phase == 'TERMINAL' and r.pending is None and
            (r.owned is None or not r.owned['owned_blocks']) and
            (r.terminal not in ('COMPLETE', 'STOPPED') or r.output == r.sent == r.received)
            for r in requests.values())
        need(not require_complete or closed, 'incomplete/drain evidence missing')
        return ValidationResult(True, closed, count, ())
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError) as exc:
        return ValidationResult(False, False, count, (str(exc),))


def main():
    import argparse
    import json
    from dataclasses import asdict
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('journal', type=Path)
    parser.add_argument('--require-complete', action='store_true')
    args = parser.parse_args()
    try:
        result = validate(json.loads(args.journal.read_text()), require_complete=args.require_complete)
    except (OSError, ValueError) as exc:
        result = ValidationResult(False, False, 0, (str(exc),))
    print(json.dumps(asdict(result), indent=2))
    return 0 if result.valid else 1


if __name__ == '__main__':
    raise SystemExit(main())
