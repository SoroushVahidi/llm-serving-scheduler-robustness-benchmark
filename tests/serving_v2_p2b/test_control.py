from dataclasses import replace
import hashlib,json
import pytest
from vllm.v1.outputs import ModelRunnerOutput
from robustbench.serving_v2.ledger import RequestSpec,ClockStamp
from robustbench.serving_v2.p2a.types import Span,Proposal,Acceptance,Rejection,BoundaryError
from robustbench.serving_v2.p2b.control import ControlledBoundary,ControlPlan,ExecutionAttestation
from robustbench.serving_v2.p2b.s02 import S02Boundary


def stamp(t):return ClockStamp('synthetic-host',float(t),'host_control')


def enqueue(b,rid,prompt,output=2,cls='loose',ordinal=0,t=0):
    tokens=(12,)*prompt
    digest=hashlib.sha256(json.dumps(list(tokens),separators=(',',':')).encode()).hexdigest()
    b.enqueue(RequestSpec('app-'+rid,rid,prompt,output,digest,stamp(t),
        (('s02_class',cls),('s02_ordinal',str(ordinal)))),tokens,stamp=stamp(t))


def plan(name,rows,holds=(),budget=128,slots=16):
    return ControlPlan(Proposal(name,tuple(Span(r,0,a,z) for r,a,z in rows),budget,slots),holds)


def ack(b,a,samples,t=2):
    ids=[s.request_id for s in a.spans]
    att=ExecutionAttestation(a.batch_id,a.native_step,a.spans,a.spans,a.sample_mask,'complete',True,
                            'synthetic-quiescence-'+a.batch_id,stamp(t),stamp(t))
    out=ModelRunnerOutput(req_ids=ids,req_id_to_index={r:i for i,r in enumerate(ids)},sampled_token_ids=samples)
    b.acknowledge(att,out,stamp=stamp(t))


@pytest.mark.parametrize('rows',[
    [('b',0,2)], [('a',0,1)], [('a',0,2)], [('b',0,2),('a',0,2)],
])
def test_p2a_substitutions_now_enforced(native_factory,rows):
    b=ControlledBoundary(native_factory(budget=128),'exact',enabled=True)
    enqueue(b,'a',2);enqueue(b,'b',2)
    p=plan('x',rows)
    a=b.schedule(p,stamp=stamp(1))
    assert isinstance(a,Acceptance),a
    assert a.spans==p.proposal.spans
    assert b.export()['batches'][0]['native']['counts']=={r:z-s for r,s,z in rows}
    assert all(e['kind']!='ack' for e in b.export()['ledger']['events'])
    ack(b,a,[[42] if s.end==2 else [] for s in a.spans])


def test_paused_prefill_and_hold(native_factory):
    b=ControlledBoundary(native_factory(budget=128),'hold',enabled=True)
    enqueue(b,'decode',1,output=3)
    a=b.schedule(plan('a',[('decode',0,1)]),stamp=stamp(1));ack(b,a,[[42]])
    enqueue(b,'prefill',300,t=3)
    a=b.schedule(plan('b',[('prefill',0,128)],('decode',)),stamp=stamp(4));assert isinstance(a,Acceptance),a
    ack(b,a,[[]],t=5)
    a=b.schedule(plan('c',[('prefill',128,256)],('decode',)),stamp=stamp(6));ack(b,a,[[]],t=7)
    a=b.schedule(plan('d',[('prefill',256,300)],('decode',)),stamp=stamp(8));ack(b,a,[[43]],t=9)
    assert b.s.requests['decode'].num_computed_tokens==1
    assert list(b.s.requests['decode'].output_token_ids)==[42]


