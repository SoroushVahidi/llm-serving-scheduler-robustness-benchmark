"""Synthetic engineering fixtures; never scientific outcomes."""
import copy, dataclasses, inspect, json
import pytest
from engine import simulate
from policies import Config, View, POLICIES, plan
from validator import validate


def request(i=0, arrival=0., prompt=3, output=2):
    return dict(id=i,arrival=arrival,prompt=prompt,output=output,deadline=10.,priority=1.)

def run(reqs, policy='chunked_fcfs_c01', cfg=Config()):
    events=[]
    terminal=simulate(reqs,policy,cfg,events.append)
    metrics=validate(reqs,dataclasses.asdict(cfg),events,terminal)
    return events,terminal,metrics

@pytest.mark.parametrize('policy',POLICIES)
def test_identical_hand_computable_single_request(policy):
    events,end,m=run([request()],policy)
    assert [e['executed'] for e in events]==[[[0,'prefill',0,3]],[[0,'decode',0,1]],[[0,'decode',1,2]]]
    assert end['requests'][0]['first']==.002
    assert end['requests'][0]['completion']==.003
    assert m['busy_device_seconds']==.003 and m['prefill_work']==3 and m['decode_work']==2
    assert m['mean_latency']==.003 and m['mean_tpot']==.001

@pytest.mark.parametrize('policy',POLICIES)
def test_deterministic_replay_and_input_immutability(policy):
    reqs=[request(0,prompt=1100),request(1,.001,4,3),request(2,.002,700,1)]
    before=copy.deepcopy(reqs)
    a=run(reqs,policy);b=run(reqs,policy)
    assert json.dumps(a,sort_keys=True)==json.dumps(b,sort_keys=True) and reqs==before

@pytest.mark.parametrize('policy',POLICIES)
def test_no_latent_output_information_in_prefix(policy):
    a=[request(0,prompt=1100,output=100),request(1,0.,2,100)]
    b=copy.deepcopy(a);b[0]['output']=200;b[1]['output']=300
    ea,_,_=run(a,policy);eb,_,_=run(b,policy)
    assert ea[:20]==eb[:20]
    assert set(View.__dataclass_fields__)=={'rid','ordinal','arrival','prompt','prefilled','generated','resident','anchor'}
    # Scheduler has no closure/global path to raw inputs, future arrivals, predictions or deadlines.
    import policies
    source=inspect.getsource(policies)
    assert 'requests[' not in source and 'deadline' not in source and 'predicted_output' not in source


def test_literal_decisions_distinguish_scheduling_rules():
    cfg=Config(budget=1024,context=2048,kv_capacity=8192)
    v=(View(0,0,0.,100,100,1,True,0.),View(1,1,0.,900,512,0,True,None),
       View(2,2,0.,600,0,0,False,None),View(3,3,0.,20,0,0,False,None))
    assert plan('chunked_fcfs_c01',.01,v,cfg)==[[0,'decode',1,2],[1,'prefill',512,900],[2,'prefill',0,512],[3,'prefill',0,20]]
    assert plan('slo_gated_c01',.01,v,cfg)==[[1,'prefill',512,900],[3,'prefill',0,20],[2,'prefill',0,512],[0,'decode',1,2]]
    assert plan('slo_gated_c01',.6,v,cfg)[0]==[0,'decode',1,2]
    whole=(v[0],v[2],v[3])
    assert plan('whole_fcfs_c01',.01,whole,cfg)==[[2,'prefill',0,600],[3,'prefill',0,20]]
    swapped=(View(0,0,0.,900,512,0,True,None),View(1,1,0.,1,1,1,True,0.))
    assert plan('decode_first_c01',.1,swapped,cfg)[0]==[1,'decode',1,2]
    assert plan('chunked_fcfs_c01',.1,swapped,cfg)[0]==[0,'prefill',512,900]

