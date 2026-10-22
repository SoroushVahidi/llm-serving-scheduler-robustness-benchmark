from dataclasses import FrozenInstanceError, replace
import copy
import json
from pathlib import Path
import subprocess
import sys
import pytest
from robustbench.serving_v2.ledger import (
    Acknowledgment, AllocationObservation, ClockStamp, ContractError, Ledger, Plan, RequestSpec)
from robustbench.serving_v2.reference import validate

CORPUS = json.loads((Path(__file__).resolve().parents[2] /
    'docs/serving-contract/v2.0.0-draft.1/cases.json').read_text())
CASES = {c['id']: c for c in CORPUS['cases']}


def check(h, complete=False):
    result = validate(h.ledger.export(), require_complete=complete)
    assert result.valid, result
    assert result.physical_status == 'NOT_VERIFIED'
    return result


def rejected(h, action):
    before = h.ledger.export()
    with pytest.raises(ContractError): action()
    after = h.ledger.export()
    assert after['events'] == before['events']
    assert len(after['faults']) == 1
    assert not validate(after).valid
    assert validate(dict(after, faults=[])).valid
    with pytest.raises(ContractError, match='LEDGER_POISONED'):
        h.ledger.hold('r', stamp=h.time())


@pytest.mark.parametrize('case_id', ['C01', 'C02'])
def test_literal_prefill_cases(harness, case_id):
    c = CASES[case_id]; h = harness(c['inputs']['P'], c['inputs']['O']); h.admit()
    start, prefix = 0, []
    for step in c['expected_steps']:
        q = step['plan']['r']
        samples = tuple(step['Y'][len(prefix):])
        state = h.work(start, start+q, 0, samples)
        assert (state.acknowledged, list(state.generated), state.state) == (
            step['C_exec'], step['Y'], step['state'])
        start += q; prefix = step['Y']; check(h)
    if state.state == 'TERMINAL': h.drain(); assert check(h, True).closed


def test_C11_C14_repeated_recompute_preserves_lifetime(harness):
    h = harness(4, 3); h.admit(); h.work(0, 4, 0, (17,))
    h.ledger.emit('r', 0, (17,), stamp=h.time('server_observation'))
    first = h.ledger.snapshot('r').first_sample
    for epoch, token in [(1, 18), (2, 19)]:
        previous = h.ledger.snapshot('r')
        h.preempt()
        reset = h.ledger.snapshot('r')
        assert reset.generated == previous.generated and reset.emitted == previous.emitted
        assert reset.first_sample == first and reset.acknowledged == reset.planned == 0
        h.admit(); s = h.work(0, 4, epoch)
        assert s.state == 'RECOMPUTE_PAUSED'
        end = 4+len(previous.generated)
        s = h.work(4, end, epoch, (token,))
        assert s.generated == tuple(range(17, token+1))
        h.ledger.emit('r', epoch, (token,), stamp=h.time('server_observation'))
        check(h)
    assert s.state == 'TERMINAL' and s.disposition == 'COMPLETE'
    assert (s.prompt_work, s.repeated_prompt_work, s.retained_output_work, s.decode_work) == (12, 8, 3, 0)
    h.drain(); check(h, True)


def test_C14_literal_cap_two(harness):
    h = harness(4, 2); h.admit(); h.work(0, 4, 0, (17,)); h.preempt(); h.admit()
    h.work(0, 4, 1); s = h.work(4, 5, 1, (18,))
    assert list(s.generated) == CASES['C14']['expected_steps'][-1]['Y']
    assert s.state == 'TERMINAL'; check(h)
    rejected(h, lambda: h.ledger.plan('r', Plan('extra','b',1,5,6), stamp=h.time()))


def test_C05_hold_C07_wait_are_observations_only(harness):
    h = harness(); h.ledger.wait('r', 'external KV refusal', stamp=h.time())
    assert h.ledger.snapshot('r').state == 'WAITING'
    h.admit(); h.work(0, 4, 0, (17,)); before = h.ledger.snapshot('r')
    h.ledger.hold('r', stamp=h.time())
    assert h.ledger.snapshot('r') == before
    h.work(4, 5, 0, (18,)); check(h)


