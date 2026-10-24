"""Descriptive scientific summaries; no inferential claims or experimental runs."""
import collections,csv,hashlib,json,math,pathlib,statistics
R=pathlib.Path(__file__).parent;S=R/'saved';O=R/'review'
def read(p):return json.loads(p.read_text())
def rows(p):
 with p.open() as f:return list(csv.DictReader(f))
def write(name,rs):
 with (O/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
def q(xs,p):
 xs=sorted(xs);z=(len(xs)-1)*p;i=int(z);return xs[i]+(xs[min(i+1,len(xs)-1)]-xs[i])*(z-i)
def mean(xs):return sum(xs)/len(xs)
def direction(m):return -1 if m.startswith(('mean_','p95_')) else 1
def pct(a,b):return 100*(b-a)/abs(a) if a else None
# Validate all remaining aggregate, telemetry and summary fields from per-cell records.
validation={}
for exp,an in [('time01','analysis-v1'),('abl01','analysis')]:
 root=S/exp;ar=root/an;m=read(root/'manifest.json')
 pairs=rows(ar/'paired-differences.csv');groups=collections.defaultdict(list)
 for x in pairs:groups[(x['metric'],x.get('policy',''))].append(x)
 for x in rows(ar/'aggregate-paired.csv'):
  xs=groups[(x['metric'],x.get('policy',''))];ds=[float(z['difference']) for z in xs]
  assert int(x['n_cells'])==len(xs)==int(x['n_observed'])
  assert math.isclose(float(x['mean_paired_difference']),mean(ds),rel_tol=2e-12,abs_tol=1e-15)
  if exp=='abl01':
   for key,value in [('minimum_difference',min(ds)),('maximum_difference',max(ds)),('mean_original',mean([float(z['original']) for z in xs])),('mean_control',mean([float(z['control']) for z in xs]))]:assert math.isclose(float(x[key]),value,rel_tol=2e-12,abs_tol=1e-15)
   for key,value in [('favorable',sum(d*direction(x['metric'])>0 for d in ds)),('adverse',sum(d*direction(x['metric'])<0 for d in ds)),('ties',sum(d==0 for d in ds))]:assert int(x[key])==value
 records={c['cell_id']:read(root/('cells' if exp=='time01' else 'derived-controls')/c['cell_id']/'result.json') for c in m['cells']}
 for x in rows(ar/'telemetry.csv'):
  r=records[x['cell_id']]
  expected={f'{g}_{k}':v for g in ['duration','composition','urgency','admission'] for k,v in r['telemetry'][g].items()} if exp=='time01' else r['baseline_telemetry' if x['arm']=='original_slo' else 'telemetry']
  for k,v in expected.items():assert float(x[k])==v
 validation[exp]={'aggregate_and_telemetry_tables':'PASS'}
# Exact control source differential, independent of tests.
a=(S/'abl01/code/research/m3-abl01/frozen_c01/policies.py').read_text();b=(S/'abl01/code/research/m3-abl01/control_policies.py').read_text();expr='sorted(waiting, key=lambda v: (v.prompt, v.ordinal))'
assert a.count(expr)==1 and a.replace(expr,'waiting')==b
validation['ablation_source_differential']='Exactly one expression replaced, all remaining bytes identical'
# All time model changes stratified by source, pressure, capacity and policy.
timecells=rows(S/'time01/analysis-v1/cells.csv');lookup={}
for x in timecells:lookup[(x['cell_id'],x['mode'])]=x
paired=rows(S/'time01/analysis-v1/paired-differences.csv');dist=[];groups=collections.defaultdict(list)
for x in paired:groups[(x['source'],x['region'],x['profile'],x['policy'],x['metric'])].append(x)
for k,xs in sorted(groups.items()):
 ds=[float(x['difference']) for x in xs];rel=[float(x['relative_change'])*100 for x in xs if x['relative_change']!=''];a=[float(x['fixed']) for x in xs];b=[float(x['variable']) for x in xs]
 dist.append(dict(source=k[0],region=k[1],profile=k[2],policy=k[3],metric=k[4],n=len(xs),fixed_mean=mean(a),variable_mean=mean(b),ratio_of_means_change_pct=pct(mean(a),mean(b)),mean_delta=mean(ds),min_delta=min(ds),median_delta=q(ds,.5),max_delta=max(ds),n_relative=len(rel),median_paired_pct=q(rel,.5) if rel else None,min_paired_pct=min(rel) if rel else None,max_paired_pct=max(rel) if rel else None,favorable=sum(d*direction(k[4])>0 for d in ds),adverse=sum(d*direction(k[4])<0 for d in ds),ties=sum(d==0 for d in ds)))
write('time01-stratified-effects.csv',dist)
# Six-row table separates absolute timing effects from relative scheduling contrast.
effects=rows(O/'source-capacity-effects.csv');ix={(x['experiment'],x['source'],x['profile'],x['policy'],x['metric']):x for x in effects};table=[]
sources=['azure_llm_2024','bailian_qwen','burstgpt']
for s in sources:
 for profile in ['kv131072','kv262144']:
  def get(p,m):return ix[('time01',s,profile,p,m)]
  row={'source':s,'slots':int(profile[2:])//32768,'n_windows':8,'n_settings':2}
  for metric,short in [('mean_latency','mean_latency'),('p95_latency','mean_window_p95'),('token_throughput','token_throughput'),('arrival_normalized_weighted_goodput','deadline_attainment')]:
   c=get('chunked_fcfs_c01',metric);z=get('slo_gated_c01',metric)
   row['chunked_timing_'+short+'_pct']=float(c['ratio_of_means_change_pct'])
   row['slo_vs_chunked_fixed_'+short+'_pct']=pct(float(c['old_mean']),float(z['old_mean']))
   row['slo_vs_chunked_variable_'+short+'_pct']=pct(float(c['new_mean']),float(z['new_mean']))
  table.append(row)
write('table-time01.csv',table)
# Global ABL contrasts, signed relative to original SLO, and source-count table.
ag=rows(S/'abl01/analysis/aggregate-paired.csv')
for x in ag:x['ratio_of_means_control_minus_slo_pct']=pct(float(x['mean_original']),float(x['mean_control']))
write('table-abl01-all-endpoints.csv',ag)
# Numerical-noise sensitivity is explanatory, not a new primary reversal rule.
ab=rows(S/'abl01/analysis/paired-differences.csv');noise={}
for metric in ['mean_latency','mean_ttft','mean_tpot','p95_tpot']:
 xs=[x for x in ab if x['metric']==metric];ds=[float(x['difference']) for x in xs]
 noise[metric]={'max_absolute_difference':max(abs(x) for x in ds),'differences_above_1e_12_seconds':sum(abs(x)>1e-12 for x in ds),'within_1e_12_seconds':sum(abs(x)<=1e-12 for x in ds)}
# Nonzero reversals and distinct experimental contexts, preserving endpoint dependence.
nonzero={}
for exp,an in [('time01','analysis-v1'),('abl01','analysis')]:
 xs=[x for x in rows(S/exp/an/'policy-comparisons.csv') if x['strict_practical_reversal']=='True']
 write(exp+'-nonzero-reversals.csv',xs)
 nonzero[exp]={'endpoint_comparisons':len(xs),'distinct_window_setting_capacity_contexts':len({(x['source'],x['window'],x['region'],x['profile']) for x in xs}),'policy_pairs':list({x['policy_a']+' vs '+x['policy_b'] for x in xs}),'source_counts':dict(collections.Counter(x['source'] for x in xs))}
# Duration summaries from the independently checked event streams.
j=read(O/'time01-journal-validation.json');groups=collections.defaultdict(list)
for x in j['records']:groups[(x['source'],x['profile'],x['policy'])].append(x)
dur=[]
for k,xs in sorted(groups.items()):
 n=sum(x['events'] for x in xs)
 dur.append(dict(source=k[0],slots=int(k[1][2:])//32768,policy=k[2],cells=len(xs),batches=n,weighted_mean_ms=1000*sum(x['duration']['mean']*x['events'] for x in xs)/n,min_batch_ms=1000*min(x['duration']['min'] for x in xs),max_batch_ms=1000*max(x['duration']['max'] for x in xs),median_cell_median_ms=1000*q([x['duration']['p50'] for x in xs],.5),min_cell_p95_ms=1000*min(x['duration']['p95'] for x in xs),max_cell_p95_ms=1000*max(x['duration']['p95'] for x in xs),pure_prefill=sum(x['composition']['prefill_only_batches'] for x in xs),pure_decode=sum(x['composition']['decode_only_batches'] for x in xs),mixed=sum(x['composition']['mixed_batches'] for x in xs),prefill_tokens=sum(x['composition']['prefill_tokens'] for x in xs),decode_tokens=sum(x['composition']['decode_tokens'] for x in xs)))
write('time01-duration-composition.csv',dur)
# The affine timing model has a useful exact total-work identity (rounding tolerated).
m=read(S/'time01/manifest.json');affine=[];fixed_new_batches=[];metricschange=0
for c in m['cells']:
 r=read(S/'time01/cells'/c['cell_id']/'result.json');old=read(S/'time01'/c['baseline']['local_file'])
 expect=.0005*r['terminal']['batches']+(.0005/512)*r['metrics']['prefill_work']+(.0005/8)*r['metrics']['decode_work']
 err=abs(expect-r['metrics']['busy_device_seconds']);assert err<1e-8
 affine.append(err);fixed_new_batches.append(r['terminal']['batches']-old['terminal']['batches'])
 metricschange+=r['metrics']!=old['metrics']
validation['affine_busy_identity']={'max_roundoff_s':max(affine),'timing_changes_batch_count_in_cells':sum(x!=0 for x in fixed_new_batches),'min_delta_batches':min(fixed_new_batches),'max_delta_batches':max(fixed_new_batches)}
summary={'validation':validation,'time01_table':table,'abl01_global':ag,'roundoff_sensitivity':noise,'nonzero_reversals':nonzero,'time01_events':sum(x['events'] for x in j['records']),'abl01_sample_events':sum(x[arm]['events'] for x in read(O/'abl01-journal-validation.json')['records'] for arm in ['control','baseline','equivalent_source'])}
(O/'scientific-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({'validation':validation,'time01_table':table,'nonzero':nonzero,'noise':noise},indent=2))

