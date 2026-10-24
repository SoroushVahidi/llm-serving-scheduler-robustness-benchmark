import ast,dataclasses,itertools,pathlib,types
import pytest
from support import *
from analysis import reversal,ranks,advantage
import engine

def test_exact_one_expression_change():
 a=(HERE/'frozen_c01/policies.py').read_text();b=(HERE/'control_policies.py').read_text();expr='sorted(waiting, key=lambda v: (v.prompt, v.ordinal))'
 assert a.count(expr)==1 and b==a.replace(expr,'waiting')
 class Replace(ast.NodeTransformer):
  count=0
  def visit_Call(self,node):
   if ast.unparse(node)=="sorted(waiting, key=lambda v: (v.prompt, v.ordinal))":self.count+=1;return ast.copy_location(ast.Name(id='waiting',ctx=ast.Load()),node)
   return self.generic_visit(node)
 t=Replace();tree=t.visit(ast.parse(a));assert t.count==1 and ast.dump(tree)==ast.dump(ast.parse(b))

def v(i,p=1,x=0,res=False,anchor=None):return View(i,i,0.,p,x,0,res,anchor)

def test_stable_fcfs_and_prompt_difference():
 cfg=Config(kv_capacity=32768);views=(v(2,5),v(0,100),v(1,5))
 assert control_plan('slo_gated_c01',0.,views,cfg)==[[0,'prefill',0,100]]
 assert original_plan('slo_gated_c01',0.,views,cfg)==[[1,'prefill',0,5]]

def test_urgency_resident_waiting_residual_phases():
 views=(v(0,1,1,True,0.),v(1,600,100,True),v(2,1,1,True,.499),v(3,100),v(4,1));cfg=Config(kv_capacity=4*32768)
 spans=control_plan('slo_gated_c01',.5,views,cfg)
 assert [s[0] for s in spans]==[0,1,3,2]
 assert [s[0] for s in original_plan('slo_gated_c01',.5,views,cfg)]==[0,1,4,2]
 assert spans[1]==[1,'prefill',100,600]

@pytest.mark.parametrize('k',[4,8])
def test_nonbinding_all_stage_masks_and_capacity(k):
 cfg=Config(kv_capacity=k*32768)
 for n in range(k+1):
  for mask in itertools.product((False,True),repeat=n):
   rs=[v(i,1 if dec else 1024,1 if dec else 300,True,0. if i%2 else .499) for i,dec in enumerate(mask)]
   ws=[v(n+j,10 if j%2 else 1000) for j in range(k+3)];views=tuple(reversed(rs+ws))
   a=control_plan('slo_gated_c01',.5,views,cfg);b=original_plan('chunked_fcfs_c01',.5,views,cfg)
   assert sorted(a)==sorted(b) and len(a)==k and sum(s[3]-s[2] for s in a)<=512*k
   for policy in ('whole_fcfs_c01','chunked_fcfs_c01','decode_first_c01'):assert control_plan(policy,.5,views,cfg)==original_plan(policy,.5,views,cfg)

def test_scope_guard_and_binding_counterexample():
 cfg=Config(budget=512);views=(v(0,1,1,True,0.),v(1,512))
 assert control_plan('slo_gated_c01',0.,views,cfg)==[[1,'prefill',0,512]]
 assert original_plan('chunked_fcfs_c01',0.,views,cfg)==[[0,'decode',0,1],[1,'prefill',0,511]]
 with pytest.raises(AssertionError):scope(dataclasses.asdict(cfg))

