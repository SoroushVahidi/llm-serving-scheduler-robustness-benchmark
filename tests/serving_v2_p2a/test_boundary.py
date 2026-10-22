from dataclasses import replace
import hashlib
import json
import pytest
from vllm.v1.outputs import ModelRunnerOutput
from robustbench.serving_v2.ledger import RequestSpec,ClockStamp
from robustbench.serving_v2.p2a.native import NativeBoundary
from robustbench.serving_v2.p2a.reference import validate
from robustbench.serving_v2.p2a.types import (Span,Proposal,Acceptance,Rejection,RunnerAck,BoundaryError)


def stamp(t):
    return ClockStamp('fixture-host-monotonic',float(t),'host_control')


def enqueue(b,rid,prompt,output=2,arrival=0):
    tokens=(12,)*prompt
    digest=hashlib.sha256(json.dumps(list(tokens),separators=(',',':')).encode()).hexdigest()
    b.enqueue(RequestSpec('app-'+rid,rid,prompt,output,digest,stamp(arrival)),tokens,stamp=stamp(arrival))


def accept(b,name,rows,budget=128,slots=16,t=1):
    p=Proposal(name,tuple(Span(r,0,a,z) for r,a,z in rows),budget,slots)
    result=b.schedule(p,stamp=stamp(t))
    assert isinstance(result,Acceptance),result
    return result


def ack(b,a,samples,t=2):
    ids=[x.request_id for x in a.spans]
    envelope=RunnerAck(a.batch_id,a.native_step,a.spans,a.sample_mask,'synthetic_cpu',True,True)
    output=ModelRunnerOutput(req_ids=ids,req_id_to_index={r:i for i,r in enumerate(ids)},
                             sampled_token_ids=samples)
    b.acknowledge(envelope,output,stamp=stamp(t))


def test_split(native_factory):
    b=NativeBoundary(native_factory(budget=128),'split',enabled=True)
    enqueue(b,'r',300)
    for i,(start,end,samples) in enumerate([(0,128,[]),(128,256,[]),(256,300,[42]),(300,301,[43])]):
        a=accept(b,f'b{i}',[('r',start,end)],t=2*i+1)
        ack(b,a,[samples],t=2*i+2)
    assert b.export()['ledger']['events'][-1]['after']['generated']==[42,43]

    assert validate(b.export()).valid,validate(b.export())


def test_contention_and_slots(native_factory):
    b=NativeBoundary(native_factory(budget=128,slots=2),'contention',enabled=True)
    enqueue(b,'a',1)
    a=accept(b,'b0',[('a',0,1)],slots=2)
    ack(b,a,[[40]])
    enqueue(b,'b',200,arrival=3)
    enqueue(b,'c',1,arrival=3)
    # Decode consumes one budget token; the waiting c cannot use the occupied slot.
    a=accept(b,'b1',[('a',1,2),('b',0,127)],slots=2,t=4)
    assert a.sample_mask==(True,False) and a.active_slots==2
    ack(b,a,[[41],[]],t=5)
    a=accept(b,'b2',[('b',127,200),('c',0,1)],slots=2,t=6)
    ack(b,a,[[42],[43]],t=7)
    a=accept(b,'b3',[('b',200,201),('c',1,2)],slots=2,t=8)
    ack(b,a,[[44],[45]],t=9)
    result=validate(b.export())
    assert result.valid and result.complete and not result.transport_closed,result
    assert result.physical_status=='NOT_VERIFIED'


