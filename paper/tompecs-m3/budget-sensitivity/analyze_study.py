#!/usr/bin/env python3
"""Independent terminal arithmetic and journal telemetry; no simulator/policy imports."""
import argparse, collections, csv, fractions, gzip, hashlib, itertools, json, math, pathlib
import numpy as np
ap=argparse.ArgumentParser();ap.add_argument('candidate',type=pathlib.Path);ap.add_argument('artifacts',type=pathlib.Path);ap.add_argument('--output',type=pathlib.Path,required=True);a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def write(name,x):(a.output/name).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
manifest=json.loads((a.artifacts/'manifest.json').read_text());ident=manifest['identity'];budgets=ident['budgets'];policies=ident['policies']
inputpath=a.candidate/'evidence/c01/inputs/full-inputs.json';assert sha(inputpath)==ident['frozen_files']['inputs/full-inputs.json']
conditions={c['condition_id']:c for c in json.loads(inputpath.read_text())['conditions']}
metrics=['mean_latency','p95_latency','mean_ttft','p95_ttft','mean_tpot','p95_tpot','token_throughput','arrival_normalized_weighted_goodput']
records=[];audit=[];terminals={};normalized={};raw={};telemetry={};maxerror=collections.defaultdict(float)
for path in sorted((a.artifacts/'cells').glob('*/result.json')):
 r=json.loads(path.read_text());assert r['run_id']==manifest['run_id'];c=conditions[r['condition_id']];req=c['requests'];end=r['terminal'];states=end['requests'];m=r['metrics'];cfg=r['config']
 assert r['requests_sha256']==c['requests_sha256'];assert all(s['completion'] is not None for s in states)
 done=sorted(states,key=lambda s:(s['completion'],s['id']));duration=max(s['completion'] for s in states)-min(x['arrival'] for x in req)
 calc=dict(num_completed=len(done),num_unfinished=0,completion_fraction=1.,observed_seconds=duration,token_throughput=sum(x['output'] for x in req)/duration,request_throughput=len(done)/duration,emitted_token_throughput=sum(s['generated'] for s in states)/duration,arrival_normalized_weighted_goodput=sum(req[s['id']]['priority'] for s in done if s['completion']<=req[s['id']]['deadline'])/sum(x['priority'] for x in req))
 for name,values in [('latency',[s['completion']-req[s['id']]['arrival'] for s in done]),('ttft',[s['first']-req[s['id']]['arrival'] for s in done]),('tpot',[(s['completion']-s['first'])/(req[s['id']]['output']-1) for s in done if req[s['id']]['output']>1])]:
  calc['mean_'+name]=math.fsum(values)/len(values);calc['p95_'+name]=float(np.quantile(values,.95,method='linear'));calc['n_'+name]=len(values)
 for k,v in calc.items():
  err=abs(v-m[k]);maxerror[k]=max(maxerror[k],err);assert math.isclose(v,m[k],rel_tol=1e-12,abs_tol=1e-12),(path,k,v,m[k])
 ep=path.parent/'events.jsonl.gz';assert sha(ep)==r['journal_sha256'];events=[json.loads(x) for x in gzip.open(ep,'rt')]
 progress={i:0 for i in range(len(req))};resident=set();anchors={};complete=set();admissions=[];full=omitted=urgent=ready_total=0;maxage=0.;totalwork=0
 for j,e in enumerate(events):
  ready={i for i in resident if progress[i]==req[i]['prompt']};ready_total+=len(ready)
  ages=[e['time']-anchors[i] for i in ready];maxage=max([maxage]+ages);urgent+=sum(age>=.495 for age in ages)
  dec={s[0] for s in e['executed'] if s[1]=='decode'};omitted+=len(ready-dec)
  work=sum(s[3]-s[2] for s in e['executed']);assert work<=cfg['budget'];full+=work==cfg['budget'];totalwork+=work
  for i,kind,start,stop in e['executed']:
   if i not in resident:admissions.append([i,j,e['time']]);resident.add(i)
   if kind=='prefill':
    progress[i]=stop
    if stop==req[i]['prompt']:anchors[i]=e['end']
   else:anchors[i]=e['end']
  for i in e['completed']:resident.remove(i);complete.add(i)
 assert len(complete)==len(req) and totalwork==sum(x['prompt']+x['output'] for x in req)
 key=(r['condition_id'],r['budget'],r['policy']);terminals[key]=end;normalized[key]=canonical([{**e,'intent':sorted(e['intent']),'executed':sorted(e['executed'])} for e in events]);raw[key]=canonical(events)
 tel=dict(batches=len(events),full_budget_batches=full,omitted_ready_decode_opportunities=omitted,ready_decode_opportunities=ready_total,urgent_decode_opportunities=urgent,max_anchor_age_s=maxage,admissions_sha256=canonical(admissions))
 telemetry[key]=tel
 row={k:r[k] for k in ['condition_id','window','region','source','budget','policy','requests_sha256','synthesis_seed','load_factor']};row.update(m);row.update(tel);records.append(row)
 audit.append(dict(result_path=str(path.relative_to(a.artifacts)),result_sha256=sha(path),journal_sha256=sha(ep),key=r['key'],baseline_result_sha256=r['baseline_result_sha256']))
