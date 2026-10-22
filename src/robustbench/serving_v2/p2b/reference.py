"""Independent P2B referee; external intents or declarative S02 token tickets.

Expected work comes from independent external intents or the S02 token-ticket
rule applied to immutable metadata and prior verified outputs, NEVER acceptance. The
P1 independent referee separately checks every request-local state transition.
An evidence consistency check is not authentication or physical execution.
"""
from dataclasses import dataclass
import json
from ..reference import validate as validate_p1, time_record
from ..p2a.pins import PINS
from .pins import PATCH_SHA256


@dataclass(frozen=True)
class Result:
    valid: bool
    complete: bool
    batches_checked: int
    errors: tuple[str, ...]
    physical_status: str = 'NOT_VERIFIED'
    transport_closed: bool = False


def check(ok, why):
    if not ok:
        raise ValueError(why)


def integer(x, minimum=0):
    check(type(x) is int and x >= minimum, 'invalid integer')


def expected_s02(running, waiting, rows, metadata, paused, budget, slots):
    """Reference token-ticket definition, independent of production policy."""
    remaining_slots = slots-len(running)
    waiting_order = sorted(waiting,key=lambda rid:(metadata[rid]['s02_class'] != 'tight',
        rows[rid]['prompt'],int(metadata[rid]['s02_ordinal'])))
    ordered = list(paused)+waiting_order[:remaining_slots]
    tickets = [(rid,pos) for rid in ordered for pos in range(rows[rid]['computed'],rows[rid]['prompt'])]
    if not tickets:
        tickets = [(rid,rows[rid]['computed']) for rid in sorted(running,
                   key=lambda rid:int(metadata[rid]['s02_ordinal']))]
    result = []
    for rid,pos in tickets[:budget]:
        if result and result[-1]['request_id'] == rid:
            result[-1]['end'] = pos+1
        else:
            result.append(dict(request_id=rid,epoch=0,start=pos,end=pos+1))
    return result


def controlled_work(intent, running, waiting, rows, budget, slots):
    work = intent['proposal']['spans']
    check(intent['proposal']['token_budget'] == budget and intent['proposal']['active_limit'] == slots,
          'external bounds')
    selected = [x['request_id'] for x in work]
    check(work and len(selected) == len(set(selected)) and set(selected) <= set(running+waiting),
          'external identities')
    phases = [rid in waiting for rid in selected]
    check(phases == sorted(phases), 'unrepresentable phase order')
    for x in work:
        r = rows[x['request_id']]
        for key in ('epoch','start','end'): integer(x[key])
        check(x['epoch'] == 0 and x['start'] == r['computed'] < x['end'] <= r['prompt']+len(r['output']),
              'external span')
    check(sum(x['end']-x['start'] for x in work) <= budget, 'external token budget')
    resident = running+[rid for rid in selected if rid in waiting]
    check(len(resident) <= slots, 'external active slots')
    holds = intent['holds']
    check(len(holds) == len(set(holds)) and set(holds) == set(running)-set(selected), 'external holds')
    return work,resident


def _allocation(snapshot):
    integer(snapshot['total_blocks'],2); integer(snapshot['free_blocks'])
    integer(snapshot['block_size'],1)
    check(snapshot['system_blocks'] == 1 and not snapshot['skipped'], 'KV/skipped domain')
    owned = []
    for r in snapshot['rows'].values():
        for block in r['blocks']:
            integer(block)
            check(block < snapshot['total_blocks'], 'block range')
        owned.extend(r['blocks'])
    check(len(owned) == len(set(owned)), 'shared/duplicate ownership')
    check(len(owned)+snapshot['free_blocks']+1 == snapshot['total_blocks'], 'cross-request KV conservation')


def _observation(obs, snapshot, rid):
    check(obs['owned_blocks'] == snapshot['rows'][rid]['blocks'] and
          obs['total_blocks'] == snapshot['total_blocks'] and
          obs['free_blocks'] == snapshot['free_blocks'] and obs['system_blocks'] == 1,
          'ledger allocation differs from native observation')