def test_C29_partial_preemption_effect_not_victim_choice(harness):
    h = harness(8, 2); h.admit(); h.work(0, 4, 0)
    h.preempt(); assert h.ledger.snapshot('r').state == 'RECOMPUTE_WAITING'
    h.admit(); h.work(0, 6, 1); s = h.work(6, 8, 1, (17,))
    assert (s.prompt_work, s.repeated_prompt_work, s.seen_prompt) == (12, 4, tuple(range(8)))
    check(h)


@pytest.mark.parametrize('phase', ['waiting', 'running', 'terminal'])
@pytest.mark.parametrize('duplicate', ['request', 'engine'])
def test_C17_identity_unique_for_lifetime(harness, phase, duplicate):
    h = harness(1, 1)
    if phase != 'waiting': h.admit()
    if phase == 'terminal': h.work(0, 1, 0, (17,))
    spec = h.spec('r' if duplicate == 'request' else 'other',
                  'e' if duplicate == 'engine' else 'other-engine')
    rejected(h, lambda: h.ledger.enqueue(spec, stamp=h.time()))


@pytest.mark.parametrize('bad', [True, 0, -1, 1.5, '2'])
def test_invalid_request_counts(bad):
    ledger = Ledger('bad')
    with pytest.raises(ContractError):
        ledger.enqueue(RequestSpec('r','e',bad,2,'digest',ClockStamp('c',0,'host_control')),
                       stamp=ClockStamp('c',1,'host_control'))
    assert ledger.export()['events'] == []


@pytest.mark.parametrize('change', [dict(start=1), dict(end=0), dict(end=5),
    dict(epoch=1), dict(start=True), dict(end=1.5), dict(plan_id=''), dict(batch_id='')])
def test_invalid_plan_spans_are_atomic(harness, change):
    h = harness(); h.admit()
    p = replace(Plan('p','b',0,0,4), **change)
    rejected(h, lambda: h.ledger.plan('r', p, stamp=h.time()))


@pytest.mark.parametrize('change', [dict(plan_id='wrong'), dict(epoch=1), dict(start=1),
    dict(executed_end=5), dict(executed_end=3), dict(epoch=True), dict(samples=()),
    dict(samples=(17,18)), dict(samples=(True,)), dict(success='yes'), dict(quiescent=False)])
def test_ack_binding_and_impossible_samples(harness, change):
    h = harness(); h.admit(); h.ledger.plan('r', Plan('p','b',0,0,4), stamp=h.time())
    ack = replace(Acknowledgment('p',0,0,4,(17,)), **change)
    rejected(h, lambda: h.ledger.acknowledge('r', ack, stamp=h.time()))


def test_C18_sample_on_intermediate_chunk(harness):
    h = harness(10, 3); h.admit(); h.ledger.plan('r', Plan('p','b',0,0,4), stamp=h.time())
    rejected(h, lambda: h.ledger.acknowledge('r', Acknowledgment('p',0,0,4,(17,)), stamp=h.time()))


@pytest.mark.parametrize('kind', ['duplicate', 'stale', 'out_of_order', 'no_plan'])
def test_C19_ack_rejection(harness, kind):
    h = harness(); h.admit()
    a = Acknowledgment('p',0,0,4,(17,))
    if kind != 'no_plan':
        h.ledger.plan('r', Plan('p','b',0,0,4), stamp=h.time())
        h.ledger.acknowledge('r', a, stamp=h.time())
    if kind == 'stale': h.preempt(); h.admit(); h.ledger.plan('r', Plan('new','b',1,0,4), stamp=h.time())
    if kind == 'out_of_order': h.ledger.plan('r', Plan('next','b',0,4,5), stamp=h.time())
    rejected(h, lambda: h.ledger.acknowledge('r', a, stamp=h.time()))


@pytest.mark.parametrize('quiescent', [True, False])
def test_C23_cancel_race_records_discarded_sample(harness, quiescent):
    h = harness(); h.admit(); h.ledger.plan('r', Plan('p','b',0,0,4), stamp=h.time())
    h.ledger.cancel('r', 'client cancelled', stamp=h.time())
    h.ledger.acknowledge('r', Acknowledgment('p',0,0,4,(17,),quiescent=quiescent), stamp=h.time())
    s = h.ledger.snapshot('r')
    assert s.generated == () and s.discarded_samples == (17,)
    if not quiescent:
        assert s.state == 'CANCEL_PENDING' and s.resident
        h.ledger.quiesce('r', h.alloc(False), stamp=h.time())
    else:
        h.ledger.release('r', h.alloc(False), stamp=h.time())
    assert h.ledger.snapshot('r').disposition == 'CANCELLED'; check(h, True)


