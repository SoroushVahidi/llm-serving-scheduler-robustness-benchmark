"""Descriptive, paired intervention analysis. No simulation or inference."""
import csv,itertools,collections
from fractions import Fraction
from support import *
METRICS={'mean_latency':-1,'p95_latency':-1,'mean_ttft':-1,'p95_ttft':-1,'mean_tpot':-1,'p95_tpot':-1,'token_throughput':1,'request_throughput':1,'emitted_token_throughput':1,'completion_fraction':1,'arrival_normalized_weighted_goodput':1}
EXTRA={'arrival_deadline_attainment':1,'completed_deadline_attainment':1}
POLICIES=('whole_fcfs_c01','chunked_fcfs_c01','decode_first_c01','slo_gated_c01')
def advantage(a,b,d):
 if a is None or b is None:return None
 x,y=Fraction(a),Fraction(b);sgn=((x>y)-(x<y))*d;loser=b if sgn>=0 else a
 return None if loser==0 else (sgn,abs(x-y)/abs(Fraction(loser)))
def reversal(a,b,c,d,direction):
 x,y=advantage(a,b,direction),advantage(c,d,direction)
 return None if x is None or y is None else x[0]*y[0]<0 and x[1]>Fraction(1,10) and y[1]>Fraction(1,10)
def ranks(v,d):
 if any(x is None for x in v.values()):return None
 return {p:1+sum(d*y>d*x for y in v.values())+(sum(y==x for y in v.values())-1)/2 for p,x in v.items()}