def test_s02_class_selection(native_factory):
    b=S02Boundary(native_factory(budget=128),'s02',enabled=True)
    enqueue(b,'medium',8,cls='medium',ordinal=0)
    enqueue(b,'loose',2,cls='loose',ordinal=1)
    enqueue(b,'tight',16,cls='tight',ordinal=2)
    a=b.schedule_s02('a',stamp=stamp(1))
    assert isinstance(a,Acceptance),a
    assert [x.request_id for x in a.spans]==['tight','loose','medium']
    ack(b,a,[[40],[41],[42]])


from dataclasses import asdict
from robustbench.serving_v2.p2b.reference import validate


def intents(*plans):return json.loads(json.dumps({p.proposal.batch_id:asdict(p) for p in plans}))


def complete_fixture(native_factory):
    b=ControlledBoundary(native_factory(budget=128),'complete',enabled=True)
    enqueue(b,'a',2,output=1);enqueue(b,'b',3,output=1)
    p=plan('x',[('b',0,3),('a',0,2)])
    a=b.schedule(p,stamp=stamp(1));assert isinstance(a,Acceptance),a
    ack(b,a,[[41],[42]])
    expected=intents(p)
    assert validate(b.export(),expected).valid,validate(b.export(),expected)
    return b,expected


def test_independent_literal_control(native_factory):
    complete_fixture(native_factory)


def test_s02_literal_and_independent_referee(native_factory):
    b=S02Boundary(native_factory(budget=128),'s02-final',enabled=True)
    enqueue(b,'medium',8,output=1,cls='medium',ordinal=0)
    enqueue(b,'loose',2,output=1,cls='loose',ordinal=1)
    enqueue(b,'tight',16,output=1,cls='tight',ordinal=2)
    a=b.schedule_s02('x',stamp=stamp(1));ack(b,a,[[41],[42],[43]])
    assert validate(b.export()).valid,validate(b.export())


def test_s02_paused_fifo_and_held_decode(native_factory):
    b=S02Boundary(native_factory(budget=3,slots=3),'fifo',enabled=True)
    enqueue(b,'decode',1,output=2,cls='loose',ordinal=0)
    a=b.schedule_s02('0',stamp=stamp(1));ack(b,a,[[40]])
    enqueue(b,'p',7,output=1,cls='loose',ordinal=1,t=3)
    a=b.schedule_s02('1',stamp=stamp(4));assert a.spans==(Span('p',0,0,3),)
    ack(b,a,[[]],t=5)
    enqueue(b,'strict',1,output=1,cls='tight',ordinal=2,t=6)
    a=b.schedule_s02('2',stamp=stamp(7));assert a.spans==(Span('p',0,3,6),)
    ack(b,a,[[]],t=8)
    a=b.schedule_s02('3',stamp=stamp(9));assert a.spans==(Span('p',0,6,7),Span('strict',0,0,1))
    ack(b,a,[[41],[42]],t=10)
    a=b.schedule_s02('4',stamp=stamp(11));assert a.spans==(Span('decode',0,1,2),)
    ack(b,a,[[43]],t=12)
    assert validate(b.export()).valid,validate(b.export())


@pytest.mark.parametrize('rows,holds,budget,slots',[
    ([('a',1,2)],(),128,16), ([('a',0,3)],(),128,16),
    ([('a',0,2),('a',0,2)],(),128,16), ([('other',0,1)],(),128,16),
    ([('a',0,2)],('a',),128,16), ([('a',0,2)],(),1,16),
    ([('a',0,2)],(),128,1),
])
def test_preflight_rejection_is_nonmutating(native_factory,rows,holds,budget,slots):
    b=ControlledBoundary(native_factory(budget=128),'invalid',enabled=True)
    enqueue(b,'a',2)
    before=b._snapshot();step=b.s.current_step
    r=b.schedule(plan('x',rows,holds,budget,slots),stamp=stamp(1))
    assert isinstance(r,Rejection) and not r.native_called
    assert b._snapshot()==before and b.s.current_step==step


