#!/usr/bin/env python3
"""Second saved-evidence audit of sensitivity counts, effects and displayed ranges.

Imports neither the study analyzer nor any engine, policy or referee.
"""
import argparse, collections, csv, gzip, hashlib, itertools, json, math, pathlib
from fractions import Fraction as F
p=argparse.ArgumentParser();p.add_argument('artifacts',type=pathlib.Path);p.add_argument('candidate',type=pathlib.Path);a=p.parse_args();out=pathlib.Path(__file__).resolve().parent
read=lambda name:list(csv.DictReader((out/name).open()))
s=json.loads((out/'summary.json').read_text());provenance=json.loads((out/'provenance.json').read_text());manifest=provenance['manifest'];cfg=manifest['identity']['config'];records={};batch_counts=collections.Counter();omitted_counts=collections.Counter();ready_counts=collections.Counter();max_age=collections.defaultdict(float)
inputs=json.loads((a.candidate/'evidence/c01/inputs/full-inputs.json').read_text())['conditions'];conditions={c['condition_id']:c for c in inputs}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for pin in provenance['cells']:
 path=a.artifacts/pin['result_path'];assert sha(path)==pin['result_sha256'];r=json.loads(path.read_text());ep=path.parent/'events.jsonl.gz';assert sha(ep)==pin['journal_sha256'];key=(r['condition_id'],r['budget'],r['policy'])
 assert r['config']=={**cfg,'budget':r['budget']};assert r['requests_sha256']==conditions[key[0]]['requests_sha256'];ev=[json.loads(line) for line in gzip.open(ep,'rt')];records[key]=(r,ev)
 # A separately reconstructed ready/anchor ledger uses prefill completion
 # and decode events rather than the analyzer's prompt-progress ledger.
 ready={};bkey=(r['budget'],r['policy'])
 for e in ev:
  decoded={span[0] for span in e['executed'] if span[1]=='decode'}
  omitted_counts[bkey]+=len(set(ready)-decoded);ready_counts[bkey]+=len(ready)
  max_age[bkey]=max([max_age[bkey]]+[e['time']-anchor for anchor in ready.values()])
  batch_counts[bkey]+=sum(span[3]-span[2] for span in e['executed'])==r['budget']
  for rid,kind,start,stop in e['executed']:
   if kind=='decode' or stop==conditions[key[0]]['requests'][rid]['prompt']:ready[rid]=e['end']
  for rid in e['completed']:ready.pop(rid,None)
assert len(records)==72
for row in read('cells.csv'):
 k=(row['condition_id'],int(row['budget']),row['policy']);r,ev=records[k]
 for name,value in r['metrics'].items():assert float(row[name])==value,(k,name)
for b in [32768,2048,1024]:
 for policy in manifest['identity']['policies']:
  subset=[r for r in read('cells.csv') if int(r['budget'])==b and r['policy']==policy]
  for field,expected in [('full_budget_batches',batch_counts[b,policy]),('omitted_ready_decode_opportunities',omitted_counts[b,policy]),('ready_decode_opportunities',ready_counts[b,policy])]:assert sum(int(r[field]) for r in subset)==expected
  assert max(float(r['max_anchor_age_s']) for r in subset)==max_age[b,policy]
for row in read('equivalence.csv'):
 cid=row['condition_id'];b=int(row['budget']);x,xe=records[cid,b,'chunked_fcfs_c01'];y,ye=records[cid,b,'decode_first_c01']
 assert (x['terminal']==y['terminal'])==(row['terminal_equal']=='True')
 equal=len(xe)==len(ye) and all(sorted(e['executed'])==sorted(f['executed']) and {k:v for k,v in e.items() if k not in ['executed','intent']}=={k:v for k,v in f.items() if k not in ['executed','intent']} for e,f in zip(xe,ye))
 assert equal==(row['normalized_events_equal']=='True')
 assert (xe==ye)==(row['raw_order_equal']=='True')
 behaviors=len({json.dumps(records[cid,b,p][0]['terminal'],sort_keys=True) for p in manifest['identity']['policies']});assert behaviors==int(row['distinct_terminal_behaviors'])