@pytest.mark.parametrize('confirmed', [0, 1, 3, 4])
@pytest.mark.parametrize('quiescent', [True, False])
def test_partial_failure_counts_only_confirmed_work(harness, confirmed, quiescent):
    h = harness(); h.admit(); h.ledger.plan('r', Plan('p','b',0,0,4), stamp=h.time())
    h.ledger.acknowledge('r', Acknowledgment('p',0,0,confirmed,success=False,quiescent=quiescent), stamp=h.time())
    s = h.ledger.snapshot('r')
    assert s.prompt_work == confirmed and s.acknowledged == confirmed and not s.generated
    if not quiescent: h.ledger.quiesce('r', h.alloc(False), stamp=h.time())
    else: h.ledger.release('r', h.alloc(False), stamp=h.time())
    assert h.ledger.snapshot('r').disposition == 'FAILED'; check(h, True)


@pytest.mark.parametrize('kind', ['cancel', 'fail'])
@pytest.mark.parametrize('phase', ['waiting', 'partial', 'decode', 'inflight'])
def test_abort_each_state(harness, kind, phase):
    h = harness()
    if phase != 'waiting': h.admit()
    if phase == 'partial': h.work(0, 2, 0)
    if phase == 'decode': h.work(0, 4, 0, (17,))
    if phase == 'inflight': h.ledger.plan('r', Plan('p','b',0,0,4), stamp=h.time())
    getattr(h.ledger, kind)('r', 'explicit reason', stamp=h.time())
    if phase == 'inflight':
        h.ledger.acknowledge('r', Acknowledgment('p',0,0,4,(17,)), stamp=h.time())
    s = h.ledger.snapshot('r')
    assert s.state == 'TERMINAL'
    if s.allocation: h.ledger.release('r', h.alloc(False), stamp=h.time())
    check(h, True)


def test_early_completion_is_not_fixed_target_success(harness):
    h = harness(); h.admit(); h.work(0, 4, 0, (17,))
    h.ledger.complete('r', 'external stop; output rule not selected', stamp=h.time())
    assert h.ledger.snapshot('r').disposition == 'STOPPED'
    h.drain(); check(h, True)
    rejected(h, lambda: h.ledger.complete('r', 'again', stamp=h.time()))


@pytest.mark.parametrize('change', [dict(free_blocks=True), dict(free_blocks=-1), dict(free_blocks=2.5),
    dict(free_blocks=float('nan')), dict(free_blocks=float('inf')), dict(owned_blocks=(1,1)),
    dict(owned_blocks=(9,)), dict(total_blocks=10), dict(owned_blocks=[1])])
def test_allocation_observations_fail_closed(harness, change):
    h = harness(); obs = replace(h.alloc(), **change)
    rejected(h, lambda: h.ledger.admit('r', obs, stamp=h.time()))


def test_observation_identity_and_pool_pin(harness):
    h = harness(); observation = h.alloc(); h.ledger.admit('r', observation, stamp=h.time())
    h.work(0, 4, 0, (17,))
    wrong = replace(h.alloc(False), pool_id='other')
    rejected(h, lambda: h.ledger.preempt('r', wrong, stamp=h.time()))


def test_C24_same_domain_reversal_and_separate_clocks(harness):
    h = harness(); h.admit()
    rejected(h, lambda: h.ledger.plan('r', Plan('p','b',0,0,4),
        stamp=ClockStamp('host/boot/monotonic',0.,'host_control')))
    h = harness(1,1); h.admit(); h.work(0,1,0,(17,))
    h.ledger.emit('r',0,(17,),stamp=h.time('server_observation'))
    h.ledger.observe('r',0,(17,),stamp=ClockStamp('client/boot/monotonic',.001,'client_observation'))
    assert check(h).valid