@pytest.mark.parametrize('rows',[
    [('b',0,2)], # native admits FIFO a, not arbitrary policy b
    [('a',0,1)], # native schedules two tokens: cannot force a short chunk
    [('a',0,2)], # native also schedules b when budget/slots permit
    [('b',0,2),('a',0,2)], # native order differs even with the same token map
])
def test_native_silently_substitutes_policy_is_no_go(native_factory,rows):
    b=NativeBoundary(native_factory(budget=128),'no-go',enabled=True)
    enqueue(b,'a',2); enqueue(b,'b',2)
    result=b.schedule(Proposal('x',tuple(Span(r,0,a,z) for r,a,z in rows),128,16),stamp=stamp(1))
    assert isinstance(result,Rejection) and result.native_called
    assert result.reason.value=='NATIVE_PLAN_DISAGREEMENT'
    assert all(e['kind']=='enqueue' for e in b.export()['ledger']['events'])
    assert b.s.requests['a'].num_computed_tokens==2 # optimistic, NOT executed
    assert not validate(b.export()).valid
    assert isinstance(b.schedule(Proposal('retry',(),128,16),stamp=stamp(2)),Rejection)


@pytest.mark.parametrize('blocks',[2,9,19])
def test_lifetime_capacity_rejection_before_native(native_factory,blocks):
    b=NativeBoundary(native_factory(budget=128,blocks=blocks),'pressure',enabled=True)
    enqueue(b,'r',300,output=8)
    result=b.schedule(Proposal('x',(Span('r',0,0,128),),128,16),stamp=stamp(1))
    assert isinstance(result,Rejection) and not result.native_called
    assert result.reason.value=='NO_PRESSURE_DOMAIN_NOT_PROVEN'
    assert b.s.requests['r'].num_computed_tokens==0


@pytest.mark.parametrize('mutation',[
    {'batch_id':'stale'}, {'native_step':0}, {'native_step':True},
    {'spans':(Span('r',1,0,2),)}, {'spans':(Span('r',0,1,2),)},
    {'spans':()}, {'sample_mask':(False,)}, {'sample_mask':(1,)},
    {'success':False}, {'quiescent':False}, {'provenance':'physical'},
])
def test_invalid_ack_atomic(native_factory,mutation):
    b=NativeBoundary(native_factory(budget=128),'bad-ack',enabled=True)
    enqueue(b,'r',2)
    a=accept(b,'b0',[('r',0,2)])
    before=b.export()['ledger']
    envelope=RunnerAck('b0',a.native_step,a.spans,(True,),'synthetic_cpu',True,True)
    runner=ModelRunnerOutput(req_ids=['r'],req_id_to_index={'r':0},sampled_token_ids=[[42]])
    with pytest.raises(BoundaryError):
        b.acknowledge(replace(envelope,**mutation),runner,stamp=stamp(2))
    assert b.export()['ledger']==before
    assert b.s.requests['r'].num_output_tokens==0
    assert not validate(b.export()).valid


@pytest.mark.parametrize('ids,index,samples',[
    (['r','r'],{'r':0},[[42],[42]]), ([],{},[]), (['other'],{'other':0},[[42]]),
    (['r'],{'r':1},[[42]]), (['r'],{'r':0},[[]]), (['r'],{'r':0},[[42,43]]),
    (['r'],{'r':0},[[True]]), (['r'],{'r':0},[[-1]]),
])
def test_bad_runner_rows(native_factory,ids,index,samples):
    b=NativeBoundary(native_factory(budget=128),'bad-runner',enabled=True)
    enqueue(b,'r',2)
    a=accept(b,'b0',[('r',0,2)])
    before=b.export()['ledger']
    envelope=RunnerAck('b0',a.native_step,a.spans,(True,),'synthetic_cpu',True,True)
    with pytest.raises(BoundaryError):
        b.acknowledge(envelope,ModelRunnerOutput(req_ids=ids,req_id_to_index=index,
                                               sampled_token_ids=samples),stamp=stamp(2))
    assert b.export()['ledger']==before


@pytest.mark.parametrize('spans,budget,slots',[
    ((Span('r',0,0,2),Span('r',0,0,2)),128,16),
    ((Span('missing',0,0,2),),128,16), ((Span('r',0,1,2),),128,16),
    ((Span('r',0,0,3),),128,16), ((Span('r',0,0,0),),128,16),
    ((Span('r',True,0,2),),128,16), ((Span('r',0,0,2),),127,16),
    ((Span('r',0,0,2),),128,15), ((Span('r',0,0,2),),True,16),
])
def test_bad_proposals(native_factory,spans,budget,slots):
    b=NativeBoundary(native_factory(budget=128),'bad-plan',enabled=True)
    enqueue(b,'r',2)
    result=b.schedule(Proposal('bad',spans,budget,slots),stamp=stamp(1))
    assert isinstance(result,Rejection) and not result.native_called


