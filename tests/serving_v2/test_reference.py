import copy
import json
from pathlib import Path
import subprocess
import sys
import pytest
from robustbench.serving_v2.ledger import Acknowledgment, ClockStamp, ContractError, Plan, TimingInterval
from robustbench.serving_v2.reference import validate


def finished(harness):
    h = harness(2, 2); h.admit(); h.work(0, 1, 0); h.work(1, 2, 0, (17,))
    h.preempt(); h.admit(); h.work(0, 2, 1); h.work(2, 3, 1, (18,)); h.drain()
    assert validate(h.ledger.export(), require_complete=True).valid
    return h


@pytest.mark.parametrize('field,value', [
    ('epoch', 99), ('acknowledged', 99), ('planned', 99), ('generated', [17,19]),
    ('emitted', 0), ('observed', 0), ('resident', True), ('disposition', 'FAILED'),
    ('repeated_prompt_work', 0), ('retained_output_work', 0), ('decode_work', 5),
    ('prompt_work', True), ('pending', {}), ('state', 'DECODE_READY')])
def test_referee_detects_corrupt_snapshot(harness, field, value):
    journal = finished(harness).ledger.export()
    journal['events'][-1]['after'][field] = value
    assert not validate(journal, require_complete=True).valid


@pytest.mark.parametrize('mutation', ['duplicate_ack', 'stale_ack', 'missing_ack', 'renumbered_missing_ack',
    'duplicate_request', 'sample_on_partial', 'wrong_engine', 'counter_bool', 'short_success',
    'bad_clock', 'prefix_change', 'invalid_observation', 'unknown_schema', 'extra_payload'])
def test_referee_rejects_event_corruption_without_using_ledger(harness, mutation):
    journal = finished(harness).ledger.export(); events = journal['events']
    ack_index = next(i for i,e in enumerate(events) if e['kind'] == 'ack')
    if mutation == 'duplicate_ack': events.insert(ack_index+1, copy.deepcopy(events[ack_index]))
    elif mutation == 'stale_ack':
        next(e for e in events if e['kind']=='ack' and e['data']['ack']['epoch']==1)['data']['ack']['epoch'] = 0
    elif mutation in ('missing_ack','renumbered_missing_ack'): events.pop(ack_index)
    elif mutation == 'duplicate_request': events.insert(1, copy.deepcopy(events[0]))
    elif mutation == 'sample_on_partial': events[ack_index]['data']['ack']['samples'] = [17]
    elif mutation == 'wrong_engine': events[0]['data']['spec']['engine_id'] = 'other'
    elif mutation == 'counter_bool': events[ack_index]['after']['acknowledged'] = True  # 1 != true
    elif mutation == 'short_success': events[ack_index]['data']['ack']['executed_end'] = 0
    elif mutation == 'bad_clock': events[-1]['stamp']['seconds'] = 0
    elif mutation == 'prefix_change': events[-1]['after']['generated'][0] = 20
    elif mutation == 'invalid_observation': events[1]['data']['allocation']['free_blocks'] = -1
    elif mutation == 'unknown_schema': journal['schema'] = 'future'
    elif mutation == 'extra_payload': events[ack_index]['data']['secret_override'] = True
    if mutation not in ('missing_ack',):
        for i,e in enumerate(events): e['sequence'] = i
    assert not validate(journal, require_complete=True).valid


def test_referee_is_independent_of_production_transition_monkeypatch(harness, monkeypatch):
    # Deliberately wrong producer: acknowledge a short prefill as if it produced a token.
    from robustbench.serving_v2.ledger import Ledger
    from dataclasses import replace
    original = Ledger._transition
    def broken(self, state, kind, data, stamp):
        new = original(self, state, kind, data, stamp)
        if kind == 'ack' and not new.generated:
            return replace(new, generated=(999,), state='DECODE_READY')
        return new
    monkeypatch.setattr(Ledger, '_transition', broken)
    h = harness(); h.admit(); h.work(0, 1, 0)
    assert not validate(h.ledger.export()).valid


@pytest.mark.parametrize('category', ['host_policy_feedback', 'gpu_execution'])
def test_intervals_preserve_clock_domains_without_latency_claims(harness, category):
    h = finished(harness)
    plan_id = next(e['data']['plan']['plan_id'] for e in h.ledger.export()['events'] if e['kind']=='plan')
    h.ledger.annotate_interval('r',plan_id,TimingInterval(
        ClockStamp('separate-device-clock', 1000., category),
        ClockStamp('separate-device-clock', 1001., category)),stamp=h.time())
    assert validate(h.ledger.export(), require_complete=True).physical_status == 'NOT_VERIFIED'