def test_C22_C25_prefix_and_chunk_evidence(harness):
    h = harness(1,2); h.admit(); h.work(0,1,0,(17,)); h.work(1,2,0,(18,))
    h.ledger.emit('r',0,(17,18),stamp=h.time('server_observation'))
    h.ledger.observe('r',0,(17,18),stamp=h.time('client_observation'))
    events = h.ledger.export()['events']
    assert len([e for e in events if e['kind']=='observe']) == 1
    assert check(h).physical_status == 'NOT_VERIFIED'
    rejected(h, lambda: h.ledger.emit('r',0,(17,),stamp=h.time('server_observation')))


def test_snapshot_and_inputs_are_immutable_and_export_detached(harness):
    h = harness(); h.admit(); s = h.ledger.snapshot('r')
    with pytest.raises(FrozenInstanceError): s.epoch = 9
    with pytest.raises(FrozenInstanceError): s.spec.prompt_tokens = 9
    with pytest.raises(FrozenInstanceError): s.allocation.free_blocks = 0
    exported = h.ledger.export(); exported['events'][0]['after']['spec']['metadata'][0][1] = 'tampered'
    assert h.ledger.snapshot('r').spec.metadata == (('fixture','synthetic'),)
    check(h)


def test_truncated_journal_is_not_complete(harness):
    h = harness(); h.admit(); h.work(0,2,0)
    assert validate(h.ledger.export()).valid
    assert not validate(h.ledger.export(), require_complete=True).valid


def test_unknown_request_does_not_create_state(harness):
    h = harness()
    rejected(h, lambda: h.ledger.admit('missing', h.alloc(), stamp=h.time()))


def test_reference_import_does_not_load_production_or_heavy_dependencies():
    root = Path(__file__).resolve().parents[2]
    code = "import sys; sys.path.insert(0, 'src'); import robustbench.serving_v2.reference; "
    code += "assert not any(k in sys.modules for k in ['robustbench.serving_v2.ledger','torch','vllm','numpy'])"
    subprocess.run([sys.executable, '-S', '-B', '-c', code], cwd=root, check=True)


def test_C03_prescribed_concurrent_work_is_not_policy_selection(harness):
    h = harness(2,3); h.admit(); h.work(0,2,0,(17,))
    p = replace(h.spec('p','pe'), prompt_tokens=7)
    h.ledger.enqueue(p,stamp=h.time()); h.ledger.admit('p',h.alloc(),stamp=h.time())
    h.ledger.plan('r',Plan('d-work','shared-batch',0,2,3),stamp=h.time())
    h.ledger.plan('p',Plan('p-work','shared-batch',0,0,3),stamp=h.time())
    h.ledger.acknowledge('r',Acknowledgment('d-work',0,2,3,(18,)),stamp=h.time())
    h.ledger.acknowledge('p',Acknowledgment('p-work',0,0,3),stamp=h.time())
    expected = CASES['C03']['expected_steps'][0]
    assert len(h.ledger.snapshot('r').generated) == expected['d_G']
    assert h.ledger.snapshot('p').acknowledged == expected['p_C_exec']
    check(h)


def test_C09_literal_allocation_observations_without_allocator(harness):
    h = harness(8,4)
    obs = AllocationObservation('one','pool',3,1,1,(1,),0)
    h.ledger.admit('r',obs,stamp=h.time()); h.work(0,4,0)
    s = h.ledger.snapshot('r'); expected = CASES['C09']['expected_steps'][0]
    assert len(s.allocation.owned_blocks)==expected['owned_blocks']
    assert s.allocation.free_blocks==expected['free_blocks']
    h.ledger.plan('r',Plan('second','b',0,4,8),stamp=h.time())
    obs = AllocationObservation('two','pool',3,1,0,(1,2),0)
    h.ledger.acknowledge('r',Acknowledgment('second',0,4,8,(17,),allocation=obs),stamp=h.time())
    s = h.ledger.snapshot('r'); expected = CASES['C09']['expected_steps'][1]
    assert len(s.allocation.owned_blocks)==expected['owned_blocks']
    assert s.allocation.free_blocks==expected['free_blocks']
    check(h)


def test_C10_literal_external_preemption_effect(harness):
    h = harness(4,3)
    h.ledger.admit('r',AllocationObservation('owned','pool',2,1,0,(1,),0),stamp=h.time())
    h.work(0,4,0,(17,))
    h.ledger.preempt('r',AllocationObservation('freed','pool',2,1,1,(),0),stamp=h.time())
    s = h.ledger.snapshot('r'); expected = CASES['C10']['expected_steps'][0]
    assert (s.epoch,s.acknowledged,s.planned,list(s.generated),s.state) == (
        expected['epoch'],expected['C_exec'],expected['C_plan'],expected['Y'],expected['state'])
    assert s.allocation.free_blocks == expected['free_blocks']; check(h)