def test_cross_phase_interleave_rejected_without_mutation(native_factory):
    b=ControlledBoundary(native_factory(budget=128),'phase',enabled=True)
    enqueue(b,'d',1,output=3)
    a=b.schedule(plan('0',[('d',0,1)]),stamp=stamp(1));ack(b,a,[[42]])
    enqueue(b,'p',2,t=3)
    before=b._snapshot();step=b.s.current_step
    r=b.schedule(plan('1',[('p',0,2),('d',1,2)]),stamp=stamp(4))
    assert isinstance(r,Rejection) and 'CROSS_PHASE' in r.detail and not r.native_called
    assert b._snapshot()==before and b.s.current_step==step


def test_capacity_refusal_preflight(native_factory):
    b=ControlledBoundary(native_factory(budget=128,blocks=9),'capacity',enabled=True)
    enqueue(b,'p',256)
    before=b._snapshot()
    r=b.schedule(plan('x',[('p',0,128)]),stamp=stamp(1))
    assert isinstance(r,Rejection) and not r.native_called
    assert b._snapshot()==before and b.s.current_step==0


def test_unexpected_allocation_refusal_no_rollback_claim(native_factory,monkeypatch):
    b=ControlledBoundary(native_factory(budget=128),'partial-alloc',enabled=True)
    enqueue(b,'a',2);enqueue(b,'b',2)
    real=b.s.kv_cache_manager.allocate_slots
    def refuse(request,*args,**kwargs):
        return None if request.request_id=='b' else real(request,*args,**kwargs)
    monkeypatch.setattr(b.s.kv_cache_manager,'allocate_slots',refuse)
    before=b._snapshot()
    r=b.schedule(plan('x',[('a',0,2),('b',0,2)]),stamp=stamp(1))
    assert isinstance(r,Rejection) and r.native_called
    assert b._snapshot()!=before # first allocation persisted; NO rollback claim
    assert b.s.requests['a'].num_preemptions==0 and b.s.requests['b'].num_preemptions==0
    assert all(e['kind']=='enqueue' for e in b.export()['ledger']['events'])
    assert b.hook.stopped
    with pytest.raises(BoundaryError):b.s.schedule()


def test_running_refusal_does_not_select_victim(native_factory,monkeypatch):
    b=ControlledBoundary(native_factory(budget=128),'running-refusal',enabled=True)
    enqueue(b,'a',1)
    a=b.schedule(plan('x',[('a',0,1)]),stamp=stamp(1));ack(b,a,[[42]])
    monkeypatch.setattr(b.s.kv_cache_manager,'allocate_slots',lambda *a,**kw:None)
    r=b.schedule(plan('y',[('a',1,2)]),stamp=stamp(3))
    assert isinstance(r,Rejection) and r.native_called
    assert b.s.requests['a'].num_preemptions==0
    assert list(b.s.requests['a'].output_token_ids)==[42]


@pytest.mark.parametrize('change',[
    {'batch_id':'wrong'}, {'native_step':0}, {'executed':()}, {'accepted':(Span('a',False,0,2),)},
    {'sample_mask':(False,)}, {'completion':'partial'}, {'completion':'failed'},
    {'quiescent':False}, {'quiescence_evidence':''}, {'provenance':'physical'},
    {'start':stamp(0)}, {'end':ClockStamp('different',2.,'host_control')},
])
def test_bad_attestation_stops(native_factory,change):
    b=ControlledBoundary(native_factory(budget=128),'attest',enabled=True)
    enqueue(b,'a',2)
    a=b.schedule(plan('x',[('a',0,2)]),stamp=stamp(1))
    att=ExecutionAttestation('x',1,a.spans,a.spans,a.sample_mask,'complete',True,'q',stamp(2),stamp(2))
    before=b.export()['ledger']
    with pytest.raises(BoundaryError):
        b.acknowledge(replace(att,**change),ModelRunnerOutput(req_ids=['a'],req_id_to_index={'a':0},sampled_token_ids=[[42]]),stamp=stamp(2))
    assert b.export()['ledger']==before