def mean(xs):return None if not xs or any(x is None for x in xs) else sum(xs)/len(xs)
def csv_new(out,name,rows):
 assert rows,name
 with (out/(name+'.csv')).open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def analyze(root,m,derived):
 out=root/'analysis';out.mkdir(exist_ok=False);index=read(root/'baseline-index.json')
 ix={(r['condition_id'],r['profile'],r['policy']):r for r in index};cellrows=[];paired=[];telemetry=[];panels={}
 for cell in m['cells']:
  r=derived[cell['cell_id']];meta={k:cell[k] for k in ('cell_id','source','window','region','profile')};i=cell['identity'];ck=(i['condition_id'],cell['profile'])
  panel={p:ix[ck+(p,)]['metrics'] for p in POLICIES};panels[(cell['source'],cell['window'],cell['region'],cell['profile'])]={'original':panel,'ablated':dict(panel,slo_gated_c01=r['metrics'])}
  for arm,metrics,t in [('original_slo',cell['baseline']['metrics'],r['baseline_telemetry']),('fcfs_waiting_control',r['metrics'],r['telemetry'])]:
   merged=dict(metrics,**{k:t[k] for k in EXTRA});cellrows.append(dict(**meta,arm=arm,**merged));telemetry.append(dict(**meta,arm=arm,**t))
  for metric,direction in dict(METRICS,**EXTRA).items():
   old=cell['baseline']['metrics'].get(metric) if metric in METRICS else r['baseline_telemetry'][metric]
   new=r['metrics'].get(metric) if metric in METRICS else r['telemetry'][metric]
   delta=None if old is None or new is None else new-old
   paired.append(dict(**meta,metric=metric,endpoint_family='primary' if metric in METRICS else 'additional_descriptive',original=old,control=new,difference=delta,relative_change=None if delta is None or old==0 else delta/abs(old),improvement_direction=direction))
 grouped=collections.defaultdict(list)
 for row in paired:grouped[(row['source'],row['region'],row['profile'],row['metric'])].append(row)
 means=[];aggregate=[]
 def summary(rows):
  ds=[r['difference'] for r in rows];valid=[x for x in ds if x is not None];direction=rows[0]['improvement_direction']
  return dict(n_cells=len(rows),n_observed=len(valid),mean_original=mean([r['original'] for r in rows]),mean_control=mean([r['control'] for r in rows]),mean_paired_difference=mean(ds),minimum_difference=min(valid) if valid else None,maximum_difference=max(valid) if valid else None,favorable=sum(x*direction>0 for x in valid),adverse=sum(x*direction<0 for x in valid),ties=sum(x==0 for x in valid))
 for (source,region,profile,metric),rs in sorted(grouped.items()):
  assert len(rs)==40
  means.append(dict(source=source,region=region,profile=profile,metric=metric,**summary(rs)))
 for metric in dict(METRICS,**EXTRA):
  rs=[r for r in paired if r['metric']==metric];assert len(rs)==1440;aggregate.append(dict(metric=metric,**summary(rs)))
 sourcepanels={}
 for source,region,profile in sorted({(s,r,p) for s,w,r,p in panels}):
  xs=[v for (s,w,r,p),v in panels.items() if (s,r,p)==(source,region,profile)];assert len(xs)==40
  sourcepanels[(source,'SOURCE_MEAN',region,profile)]={arm:{policy:{metric:mean([x[arm][policy][metric] for x in xs]) for metric in METRICS} for policy in POLICIES} for arm in ('original','ablated')}
 rankings=[];comparisons=[]
 def compare(family,level,g,metric,a,b,x,y,u,v,arm='intervention',context2=''):
  d=METRICS[metric];aa,bb=advantage(x,y,d),advantage(u,v,d)
  comparisons.append(dict(family=family,level=level,source=g[0],window=g[1],region=g[2],profile=g[3],context2=context2,arm=arm,metric=metric,policy_a=a,policy_b=b,value1_a=x,value1_b=y,value2_a=u,value2_b=v,margin1=None if aa is None else str(aa[1]),margin2=None if bb is None else str(bb[1]),strict_practical_reversal=reversal(x,y,u,v,d)))
 for level,panel in [('window',panels),('source_mean',sourcepanels)]:
  for g,v in sorted(panel.items()):
   for metric,d in METRICS.items():
    vals={arm:{p:v[arm][p][metric] for p in POLICIES} for arm in ('original','ablated')};rr={arm:ranks(vv,d) for arm,vv in vals.items()}
    tops={arm:None if rank is None else '|'.join(p for p in POLICIES if rank[p]==min(rank.values())) for arm,rank in rr.items()}
    for p in POLICIES:rankings.append(dict(level=level,source=g[0],window=g[1],region=g[2],profile=g[3],metric=metric,policy=p,original_rank=None if rr['original'] is None else rr['original'][p],ablated_rank=None if rr['ablated'] is None else rr['ablated'][p],original_top=tops['original'],ablated_top=tops['ablated'],top_changed=None if None in tops.values() else tops['original']!=tops['ablated']))
    for a,b in itertools.combinations(POLICIES,2):compare('intervention',level,g,metric,a,b,vals['original'][a],vals['original'][b],vals['ablated'][a],vals['ablated'][b])
 groups=sorted(sourcepanels)
 for g,h in itertools.combinations(groups,2):
  if g[3]!=h[3]:continue
  family='cross_source' if g[2]==h[2] and g[0]!=h[0] else 'cross_condition' if g[0]==h[0] and g[2]!=h[2] else None
  if family is None:continue
  for arm in ('original','ablated'):
   for metric in METRICS:
    for a,b in itertools.combinations(POLICIES,2):compare(family,'source_mean',g,metric,a,b,sourcepanels[g][arm][a][metric],sourcepanels[g][arm][b][metric],sourcepanels[h][arm][a][metric],sourcepanels[h][arm][b][metric],arm, h[0] if family=='cross_source' else h[2])
 counts=[];cg=collections.defaultdict(list)
 for r in comparisons:cg[(r['family'],r['level'],r['arm'],r['metric'])].append(r['strict_practical_reversal'])
 for (family,level,arm,metric),rs in sorted(cg.items()):counts.append(dict(family=family,level=level,arm=arm,metric=metric,reversals=sum(x is True for x in rs),eligible=sum(x is not None for x in rs),total=len(rs),unestimable=sum(x is None for x in rs)))
 for name,rs in [('cells',cellrows),('paired-differences',paired),('source-condition-means',means),('aggregate-paired',aggregate),('rankings',rankings),('policy-comparisons',comparisons),('reversal-counts',counts),('telemetry',telemetry)]:csv_new(out,name,rs)
 save_new(out/'verification.json',dict(status='PASS',code_sha=m['code_sha'],manifest_sha256=sha(root/'manifest.json'),pairs=1440,new_simulations=0,paired_rows=len(paired),ranking_rows=len(rankings),comparison_rows=len(comparisons),output_hashes={p.name:sha(p) for p in out.glob('*.csv')},inference='DESCRIPTIVE_FINITE_SELECTED_CORPUS',scientific_review_required=True))