@pytest.mark.parametrize('operation', ['admit','preempt','hold','complete','plan','quiesce','release'])
def test_illegal_inflight_operations(harness, operation):
    h = harness(); h.admit(); h.ledger.plan('r',Plan('p','b',0,0,4),stamp=h.time())
    calls = {'admit':lambda:h.ledger.admit('r',h.alloc(),stamp=h.time()),
        'preempt':lambda:h.preempt(), 'hold':lambda:h.ledger.hold('r',stamp=h.time()),
        'complete':lambda:h.ledger.complete('r','stop',stamp=h.time()),
        'plan':lambda:h.ledger.plan('r',Plan('another','b',0,0,1),stamp=h.time()),
        'quiesce':lambda:h.ledger.quiesce('r',h.alloc(False),stamp=h.time()),
        'release':lambda:h.ledger.release('r',h.alloc(False),stamp=h.time())}
    rejected(h,calls[operation])


def test_reused_plan_id_rejected(harness):
    h=harness(); h.admit(); h.ledger.plan('r',Plan('p','b',0,0,4),stamp=h.time())
    h.ledger.acknowledge('r',Acknowledgment('p',0,0,4,(17,)),stamp=h.time())
    rejected(h,lambda:h.ledger.plan('r',Plan('p','b2',0,4,5),stamp=h.time()))


def test_reused_observation_id_rejected(harness):
    h=harness(); observation=h.alloc(); h.ledger.admit('r',observation,stamp=h.time())
    h.ledger.plan('r',Plan('p','b',0,0,4),stamp=h.time())
    rejected(h,lambda:h.ledger.acknowledge('r',Acknowledgment('p',0,0,4,(17,),allocation=observation),stamp=h.time()))


@pytest.mark.parametrize('value', [float('nan'),float('inf'),-1.,True,'1'])
def test_invalid_time_is_not_coerced(harness,value):
    h=harness()
    rejected(h,lambda:h.ledger.admit('r',h.alloc(),stamp=ClockStamp('host',value,'host_control')))


@pytest.mark.parametrize('metadata', [[('a','b')], (('a','b'),('a','c')), (('a',None),), (('a',),)])
def test_C16_metadata_shape_not_class_policy(harness,metadata):
    h=harness(); s=replace(h.spec('other','other'),metadata=metadata)
    rejected(h,lambda:h.ledger.enqueue(s,stamp=h.time()))


def test_client_observation_after_cancel_preserves_previously_emitted_prefix(harness):
    h=harness(); h.admit(); h.work(0,4,0,(17,))
    h.ledger.emit('r',0,(17,),stamp=h.time('server_observation'))
    h.ledger.cancel('r','client stop',stamp=h.time())
    h.ledger.observe('r',0,(17,),stamp=h.time('client_observation'))
    h.ledger.release('r',h.alloc(False),stamp=h.time()); check(h,True)
    rejected(h,lambda:h.ledger.emit('r',1,(18,),stamp=h.time('server_observation')))


def test_cross_request_ack_binding(harness):
    h=harness(); h.admit()
    h.ledger.enqueue(h.spec('other','other'),stamp=h.time())
    h.ledger.admit('other',h.alloc(),stamp=h.time())
    h.ledger.plan('r',Plan('p','batch',0,0,4),stamp=h.time())
    h.ledger.plan('other',Plan('q','batch',0,0,4),stamp=h.time())
    rejected(h,lambda:h.ledger.acknowledge('other',Acknowledgment('p',0,0,4,(17,)),stamp=h.time()))


def test_C28_terminal_cannot_be_replanned(harness):
    h=harness(4,2); h.admit(); h.work(0,4,0,(17,)); h.work(4,5,0,(18,))
    rejected(h,lambda:h.ledger.plan('r',Plan('extra','b',0,5,6),stamp=h.time()))


def test_run_identity_and_provenance_are_read_only(harness):
    h=harness()
    with pytest.raises(AttributeError): h.ledger.run_id='other'
    with pytest.raises(AttributeError): h.ledger.provenance='physical'
    check(h)