@pytest.mark.parametrize('path,value',[
    (('batches',0,'native','counts'),{'a':2,'b':4}),
    (('batches',0,'acceptance','spans',0,'end'),4),
    (('batches',0,'control','proposal','spans',0,'request_id'),'a'),
    (('batches',0,'native','new',0,'start'),1),
    (('batches',0,'native','preempted'),['a']),
    (('batches',0,'scheduled','rows','a','computed'),1),
    (('batches',0,'attestation','quiescent'),False),
    (('batches',0,'attestation','executed'),[]),
    (('batches',0,'attestation','completion'),'failed'),
    (('batches',0,'executed','rows','a','output'),[999]),
    (('control_profile',),'native-fcfs'),
])
def test_independent_corruptions(native_factory,path,value):
    b,expected=complete_fixture(native_factory)
    j=b.export();target=j
    for key in path[:-1]:target=target[key]
    target[path[-1]]=value
    assert not validate(j,expected).valid,path


def test_reference_requires_external_intent_and_rejects_forgery(native_factory):
    b,expected=complete_fixture(native_factory)
    assert not validate(b.export()).valid
    expected['x']['proposal']['spans'].reverse()
    assert not validate(b.export(),expected).valid


def test_missing_and_duplicate_ack(native_factory):
    b=ControlledBoundary(native_factory(budget=128),'missing',enabled=True)
    enqueue(b,'a',2,output=1)
    p=plan('x',[('a',0,2)]);a=b.schedule(p,stamp=stamp(1))
    assert validate(b.export(),intents(p),require_complete=False).valid
    assert not validate(b.export(),intents(p)).valid
    ack(b,a,[[42]])
    with pytest.raises(BoundaryError):ack(b,a,[[42]],t=3)


@pytest.mark.parametrize('field,value', [('num_computed_tokens',1),('num_in_flight_tokens',1),('num_preemptions',1)])
def test_inconsistent_native_state(native_factory,field,value):
    b=ControlledBoundary(native_factory(budget=128),'drift',enabled=True);enqueue(b,'a',2)
    setattr(b.s.requests['a'],field,value)
    before=b._snapshot()
    r=b.schedule(plan('x',[('a',0,2)]),stamp=stamp(1))
    assert isinstance(r,Rejection) and b.s.current_step==0 and b._snapshot()==before


def test_equal_s02_keys_stable_unique_ordinal(native_factory):
    b=S02Boundary(native_factory(budget=128),'ties',enabled=True)
    enqueue(b,'second',2,output=1,cls='medium',ordinal=2)
    enqueue(b,'first',2,output=1,cls='loose',ordinal=1)
    a=b.schedule_s02('x',stamp=stamp(1))
    assert [s.request_id for s in a.spans]==['first','second']
    ack(b,a,[[41],[42]])
    assert validate(b.export()).valid,validate(b.export())


@pytest.mark.parametrize('cls,ordinal',[('unknown',1),('tight',0)])
def test_s02_invalid_metadata(native_factory,cls,ordinal):
    b=S02Boundary(native_factory(),'metadata',enabled=True)
    enqueue(b,'a',2,cls='loose',ordinal=0)
    with pytest.raises(BoundaryError):enqueue(b,'b',2,cls=cls,ordinal=ordinal)
    assert list(b.s.requests)==['a']


def test_no_future_output_length_in_admission():
    from robustbench.serving_v2.p2b.s02 import View
    assert 'output_limit' not in View.__dataclass_fields__
    assert 'remaining_output' not in View.__dataclass_fields__