def validate(journal, intents=None, *, require_complete=True):
    count = 0
    try:
        # Strict JSON round trip rejects NaN and removes aliasing.
        j = json.loads(json.dumps(journal,allow_nan=False))
        check(j['schema'] == 'lssp-p2b-control/0.1.0' and
              j['provenance'] == 'synthetic_cpu' and not j['faults'], 'schema/provenance/fault')
        check(j['source_hashes'] == PINS, 'source identity')
        check(j['control_profile'] in ('lssp-native-span-control/0.1.0','lssp-slai-s02-prefill-control/0.1.0'), 'profile')
        check(j['patched_schedule_sha256'] == PATCH_SHA256, 'patch identity')
        check(j['hook_id'] == 'vllm-0.27.1-exact-span-hook/0.1.0', 'hook identity')
        if j['control_profile'] == 'lssp-native-span-control/0.1.0':
            check(type(intents) is dict, 'independent external intents required')
            intents = json.loads(json.dumps(intents,allow_nan=False))
        check(len(j['control_attempts']) == len(j['batches']) and
              all(a['preflight'] == 'PASS' for a in j['control_attempts']), 'control attempt evidence')
        metadata = {}; paused = []; quiescence_ids = set()
        local = validate_p1(j['ledger'])
        check(local.valid, 'P1: '+str(local.errors))
        check(j['ledger']['provenance'] == 'cpu_fixture', 'P1 provenance')
        profile = j['configuration']
        for key in ('token_budget','active_limit','max_model_len','block_size','total_blocks'):
            integer(profile[key],1)
        check(profile['policy'] == 'fcfs' and profile['runner'] == 'v2' and profile['device'] == 'cpu' and
              profile['prefix_caching'] is False and profile['reserve_full_input'] is True and
              profile['sampling'] == 'fixed-output-synthetic' and profile['parallelism'] == [1,1,1],
              'unsupported configuration')
        events = j['ledger']['events']
        registry = j['registry']
        check(len(registry.values()) == len(set(registry.values())), 'application identity collision')
        rows, running, waiting, seen, known_ids = {}, [], [], set(), {}
        cursor = 0
        pending = False
        step = 0
        configuration = None
        for batch in j['batches']:
            check(not pending and 'rejection' not in batch, 'rejected/overlapping batch')
            integer(batch['ledger_start'])
            check(cursor <= batch['ledger_start'] <= len(events), 'ledger batch boundary')
            for e in events[cursor:batch['ledger_start']]:
                check(e['kind'] == 'enqueue', 'unbound ledger event')
                spec = e['data']['spec']; rid = spec['engine_id']
                check(rid not in rows and registry[rid] == spec['request_id'], 'enqueue identity')
                rows[rid] = dict(prompt=spec['prompt_tokens'],limit=spec['output_limit'],
                                 computed=0,output=[],arrival=spec['arrival']['seconds'])
                check(spec['prompt_tokens']+spec['output_limit'] <= profile['max_model_len'], 'context limit')
                metadata[rid] = dict(spec['metadata'])
                if j['control_profile'] == 'lssp-slai-s02-prefill-control/0.1.0':
                    check(metadata[rid]['s02_class'] in ('tight','medium','loose'), 'S02 class')
                    ordinal = int(metadata[rid]['s02_ordinal'])
                    check(ordinal >= 0 and str(ordinal) == metadata[rid]['s02_ordinal'] and
                          all(other == rid or int(m['s02_ordinal']) != ordinal for other,m in metadata.items()), 'S02 ordinal')
                known_ids[rid] = spec['request_id']
                waiting.append(rid)
            p = batch['proposal']; before = batch['before']; after = batch['scheduled']; wire = batch['native']
            integer(batch['step'],1)
            check(batch['step'] == step+1, 'native step continuity'); step = batch['step']
            check(type(p['batch_id']) is str and bool(p['batch_id'].strip()) and p['batch_id'] not in seen,
                  'batch identity'); seen.add(p['batch_id'])
            current_config = (p['token_budget'],p['active_limit'],before['total_blocks'],before['block_size'])
            if configuration is None:
                configuration = current_config
            check(configuration == current_config == (profile['token_budget'],profile['active_limit'],
                  profile['total_blocks'],profile['block_size']), 'configuration drift')
            for collection in (p['spans'],batch['acceptance']['spans'],batch.get('ack',{}).get('spans',[])):
                for span in collection:
                    check(type(span['request_id']) is str, 'span ID')
                    for key in ('epoch','start','end'):
                        integer(span[key])
            for value in wire['counts'].values():
                integer(value,1)
            integer(wire['total'],1)
            for row in wire['new']+wire['cached']:
                integer(row['start'])
            for key in ('tokens','active_slots','native_step'):
                integer(batch['acceptance'][key],1)
            if 'ack' in batch:
                integer(batch['ack']['native_step'],1)
                for value in batch['runner']['index'].values():
                    integer(value)
            for snap in (before,after,batch.get('executed',after)):
                for row in snap['rows'].values():
                    for key in ('prompt','limit','computed','inflight','preemptions'):
                        integer(row[key])
                    for value in row['output']:
                        integer(value)
            for snap in (before,after):
                _allocation(snap)
                check(set(snap['rows']) == set(rows), 'registry conservation')
                check(len(snap['live']) == len(set(snap['live'])) and
                      set(snap['live']) == set(running+waiting), 'live conservation')
            check(before['running'] == running and before['waiting'] == waiting, 'queue continuity')
            for rid,r in rows.items():
                native = before['rows'][rid]
                check(all(native[k] == v for k,v in r.items()), 'native before differs from history')
                check(native['inflight'] == 0 and native['preemptions'] == 0, 'inflight/preemption')
                check(native['status'] == ('RUNNING' if rid in running else
                       'WAITING' if rid in waiting else 'FINISHED_LENGTH_CAPPED'), 'native state')
            bs = before['block_size']
            bound = sum((rows[r]['prompt']+rows[r]['limit']+bs-1)//bs for r in running+waiting)
            check(bound <= before['total_blocks']-1, 'no-pressure domain')
            if j['control_profile'] == 'lssp-native-span-control/0.1.0':
                intent = intents[p['batch_id']]
                check(intent['proposal']['batch_id'] == p['batch_id'], 'external batch ID')
            else:
                work = expected_s02(running,waiting,rows,metadata,paused,p['token_budget'],p['active_limit'])
                selected = [x['request_id'] for x in work]
                intent = dict(proposal=dict(batch_id=p['batch_id'],spans=work,token_budget=p['token_budget'],
                    active_limit=p['active_limit']),holds=[r for r in running if r not in selected])
            expected,resident = controlled_work(intent,running,waiting,rows,p['token_budget'],p['active_limit'])
            check(batch['control'] == intent and p == intent['proposal'], 'control differs from independent intent')
            check(j['control_attempts'][count]['control'] == intent, 'control attempt mismatch')
            ids = [r['request_id'] for r in expected]
            counts = {r['request_id']:r['end']-r['start'] for r in expected}
            check(wire['counts'] == counts and wire['total'] == sum(counts.values()), 'native tokens')
            check(not any(wire[k] for k in ('resumed','preempted','speculative','encoder','connector')),
                  'unsupported native work')
            check(wire['new'] == [dict(id=x['request_id'],start=x['start']) for x in expected
                                 if x['request_id'] in waiting], 'new-request positions')
            check(wire['cached'] == [dict(id=x['request_id'],start=x['start']) for x in expected
                                    if x['request_id'] in running], 'cached positions')
            mask = [x['end'] == rows[x['request_id']]['prompt']+len(rows[x['request_id']]['output'])
                    for x in expected]
            acceptance = dict(batch_id=p['batch_id'],native_step=step,spans=expected,
                              tokens=sum(counts.values()),active_slots=len(resident),sample_mask=mask)
            check(batch['acceptance'] == acceptance, 'advertised acceptance corrupt')
            check(all(type(v) is bool for v in batch['acceptance']['sample_mask']), 'mask type')
            check(after['running'] == resident and
                  after['waiting'] == [r for r in waiting if r not in ids], 'native admission')
            for rid,r in rows.items():
                a = after['rows'][rid]
                end = r['computed']+counts.get(rid,0)
                check(a['computed'] == end and a['inflight'] == counts.get(rid,0) and
                      a['output'] == r['output'] and a['preemptions'] == 0, 'optimistic progress')
                check(a['status'] == ('RUNNING' if rid in resident else
                      'WAITING' if rid in waiting else 'FINISHED_LENGTH_CAPPED'), 'scheduled state')
                if rid in resident:
                    check(len(a['blocks']) == (end+bs-1)//bs, 'native block count')
            plan_events = events[batch['ledger_start']:batch['ledger_planned']]
            kinds = []
            for x in expected:
                rid = x['request_id']; app = registry[rid]
                if rid in waiting:
                    kinds.append(('admit',app))
                kinds.append(('plan',app))
            check([(e['kind'],e['request_id']) for e in plan_events] == kinds, 'ledger plan conservation')
            for e in plan_events:
                rid = next(r for r in ids if registry[r] == e['request_id'])
                if e['kind'] == 'admit':
                    _observation(e['data']['allocation'],after,rid)
                else:
                    x = expected[ids.index(rid)]
                    check(e['data']['plan'] == dict(plan_id=p['batch_id']+'/'+rid,batch_id=p['batch_id'],
                          epoch=0,start=x['start'],end=x['end']), 'ledger/native plan mismatch')
            cursor = batch['ledger_planned']
            count += 1
            if 'ack' not in batch:
                pending = True
                continue
            att = batch['attestation']
            time_record(att['start']); time_record(att['end'])
            integer(att['native_step'],1)
            for vector in (att['accepted'],att['executed']):
                for span in vector:
                    for key in ('epoch','start','end'): integer(span[key])
            check(att == batch['attestation_attempt'] and att['batch_id'] == p['batch_id'] and
                  att['native_step'] == step and att['accepted'] == expected and att['executed'] == expected and
                  att['sample_mask'] == mask and att['completion'] == 'complete' and att['quiescent'] is True and
                  att['provenance'] == 'synthetic_cpu' and type(att['quiescence_evidence']) is str and
                  bool(att['quiescence_evidence'].strip()) and att['quiescence_evidence'] not in quiescence_ids,
                  'execution attestation')
            quiescence_ids.add(att['quiescence_evidence'])
            check(att['start']['domain'] == att['end']['domain'] and
                  att['start']['category'] == att['end']['category'] == 'host_control' and
                  att['start']['seconds'] <= att['end']['seconds'], 'attestation clock domain')
            for event in plan_events:
                check(event['stamp']['domain'] == att['start']['domain'] and
                      event['stamp']['seconds'] <= att['start']['seconds'], 'attested execution before plan')
            ack = batch['ack']
            check(batch['ack_attempt'] == ack, 'ACK attempt differs')
            runner = batch['runner']; final = batch['executed']
            check(ack == dict(batch_id=p['batch_id'],native_step=step,spans=expected,sample_mask=mask,
                  provenance='synthetic_cpu',success=True,quiescent=True), 'ACK attestation')
            check(ack['success'] is True and ack['quiescent'] is True and
                  all(type(v) is bool for v in ack['sample_mask']), 'ACK flag types')
            runner_ids = runner['ids']
            check(type(runner_ids) is list and len(runner_ids) == len(set(runner_ids)) == len(ids) and
                  set(runner_ids) == set(ids) and
                  runner['index'] == {r:i for i,r in enumerate(runner_ids)}, 'runner identities')
            raw_samples = runner['samples']
            check(type(raw_samples) is list and len(raw_samples) == len(ids), 'runner rows')
            samples = [raw_samples[runner['index'][rid]] for rid in ids]
            for tokens,m in zip(samples,mask,strict=True):
                check(type(tokens) is list and len(tokens) == int(m), 'valid sample mask')
                for token in tokens:
                    integer(token)
            ack_events = events[cursor:batch['ledger_end']]
            expected_kinds = []
            for x,tokens in zip(expected,samples,strict=True):
                rid = x['request_id']; rows[rid]['computed'] = x['end']; rows[rid]['output'] += tokens
                expected_kinds.append(('ack',registry[rid]))
            finished = [r for r in resident if len(rows[r]['output']) == rows[r]['limit']]
            expected_kinds += [('release',registry[r]) for r in ids if r in finished]
            check([(e['kind'],e['request_id']) for e in ack_events] == expected_kinds, 'ledger ACK conservation')
            for e in ack_events:
                check(e['stamp']['domain'] == att['end']['domain'] and att['end']['seconds'] <= e['stamp']['seconds'], 'attestation after ACK')
                rid = next(r for r in ids if registry[r] == e['request_id'])
                if e['kind'] == 'ack':
                    a = e['data']['ack']; x = expected[ids.index(rid)]
                    check(a['plan_id'] == p['batch_id']+'/'+rid and a['epoch'] == 0 and
                          a['start'] == x['start'] and a['executed_end'] == x['end'] and
                          a['samples'] == samples[ids.index(rid)] and
                          a['success'] is True and a['quiescent'] is True, 'ledger/execution ACK mismatch')
                    _observation(a['allocation'],after,rid)
                else:
                    _observation(e['data']['allocation'],final,rid)
            paused = [r for r in paused if r not in ids]+[x['request_id'] for x in expected
                     if x['end'] < rows[x['request_id']]['prompt']]
            running = [r for r in resident if r not in finished]
            waiting = [r for r in waiting if r not in resident]
            _allocation(final)
            check(final['running'] == running and final['waiting'] == waiting and
                  set(final['live']) == set(running+waiting), 'post-execution identity')
            for rid,r in rows.items():
                a = final['rows'][rid]
                check(all(a[k] == v for k,v in r.items()) and a['inflight'] == 0 and a['preemptions'] == 0,
                      'runner/native progress differs')
                check(a['status'] == ('RUNNING' if rid in running else 'WAITING' if rid in waiting else
                      'FINISHED_LENGTH_CAPPED'), 'post-execution state')
                check(a['blocks'] == ([] if rid in finished else after['rows'][rid]['blocks']), 'KV release')
            cursor = batch['ledger_end']
        check(cursor == len(events) and known_ids == registry, 'unbound ledger/registry evidence')
        if j['control_profile'] == 'lssp-slai-s02-prefill-control/0.1.0':
            check(j['paused_fifo'] == paused, 'persistent paused FIFO')
        complete = bool(count) and not pending and not running and not waiting
        check(not require_complete or complete, 'incomplete batch/run')
        return Result(True,complete,count,(),transport_closed=local.closed)
    except (ValueError,TypeError,KeyError,IndexError,AttributeError,StopIteration) as e:
        return Result(False,False,count,(str(e),))