def test_duplicate_ack_and_missing_ack(native_factory):
    b=NativeBoundary(native_factory(budget=128),'duplicate',enabled=True)
    enqueue(b,'r',2,output=1)
    a=accept(b,'b0',[('r',0,2)])
    assert validate(b.export(),require_complete=False).valid
    assert not validate(b.export()).valid
    ack(b,a,[[42]])
    assert validate(b.export()).valid
    with pytest.raises(BoundaryError):
        ack(b,a,[[42]],t=3)


def test_partial_batch_failure_no_partial_commit(native_factory):
    b=NativeBoundary(native_factory(budget=128),'atomic',enabled=True)
    enqueue(b,'a',2);enqueue(b,'b',2)
    a=accept(b,'b0',[('a',0,2),('b',0,2)])
    before=b.export()['ledger']
    with pytest.raises(BoundaryError):
        ack(b,a,[[42],[]])
    assert b.export()['ledger']==before
    assert all(r.num_output_tokens==0 for r in b.s.requests.values())


def test_source_and_optin_guards(native_factory,monkeypatch):
    with pytest.raises(BoundaryError,match='opt-in'):
        NativeBoundary(native_factory(),'x')
    from robustbench.serving_v2.p2a import native
    monkeypatch.setitem(native.PINS,'v1/outputs.py','0'*64)
    with pytest.raises(BoundaryError,match='source mismatch'):
        NativeBoundary(native_factory(),'x',enabled=True)


def test_duplicate_request_identity(native_factory):
    b=NativeBoundary(native_factory(),'identity',enabled=True)
    enqueue(b,'r',2)
    with pytest.raises(BoundaryError):
        enqueue(b,'r',2)
    assert len(b.s.requests)==1


def test_immutable_request_guard(native_factory):
    b=NativeBoundary(native_factory(budget=128),'drift',enabled=True)
    enqueue(b,'r',2)
    b.s.requests['r'].prompt_token_ids[0]=99
    r=b.schedule(Proposal('x',(Span('r',0,0,2),),128,16),stamp=stamp(1))
    assert isinstance(r,Rejection) and not r.native_called


def test_unexpected_native_refusal_stops(native_factory,monkeypatch):
    b=NativeBoundary(native_factory(budget=128),'refusal',enabled=True)
    enqueue(b,'r',2)
    monkeypatch.setattr(b.s.kv_cache_manager,'allocate_slots',lambda *a,**kw:None)
    result=b.schedule(Proposal('x',(Span('r',0,0,2),),128,16),stamp=stamp(1))
    assert isinstance(result,Rejection) and result.native_called
    assert b.export()['batches'][0]['native']['counts']=={}


def test_actual_native_refusal_without_adapter(native_factory):
    # Characterization only, outside the P2A sufficient capacity domain.
    from vllm.v1.request import Request
    from vllm.sampling_params import SamplingParams
    s=native_factory(budget=128,blocks=9)
    s.add_request(Request('r',prompt_token_ids=[12]*256,pooling_params=None,
                          sampling_params=SamplingParams(max_tokens=2,ignore_eos=True)))
    out=s.schedule()
    assert out.num_scheduled_tokens=={}
    assert [r.request_id for r in s.waiting]==['r']
    assert s.kv_cache_manager.get_block_ids('r')==([],)


def completed(native_factory):
    b=NativeBoundary(native_factory(budget=128),'complete',enabled=True)
    enqueue(b,'a',2,output=1);enqueue(b,'b',3,output=1)
    a=accept(b,'b0',[('a',0,2),('b',0,3)])
    ack(b,a,[[41],[42]])
    assert validate(b.export()).valid,validate(b.export())
    return b