def test_faulty_hook_cannot_silently_substitute(native_factory,monkeypatch):
    b=ControlledBoundary(native_factory(budget=128),'faulty-hook',enabled=True)
    enqueue(b,'a',2);enqueue(b,'b',2)
    # Deliberately remove the token clamp: source-native larger chunk is rejected.
    monkeypatch.setattr(b.s,'_p2b_count',lambda request,upper:upper)
    r=b.schedule(plan('x',[('a',0,1)]),stamp=stamp(1))
    assert isinstance(r,Rejection) and r.native_called and b.hook.stopped
    assert all(e['kind']=='enqueue' for e in b.export()['ledger']['events'])


def test_installed_native_schedule_unchanged(native_factory):
    import inspect,hashlib
    from robustbench.serving_v2.p2a.pins import PINS
    from vllm.v1.core.sched.scheduler import Scheduler
    from pathlib import Path
    source=Path(inspect.getfile(Scheduler))
    original=Scheduler.schedule
    b=ControlledBoundary(native_factory(),'isolated',enabled=True)
    assert Scheduler.schedule is original
    assert hashlib.sha256(source.read_bytes()).hexdigest()==PINS['v1/core/sched/scheduler.py']
    assert 'P2B_NATIVE_ALLOCATION_REFUSAL_NO_RETRY' in b.hook.patch


def test_slot_conservation_includes_held_decode(native_factory):
    b=ControlledBoundary(native_factory(budget=128,slots=1),'slot',enabled=True)
    enqueue(b,'d',1,output=2)
    a=b.schedule(plan('0',[('d',0,1)],slots=1),stamp=stamp(1));ack(b,a,[[42]])
    enqueue(b,'p',2,t=3)
    before=b._snapshot()
    r=b.schedule(plan('1',[('p',0,2)],('d',),slots=1),stamp=stamp(4))
    assert isinstance(r,Rejection) and not r.native_called and b._snapshot()==before


def test_explicit_budget_overcommit(native_factory):
    b=ControlledBoundary(native_factory(budget=2,slots=2),'budget',enabled=True)
    enqueue(b,'a',2);enqueue(b,'b',2)
    before=b._snapshot()
    r=b.schedule(plan('0',[('a',0,2),('b',0,1)],budget=2,slots=2),stamp=stamp(1))
    assert isinstance(r,Rejection) and not r.native_called and b._snapshot()==before


def test_persistent_fifo_rotation_literal():
    from robustbench.serving_v2.p2b.s02 import PrefillPolicy,View
    # State reconstructed from an explicit prior accepted batch: p then q.
    p=PrefillPolicy()
    first=p.propose('0',[View('p',5,0,0,'tight',0,False),View('q',8,0,0,'loose',1,False)],6,2)
    assert first.proposal.spans==(Span('p',0,0,5),Span('q',0,0,1))
    p.acknowledged('0')
    assert p.paused==['q']
    # No completed-prefill request is reinserted into the paused queue.
    second=p.propose('1',[View('p',5,5,1,'tight',0,True),View('q',8,1,0,'loose',1,True)],2,2)
    assert second.proposal.spans==(Span('q',0,1,3),) and second.holds==('p',)
    p.acknowledged('1');assert p.paused==['q']


def test_exhaustive_external_selection_and_chunks(native_factory):
    from itertools import product
    cases=0
    for pa,pb,budget,order in product((1,2),(1,2),(2,3),(('a',),('b',),('a','b'),('b','a'))):
        sizes={'a':pa,'b':pb}
        for counts in product(*(range(1,sizes[r]+1) for r in order)):
            if sum(counts)>budget:continue
            b=ControlledBoundary(native_factory(budget=budget,slots=2),f'enum-{cases}',enabled=True)
            enqueue(b,'a',pa,output=1);enqueue(b,'b',pb,output=1)
            rows=[(r,0,c) for r,c in zip(order,counts,strict=True)]
            p=plan('0',rows,budget=budget,slots=2)
            a=b.schedule(p,stamp=stamp(1));assert isinstance(a,Acceptance),a
            ack(b,a,[[42] if c==sizes[r] else [] for r,c in zip(order,counts,strict=True)])
            assert validate(b.export(),intents(p),require_complete=False).valid,validate(b.export(),intents(p),require_complete=False)
            assert sum(x.end-x.start for x in a.spans)==sum(counts)
            cases+=1
    assert cases==48,cases # 8 + 12 + 12 + 16 feasible plans


