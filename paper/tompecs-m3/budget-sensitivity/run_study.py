#!/usr/bin/env python3
"""Bounded budget-only study using hash-verified, unmodified frozen C01 code."""
import argparse, dataclasses, gzip, hashlib, json, pathlib, sys, time, platform
P=pathlib.Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('candidate',type=pathlib.Path);ap.add_argument('output',type=pathlib.Path);ap.add_argument('--phase',choices=['pilot','study'],required=True);a=ap.parse_args()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def save(p,x):
 p.parent.mkdir(parents=True,exist_ok=True); tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(x,sort_keys=True,indent=2)+'\n');tmp.replace(p)
frozen=a.candidate.resolve()/'evidence/c01';launch=json.loads((frozen/'launch.json').read_text())
paths=['inputs/full-inputs.json']+['research/lssp-c01/'+n+'.py' for n in ['engine','policies','validator']]
for p in paths:assert sha(frozen/p)==launch['files'][p],p
sys.dont_write_bytecode=True;sys.path.insert(0,str(frozen/'research/lssp-c01'))
from engine import simulate
from policies import Config,POLICIES
from validator import validate
allc=json.loads((frozen/'inputs/full-inputs.json').read_text())['conditions']
for c in allc:assert canon(c['requests'])==c['requests_sha256']
windows=sorted({c['window'] for c in allc if c['source']=='burstgpt' and 512<max(r['prompt'] for r in c['requests'])<=1024})[:3]
cs=sorted([c for c in allc if c['window'] in windows and c['region'] in ['LOW','HIGH_PRESSURE']],key=lambda c:c['condition_id'])
base=json.loads((frozen/'runs/c01-full-167b9074e5711420/analysis/absolute_metrics.json').read_text())
base={(r['condition_id'],r['policy']):r for r in base if r['profile']=='kv262144'}
identity=dict(protocol_sha256=sha(P/'PROTOCOL.md'),runner_sha256=sha(pathlib.Path(__file__)),frozen_files={p:sha(frozen/p) for p in paths},conditions=[{k:v for k,v in c.items() if k!='requests'} for c in cs],budgets=[32768,2048,1024],policies=POLICIES,config=dataclasses.asdict(Config(kv_capacity=262144)))
actual_runner_sha256=identity['runner_sha256']
identity=json.loads(json.dumps(identity))  # normalize tuples before comparison
run_id=canon(identity);a.output.mkdir(parents=True,exist_ok=True)
manifest=a.output/'manifest.json'
if manifest.exists():
 previous=json.loads(manifest.read_text())
 # Only this explicitly recorded metadata-only predecessor is compatible.
 if previous['identity']['runner_sha256'] != actual_runner_sha256:
  assert previous['identity']['runner_sha256']=='03f942fbe016b3b270cab037156461c490ef44c2568b3e1908aa29c1f862ac68'
  identity['runner_sha256']=previous['identity']['runner_sha256']
 assert previous['identity']==identity
 run_id=canon(identity);assert run_id==previous['run_id']
else:save(manifest,dict(identity=identity,run_id=run_id,candidate=str(a.candidate.resolve()),python=sys.version,platform=platform.platform()))
selected=cs[:1] if a.phase=='pilot' else cs
started=time.monotonic();new=0;reused=0
for c in selected:
 for budget in identity['budgets']:
  cfg=dataclasses.replace(Config(kv_capacity=262144),budget=budget)
  for policy in POLICIES:
   key=c['condition_id']+'::'+str(budget)+'::'+policy;folder=a.output/'cells'/canon(key)[:20];rp=folder/'result.json';ep=folder/'events.jsonl.gz'
   if rp.exists():
    r=json.loads(rp.read_text());assert r['run_id']==run_id and r['key']==key and r['journal_sha256']==sha(ep)
    events=[json.loads(x) for x in gzip.open(ep,'rt')];assert validate(c['requests'],r['config'],events,r['terminal'])==r['metrics'];reused+=1
    continue
   t=time.monotonic();events=[];terminal=simulate(c['requests'],policy,cfg,events.append);metrics=validate(c['requests'],dataclasses.asdict(cfg),events,terminal)
   b=base[c['condition_id'],policy];baseline=json.loads((frozen/b['result_path']/'result.json').read_text());assert sha(frozen/b['result_path']/'result.json')==b['result_sha256']
   if budget==32768:assert terminal==baseline['terminal'] and metrics==baseline['metrics']
   folder.mkdir(parents=True,exist_ok=False)
   with ep.open('wb') as raw:
    with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as out:
     for e in events:out.write((json.dumps(e,separators=(',',':'))+'\n').encode())
   r=dict(execution_runner_sha256=actual_runner_sha256,run_id=run_id,key=key,condition_id=c['condition_id'],window=c['window'],region=c['region'],source=c['source'],budget=budget,policy=policy,config=dataclasses.asdict(cfg),requests_sha256=c['requests_sha256'],synthesis_seed=c['synthesis_seed'],load_factor=c['load_factor'],terminal=terminal,metrics=metrics,journal_sha256=sha(ep),baseline_result_sha256=b['result_sha256'],elapsed_seconds=time.monotonic()-t,validated=True)
   save(rp,r);new+=1;print(key,metrics['num_completed'],round(r['elapsed_seconds'],3),flush=True)
report=dict(execution_runner_sha256=actual_runner_sha256,state='COMPLETED_SUCCESS',phase=a.phase,run_id=run_id,new_cells=new,reused_cells=reused,total_cells=new+reused,elapsed_seconds=time.monotonic()-started)
save(a.output/(a.phase+'-execution.json'),report);print(json.dumps(report),flush=True)
