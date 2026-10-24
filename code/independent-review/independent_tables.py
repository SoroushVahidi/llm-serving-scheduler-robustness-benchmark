"""Independent checks from immutable result records. Imports no experiment code."""
import collections,csv,hashlib,itertools,json,math,pathlib,statistics,subprocess,time
from fractions import Fraction
R=pathlib.Path(__file__).parent
S=R/'saved'
BASE=pathlib.Path('/home/soroush/artifacts/m3-four-platform-refresh-20261024/prepared/canonical/evidence/c01')
OUT=R/'review';OUT.mkdir(exist_ok=True)
POL=['whole_fcfs_c01','chunked_fcfs_c01','decode_first_c01','slo_gated_c01']
MET=['mean_latency','p95_latency','mean_ttft','p95_ttft','mean_tpot','p95_tpot','token_throughput','request_throughput','emitted_token_throughput','completion_fraction','arrival_normalized_weighted_goodput']
EXTRA=['arrival_deadline_attainment','completed_deadline_attainment']
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def rows(p):
 with p.open() as f:return list(csv.DictReader(f))
def num(x):return None if x in ['',None] else float(x)
def direction(m):return -1 if m.startswith(('mean_','p95_')) else 1
def near(a,b,label=''):
 if a is None or b is None:assert a is b,(label,a,b)
 else:assert math.isclose(a,b,rel_tol=3e-12,abs_tol=1e-14),(label,a,b)
def pct(a,b):return None if a in (0,None) or b is None else 100*(b-a)/abs(a)
def quantile(a,q):
 a=sorted(a);x=(len(a)-1)*q;i=int(x);return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(x-i)
def mean(a):return sum(a)/len(a) if a and all(x is not None for x in a) else None
def terminal_metrics(requests,r):
 t=r['terminal'];by={x['id']:x for x in t['requests']};done=[i for i in by if by[i]['completion'] is not None]
 elapsed=t['observed_end']-requests[0]['arrival'];total=len(requests)
 m={'num_total':total,'num_completed':len(done),'num_unfinished':total-len(done),'completion_fraction':len(done)/total,'observed_seconds':elapsed,
 'request_throughput':len(done)/elapsed,'token_throughput':sum(requests[i]['output'] for i in done)/elapsed,
 'emitted_token_throughput':sum(x['generated'] for x in by.values())/elapsed,
 'arrival_normalized_weighted_goodput':sum(requests[i]['priority'] for i in done if by[i]['completion']<=requests[i]['deadline'])/sum(q['priority'] for q in requests),
 'prefill_work':sum(x['prefilled'] for x in by.values()),'decode_work':sum(x['generated'] for x in by.values())}
 for label,vs in [('latency',[by[i]['completion']-requests[i]['arrival'] for i in done]),('ttft',[by[i]['first']-requests[i]['arrival'] for i in done]),('tpot',[(by[i]['completion']-by[i]['first'])/(requests[i]['output']-1) for i in done if requests[i]['output']>1])]:
  m['n_'+label]=len(vs);m['mean_'+label]=mean(vs);m['p95_'+label]=quantile(vs,.95) if vs else None
 for k,v in m.items():near(v,r['metrics'][k],k)
 hit=sum(by[i]['completion']<=requests[i]['deadline'] for i in done)
 return {'arrival_deadline_attainment':hit/total,'completed_deadline_attainment':hit/len(done) if done else None}
def rank(v,m):
 ordered=sorted(v.items(),key=lambda kv:direction(m)*kv[1],reverse=True);out={};i=0
 while i<len(ordered):
  j=i+1
  while j<len(ordered) and ordered[j][1]==ordered[i][1]:j+=1
  for k,_ in ordered[i:j]:out[k]=(i+1+j)/2
  i=j
 return out
def adv(a,b,m):
 if a is None or b is None:return None
 a,b=Fraction(a),Fraction(b)
 s=((a>b)-(a<b))*direction(m)
 loser=b if s>=0 else a
 if loser==0:return None
 return s,abs(a-b)/abs(loser)
def rev(a,b,c,d,m):
 x,y=adv(a,b,m),adv(c,d,m)
 return None if x is None or y is None else x[0]*y[0]<0 and min(x[1],y[1])>Fraction(1,10)