@pytest.mark.parametrize('policy',POLICIES)
def test_reservation_holds_and_release(policy):
    cfg=Config(context=16,kv_capacity=16,budget=16)
    ev,end,m=run([request(0,prompt=3,output=2),request(1,prompt=1,output=1)],policy,cfg)
    assert all(e['reserved']==16 for e in ev)
    assert all({s[0] for s in e['executed']} in ({0},{1}) for e in ev)
    first_id = 1 if policy == 'slo_gated_c01' else 0
    release = next(k for k,e in enumerate(ev) if e['completed']==[first_id])
    assert ev[release+1]['executed'][0][0] == 1-first_id
    assert all(s[0]==first_id for e in ev[:release+1] for s in e['executed'])
    assert m['num_completed']==2


def test_batched_budget_and_partial_prefill():
    cfg=Config(budget=600,context=1024,kv_capacity=4096)
    ev,_,_=run([request(0,prompt=600),request(1,prompt=600)],cfg=cfg)
    assert ev[0]['executed']==[[0,'prefill',0,512],[1,'prefill',0,88]]
    assert all(sum(b-a for _,_,a,b in e['executed'])<=600 for e in ev)


def test_in_batch_arrival_idle_and_horizon_missingness():
    ev,_,_=run([request(0,prompt=1,output=1),request(1,arrival=.0005,prompt=1,output=1)])
    assert {s[0] for s in ev[0]['executed']}=={0}
    assert any(s[0]==1 for s in ev[1]['executed'])
    ev,_,m=run([request(0,prompt=1,output=100)],cfg=Config(drain=.003))
    assert len(ev)==3 and m['num_unfinished']==1 and m['mean_latency'] is None
    assert m['n_ttft']==0 and m['arrival_normalized_weighted_goodput']==0
    ev,_,_=run([request(0,prompt=1,output=1),request(1,arrival=2.,prompt=1,output=1)])
    assert ev[2]['time']==2.

@pytest.mark.parametrize('mutation',['span','intent','id','time','kv','completion','terminal','budget','missing_event'])
def test_independent_referee_rejects_corruption(mutation):
    reqs=[request()];cfg=Config();ev,end,_=run(reqs)
    if mutation=='span': ev[0]['executed'][0][3]+=1
    if mutation=='intent': ev[0]['intent']=[]
    if mutation=='id': ev[0]['executed'][0][0]=999
    if mutation=='time': ev[0]['end']+=.002
    if mutation=='kv': ev[0]['reserved']-=1
    if mutation=='completion': ev[0]['completed']=[0]
    if mutation=='terminal': end['requests'][0]['completion']=99.
    if mutation=='budget': cfg=Config(budget=1)
    if mutation=='missing_event': ev.pop(1)
    with pytest.raises(ValueError): validate(reqs,dataclasses.asdict(cfg),ev,end)

@pytest.mark.parametrize('bad',[dict(prompt=40000),dict(output=40000),dict(prompt=0),dict(arrival=float('nan'))])
def test_invalid_inputs_fail_closed(bad):
    r=request();r.update(bad)
    with pytest.raises(ValueError):run([r])

def test_duplicate_identity_rejected():
    with pytest.raises(ValueError):run([request(),request()])


def test_engine_has_no_policy_specific_service_path(monkeypatch):
    import engine
    original=plan
    monkeypatch.setattr(engine,'plan',lambda _policy,t,views,cfg:original('chunked_fcfs_c01',t,views,cfg))
    requests=[request(0,prompt=700,output=2),request(1,0.,4,3)]
    results=[run(requests,p) for p in POLICIES]
    assert all(r==results[0] for r in results)


def test_future_arrivals_and_metric_overlays_not_in_online_view():
    a=[request(0,0.,700,100),request(1,10.,1,1)]
    b=copy.deepcopy(a);b[1]['arrival']=20.;b[0]['deadline']=.0001;b[0]['historical_prediction']=999999
    for p in POLICIES:
        assert run(a,p)[0][:20]==run(b,p)[0][:20]