def test_s02_output_limits_do_not_change_admission(native_factory):
    orders=[]
    for limits in [(1,30),(30,1)]:
        b=S02Boundary(native_factory(budget=128),'limits',enabled=True)
        enqueue(b,'medium',8,limits[0],cls='medium',ordinal=0)
        enqueue(b,'loose',2,limits[1],cls='loose',ordinal=1)
        a=b.schedule_s02('0',stamp=stamp(1));orders.append([s.request_id for s in a.spans])
    assert orders==[['loose','medium'],['loose','medium']]


def test_forged_s02_policy_rejected_independently(native_factory,monkeypatch):
    b=S02Boundary(native_factory(budget=128),'faulty-policy',enabled=True)
    enqueue(b,'loose',2,output=1,ordinal=0)
    enqueue(b,'tight',8,output=1,cls='tight',ordinal=1)
    original=b.policy.propose
    def wrong(*args):
        result=original(*args)
        bad=ControlPlan(replace(result.proposal,spans=tuple(reversed(result.proposal.spans))),result.holds)
        b.policy._pending=(bad,b.policy._pending[1])
        return bad
    monkeypatch.setattr(b.policy,'propose',wrong)
    a=b.schedule_s02('0',stamp=stamp(1));ack(b,a,[[41],[42]])
    assert not validate(b.export()).valid


def test_fixture_and_patch_evidence(native_factory):
    import os
    from pathlib import Path
    b,expected=complete_fixture(native_factory)
    if os.getenv('P2B_EVIDENCE_DIR'):
        h=Path(os.environ['P2B_EVIDENCE_DIR']);h.mkdir(parents=True,exist_ok=True)
        (h/'native-control-fixture.json').write_text(json.dumps(b.export(),indent=2)+'\n')
        (h/'independent-intents.json').write_text(json.dumps(expected,indent=2)+'\n')
        (h/'scheduler.patch').write_text(b.hook.patch)
        (h/'patch-identity.json').write_text(json.dumps(dict(hook_id=b.export()['hook_id'],
            patched_schedule_sha256=b.hook.digest),indent=2)+'\n')


def test_referee_imports_without_adapter_or_native():
    import subprocess,sys
    script="import sys; import robustbench.serving_v2.p2b.reference; assert not any(x in sys.modules for x in ('torch','vllm','robustbench.serving_v2.p2b.control','robustbench.serving_v2.p2b.hook','robustbench.serving_v2.p2b.s02','robustbench.serving_v2.ledger'))"
    subprocess.run([sys.executable,'-B','-c',script],check=True)


def test_multiple_paused_residents_reorder_exactly(native_factory):
    b=ControlledBoundary(native_factory(budget=128),'resident-order',enabled=True)
    enqueue(b,'p',5);enqueue(b,'q',5)
    p0=plan('0',[('p',0,2),('q',0,1)])
    a=b.schedule(p0,stamp=stamp(1));ack(b,a,[[],[]])
    p1=plan('1',[('q',1,3),('p',2,3)])
    a=b.schedule(p1,stamp=stamp(3));assert a.spans==p1.proposal.spans
    ack(b,a,[[],[]],t=4)
    assert validate(b.export(),intents(p0,p1),require_complete=False).valid
    assert [r.request_id for r in b.s.running]==['p','q'] # canonical residents retained