@pytest.mark.parametrize('path,value',[
    (('batches',0,'acceptance','tokens'),4),
    (('batches',0,'acceptance','active_slots'),1),
    (('batches',0,'acceptance','sample_mask'),[False,True]),
    (('batches',0,'acceptance','spans',0,'start'),1),
    (('batches',0,'native','counts'),{'a':2}),
    (('batches',0,'native','total'),6),
    (('batches',0,'native','new',0,'start'),1),
    (('batches',0,'native','new',1,'id'),'a'),
    (('batches',0,'native','cached'),[{'id':'a','start':0}]),
    (('batches',0,'native','preempted'),['a']),
    (('batches',0,'before','waiting'),['b','a']),
    (('batches',0,'before','rows','a','computed'),1),
    (('batches',0,'before','free_blocks'),1),
    (('batches',0,'scheduled','rows','a','computed'),1),
    (('batches',0,'scheduled','rows','b','blocks'),[1]),
    (('batches',0,'ack','native_step'),2),
    (('batches',0,'ack','quiescent'),False),
    (('batches',0,'ack','provenance'),'physical'),
    (('batches',0,'runner','samples'),[[41],[]]),
    (('batches',0,'runner','index'),{'a':1,'b':0}),
    (('batches',0,'executed','rows','a','output'),[99]),
    (('batches',0,'executed','running'),['a']),
    (('batches',0,'ledger_end'),4),
    (('registry','b'),'app-a'),
    (('provenance',),'physical'),
])
def test_independent_referee_corruptions(native_factory,path,value):
    j=completed(native_factory).export()
    target=j
    for key in path[:-1]:
        target=target[key]
    target[path[-1]]=value
    assert not validate(j).valid,path


def test_faulty_adapter_invents_acceptance(native_factory,monkeypatch):
    b=NativeBoundary(native_factory(budget=128),'faulty',enabled=True)
    enqueue(b,'a',2);enqueue(b,'b',3)
    # Fault injection: producer ignores native FIFO a and fabricates b-only acceptance.
    def faulty(p,before,after,wire):
        return Acceptance(p.batch_id,b.s.current_step,p.spans,3,1,(True,))
    monkeypatch.setattr(b,'_accepted',faulty)
    result=b.schedule(Proposal('b0',(Span('b',0,0,3),),128,16),stamp=stamp(1))
    assert isinstance(result,Acceptance) # deliberately broken producer
    assert not validate(b.export(),require_complete=False).valid


def test_faulty_adapter_drops_ledger_ack(native_factory):
    b=completed(native_factory)
    journal=b.export()
    # Dropping a request's ACK while retaining an advertised success is detectable
    # by both local conservation and batch/event binding.
    journal['ledger']['events']=[e for e in journal['ledger']['events']
                               if not(e['kind']=='ack' and e['request_id']=='app-b')]
    assert not validate(journal).valid


def test_exhaustive_small_native_schedules(native_factory):
    from itertools import product
    from robustbench.serving_v2.p2a.reference import fcfs_work
    cases=0
    for pa,pb,oa,ob,budget,slots in product(range(1,4),range(1,4),range(1,3),range(1,3),range(2,5),(1,2)):
        b=NativeBoundary(native_factory(budget=budget,slots=slots),f'case-{cases}',enabled=True)
        enqueue(b,'a',pa,oa);enqueue(b,'b',pb,ob)
        rows={'a':dict(prompt=pa,computed=0,output=[]),'b':dict(prompt=pb,computed=0,output=[])}
        limits={'a':oa,'b':ob}; running=[];waiting=['a','b'];step=0
        while running or waiting:
            work,resident=fcfs_work(running,waiting,rows,budget,slots)
            spans=tuple(Span(**x) for x in work)
            mask=tuple(x['end']==rows[x['request_id']]['prompt']+len(rows[x['request_id']]['output']) for x in work)
            result=b.schedule(Proposal(f'b{step}',spans,budget,slots),stamp=stamp(step*2+1))
            assert isinstance(result,Acceptance),(cases,result)
            assert result.spans==spans and result.sample_mask==mask
            ids=[x.request_id for x in spans]
            samples=[[100+step] if m else [] for m in mask]
            envelope=RunnerAck(f'b{step}',step+1,spans,mask,'synthetic_cpu',True,True)
            b.acknowledge(envelope,ModelRunnerOutput(req_ids=ids,req_id_to_index={r:i for i,r in enumerate(ids)},
                                                    sampled_token_ids=samples),stamp=stamp(step*2+2))
            for x,tokens in zip(work,samples,strict=True):
                rows[x['request_id']]['computed']=x['end']; rows[x['request_id']]['output']+=tokens
            running=[r for r in resident if len(rows[r]['output'])<limits[r]]
            waiting=[r for r in waiting if r not in resident]
            step+=1
            assert step<=10
        assert validate(b.export()).valid,(cases,validate(b.export()))
        cases+=1
    assert cases==216