for row in read('effects.csv'):
 cid,b,p=row['condition_id'],int(row['budget']),row['policy'];m=row['metric'];x=records[cid,b,p][0]['metrics'][m];y=records[cid,32768,p][0]['metrics'][m]
 assert x==float(row['perturbed']) and y==float(row['baseline']) and x-y==float(row['absolute_difference'])
 if y:assert (x-y)/abs(y)==float(row['relative_difference'])
reversals=0;eligible=0;total=0;order_changes=0
for row in read('rank-comparisons.csv'):
 cid,b,p,q,m=row['condition_id'],int(row['budget']),row['p'],row['q'],row['metric'];higher=m in ['token_throughput','arrival_normalized_weighted_goodput']
 vals=[[records[cid,budget,policy][0]['metrics'][m] for policy in [p,q]] for budget in [32768,b]]
 directions=[];elig=[];ordinary=[]
 for x,y in vals:
  losing=(min if higher else max)(x,y);elig.append(losing!=0)
  practical=losing!=0 and 10*abs(F(x)-F(y))>abs(F(losing))
  directions.append((1 if x>y else -1 if x<y else 0) if practical else 0)
  ordinary.append(0 if abs(x-y)<=1e-12*max(1.,abs(x),abs(y)) else (1 if x>y else -1))
 rev=directions[0]*directions[1]<0;assert rev==(row['strict_practical_reversal']=='True');assert all(elig)==(row['eligible']=='True')
 assert (ordinary[0]!=ordinary[1])==(row['tolerant_order_changed']=='True');reversals+=rev;eligible+=all(elig);total+=1;order_changes+=ordinary[0]!=ordinary[1]
assert s['baseline_comparisons']==dict(total=total,eligible=eligible,strict_practical_reversals=reversals,tolerant_order_changes=order_changes)
# Independently enumerate the numerical-tolerance top sets from raw results.
top_changes=[]
metrics=['mean_latency','p95_latency','mean_ttft','p95_ttft','mean_tpot','p95_tpot','token_throughput','arrival_normalized_weighted_goodput']
for cid in sorted({k[0] for k in records}):
 for budget in [2048,1024]:
  for metric in metrics:
   sets=[]
   for b in [32768,budget]:
    values={p:records[cid,b,p][0]['metrics'][metric] for p in manifest['identity']['policies']}
    optimum=sorted(values.values(),reverse=metric in metrics[-2:])[0]
    sets.append(sorted(p for p,v in values.items() if abs(v-optimum)<=1e-12*max(1,abs(optimum))))
   if sets[0]!=sets[1]:top_changes.append(dict(condition_id=cid,budget=budget,metric=metric,baseline=sets[0],perturbed=sets[1]))
assert s['tolerant_top_set_comparisons']==dict(total=96,changes=len(top_changes),changed_cases=top_changes)
# Directly recompute every displayed table range from raw terminal-derived metrics.
table=(out/'effects-table.tex').read_text();display_rows=0
for budget in [2048,1024]:
 for policy in ['whole_fcfs_c01','chunked_fcfs_c01','slo_gated_c01']:
  diffs={m:[] for m in ['mean_latency','p95_latency','token_throughput']}
  for cid in {key[0] for key in records}:
   for m in diffs:diffs[m].append(records[cid,budget,policy][0]['metrics'][m]-records[cid,32768,policy][0]['metrics'][m])
  for m,values in diffs.items():
   scale=1 if m=='token_throughput' else 1000;assert f'[{min(values)*scale:.3f}, {max(values)*scale:.3f}]' in table
  display_rows+=1
# Independent input-domain census, with whole windows retained.
census={}
for source in sorted({c['source'] for c in inputs}):
 windows={c['window']:max(r['prompt'] for r in c['requests']) for c in inputs if c['source']==source}
 census[source]=dict(windows=len(windows),min_window_max_prompt=min(windows.values()),max_window_max_prompt=max(windows.values()),feasible_counts={str(b):sum(v<=b for v in windows.values()) for b in [512,1024,2048,4096]})
report=dict(state='COMPLETED_SUCCESS',cells=72,effects=len(read('effects.csv')),normalized_event_pairs=18,display_rows=display_rows,top_set_comparisons=96,top_set_changes=len(top_changes),rank_comparisons=total,eligible=eligible,practical_reversals=reversals,tolerant_order_changes=order_changes,input_census=census,analyzer_not_imported=True,engine_policy_referee_not_imported=True)
(out/'independent-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
