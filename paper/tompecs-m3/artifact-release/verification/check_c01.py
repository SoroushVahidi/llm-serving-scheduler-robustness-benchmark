# Adapted from the PR17 saved-record checker; no experiment execution.
import argparse
_parser=argparse.ArgumentParser()
_parser.add_argument('candidate',type=str)
_parser.add_argument('output',type=str)
_args=_parser.parse_args()
from pathlib import Path
import json,hashlib,math,collections
p=Path(_args.candidate)/'evidence/c01';read=lambda f:json.loads(f.read_text());sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();canon=lambda x:hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
sp=read(p/'launch.json');assert canon(sp)=='167b9074e57114203e6aaaf3ded08b7b4d8f0a72b35c69054fa995de8d4ef47a'
for name,h in sp['files'].items():assert sha(p/name)==h,name
m=read(p/sp['manifest']);data=read(p/sp['inputs']);cond={c['condition_id']:c for c in data['conditions']};profiles={x['name']:x['config'] for x in m['profiles']};assert len(cond)==720
assert [{k:v for k,v in c.items() if k!='requests'} for c in data['conditions']]==m['conditions']
for c in cond.values():assert len(c['requests'])==200 and canon(c['requests'])==c['requests_sha256']
rows=read(p/'runs/c01-full-167b9074e5711420/analysis/absolute_metrics.json');expected={(c,k,a) for c in cond for k in profiles for a in m['policies']};assert {(r['condition_id'],r['profile'],r['policy']) for r in rows}==expected
reuse={x['key']:x for x in read(p/'reuse_index.json')['cells']};seen=set();terminal_checked=0;maxdiff=collections.defaultdict(float);journal_map=collections.defaultdict(dict)
for r in rows:
 path=p/r['result_path']/'result.json'
 assert path.is_file(), path
 assert sha(path)==r['result_sha256'];q=read(path);assert q['validated'] and q['identity']==r['record_identity'] and q['metrics']==r['metrics'] and q['journal_sha256']==r['journal_sha256']
 c=cond[r['condition_id']];k=r['profile'];assert r['requests_sha256']==c['requests_sha256']==q['requests_sha256'];assert (r['load_factor'],r['synthesis_seed'])==(c['load_factor'],c['synthesis_seed']);key=r['condition_id']+'::'+k+'::'+r['policy'];seen.add(key)
 if r['reused']:
  assert key in reuse and reuse[key]['result_sha256']==r['result_sha256'] and reuse[key]['journal_sha256']==r['journal_sha256']
 else:assert key not in reuse and q['identity']==canon(sp)
 inp=c['requests'];term=q['terminal'];t=term['requests'];assert len(t)==200 and [x['id'] for x in t]==list(range(200));done=sorted((x for x in t if x['completion'] is not None),key=lambda x:(x['completion'],x['id']))
 assert len(done)==200 and not term['unfinished'];cfg=profiles[k];assert term['administrative_horizon']==max(x['arrival'] for x in inp)+cfg['drain'];assert term['observed_end']<=term['administrative_horizon'];assert all(x['prefilled']==inp[x['id']]['prompt'] and x['generated']==inp[x['id']]['output'] and x['completion']>=x['first']>=inp[x['id']]['arrival'] for x in done)
 duration=term['observed_end']-min(x['arrival'] for x in inp)
 vals={'latency':[x['completion']-inp[x['id']]['arrival'] for x in done],'ttft':[x['first']-inp[x['id']]['arrival'] for x in done],'tpot':[(x['completion']-x['first'])/(inp[x['id']]['output']-1) for x in done if inp[x['id']]['output']>1]}
 metrics={'num_total':200,'num_completed':len(done),'num_unfinished':0,'completion_fraction':1.,'observed_seconds':duration,'request_throughput':200/duration,'token_throughput':sum(x['output'] for x in inp)/duration,'emitted_token_throughput':sum(x['generated'] for x in t)/duration,'prefill_work':sum(x['prompt'] for x in inp),'decode_work':sum(x['output'] for x in inp),'busy_device_seconds':term['batches']*cfg['dt'],'arrival_normalized_weighted_goodput':sum(inp[x['id']]['priority'] for x in done if x['completion']<=inp[x['id']]['deadline'])/sum(x['priority'] for x in inp)}
 for name,v in vals.items():
  v.sort();pos=(len(v)-1)*.95;i=int(pos)
  metrics['n_'+name]=len(v);metrics['p95_'+name]=v[i]+(v[min(i+1,len(v)-1)]-v[i])*(pos-i)
  # Stable summation independently checks the saved naive-sum mean; report actual roundoff.
  metrics['mean_'+name]=math.fsum(v)/len(v)
 for name,v in metrics.items():
  d=abs(v-r['metrics'][name]);maxdiff[name]=max(maxdiff[name],d)
  if not name.startswith('mean_'):assert d==0,(key,name,d)
 assert r['metrics']['peak_used_kv']<=r['metrics']['peak_reserved_kv']<=cfg['kv_capacity']
 journal_map[(r['condition_id'],k)][r['policy']]=q['terminal'];terminal_checked+=1
result=dict(launch_hashes=len(sp['files']),input_conditions=len(cond),expected_cells=len(expected),terminal_metric_records_checked=terminal_checked,reused=sum(x['reused'] for x in rows),distinct_records=len(seen),mean_recomputation_max_absolute_difference=dict(maxdiff),chunked_decode_terminal_equal=sum(v.get('chunked_fcfs_c01')==v.get('decode_first_c01') for v in journal_map.values() if 'chunked_fcfs_c01' in v and 'decode_first_c01' in v))
print(json.dumps(result,indent=2));Path(_args.output).write_text(json.dumps(result,indent=2));assert terminal_checked==5760

assert result["chunked_decode_terminal_equal"]==1440
assert all(v<=1e-12 for v in maxdiff.values()), dict(maxdiff)