@pytest.mark.parametrize('start,end', [
    (ClockStamp('a',1.,'gpu_execution'),ClockStamp('b',2.,'gpu_execution')),
    (ClockStamp('a',1.,'host_policy_feedback'),ClockStamp('a',2.,'gpu_execution')),
    (ClockStamp('a',3.,'host_policy_feedback'),ClockStamp('a',2.,'host_policy_feedback')),
    (ClockStamp('a',float('nan'),'gpu_execution'),ClockStamp('a',2.,'gpu_execution'))])
def test_invalid_intervals(harness, start, end):
    h = finished(harness)
    pid = next(e['data']['plan']['plan_id'] for e in h.ledger.export()['events'] if e['kind']=='plan')
    before = h.ledger.export()['events']
    with pytest.raises(ContractError):
        h.ledger.annotate_interval('r',pid,TimingInterval(start,end),stamp=h.time())
    assert h.ledger.export()['events'] == before


def test_no_client_chunk_can_be_mislabeled_as_gpu_ack(harness):
    h = harness(); h.admit(); h.ledger.plan('r',Plan('p','b',0,0,4),stamp=h.time())
    with pytest.raises(ContractError, match='WRONG_BOUNDARY_CATEGORY'):
        h.ledger.acknowledge('r',Acknowledgment('p',0,0,4,(17,)),stamp=h.time('gpu_execution'))


def test_referee_cli_and_deterministic_export(harness, tmp_path):
    h1, h2 = finished(harness), finished(harness)
    assert json.dumps(h1.ledger.export(),sort_keys=True) == json.dumps(h2.ledger.export(),sort_keys=True)
    journal = tmp_path/'fixture.json'; journal.write_text(json.dumps(h1.ledger.export()))
    result = subprocess.run([sys.executable,'-B','-m','robustbench.serving_v2.reference',
        str(journal),'--require-complete'], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['closed']


def histories(p, o, max_preemptions, c=0, g=0, epoch=0):
    """Exhaust every legal q and optional preemption boundary in this bounded model.

    Independent mathematical generator: no ledger/referee calls or snapshots.
    Each work action stands for one plan + quiescent ACK; generated symbols depend
    only on lifetime output index. Preemption is an external event, never a policy.
    """
    if g == o:
        yield ()
        return
    for q in range(1, p+g-c+1):
        end = c+q
        sampled = end == p+g
        action = ('work', c, end, epoch, (17+g,) if sampled else ())
        for rest in histories(p,o,max_preemptions,end,g+int(sampled),epoch):
            yield (action,)+rest
    if epoch < max_preemptions:
        for rest in histories(p,o,max_preemptions,0,g,epoch+1):
            yield (('preempt',),)+rest


@pytest.mark.parametrize('p,o', [(p,o) for p in range(1,4) for o in range(1,3)])
def test_exhaustive_position_and_recompute_histories(harness, p, o):
    limit = 2 if p <= 2 else 1
    count = 0
    max_events = 0
    for history in histories(p,o,limit):
        h = harness(p,o); h.admit()
        generated, epoch, confirmed = (), 0, 0
        for action in history:
            if action[0] == 'preempt':
                h.preempt(); epoch += 1; confirmed = 0; h.admit()
            else:
                _, start, end, e, samples = action
                assert e == epoch
                h.work(start,end,e,samples); confirmed = end; generated += samples
                if samples:
                    h.ledger.emit('r',len(generated)-1,samples,stamp=h.time('server_observation'))
            s = h.ledger.snapshot('r')
            assert (s.epoch,s.acknowledged,s.generated) == (epoch,confirmed,generated)
            assert s.prompt_work-s.repeated_prompt_work == len(s.seen_prompt) <= p
            assert 0 <= s.observed <= s.emitted <= len(generated) <= o
        assert h.ledger.snapshot('r').state == 'TERMINAL'
        h.drain()
        result = validate(h.ledger.export(), require_complete=True)
        assert result.valid and result.closed, (history,result)
        count += 1; max_events = max(max_events,result.events_checked)
    print(f'EXHAUSTIVE P={p} O={o} max_preemptions={limit} histories={count} max_events={max_events} seed=none')
    assert count > 1