def test_reference_rejects_invalid_common_plan_even_when_intent_matches():
    reqs=[request()];ev,end,_=run(reqs)
    ev[0]['intent']=[[0,'decode',0,1]];ev[0]['executed']=copy.deepcopy(ev[0]['intent'])
    with pytest.raises(ValueError):validate(reqs,dataclasses.asdict(Config()),ev,end)


def test_analyzer_ties_missingness_and_rank_agreement():
    from analyze import top,spearman,relative
    assert top({'a':1.,'b':1.,'c':None})==['a','b']
    assert top({'a':1.,'b':1.-1e-13},1e-12)==['a','b']
    assert spearman([1,1],[1,2]) is None
    assert spearman([1,2,3],[3,2,1])==-1.
    assert relative(None,2) is None


def test_runner_resume_identity_corruption_and_analysis(tmp_path,monkeypatch):
    import run as runner
    from pathlib import Path
    monkeypatch.setattr(runner,'HERE',tmp_path)
    conditions=[dict(condition_id='fixture::w0::LOW',source='fixture',window='w0',region='LOW',
        requests=[request()],requests_sha256=runner.canonical([request()]),
        historical={p:{'arrival_normalized_weighted_goodput':1.} for p in POLICIES})]
    inputs=tmp_path/'inputs.json';runner.atomic(inputs,dict(conditions=conditions,historical_comparisons=[]))
    manifest=dict(input_sha256=runner.sha(inputs),conditions=[dict(condition_id=conditions[0]['condition_id'],requests_sha256=conditions[0]['requests_sha256'])],
        profiles=[dict(name='kv131072',config=dataclasses.asdict(Config())),dict(name='kv262144',config=dataclasses.asdict(Config(kv_capacity=262144)))],
        policies=list(POLICIES),expected_cells=8,historical_policy_mapping={p:p for p in POLICIES})
    runner.atomic(tmp_path/'input_manifest.json',manifest)
    launch=tmp_path/'launch-spec.json';runner.atomic(launch,dict(input_sha256=runner.sha(inputs),files={'input_manifest.json':runner.sha(tmp_path/'input_manifest.json')}))
    out=tmp_path/'out';assert runner.run(inputs,launch,out)==0
    assert runner.read(out/'analysis_status.json')['validated_cells']==8
    before={str(p):runner.sha(p) for p in (out/'cells').glob('*/result.json')}
    monkeypatch.setattr(runner,'simulate',lambda *a: (_ for _ in ()).throw(AssertionError('duplicate simulation')))
    assert runner.run(inputs,launch,out)==0
    assert before=={str(p):runner.sha(p) for p in (out/'cells').glob('*/result.json')}
    result=next((out/'cells').glob('*/result.json'));r=runner.read(result);r['metrics']['num_completed']=99;runner.atomic(result,r)
    with pytest.raises(ValueError,match='resume metric'):runner.run(inputs,launch,out)
    # Hash mismatch must stop before checkpoint or simulation.
    inputs.write_text('{}')
    with pytest.raises(ValueError,match='input payload'):runner.run(inputs,launch,out)


def test_historical_margin_threshold_and_zero_loser():
    from analyze import historical_margin,relative
    assert historical_margin(.55,.5)==pytest.approx(.10)
    assert historical_margin(1.,0.) is None
    assert historical_margin(.6,.5)==pytest.approx(.2)
    assert relative(.6,.5)==pytest.approx(1/6)

@pytest.mark.parametrize('field,value',[('kv_capacity',16),('max_sequences',1)])
def test_independent_capacity_limits(field,value):
    reqs=[request(0),request(1)];ev,end,_=run(reqs)
    cfg=dataclasses.asdict(Config());cfg[field]=value
    with pytest.raises(ValueError,match='resource enforcement'):validate(reqs,cfg,ev,end)


def test_unfinished_tokens_are_not_completed_token_throughput():
    _,_,m=run([request(output=100)],cfg=Config(drain=.003))
    assert m['token_throughput']==0 and m['emitted_token_throughput']>0
