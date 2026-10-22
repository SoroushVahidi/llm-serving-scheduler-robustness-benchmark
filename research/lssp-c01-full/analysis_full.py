"""Prospectively specified descriptive summaries. No inferential statistics."""
import collections, itertools, math
from fractions import Fraction
from common import immutable
METRICS={**{m:1 for m in ('arrival_normalized_weighted_goodput','completion_fraction','token_throughput','emitted_token_throughput','request_throughput')},**{m:-1 for m in ('mean_latency','p95_latency','mean_ttft','p95_ttft','mean_tpot','p95_tpot')}}

def assessment(a,b,d):
    if a is None or b is None:return (None,False,None)
    diff=d*(a-b);sign=(diff>0)-(diff<0)
    loser=min(a,b) if d==1 else max(a,b)
    if loser==0:return (sign,False,None)
    ratio=abs(Fraction(a)-Fraction(b))/abs(Fraction(loser))
    return (sign,ratio>Fraction(1,10),float(ratio))

def rank(values,d):
    if any(v is None for v in values.values()):return dict(ranks=None,top=[],sensitivity_top=[],missing=[p for p,v in values.items() if v is None])
    scores={p:d*v for p,v in values.items()};best=max(scores.values())
    return dict(ranks={p:1+sum(x>v for x in scores.values())+(sum(x==v for x in scores.values())-1)/2 for p,v in scores.items()},top=sorted(p for p,v in scores.items() if v==best),sensitivity_top=sorted(p for p,v in scores.items() if best-v<=1e-12*max(1,abs(best))),missing=[])

def counts(left,right=None):
    # Each item: sign, practical >10%, margin (None = unestimable).
    a=[x for x in left if x[2] is not None]
    if right is None:
        total=len(left)*(len(left)-1)//2;eligible=len(a)*(len(a)-1)//2
        reversals=sum(x[0]>0 and x[1] for x in a)*sum(x[0]<0 and x[1] for x in a)
    else:
        b=[x for x in right if x[2] is not None];total=len(left)*len(right);eligible=len(a)*len(b)
        reversals=sum(x[0]>0 and x[1] for x in a)*sum(x[0]<0 and x[1] for x in b)+sum(x[0]<0 and x[1] for x in a)*sum(x[0]>0 and x[1] for x in b)
    return dict(total=total,eligible=eligible,unestimable=total-eligible,reversals=reversals,frequency=reversals/eligible if eligible else None)

