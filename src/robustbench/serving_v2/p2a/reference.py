"""Independent CPU batch referee; no producer/adapter/native-vLLM imports.

Expected work is computed from enqueue order, prior verified outputs and the
pinned no-pressure FCFS service rule, NEVER from advertised acceptance. The
P1 independent referee separately checks every request-local state transition.
An evidence consistency check is not authentication or physical execution.
"""
from dataclasses import dataclass
import json
from ..reference import validate as validate_p1
from .pins import PINS


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


def fcfs_work(running, waiting, rows, budget, slots):
    """Standalone specification: resident work first, then FIFO admissions.

    Domain: no-pressure full-attention, no caching, no speculation, no skips,
    no recomputation, known prompt + output prefix, context slack >= one token.
    Returns positions, sample validity and resident set, not ACKs.
    """
    integer(budget,1); integer(slots,1)
    check(len(running) <= slots, 'resident overcommitment')
    resident = list(running)
    work = []
    for rid in list(running)+list(waiting):
        if budget == 0:
            break
        if rid in waiting:
            if len(resident) == slots:
                break
            resident.append(rid)
        r = rows[rid]
        start = r['computed']
        frontier = r['prompt']+len(r['output'])
        check(frontier > start, 'no work at frontier')
        end = min(frontier,start+budget)
        work.append(dict(request_id=rid,epoch=0,start=start,end=end))
        budget -= end-start
    return work, resident


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


def validate(journal, *, require_complete=True):
    count = 0
    try:
        # Strict JSON round trip rejects NaN and removes aliasing.
        j = json.loads(json.dumps(journal,allow_nan=False))
        check(j['schema'] == 'lssp-p2a-boundary/0.1.0' and
              j['provenance'] == 'synthetic_cpu' and not j['faults'], 'schema/provenance/fault')
        check(j['source_hashes'] == PINS, 'source identity')
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
            expected,resident = fcfs_work(running,waiting,rows,p['token_budget'],p['active_limit'])
            check(expected and p['spans'] == expected, 'proposal differs from independent FCFS expectation')
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
        complete = bool(count) and not pending and not running and not waiting
        check(not require_complete or complete, 'incomplete batch/run')
        return Result(True,complete,count,(),transport_closed=local.closed)
    except (ValueError,TypeError,KeyError,IndexError,AttributeError,StopIteration) as e:
        return Result(False,False,count,(str(e),))