@pytest.mark.parametrize('k',[4,8])
@pytest.mark.parametrize('staggered',[False,True])
def test_complete_engine_coupling_and_referee(k,staggered):
 cfg=Config(kv_capacity=k*32768);rs=[dict(id=i,arrival=(i//3)*.004 if staggered else 0.,prompt=[1,513,1024][i%3],output=2+i%3,deadline=2.,priority=1.) for i in range(12)]
 cf=[];tcf=engine.simulate(rs,'chunked_fcfs_c01',cfg,cf.append)
 # Isolated function globals: authoritative engine module is not mutated.
 sim=types.FunctionType(engine.simulate.__code__,dict(engine.simulate.__globals__,plan=control_plan));ce=[];tc=sim(rs,'slo_gated_c01',cfg,ce.append)
 assert tc==tcf and validate(rs,dataclasses.asdict(cfg),cf,tcf)==validate(rs,dataclasses.asdict(cfg),ce,tc)
 rebuilt,metrics,tel=replay(rs,dataclasses.asdict(cfg),cf,tcf,'chunked_fcfs_c01',True)
 assert rebuilt==ce
 again=[];assert sim(rs,'slo_gated_c01',cfg,again.append)==tc and again==ce

@pytest.mark.parametrize('k',[4,8])
def test_censoring_and_idle_reconstruction(k):
 cfg=Config(kv_capacity=k*32768,drain=.002);rs=[dict(id=0,arrival=.1,prompt=10,output=100,deadline=.2,priority=1.)]
 es=[];terminal=engine.simulate(rs,'chunked_fcfs_c01',cfg,es.append);assert terminal['unfinished'];assert validate(rs,dataclasses.asdict(cfg),es,terminal)['num_unfinished']==1
 # Production scope intentionally rejects changed drain, even though coupling still holds.
 with pytest.raises(AssertionError):scope(dataclasses.asdict(cfg))

def test_referee_rejects_corrupt_timestamps():
 cfg=Config();rs=[dict(id=0,arrival=0.,prompt=1,output=1,deadline=1.,priority=1.)];es=[];t=engine.simulate(rs,'chunked_fcfs_c01',cfg,es.append);es[0]['end']+=.001
 with pytest.raises(ValueError):validate(rs,dataclasses.asdict(cfg),es,t)

def test_strict_margin_ties_undefined_and_midrank():
 assert reversal(90,100,100,90,-1) is False
 assert reversal(89,100,100,89,-1) is True
 assert reversal(110,100,100,110,1) is False
 assert reversal(111,100,100,111,1) is True
 assert reversal(100,100,90,100,-1) is False
 assert reversal(None,100,90,100,-1) is None
 assert reversal(0,0,90,100,-1) is None
 assert ranks({'a':1,'b':1,'c':2},-1)=={'a':1.5,'b':1.5,'c':3.}
 assert ranks({'a':None,'b':1},1) is None

def test_analysis_denominators_and_known_reversal(tmp_path,monkeypatch):
 # Fabricated metric-table UNIT fixture, not workloads/simulations/evidence.
 import analysis,csv
 monkeypatch.setattr(analysis,'METRICS',{'mean_latency':-1})
 cells=[];index=[];derived={}
 for source in ['A','B','C']:
  for w in range(40):
   for region in ['R0','R1','R2','R3','R4','R5']:
    for profile in ['K4','K8']:
     condition=f'{source}:{w}:{region}';cid=condition+':'+profile
     for policy,value in zip(analysis.POLICIES,[100.,80.,80.,120.]):index.append(dict(condition_id=condition,profile=profile,policy=policy,metrics={'mean_latency':value}))
     cells.append(dict(cell_id=cid,source=source,window=str(w),region=region,profile=profile,identity={'condition_id':condition},baseline={'metrics':{'mean_latency':120.}}))
     t=dict(arrival_deadline_attainment=.5,completed_deadline_attainment=.5)
     derived[cid]=dict(metrics={'mean_latency':80.},telemetry=t,baseline_telemetry=t)
 m=dict(cells=cells,code_sha='unit-test-only');save_new(tmp_path/'manifest.json',m);save_new(tmp_path/'baseline-index.json',index)
 analysis.analyze(tmp_path,m,derived)
 def rows(name):
  with (tmp_path/'analysis'/(name+'.csv')).open() as f:return list(csv.DictReader(f))
 counts=rows('reversal-counts');iv=next(r for r in counts if r['family']=='intervention' and r['level']=='window')
 assert (int(iv['reversals']),int(iv['eligible']),int(iv['total']))==(1440,8640,8640)
 sm=next(r for r in counts if r['family']=='intervention' and r['level']=='source_mean');assert int(sm['reversals'])==36 and int(sm['total'])==216
 for r in counts:
  if r['family']=='cross_source':assert int(r['total'])==216 and int(r['reversals'])==0
  if r['family']=='cross_condition':assert int(r['total'])==540 and int(r['reversals'])==0
 diffs=rows('paired-differences');assert all(float(r['difference'])==-40. for r in diffs if r['metric']=='mean_latency')