def test_fixture_evidence(native_factory):
    import os
    from pathlib import Path
    b=completed(native_factory)
    if os.environ.get('P2A_EVIDENCE_DIR'):
        directory=Path(os.environ['P2A_EVIDENCE_DIR'])
        directory.mkdir(parents=True,exist_ok=True)
        (directory/'native-cpu-fixture.json').write_text(json.dumps(b.export(),indent=2)+'\n')
    assert validate(b.export()).valid


def test_cancellation_race_stops_without_ack_progress(native_factory):
    from vllm.v1.request import RequestStatus
    b=NativeBoundary(native_factory(budget=128),'cancel',enabled=True)
    enqueue(b,'r',2)
    a=accept(b,'b0',[('r',0,2)])
    before=b.export()['ledger']
    b.s.finish_requests(['r'],RequestStatus.FINISHED_ABORTED)
    with pytest.raises(BoundaryError):
        ack(b,a,[[42]])
    assert b.export()['ledger']==before
    assert not validate(b.export()).valid


def test_second_batch_before_ack_is_rejected(native_factory):
    b=NativeBoundary(native_factory(budget=128),'overlap',enabled=True)
    enqueue(b,'r',300)
    accept(b,'b0',[('r',0,128)])
    before=b.export()['ledger']
    result=b.schedule(Proposal('b1',(Span('r',0,128,256),),128,16),stamp=stamp(2))
    assert isinstance(result,Rejection) and not result.native_called
    assert b.export()['ledger']==before


@pytest.mark.parametrize('mutator',[
    lambda c:setattr(c.scheduler_config,'policy','priority'),
    lambda c:setattr(c.scheduler_config,'async_scheduling',True),
    lambda c:setattr(c.scheduler_config,'long_prefill_token_threshold',1),
    lambda c:setattr(c.cache_config,'enable_prefix_caching',True),
    lambda c:setattr(c.parallel_config,'tensor_parallel_size',2),
    lambda c:setattr(c.parallel_config,'data_parallel_size',2),
    lambda c:setattr(c.parallel_config,'pipeline_parallel_size',2),
    None, # runner selection is an environment-backed read-only property
])
def test_unsupported_configuration(native_factory,mutator,monkeypatch):
    s=native_factory()
    if mutator is None:
        monkeypatch.setenv("VLLM_USE_V2_MODEL_RUNNER","0")
    else:
        mutator(s.vllm_config)
    with pytest.raises(BoundaryError):
        NativeBoundary(s,'unsupported',enabled=True)


@pytest.mark.parametrize('path,value',[
    (('batches',0,'ack','spans',0,'epoch'),False),
    (('batches',0,'acceptance','native_step'),True),
    (('batches',0,'native','counts','a'),2.0),
    (('batches',0,'runner','index','a'),False),
    (('configuration','token_budget'),127),
])
def test_strict_telemetry_types(native_factory,path,value):
    j=completed(native_factory).export()
    ref=j
    for key in path[:-1]:ref=ref[key]
    ref[path[-1]]=value
    assert not validate(j).valid