def savecsv(name,rs):
 with (OUT/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
full=load(BASE/'inputs/full-inputs.json')
conditions={x['condition_id']:x for x in full['conditions']}
assert len(conditions)==720
allpanels={};summaries={};time_records={};abl_records={};checks={}
for exp,n in [('time01',384),('abl01',1440)]:
 root=S/exp;m=load(root/'manifest.json');complete=load(root/'complete.json')
 assert len(m['cells'])==len({c['cell_id'] for c in m['cells']})==n
 assert complete['code_sha']==m['code_sha'] and complete['manifest_sha256']==sha(root/'manifest.json')
 assert (root/'slurm.exit').read_text().strip()=='0'
 assert sha(root/'inputs.json')==m['inputs_sha256']
 inputs=load(root/'inputs.json')['conditions']
 for c in inputs:
  assert c==conditions[c['condition_id']]
  assert canon(c['requests'])==c['requests_sha256']
 code=root/'code/research'/('m3-'+exp)
 repo=pathlib.Path('/home/soroush/repos/llm-serving-scheduler-m3-'+exp+'-20261023')
 for name,h in m['files'].items():
  assert sha(code/name)==h,(exp,name)
  data=subprocess.check_output(['git','-C',str(repo),'show',m['code_sha']+':research/m3-'+exp+'/'+name])
  assert hashlib.sha256(data).hexdigest()==h
 analysis=root/('analysis-v1' if exp=='time01' else 'analysis')
 hashes=load(root/'analysis-control-v1/analysis-completion.json')['output_hashes'] if exp=='time01' else load(analysis/'verification.json')['output_hashes']
 for name,h in hashes.items():assert sha(analysis/name)==h
 if exp=='abl01':
  assert sha(root/'baseline-index.json')==m['index_sha256']
  assert sha(analysis/'verification.json')==complete['analysis_verification_sha256']
  idx=load(root/'baseline-index.json');assert len(idx)==5760
  ix={(x['condition_id'],x['profile'],x['policy']):x for x in idx};assert len(ix)==5760
  for x in idx:
   f=BASE/x['result_path']/'result.json';assert sha(f)==x['result_sha256']
   r=load(f);assert r['metrics']==x['metrics'] and r['requests_sha256']==x['requests_sha256']
  result_hashes=load(root/'reuse-complete.json')['result_hashes']
 else:result_hashes=complete['result_hashes']
 panels={};records={}
 for c in m['cells']:
  cid=c['cell_id'];i=c['identity'];assert canon(i)==cid and i['code_sha']==m['code_sha']
  inp=conditions[i['condition_id']];assert inp['requests_sha256']==i['requests_sha256'] and inp['synthesis_seed']==i['synthesis_seed'] and inp['load_factor']==i['load_factor']
  key=(c['source'],c['window'],c['region'],c['profile'])
  f=root/('cells' if exp=='time01' else 'derived-controls')/cid/'result.json';assert sha(f)==result_hashes[cid]
  r=load(f);assert r['cell_id']==cid and r['identity']==i and r['manifest_sha256']==sha(root/'manifest.json') and r['validated']
  terminal_metrics(inp['requests'],r)
  if exp=='time01':
   b=load(root/c['baseline']['local_file'])
   assert sha(root/c['baseline']['local_file'])==sha(BASE/c['baseline']['result_path']/'result.json')==c['baseline']['result_sha256']
   terminal_metrics(inp['requests'],b)
   panels.setdefault(key,[{},{}])
   panels[key][0][i['policy']]=b['metrics'];panels[key][1][i['policy']]=r['metrics']
   records[cid]={'cell':c,'new':r,'old':b}
  else:
   baseline=c['baseline'];control=c['equivalent_control']
   for x in [baseline,control]:
    z=ix[(i['condition_id'],c['profile'],x['policy'])];assert z==x
   b=load(BASE/baseline['result_path']/'result.json');cf=load(BASE/control['result_path']/'result.json')
   assert r['terminal']==cf['terminal'] and r['metrics']==cf['metrics'] and r['simulated'] is False
   assert r['source_result_sha256']==control['result_sha256'] and r['source_journal_sha256']==control['journal_sha256'] and r['baseline_result_sha256']==baseline['result_sha256']
   ex0=terminal_metrics(inp['requests'],b);ex1=terminal_metrics(inp['requests'],r)
   for x,y in [(ex0,r['baseline_telemetry']),(ex1,r['telemetry'])]:
    for k,v in x.items():near(v,y[k],k)
   old={p:ix[(i['condition_id'],c['profile'],p)]['metrics'] for p in POL};new={**old,'slo_gated_c01':r['metrics']}
   panels[key]=[old,new]
   records[cid]={'cell':c,'new':r,'old':b,'extra_old':ex0,'extra_new':ex1}
 # Verify every serialized cell row and every paired difference against raw records.
 cr=rows(analysis/'cells.csv');assert len(cr)==n*2
 seen=set()
 for x in cr:
  mode=x.get('mode',x.get('arm'));key=(x['cell_id'],mode);assert key not in seen;seen.add(key)
  rec=records[x['cell_id']];isnew=mode in ['composition-v1','fcfs_waiting_control'];r=rec['new' if isnew else 'old']
  for k,v in r['metrics'].items():near(num(x[k]),v,(exp,k))
  if exp=='abl01':
   for k,v in rec['extra_new' if isnew else 'extra_old'].items():near(num(x[k]),v,k)
 pairs=rows(analysis/'paired-differences.csv');assert len(pairs)==n*(11 if exp=='time01' else 13);seen=set()
 for x in pairs:
  k=(x['cell_id'],x['metric']);assert k not in seen;seen.add(k);rec=records[k[0]];metric=k[1]
  a=rec['old']['metrics'].get(metric,rec.get('extra_old',{}).get(metric));b=rec['new']['metrics'].get(metric,rec.get('extra_new',{}).get(metric))
  near(num(x['fixed' if exp=='time01' else 'original']),a);near(num(x['variable' if exp=='time01' else 'control']),b)
  near(num(x['difference']),b-a if None not in (a,b) else None)
  near(num(x['relative_change']),None if pct(a,b) is None else pct(a,b)/100)
 source={}
 for g in sorted({(k[0],k[2],k[3]) for k in panels}):
  vv=[v for k,v in panels.items() if (k[0],k[2],k[3])==g];assert len(vv)==(8 if exp=='time01' else 40)
  source[(g[0],'SOURCE_MEAN',g[1],g[2])]=[{p:{metric:mean([v[arm][p][metric] for v in vv]) for metric in MET} for p in POL} for arm in [0,1]]
 # Source summaries are directly reconciled.
 if exp=='time01':
  for x in rows(analysis/'source-means.csv'):
   g=(x['source'],'SOURCE_MEAN',x['region'],x['profile']);near(num(x['mean']),source[g][0 if x['mode']=='fixed' else 1][x['policy']][x['metric']])
 else:
  for x in rows(analysis/'source-condition-means.csv'):
   rs=[v for v in records.values() if (v['cell']['source'],v['cell']['region'],v['cell']['profile'])==(x['source'],x['region'],x['profile'])]
   metric=x['metric'];a=[v['old']['metrics'].get(metric,v['extra_old'].get(metric)) for v in rs];b=[v['new']['metrics'].get(metric,v['extra_new'].get(metric)) for v in rs]
   near(num(x['mean_original']),mean(a));near(num(x['mean_control']),mean(b));near(num(x['mean_paired_difference']),mean([y-z for z,y in zip(a,b)]))
 # Ranks and top-set change are reconstructed from raw panel metrics.
 rankcounts=collections.defaultdict(lambda:collections.Counter())
 seen=set()
 for x in rows(analysis/'rankings.csv'):
  key=(x['source'],x['window'],x['region'],x['profile']);vs=(panels if x['level']=='window' else source)[key];metric=x['metric']
  k=(x['level'],key,metric,x['policy']);assert k not in seen;seen.add(k)
  rr=[rank({p:v[p][metric] for p in POL},metric) for v in vs]
  ts=[{p for p in POL if rr[a][p]==min(rr[a].values())} for a in [0,1]]
  near(num(x['fixed_rank' if exp=='time01' else 'original_rank']),rr[0][x['policy']]);near(num(x['variable_rank' if exp=='time01' else 'ablated_rank']),rr[1][x['policy']])
  assert set(x['fixed_top_set' if exp=='time01' else 'original_top'].split('|'))==ts[0]
  assert set(x['variable_top_set' if exp=='time01' else 'ablated_top'].split('|'))==ts[1]
  if x['policy']==POL[0]:
   cnt=rankcounts[(x['level'],metric)];cnt['panels']+=1;cnt['top_set_changed']+=ts[0]!=ts[1];cnt['ranks_changed']+=rr[0]!=rr[1];cnt['top_sets_disjoint']+=not bool(ts[0]&ts[1])
   nts=[]
   for arm in [0,1]:
    z={p:vs[arm][p][metric] for p in POL};best=max(direction(metric)*v for v in z.values())*direction(metric)
    nts.append({p for p,v in z.items() if abs(v-best)<=1e-12*max(1,abs(best))})
   cnt['near_tie_top_set_changed']+=nts[0]!=nts[1]
 # Reversal counts and exact rational margins independently recalculated.
 counts=collections.defaultdict(collections.Counter);comparisons=rows(analysis/'policy-comparisons.csv');seen=set()
 for x in comparisons:
  g=(x['source'],x['window'],x['region'],x['profile']);metric=x['metric'];a,b=x['policy_a'],x['policy_b'];v=(panels if x['level']=='window' else source)[g]
  family=x.get('family','timing');arm=x.get('arm','timing')
  if family in ['timing','intervention']:expect=[v[0][a][metric],v[0][b][metric],v[1][a][metric],v[1][b][metric]]
  else:
   h=(x['context2'],'SOURCE_MEAN',g[2],g[3]) if family=='cross_source' else (g[0],'SOURCE_MEAN',x['context2'],g[3]);j=0 if arm=='original' else 1
   expect=[source[g][j][a][metric],source[g][j][b][metric],source[h][j][a][metric],source[h][j][b][metric]]
  fields=['fixed_a','fixed_b','variable_a','variable_b'] if exp=='time01' else ['value1_a','value1_b','value2_a','value2_b'];values=[num(x[k]) for k in fields]
  for z,y in zip(values,expect):near(z,y)
  k=(family,x['level'],arm,g,x.get('context2',''),metric,a,b);assert k not in seen;seen.add(k)
  answer=rev(*values,metric);assert x['strict_practical_reversal']==('' if answer is None else str(answer))
  for j,f in [(0,'fixed_margin' if exp=='time01' else 'margin1'),(2,'variable_margin' if exp=='time01' else 'margin2')]:
   margin=adv(values[j],values[j+1],metric);assert x[f]==('' if margin is None else str(margin[1]))
  cnt=counts[(family,x['level'],arm,metric)];cnt['total']+=1;cnt['eligible']+=answer is not None;cnt['reversals']+=answer is True;cnt['unestimable']+=answer is None
 for x in rows(analysis/'reversal-counts.csv'):
  k=(x.get('family','timing'),x['level'],x.get('arm','timing'),x['metric'])
  assert all(int(x[f])==counts[k][f] for f in ['total','eligible','reversals','unestimable'])
 savecsv(exp+'-rank-changes.csv',[dict(level=k[0],metric=k[1],**v) for k,v in sorted(rankcounts.items())])
 savecsv(exp+'-reversal-counts.csv',[dict(family=k[0],level=k[1],arm=k[2],metric=k[3],**v) for k,v in sorted(counts.items())])
 checks[exp]={'status':'PASS','cells_or_pairs':n,'raw_terminal_metric_sets_recomputed':2*n,'unique_analysis_rows':len(cr),'paired_rows':len(pairs),'comparison_rows':len(comparisons),'source_files_checked':len(m['files']),'input_conditions':len(inputs),'policy_panels':len(panels),'code_sha':m['code_sha'],'manifest_sha256':sha(root/'manifest.json'),'all_hashes_and_pairing_checks':'PASS','analysis_verdict':'all cells, paired values, source means, rank rows, rational margins and reversal totals match raw saved results'}
 allpanels[exp]={'window':panels,'source_mean':source};summaries[exp]=records
 print(exp,'independent table and record checks PASS',flush=True)
# Source/capacity summaries for manuscript; equal settings then equal windows.
effect_rows=[];distribution=[]
for exp,records in summaries.items():
 metrics=MET+(EXTRA if exp=='abl01' else [])
 groups=collections.defaultdict(list)
 for rec in records.values():
  c=rec['cell'];groups[(c['source'],c['profile'],c['identity']['policy'] if exp=='time01' else 'prompt_order_intervention')].append(rec)
 for (source,profile,policy),rr in sorted(groups.items()):
  for metric in metrics:
   a=[r['old']['metrics'].get(metric,r.get('extra_old',{}).get(metric)) for r in rr];b=[r['new']['metrics'].get(metric,r.get('extra_new',{}).get(metric)) for r in rr];ds=[y-x for x,y in zip(a,b)]
   effect_rows.append(dict(experiment=exp,source=source,profile=profile,policy=policy,metric=metric,n_cells=len(rr),old_mean=mean(a),new_mean=mean(b),mean_difference=mean(ds),ratio_of_means_change_pct=pct(mean(a),mean(b)),new_better=sum(direction(metric)*x>0 for x in ds),new_worse=sum(direction(metric)*x<0 for x in ds),exact_ties=sum(x==0 for x in ds)))
 for metric in metrics:
  for source in sorted({r['cell']['source'] for r in records.values()}):
   rr=[r for r in records.values() if r['cell']['source']==source]
   if exp=='time01':continue
   a=[r['old']['metrics'].get(metric,r['extra_old'].get(metric)) for r in rr];b=[r['new']['metrics'].get(metric,r['extra_new'].get(metric)) for r in rr]
   changes=[pct(x,y) for x,y in zip(a,b) if x!=0]
   ds=[y-x for x,y in zip(a,b)]
   distribution.append(dict(source=source,metric=metric,n= len(rr),control_better=sum(x*direction(metric)>0 for x in ds),control_worse=sum(x*direction(metric)<0 for x in ds),ties=sum(x==0 for x in ds),min_delta=min(ds),median_delta=quantile(ds,.5),p95_delta=quantile(ds,.95),max_delta=max(ds),n_relative=len(changes),relative_min=min(changes),relative_p05=quantile(changes,.05),relative_median=quantile(changes,.5),relative_p95=quantile(changes,.95),relative_max=max(changes)))
savecsv('source-capacity-effects.csv',effect_rows);savecsv('abl01-effect-distributions.csv',distribution)
# Relative SLO-vs-chunked and whole-vs-chunked contrasts under both timing models.
contrasts=[]
for g,vs in allpanels['time01']['source_mean'].items():
 for arm in [0,1]:
  for p in ['slo_gated_c01','whole_fcfs_c01']:
   for metric in MET:
    a=vs[arm]['chunked_fcfs_c01'][metric];b=vs[arm][p][metric]
    contrasts.append(dict(source=g[0],region=g[2],profile=g[3],mode=['fixed','variable'][arm],policy=p,metric=metric,chunked_mean=a,policy_mean=b,relative_change_pct=pct(a,b)))
savecsv('time01-policy-contrasts.csv',contrasts)
# Source selection recomputation exclusively from full C01 inputs.
desc=[]
for c in full['conditions']:
 if c['region']=='LOW':
  q=c['requests'];freq=collections.Counter(x['arrival'] for x in q)
  desc.append(dict(source=c['source'],window=c['window'],mean_prompt=sum(x['prompt'] for x in q)/len(q),mean_output=sum(x['output'] for x in q)/len(q),burst_fraction=sum(n for n in freq.values() if n>1)/len(q)))
chosen=[]
for source in sorted({d['source'] for d in desc}):
 groups=[[d for d in desc if d['source']==source]]
 for feature in ['mean_prompt','mean_output','burst_fraction']:
  groups=[part for group in groups for part in (sorted(group,key=lambda d:(d[feature],d['window']))[:len(group)//2],sorted(group,key=lambda d:(d[feature],d['window']))[len(group)//2:])]
 for g in groups:chosen.append(sorted(d['window'] for d in g)[2])
sel=load(S/'time01/selection.json');assert chosen==sel['selected_windows'];assert desc==sel['descriptors']
checks['selection']={'input_only_stratification':'PASS','selected_windows':chosen,'statistical_design':'Purposive deterministic selection; no random probability sample'}
(OUT/'independent-validation.json').write_text(json.dumps(checks,indent=2)+'\n')
print('PASS all critical table arithmetic, source identity, pairing and selection checks.',flush=True)