D={(r['condition_id'],r['budget'],r['policy']):r for r in records};ids=sorted({k[0] for k in D});expected={(c['condition_id'],b,p) for c in ident['conditions'] for b in budgets for p in policies};assert set(D)==expected
comparisons=[];effects=[];equiv=[]
def practical(x,y,metric):
 if x==y:return 0,True
 larger=metric in ['token_throughput','arrival_normalized_weighted_goodput'];loser=min(x,y) if larger else max(x,y)
 if loser==0:return 0,False
 fx,fy,fl=map(fractions.Fraction.from_float,[float(x),float(y),float(loser)])
 if abs(fx-fy)/abs(fl)<=fractions.Fraction(1,10):return 0,True
 return (1 if x>y else -1)*(1 if larger else -1),True
for cid in ids:
 for budget in budgets:
  k=(cid,budget);cf=k+('chunked_fcfs_c01',);df=k+('decode_first_c01',)
  equiv.append(dict(condition_id=cid,budget=budget,terminal_equal=terminals[cf]==terminals[df],normalized_events_equal=normalized[cf]==normalized[df],raw_order_equal=raw[cf]==raw[df],different_request_terminal_count=sum(x!=y for x,y in zip(terminals[cf]['requests'],terminals[df]['requests'])),distinct_terminal_behaviors=len({canonical(terminals[k+(p,)]) for p in policies})))
  if budget==32768:continue
  for p in policies:
   current=D[cid,budget,p];base=D[cid,32768,p]
   changed=normalized[cid,budget,p]!=normalized[cid,32768,p]
   for metric in metrics:
    delta=current[metric]-base[metric];relative=delta/abs(base[metric]) if base[metric] else None
    substantive=changed and ((metric in ['mean_latency','p95_latency','mean_ttft','p95_ttft'] and abs(delta)>=.001) or (metric=='token_throughput' and abs(relative)>=.01) or (metric=='arrival_normalized_weighted_goodput' and abs(delta)>=.005-1e-14))
    effects.append(dict(condition_id=cid,budget=budget,policy=p,metric=metric,baseline=base[metric],perturbed=current[metric],absolute_difference=delta,relative_difference=relative,execution_changed=changed,substantive=substantive))
  for p,q in itertools.combinations(policies,2):
   for metric in metrics:
    x,y=D[cid,32768,p][metric],D[cid,32768,q][metric];u,v=D[cid,budget,p][metric],D[cid,budget,q][metric]
    sa,ea=practical(x,y,metric);sb,eb=practical(u,v,metric)
    # signs after the existing scale tolerance, independent of practical-margin screen
    def sign(a,b):return 0 if abs(a-b)<=1e-12*max(1.,abs(a),abs(b)) else (1 if a>b else -1)
    comparisons.append(dict(condition_id=cid,budget=budget,p=p,q=q,metric=metric,eligible=ea and eb,strict_practical_reversal=sa*sb<0,tolerant_order_changed=sign(x,y)!=sign(u,v)))