def summarize(rows,manifest):
    policies=manifest['policies'];pairs=list(itertools.combinations(policies,2));meta={w['window_id']:w for w in manifest['windows']}
    groups=collections.defaultdict(dict)
    for r in rows:
        k=(r['source'],r['window'],r['region'],r['profile'])
        if r['policy'] in groups[k]:raise ValueError('duplicate analysis cell')
        groups[k][r['policy']]=r
    assert len(rows)==manifest['expected_cells'] and all(set(g)==set(policies) for g in groups.values())
    rankings=[];differences=[];indexed={};means=collections.defaultdict(list);freq=collections.defaultdict(list)
    for (s,w,l,k),g in sorted(groups.items()):
        for m,d in METRICS.items():
            vals={p:g[p]['metrics'][m] for p in policies};rr=rank(vals,d)
            rankings.append(dict(source=s,window=w,region=l,profile=k,metric=m,values=vals,**rr))
            for scope,value in [('all','ALL'),('stratum',meta[w]['chronology_stratum']),('block',str(meta[w]['block']))]:
                freq[s,l,k,m,scope,value].append(rr)
                for p in policies:means[s,l,k,m,p,scope,value].append(vals[p])
            for a,b in pairs:
                state=assessment(vals[a],vals[b],d);indexed[s,w,l,k,m,a,b]=state
                differences.append(dict(source=s,window=w,region=l,profile=k,metric=m,policy_a=a,policy_b=b,a=vals[a],b=vals[b],difference=None if vals[a] is None or vals[b] is None else vals[a]-vals[b],sign=state[0],practical=state[1],margin=state[2]))
    frequencies=[]
    for k,v in sorted(freq.items()):
        s,l,kv,m,scope,value=k;eligible=[x for x in v if not x['missing']]
        frequencies.append(dict(source=s,region=l,profile=kv,metric=m,scope=scope,group=value,total=len(v),missing=len(v)-len(eligible),ties=sum(len(x['top'])>1 for x in eligible),top_sets=dict(collections.Counter('|'.join(x['top']) for x in eligible)),sensitivity_top_sets=dict(collections.Counter('|'.join(x['sensitivity_top']) for x in eligible))))
    aggregates=[];source_means={}
    for k,v in sorted(means.items()):
        observed=[x for x in v if x is not None];avg=math.fsum(observed)/len(observed) if observed else None
        s,l,kv,m,p,scope,value=k
        aggregates.append(dict(source=s,region=l,profile=kv,metric=m,policy=p,scope=scope,group=value,total=len(v),observed=len(observed),missing=len(v)-len(observed),mean=avg,minimum=min(observed) if observed else None,maximum=max(observed) if observed else None))
        if scope=='all':source_means[s,l,kv,m,p]=avg if len(observed)==len(v) else None
    source_ranks=[]
    for s,l,kv,m in itertools.product(manifest['sources'],manifest['regions'],[p['name'] for p in manifest['profiles']],METRICS):
        values={p:source_means[s,l,kv,m,p] for p in policies};source_ranks.append(dict(source=s,region=l,profile=kv,metric=m,values=values,**rank(values,METRICS[m])))
    windows={s:[w['window_id'] for w in manifest['windows'] if w['source_family']==s] for s in manifest['sources']}
    reverse=[]
    def emit(axis,labels,left,right=None):reverse.append(dict(axis=axis,labels=list(labels),**counts(left,right)))
    sources=manifest['sources'];regions=manifest['regions'];profiles=[p['name'] for p in manifest['profiles']]
    for l,kv,m,(a,b) in itertools.product(regions,profiles,METRICS,pairs):
        for s in sources:emit('window',(s,l,kv,m,a,b),[indexed[s,w,l,kv,m,a,b] for w in windows[s]])
        for s,t in itertools.combinations(sources,2):
            emit('source',(s,t,l,kv,m,a,b),[indexed[s,w,l,kv,m,a,b] for w in windows[s]],[indexed[t,w,l,kv,m,a,b] for w in windows[t]])
            emit('source_mean',(s,t,l,kv,m,a,b),[assessment(source_means[s,l,kv,m,a],source_means[s,l,kv,m,b],METRICS[m])],[assessment(source_means[t,l,kv,m,a],source_means[t,l,kv,m,b],METRICS[m])])
    # Matched-window comparisons are aggregated only after computing each pair.
    def matched(axis,labels,comparisons):
        terms=[counts([x],[y]) for x,y in comparisons]
        totals={k:sum(v[k] for v in terms) for k in ('total','eligible','unestimable','reversals')}
        reverse.append(dict(axis=axis,labels=list(labels),**totals,frequency=totals['reversals']/totals['eligible'] if totals['eligible'] else None))
    for s,kv,m,(a,b),(l,h) in itertools.product(sources,profiles,METRICS,pairs,itertools.combinations(regions,2)):
        matched('load',(s,l,h,kv,m,a,b),[(indexed[s,w,l,kv,m,a,b],indexed[s,w,h,kv,m,a,b]) for w in windows[s]])
    for s,l,m,(a,b) in itertools.product(sources,regions,METRICS,pairs):
        matched('kv',(s,l,m,a,b),[(indexed[s,w,l,profiles[0],m,a,b],indexed[s,w,l,profiles[1],m,a,b]) for w in windows[s]])
    for s,l,kv,(a,b),(m,n) in itertools.product(sources,regions,profiles,pairs,itertools.combinations(METRICS,2)):
        matched('metric',(s,l,kv,m,n,a,b),[(indexed[s,w,l,kv,m,a,b],indexed[s,w,l,kv,n,a,b]) for w in windows[s]])
    return dict(rankings=rankings,pairwise=differences,ranking_frequencies=frequencies,window_aggregates=aggregates,source_mean_rankings=source_ranks,reversals=reverse)

def write_analysis(rows,manifest,out):
    report=summarize(rows,manifest)
    immutable(out/'absolute_metrics.json',rows)
    for name,data in report.items():immutable(out/(name+'.json'),data)
    from verify_analysis import verify
    verification=verify(rows,manifest,report)
    immutable(out/'independent_analysis_validation.json',verification)
    return verification