def test_detached_export_and_no_import_of_producer_in_referee(native_factory):
    import subprocess,sys
    b=completed(native_factory)
    exported=b.export();exported['batches'].clear()
    assert len(b.export()['batches'])==1
    command="import sys; import robustbench.serving_v2.p2a.reference; assert not any(x in sys.modules for x in ['vllm','torch','robustbench.serving_v2.ledger','robustbench.serving_v2.p2a.native'])"
    subprocess.run([sys.executable,'-B','-c',command],check=True)


def test_noncritical_decode_vs_paused_prefill_distinguishing_case(native_factory):
    b=NativeBoundary(native_factory(budget=128),'paused',enabled=True)
    enqueue(b,'decode',1,output=4)
    a=accept(b,'b0',[('decode',0,1)]);ack(b,a,[[42]])
    enqueue(b,'prefill',300,arrival=3)
    a=accept(b,'b1',[('decode',1,2),('prefill',0,127)],t=4)
    ack(b,a,[[43],[]],t=5)
    # Hypothetical S02 proposal holds a noncritical decode and serves paused
    # prefill first. The native RUNNING list serves decode first regardless.
    proposal=Proposal('b2',(Span('prefill',0,127,255),),128,16)
    rejection=b.schedule(proposal,stamp=stamp(6))
    assert isinstance(rejection,Rejection) and rejection.native_called
    assert b.export()['batches'][-1]['native']['counts']=={'decode':1,'prefill':127}


def test_s02_binary_vs_three_tier_literal_case():
    # Recommendation comparison only; neither key is installed in the adapter.
    rows=[dict(id='medium-long',tier=1,strict=False,prompt=256,ordinal=0),
          dict(id='loose-short',tier=2,strict=False,prompt=8,ordinal=1)]
    old=sorted(rows,key=lambda r:(r['tier'],r['prompt'],r['ordinal']))
    candidate=sorted(rows,key=lambda r:(not r['strict'],r['prompt'],r['ordinal']))
    assert [r['id'] for r in old]==['medium-long','loose-short']
    assert [r['id'] for r in candidate]==['loose-short','medium-long']


def test_s02_explicit_ordinal_resolves_equal_heap_keys():
    import heapq
    a,b=object(),object()
    queue=[(1.0,0.0,a)]
    with pytest.raises(TypeError):heapq.heappush(queue,(1.0,0.0,b))
    queue=[(1.0,0.0,0,a)];heapq.heappush(queue,(1.0,0.0,1,b))
    assert heapq.heappop(queue)[-1] is a


def test_pinned_v2_runner_row_permutation(native_factory):
    import ast
    from pathlib import Path
    import vllm
    # Execute ONLY the source-pinned standalone pure-Python ordering helper.
    # Never import/instantiate GPUModelRunner or execute its kernels.
    path=Path(vllm.__file__).parent/'v1/worker/gpu/model_runner.py'
    tree=ast.parse(path.read_text())
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='sort_batch_req_ids')
    namespace={}
    exec(compile(ast.Module(body=[function],type_ignores=[]),str(path),'exec'),namespace)
    order=namespace['sort_batch_req_ids']({'long':3,'short':2,'decode':1},1)
    assert order==['decode','short','long']
    b=NativeBoundary(native_factory(budget=128),'permuted',enabled=True)
    enqueue(b,'long',3,output=1);enqueue(b,'short',2,output=1);enqueue(b,'decode',1,output=1)
    a=accept(b,'b0',[('long',0,3),('short',0,2),('decode',0,1)])
    output=ModelRunnerOutput(req_ids=order,req_id_to_index={rid:i for i,rid in enumerate(order)},
                             sampled_token_ids=[[101],[102],[103]])
    b.acknowledge(RunnerAck('b0',a.native_step,a.spans,(True,True,True),'synthetic_cpu',True,True),
                  output,stamp=stamp(2))
    assert validate(b.export()).valid,validate(b.export())
    generated={e['request_id']:e['after']['generated'] for e in b.export()['ledger']['events'] if e['kind']=='ack'}
    assert generated=={'app-long':[103],'app-short':[102],'app-decode':[101]}
