"""Post hoc projection of frozen outputs; no engine, experiments, or original writes.
Independent cross-check: Fraction arithmetic on absolute cells vs archived reversal
counts (whose complete direct-enumeration oracle is also run by scripts/validate.py).
"""
import collections, fractions, functools, gzip, hashlib, itertools, json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(__file__).resolve().parent
METRICS=('arrival_normalized_weighted_goodput','token_throughput','mean_latency','p95_latency','mean_ttft','p95_ttft','mean_tpot','p95_tpot')
POLICIES=('whole_fcfs_c01','chunked_fcfs_c01','slo_gated_c01')
def read(name):
 return json.load(gzip.open(ROOT/'evidence/inputs'/('c01-'+name+'.json.gz')))
rows=read('absolute_metrics'); archived=read('reversals'); rankings=read('rankings')
data={(r['source'],r['window'],r['region'],r['profile'],r['policy']):r['metrics'] for r in rows}
windows=collections.defaultdict(set)
for s,w,l,k,p in data:windows[s].add(w)
windows={s:sorted(ws) for s,ws in windows.items()}
profiles=sorted({r['profile'] for r in rows})
F=fractions.Fraction
@functools.lru_cache(None)
def comparison(a,b,m):
 direction=1 if m in METRICS[:2] else -1
 loser=min(a,b) if direction==1 else max(a,b)
 if loser==0:return None
 delta=F(a)-F(b)
 return ((delta>0)-(delta<0))*direction if abs(delta)>F(1,10)*abs(F(loser)) else 0
@functools.lru_cache(None)
def state(s,w,l,k,m,a,b):return comparison(data[s,w,l,k,a][m],data[s,w,l,k,b][m],m)
def states(s,l,k,m,a,b):return [state(s,w,l,k,m,a,b) for w in windows[s]]
def mean_state(s,l,k,m,a,b):
 return comparison(*(math.fsum(data[s,w,l,k,p][m] for w in windows[s])/len(windows[s]) for p in (a,b)),m)
def counts(seq):
 total=eligible=rev=0
 for x,y in seq:
  total+=1
  if x is not None and y is not None:eligible+=1;rev+=int(x*y<0)
 return total,eligible,rev
# Metric position varies across axes; require every endpoint label to be retained.
allmetrics={r['metric'] for r in rankings}
selected=[r for r in archived if set(r['labels'][-2:])<=set(POLICIES) and set(r['labels']).intersection(allmetrics)<=set(METRICS)]
summary=collections.defaultdict(lambda:dict(groups=0,total=0,eligible=0,reversals=0))
for r in selected:
 ax=r['axis'];v=r['labels']
 if ax=='window':
  s,l,k,m,a,b=v;seq=itertools.combinations(states(s,l,k,m,a,b),2)
 elif ax=='source':
  s,t,l,k,m,a,b=v;seq=itertools.product(states(s,l,k,m,a,b),states(t,l,k,m,a,b))
 elif ax=='source_mean':
  s,t,l,k,m,a,b=v;seq=[(mean_state(s,l,k,m,a,b),mean_state(t,l,k,m,a,b))]
 elif ax=='load':
  s,l,h,k,m,a,b=v;seq=zip(states(s,l,k,m,a,b),states(s,h,k,m,a,b))
 elif ax=='kv':
  s,l,m,a,b=v;seq=zip(*(states(s,l,k,m,a,b) for k in profiles))
 elif ax=='metric':
  s,l,k,m,n,a,b=v;seq=zip(states(s,l,k,m,a,b),states(s,l,k,n,a,b))
 else:raise AssertionError(ax)
 result=counts(seq)
 assert result==(r['total'],r['eligible'],r['reversals']),(ax,v,result)
 d=summary[ax];d['groups']+=1
 for key,value in zip(('total','eligible','reversals'),result):d[key]+=value
# Verify exact metric equivalence and ranking redundancy over complete panel.
condition_keys=sorted({key[:4] for key in data})
for key in condition_keys:
 assert data[*key,'chunked_fcfs_c01']==data[*key,'decode_first_c01']
 for p in POLICIES:
  d=data[*key,p];assert d['completion_fraction']==1 and d['token_throughput']==d['emitted_token_throughput']
 for a,b in itertools.combinations(POLICIES,2):
  va,vb=data[*key,a],data[*key,b]
  assert ((va['token_throughput']>vb['token_throughput'])-(va['token_throughput']<vb['token_throughput']))==((va['request_throughput']>vb['request_throughput'])-(va['request_throughput']<vb['request_throughput']))
tpot={}
for m in ('mean_tpot','p95_tpot'):
 changed=whole_worse=practical_worse=0;gap=0
 for key in condition_keys:
  v={p:data[*key,p][m] for p in POLICIES};best=min(v.values())
  exact={p for p in v if v[p]==best};near={p for p in v if abs(v[p]-best)<=1e-12*max(1,abs(best))}
  changed+=exact!=near;whole_worse+=v[POLICIES[0]]-best>1e-12*max(1,abs(best))
  practical_worse+=comparison(v[POLICIES[0]],best,m)==-1
  gap=max(gap,abs(v[POLICIES[1]]-v[POLICIES[2]]))
 tpot[m]=dict(top_set_changes=changed,whole_fcfs_worse_beyond_tolerance=whole_worse,whole_fcfs_worse_strict_10pct=practical_worse,max_chunked_slo_gap_seconds=gap)
result=dict(status='PASS',post_hoc=True,policies=POLICIES,metrics=METRICS,metric_families=5,conditions=len(condition_keys),rankings=len(condition_keys)*len(METRICS),pairwise=len(condition_keys)*len(METRICS)*3,reversal_groups=len(selected),axes=dict(sorted(summary.items())),tpot=tpot,original_counts=dict(cells=5760,rankings=15840,pairwise=95040,reversal_groups=26136),input_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'evidence/inputs').glob('c01-*.json.gz'))},verification='Every selected archived reversal group independently recomputed from absolute cells with Fraction.from_float-equivalent exact dyadic arithmetic; no imports from either original analyzer or oracle. Near-tie tolerance used only for TPOT top-set diagnostics, never to change practical-reversal rule.')
(OUT/'reduced-comparisons.json').write_text(json.dumps(result,indent=2)+'\n')
lines=[r'\begin{tabular}{@{}lrrr@{}}\toprule',r'Axis & Reversals & Eligible & Total \\\midrule']
for axis,title in [('source_mean','Source means'),('window','Within-source windows'),('source','Cross-source windows'),('load','Settings'),('kv','Capacity'),('metric','Metric')]:
 d=summary[axis];lines.append(f"{title} & {d['reversals']:,} & {d['eligible']:,} & {d['total']:,} \\\\")
lines.append(r'\bottomrule\end{tabular}')
(OUT/'reduced-comparisons.tex').write_text('\n'.join(lines)+'\n')
print(json.dumps({k:result[k] for k in ('status','rankings','pairwise','reversal_groups','axes','tpot')},indent=2))
