"""Immutable evidence utilities and explicit original CM-0.1 imports."""
import pathlib,sys,json,hashlib,gzip,datetime
HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'frozen_c01'))
from policies import Config,View,plan as original_plan
from validator import validate
from control_policies import plan as control_plan
CONTROL='slo_gated_fcfs_c01'
def read(p):return json.loads(pathlib.Path(p).read_text())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def canon(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save_new(p,x):
 with pathlib.Path(p).open('x') as f:json.dump(x,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
def events(p):
 with gzip.open(p,'rt') as f:return [json.loads(s) for s in f]
def scope(config):
 cfg=Config(**config);k=min(cfg.max_sequences,cfg.kv_capacity//cfg.context)
 assert k in (4,8) and config==dict(block=16,budget=32768,context=32768,drain=50.,dt=.001,kv_capacity=k*32768,max_sequences=64)
 assert cfg.budget>=512*k
 return cfg

def replay(requests,config,es,terminal,original_policy,transform_control=False):
 """Replay saved decisions; never call a simulator or generate a new trajectory."""
 cfg=scope(config);s={r['id']:dict(p=0,d=0,res=False,anchor=None,done=False) for r in requests}
 out=[];admitted={};ready=critical=omitted=selected_critical=order_changed=differential=0;max_age=0.
 for e in es:
  views=tuple(View(r['id'],r['id'],r['arrival'],r['prompt'],s[r['id']]['p'],s[r['id']]['d'],s[r['id']]['res'],s[r['id']]['anchor']) for r in requests if r['arrival']<=e['time'] and not s[r['id']]['done'])
  orig=original_plan(original_policy,e['time'],views,cfg);assert orig==e['intent']==e['executed'],'saved policy mismatch'
  chosen=control_plan('slo_gated_c01',e['time'],views,cfg) if transform_control else orig
  if transform_control:
   assert original_policy=='chunked_fcfs_c01'
   assert sorted(chosen)==sorted(orig),'equivalence failed; do not silently simulate'
   order_changed+=chosen!=orig
  other=original_plan('slo_gated_c01',e['time'],views,cfg) if transform_control else control_plan('slo_gated_c01',e['time'],views,cfg)
  differential+=sorted(chosen)!=sorted(other)
  ds=[v for v in views if v.resident and v.prefilled==v.prompt]
  cr=[v for v in ds if v.anchor is not None and e['time']-v.anchor>=.495];ids={x[0] for x in chosen}
  ready+=len(ds);critical+=len(cr);selected_critical+=sum(v.rid in ids for v in cr);omitted+=sum(v.rid not in ids for v in ds)
  max_age=max([max_age]+[e['time']-v.anchor for v in ds if v.anchor is not None])
  new=dict(e,intent=chosen,executed=chosen);out.append(new)
  for i,kind,a,b in chosen:
   st=s[i];admitted.setdefault(i,e['time']);st['res']=True;st['p' if kind=='prefill' else 'd']=b
   if kind=='decode' or b==requests[i]['prompt']:st['anchor']=e['end']
  for i in e['completed']:s[i]['done']=True;s[i]['res']=False
 metrics=validate(requests,config,out,terminal)
 waits=[t-requests[i]['arrival'] for i,t in admitted.items()]
 completed=[r for r in terminal['requests'] if r['completion'] is not None]
 attainment=sum(r['completion']<=requests[r['id']]['deadline'] for r in completed)
 telemetry=dict(batches=len(out),ready=ready,critical=critical,selected_critical=selected_critical,omitted=omitted,max_age=max_age,
  serialized_order_changed_batches=order_changed,same_state_slo_control_work_difference_batches=differential,
  n_admitted=len(waits),mean_admission_wait=sum(waits)/len(waits) if waits else None,
  deadline_met=attainment,arrival_deadline_attainment=attainment/len(requests),
  completed_deadline_attainment=attainment/len(completed) if completed else None)
 return out,metrics,telemetry

def checked_source(base,row,c,config,transform=False):
 folder=base/row['result_path'];assert sha(folder/'result.json')==row['result_sha256']
 r=read(folder/'result.json');assert r['validated'] is True and r['identity']==row['record_identity'] and r['requests_sha256']==c['requests_sha256']
 assert r['condition_id']==c['condition_id'] and r['policy']==row['policy'] and r['profile']==row['profile']
 assert r['metrics']==row['metrics'] and sha(folder/'events.jsonl.gz')==r['journal_sha256']==row['journal_sha256']
 es=events(folder/'events.jsonl.gz');assert validate(c['requests'],config,es,r['terminal'])==r['metrics']
 out,metrics,telem=replay(c['requests'],config,es,r['terminal'],row['policy'],transform)
 assert metrics==r['metrics']
 return r,out,telem