def test_native_runner_permutation_preserves_output_identity(native_factory):
    b=ControlledBoundary(native_factory(budget=128),'permutation',enabled=True)
    enqueue(b,'long',3,output=1);enqueue(b,'short',1,output=1)
    p=plan('x',[('long',0,3),('short',0,1)])
    a=b.schedule(p,stamp=stamp(1))
    att=ExecutionAttestation('x',1,a.spans,a.spans,a.sample_mask,'complete',True,'q',stamp(2),stamp(2))
    b.acknowledge(att,ModelRunnerOutput(req_ids=['short','long'],req_id_to_index={'short':0,'long':1},
                    sampled_token_ids=[[41],[42]]),stamp=stamp(2))
    assert validate(b.export(),intents(p)).valid,validate(b.export(),intents(p))


def test_faulty_hook_extra_native_requests_rejected(native_factory,monkeypatch):
    from vllm.v1.core.sched.scheduler import Scheduler
    b=ControlledBoundary(native_factory(budget=128),'extra',enabled=True)
    enqueue(b,'a',2);enqueue(b,'b',2)
    monkeypatch.setattr(b.hook,'function',Scheduler.schedule)
    r=b.schedule(plan('x',[('a',0,2)]),stamp=stamp(1))
    assert isinstance(r,Rejection) and r.native_called and b.hook.stopped
    assert all(e['kind']=='enqueue' for e in b.export()['ledger']['events'])


def test_changed_patch_source_rejected(native_factory,monkeypatch):
    from robustbench.serving_v2.p2b import hook
    original=hook.inspect.getsource
    monkeypatch.setattr(hook.inspect,'getsource',lambda f:original(f).replace('request_queue.peek_request()', 'request_queue.peek_changed()'))
    with pytest.raises(BoundaryError,match='patch anchor'):
        ControlledBoundary(native_factory(),'source-drift',enabled=True)


@pytest.mark.parametrize('case_id',['L01','L02','L03','L04','L05'])
def test_frozen_literal_cases(native_factory,case_id):
    from pathlib import Path
    corpus=json.loads((Path(__file__).parents[2]/'docs/serving-contract/p2b-0.1.0/literal-cases.json').read_text())
    c=next(c for c in corpus['cases'] if c['id']==case_id)
    cls=S02Boundary if c['kind']=='s02' else ControlledBoundary
    b=cls(native_factory(budget=128),case_id,enabled=True)
    for rid,prompt,cl,ordinal in c['requests']:enqueue(b,rid,prompt,output=1,cls=cl,ordinal=ordinal)
    p=plan('x',c['spans'])
    a=b.schedule_s02('x',stamp=stamp(1)) if c['kind']=='s02' else b.schedule(p,stamp=stamp(1))
    assert isinstance(a,Acceptance) and a.spans==p.proposal.spans and a.sample_mask==tuple(c['mask'])
    ack(b,a,[[42] if m else [] for m in c['mask']])
    expected=None if c['kind']=='s02' else intents(p)
    assert validate(b.export(),expected,require_complete=False).valid


def test_referee_rejects_wrong_patch_identity(native_factory):
    b,expected=complete_fixture(native_factory)
    j=b.export();j['patched_schedule_sha256']='0'*64
    assert not validate(j,expected).valid


@pytest.mark.parametrize('enabled,device',[(False,'cpu'),(True,'cuda')])
def test_low_level_hook_is_explicitly_cpu_only(native_factory,enabled,device):
    from robustbench.serving_v2.p2b.hook import ControlHook
    s=native_factory()
    s.vllm_config.device_config.device=device # config only; never constructs CUDA tensors
    original=s.schedule
    with pytest.raises(BoundaryError,match='CPU-only'):
        ControlHook(s,enabled=enabled)
    assert s.schedule==original


def test_queue_object_alias_is_rejected_before_mutation(native_factory):
    import copy
    b=ControlledBoundary(native_factory(budget=128),'alias',enabled=True)
    enqueue(b,'a',2)
    b.s.waiting[0]=copy.copy(b.s.requests['a'])
    r=b.schedule(plan('x',[('a',0,2)]),stamp=stamp(1))
    assert isinstance(r,Rejection) and not r.native_called and b.s.current_step==0
