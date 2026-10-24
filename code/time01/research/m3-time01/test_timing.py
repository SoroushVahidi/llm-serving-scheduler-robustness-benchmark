import copy, dataclasses, json, math
import pytest
from support import verify_policy
from policies import Config, POLICIES, View
from engine import simulate as original
from validator import validate as original_validate
from timed_engine import simulate
from timed_validator import validate
from timing import Timing, composition, urgency

T = Timing(mode='composition-v1')
def req(i=0, arrival=0., prompt=512, output=2):
    return dict(id=i,arrival=arrival,prompt=prompt,output=output,deadline=10.,priority=1.)
def run(rs,policy='chunked_fcfs_c01',cfg=Config(),timing=T):
    es=[];tr=simulate(rs,policy,cfg,es.append,timing)
    m=validate(rs,dataclasses.asdict(cfg),es,tr,timing.identity())
    verify_policy(rs,dataclasses.asdict(cfg),policy,es,tr)
    return es,tr,m

@pytest.mark.parametrize('policy',POLICIES)
def test_fixed_exact_original(policy):
    rs=[req(0,prompt=1200),req(1,.0005,30,3),req(2,.01,100,1)]
    cfg=Config();es=[];tr=original(rs,policy,cfg,es.append)
    m=original_validate(rs,dataclasses.asdict(cfg),es,tr)
    assert run(rs,policy,cfg,Timing())==(es,tr,m)

@pytest.mark.parametrize('p,d',[(1,0),(32768,0),(0,1),(0,8),(4092,4)])
def test_duration_positive_composition(p,d):
    spans=([[0,'prefill',7,7+p]] if p else [])+[[i+1,'decode',9,10] for i in range(d)]
    assert composition(spans)==(p,d)
    duration=T.duration(spans,.001)
    assert math.isfinite(duration) and duration>0
    assert duration==(.0005+.0005*p/512+.0005*d/8)
    assert duration==T.duration(list(reversed(spans)),.001)

@pytest.mark.parametrize('bad',[0,-1,float('nan'),float('inf')])
def test_invalid_parameters(bad):
    with pytest.raises(ValueError): Timing(overhead_s=bad)

@pytest.mark.parametrize('policy',POLICIES)
def test_clock_arrivals_completion_metrics(policy):
    rs=[req(output=1),req(1,arrival=.0007,prompt=1,output=1)]
    es,tr,m=run(rs,policy)
    assert es[0]['end']==.001
    assert {s[0] for s in es[0]['executed']}=={0}
    assert any(s[0]==1 for s in es[1]['executed'])
    for e in es:
        p=sum(b-a for i,k,a,b in e['executed'] if k=='prefill')
        d=sum(b-a for i,k,a,b in e['executed'] if k=='decode')
        assert e['end']==e['time']+(.0005+p/1024000+d/16000)
    completions={i:e['end'] for e in es for i in e['completed']}
    assert {s['id']:s['completion'] for s in tr['requests']}==completions
    lat=sorted(completions[i]-r['arrival'] for i,r in enumerate(rs))
    assert m['mean_latency']==sum(lat)/2
    assert m['p95_latency']==lat[0]+.95*(lat[1]-lat[0])
    assert m['token_throughput']==2/max(completions.values())
    assert m['request_throughput']==m['token_throughput']
    assert tr!=run(rs,policy,timing=Timing())[1]

@pytest.mark.parametrize('policy',POLICIES)
def test_deterministic_replay_and_no_oracle_leak(policy):
    rs=[req(0,prompt=1200,output=100),req(1,.0003,32,100)]
    before=copy.deepcopy(rs); a=run(rs,policy)
    assert run(rs,policy)==a and rs==before
    other=copy.deepcopy(rs)
    for r in other:r['output']=200;r['deadline']=100;r['priority']=2
    assert a[0][:20]==run(other,policy)[0][:20]

@pytest.mark.parametrize('drain',[.0001,.001,.0012,.002125])
def test_horizon_refuses_partial_batch(drain):
    rs=[req(output=100)];cfg=Config(drain=drain)
    es,tr,m=run(rs,cfg=cfg)
    assert tr['unfinished'] and tr['observed_end']==drain
    assert all(e['end']<=drain for e in es)
    assert m['mean_latency'] is None and m['token_throughput']==0

@pytest.mark.parametrize('policy',POLICIES)
def test_urgency_uses_elapsed_time_and_reconstructed_anchor(policy):
    # Engineering fixture deliberately lengthens batches to exercise urgency.
    # Scientific parameters remain T, unchanged.
    slow=Timing(mode='composition-v1',prefill_s_per_token=.001)
    rs=[req(0,prompt=1,output=3),req(1,.0005,600,1),req(2,.001,600,1)]
    es,tr,m=run(rs,policy,timing=slow)
    if policy=='whole_fcfs_c01':
        assert any(e['timing']['urgency']['critical'] for e in es)
    assert sum(e['timing']['decode_tokens'] for e in es)==m['decode_work']
    assert sum(e['timing']['prefill_tokens'] for e in es)==m['prefill_work']

def test_gate_threshold_literal():
    views=(View(0,0,0.,1,1,1,True,0.),)
    assert urgency(.494,views,[])['critical']==0
    assert urgency(.495,views,[[0,'decode',1,2]])['selected_critical']==1

def test_independent_referee_rejects_corruption():
    rs=[req()];es,tr,m=run(rs)
    for field in ('duration','prefill_tokens','decode_tokens'):
        bad=copy.deepcopy(es);bad[0]['timing'][field]+=1
        with pytest.raises(ValueError):validate(rs,dataclasses.asdict(Config()),bad,tr,T.identity())
    bad=copy.deepcopy(es);bad[0]['end']+=.0001
    with pytest.raises(ValueError):validate(rs,dataclasses.asdict(Config()),bad,tr,T.identity())
    bad=copy.deepcopy(es);bad[0]['timing']['urgency']['critical']=1
    with pytest.raises(ValueError):validate(rs,dataclasses.asdict(Config()),bad,tr,T.identity())

def test_idle_advance():
    rs=[req(output=1),req(1,10.,prompt=1,output=1)]
    es,tr,m=run(rs)
    assert any(e['time']==10. for e in es)
    assert m['observed_seconds']==tr['observed_end']


def test_horizon_after_idle_jump():
    # First request finishes, second arrives after an idle gap and cannot finish prefill.
    rs=[req(0,prompt=1,output=1),req(1,10.,prompt=512,output=1)]
    es,tr,m=run(rs,cfg=Config(drain=.0001))
    assert tr['blocked_batch']['time']==10.
    assert m['num_completed']==1 and tr['requests'][1]['prefilled']==0