summary=dict(state='COMPLETED_SUCCESS',cells=len(records),completed_request_executions=sum(r['num_completed'] for r in records),independent_terminal_metric_max_error=dict(maxerror),per_budget=[],baseline_comparisons=dict(total=len(comparisons),eligible=sum(x['eligible'] for x in comparisons),strict_practical_reversals=sum(x['strict_practical_reversal'] for x in comparisons),tolerant_order_changes=sum(x['tolerant_order_changed'] for x in comparisons)),substantive_endpoint_changes=sum(x['substantive'] for x in effects),uncertainty='Finite, input-selected three-window corpus; paired ranges, no population confidence intervals or IID tests.')
for b in budgets:
 es=[x for x in equiv if x['budget']==b];rs=[r for r in records if r['budget']==b];ef=[x for x in effects if x['budget']==b]
 summary['per_budget'].append(dict(budget=b,cells=len(rs),matched_conditions=len(es),terminal_equal=sum(x['terminal_equal'] for x in es),normalized_events_equal=sum(x['normalized_events_equal'] for x in es),raw_order_equal=sum(x['raw_order_equal'] for x in es),distinct_terminal_behavior_counts=dict(collections.Counter(x['distinct_terminal_behaviors'] for x in es)),full_budget_batches=sum(x['full_budget_batches'] for x in rs),batches=sum(x['batches'] for x in rs),urgent_decode_opportunities=sum(x['urgent_decode_opportunities'] for x in rs),max_anchor_age_s=max(x['max_anchor_age_s'] for x in rs),effects_by_policy={p:{m:{'absolute_range':[min(x['absolute_difference'] for x in ef if x['policy']==p and x['metric']==m),max(x['absolute_difference'] for x in ef if x['policy']==p and x['metric']==m)],'relative_range':[min(x['relative_difference'] for x in ef if x['policy']==p and x['metric']==m and x['relative_difference'] is not None),max(x['relative_difference'] for x in ef if x['policy']==p and x['metric']==m and x['relative_difference'] is not None)]} for m in metrics} for p in policies} if ef else {}))
for name,rows in [('cells.csv',records),('effects.csv',effects),('rank-comparisons.csv',comparisons),('equivalence.csv',equiv)]:
 with (a.output/name).open('w') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
top_changes=[]
for cid in ids:
 for budget in [2048,1024]:
  for metric in metrics:
   def tops(b):
    values={p:D[cid,b,p][metric] for p in policies};best=(max if metric in metrics[-2:] else min)(values.values())
    return sorted(p for p,v in values.items() if abs(v-best)<=1e-12*max(1,abs(best)))
   if tops(32768)!=tops(budget):top_changes.append(dict(condition_id=cid,budget=budget,metric=metric,baseline=tops(32768),perturbed=tops(budget)))
summary['tolerant_top_set_comparisons']=dict(total=len(ids)*2*len(metrics),changes=len(top_changes),changed_cases=top_changes)
lines=[r'\begin{tabular}{@{}rlrrr@{}}\toprule',r'Budget & Adaptation & $\Delta$mean & $\Delta$p95 & $\Delta$throughput \\ \midrule']
for row in summary['per_budget'][1:]:
 for policy,label in [('whole_fcfs_c01','Whole-FCFS'),('chunked_fcfs_c01','Chunked-FCFS'),('slo_gated_c01','SLO-gated')]:
  values=[]
  for metric,scale in [('mean_latency',1000),('p95_latency',1000),('token_throughput',1)]:
   lo,hi=row['effects_by_policy'][policy][metric]['absolute_range'];values.append(f'[{lo*scale:.3f}, {hi*scale:.3f}]')
  lines.append(str(row['budget'])+' & '+label+' & '+' & '.join(values)+r' \\')
lines.append(r'\bottomrule\end{tabular}')
(a.output/'effects-table.tex').write_text('\n'.join(lines)+'\n')
write('summary.json',summary);write('provenance.json',dict(manifest=manifest,artifacts=str(a.artifacts.resolve()),execution_reports={p:json.loads((a.artifacts/(p+'-execution.json')).read_text()) for p in ['pilot','study']},cells=audit))
print(json.dumps({k:v for k,v in summary.items() if k!='per_budget'},indent=2))
