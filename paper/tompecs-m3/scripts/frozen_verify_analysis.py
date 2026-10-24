"""Separate summary oracle: no imports from the production analyzer."""
import collections, itertools, math
DIRECTIONS={m:1 for m in ('arrival_normalized_weighted_goodput','completion_fraction','token_throughput','emitted_token_throughput','request_throughput')}
DIRECTIONS.update({m:-1 for m in ('mean_latency','p95_latency','mean_ttft','p95_ttft','mean_tpot','p95_tpot')})

def oracle(a,b,d):
    if a is None or b is None:return None,False,None
    sign=(a>b)-(a<b);sign*=d
    loser=(a if a<=b else b) if d>0 else (a if a>=b else b)
    if loser==0:return sign,False,None
    an,ad=float(a).as_integer_ratio();bn,bd=float(b).as_integer_ratio();ln,ld=float(loser).as_integer_ratio()
    numerator=abs(an*bd-bn*ad)*ld;denominator=ad*bd*abs(ln)
    return sign,10*numerator>denominator,numerator/denominator

def ranked(v,d):
    if any(x is None for x in v.values()):return None,[],[],[p for p,x in v.items() if x is None]
    order=sorted(v,key=lambda p:d*v[p],reverse=True);ranks={};i=0
    while i<len(order):
        j=i+1
        while j<len(order) and v[order[j]]==v[order[i]]:j+=1
        for p in order[i:j]:ranks[p]=(i+1+j)/2
        i=j
    best=v[order[0]]
    return ranks,sorted(p for p in v if v[p]==best),sorted(p for p in v if abs(v[p]-best)<=1e-12*max(1,abs(best))),[]

def verify(rows,manifest,report):
    data={(r['source'],r['window'],r['region'],r['profile'],r['policy']):r['metrics'] for r in rows}
    assert len(data)==len(rows)==manifest['expected_cells']
    sources=manifest['sources'];regions=manifest['regions'];profiles=[p['name'] for p in manifest['profiles']];policies=manifest['policies']
    windows={s:[w['window_id'] for w in manifest['windows'] if w['source_family']==s] for s in sources};meta={w['window_id']:w for w in manifest['windows']}
    expected={(s,w,l,k,p) for s in sources for w in windows[s] for l in regions for k in profiles for p in policies};assert set(data)==expected
    def value(s,w,l,k,p,m):return data[s,w,l,k,p][m]
    def state(s,w,l,k,m,a,b):return oracle(value(s,w,l,k,a,m),value(s,w,l,k,b,m),DIRECTIONS[m])
    def check_ranking(r,v):
        ranks,top,sensitivity,missing=ranked(v,DIRECTIONS[r['metric']])
        assert (r['values'],r['ranks'],r['top'],r['sensitivity_top'],r['missing'])==(v,ranks,top,sensitivity,missing)
    assert len(report['rankings'])==len(rows)//len(policies)*len(DIRECTIONS)
    seen=set();frequency_groups=collections.defaultdict(list)
    for r in report['rankings']:
        s,w,l,k,m=(r[x] for x in ('source','window','region','profile','metric'));key=s,w,l,k,m;assert key not in seen;seen.add(key)
        check_ranking(r,{p:value(s,w,l,k,p,m) for p in policies})
        for scope,g in [('all','ALL'),('stratum',meta[w]['chronology_stratum']),('block',str(meta[w]['block']))]:frequency_groups[s,l,k,m,scope,g].append(r)
    assert len(report['ranking_frequencies'])==len(frequency_groups)
    seen=set()
    for r in report['ranking_frequencies']:
        key=tuple(r[x] for x in ('source','region','profile','metric','scope','group'));assert key not in seen;seen.add(key);g=frequency_groups[key];v=[x for x in g if x['ranks'] is not None]
        assert r['total']==len(g) and r['missing']==len(g)-len(v) and r['ties']==sum(len(x['top'])>1 for x in v)
        assert r['top_sets']==dict(collections.Counter('|'.join(x['top']) for x in v))
        assert r['sensitivity_top_sets']==dict(collections.Counter('|'.join(x['sensitivity_top']) for x in v))
    seen=set();pairs=list(itertools.combinations(policies,2));assert len(report['pairwise'])==len(rows)//len(policies)*len(DIRECTIONS)*len(pairs)
    for r in report['pairwise']:
        s,w,l,k,m,a,b=(r[x] for x in ('source','window','region','profile','metric','policy_a','policy_b'));key=s,w,l,k,m,a,b;assert key not in seen and (a,b) in pairs;seen.add(key)
        av,bv=value(s,w,l,k,a,m),value(s,w,l,k,b,m);q=state(*key)
        assert (r['a'],r['b'],r['difference'],r['sign'],r['practical'],r['margin'])==(av,bv,None if av is None or bv is None else av-bv,*q)
    agg_expected={(s,l,k,m,p,scope,g) for s,l,k,m,scope,g in frequency_groups for p in policies};assert len(report['window_aggregates'])==len(agg_expected)
    source_means={};seen=set()
    for r in report['window_aggregates']:
        s,l,k,m,p,scope,g=key=tuple(r[x] for x in ('source','region','profile','metric','policy','scope','group'));assert key in agg_expected and key not in seen;seen.add(key)
        ws=[w for w in windows[s] if scope=='all' or (scope=='stratum' and meta[w]['chronology_stratum']==g) or (scope=='block' and str(meta[w]['block'])==g)]
        v=[value(s,w,l,k,p,m) for w in ws];observed=[x for x in v if x is not None];mean=math.fsum(observed)/len(observed) if observed else None
        assert (r['total'],r['observed'],r['missing'],r['mean'],r['minimum'],r['maximum'])==(len(v),len(observed),len(v)-len(observed),mean,min(observed) if observed else None,max(observed) if observed else None)
        if scope=='all':source_means[s,l,k,m,p]=mean if len(observed)==len(v) else None
    assert len(report['source_mean_rankings'])==len(sources)*len(regions)*len(profiles)*len(DIRECTIONS);seen=set()
    for r in report['source_mean_rankings']:
        s,l,k,m=key=tuple(r[x] for x in ('source','region','profile','metric'));assert key not in seen;seen.add(key)
        check_ranking(r,{p:source_means[s,l,k,m,p] for p in policies})
    expected_reverse=set()
    for l,k,m,(a,b) in itertools.product(regions,profiles,DIRECTIONS,pairs):
        expected_reverse.update(('window',(s,l,k,m,a,b)) for s in sources)
        for s,t in itertools.combinations(sources,2):
            expected_reverse.add(('source',(s,t,l,k,m,a,b)));expected_reverse.add(('source_mean',(s,t,l,k,m,a,b)))
    expected_reverse.update(('load',(s,l,h,k,m,a,b)) for s,k,m,(a,b),(l,h) in itertools.product(sources,profiles,DIRECTIONS,pairs,itertools.combinations(regions,2)))
    expected_reverse.update(('kv',(s,l,m,a,b)) for s,l,m,(a,b) in itertools.product(sources,regions,DIRECTIONS,pairs))
    expected_reverse.update(('metric',(s,l,k,m,n,a,b)) for s,l,k,(a,b),(m,n) in itertools.product(sources,regions,profiles,pairs,itertools.combinations(DIRECTIONS,2)))
    assert len(report['reversals'])==len(expected_reverse);seen=set()
    # Independent direct enumeration, not the analyzer's sign-count products.
    cache={}
    def st(s,w,l,k,m,a,b):
        key=s,w,l,k,m,a,b
        if key not in cache:cache[key]=state(*key)
        return cache[key]
    for r in report['reversals']:
        axis=r['axis'];labels=tuple(r['labels']);key=axis,labels;assert key in expected_reverse and key not in seen;seen.add(key)
        if axis=='window':
            s,l,k,m,a,b=labels;comparisons=((st(s,u,l,k,m,a,b),st(s,v,l,k,m,a,b)) for u,v in itertools.combinations(windows[s],2))
        elif axis=='source':
            s,t,l,k,m,a,b=labels;comparisons=((st(s,u,l,k,m,a,b),st(t,v,l,k,m,a,b)) for u,v in itertools.product(windows[s],windows[t]))
        elif axis=='source_mean':
            s,t,l,k,m,a,b=labels;comparisons=[(oracle(source_means[s,l,k,m,a],source_means[s,l,k,m,b],DIRECTIONS[m]),oracle(source_means[t,l,k,m,a],source_means[t,l,k,m,b],DIRECTIONS[m]))]
        elif axis=='load':
            s,l,h,k,m,a,b=labels;comparisons=((st(s,w,l,k,m,a,b),st(s,w,h,k,m,a,b)) for w in windows[s])
        elif axis=='kv':
            s,l,m,a,b=labels;comparisons=((st(s,w,l,profiles[0],m,a,b),st(s,w,l,profiles[1],m,a,b)) for w in windows[s])
        else:
            s,l,k,m,n,a,b=labels;comparisons=((st(s,w,l,k,m,a,b),st(s,w,l,k,n,a,b)) for w in windows[s])
        total=eligible=reversed_count=0
        for x,y in comparisons:
            total+=1
            if x[2] is not None and y[2] is not None:
                eligible+=1;reversed_count+=int(x[0]*y[0]<0 and x[1] and y[1])
        assert (r['total'],r['eligible'],r['unestimable'],r['reversals'],r['frequency'])==(total,eligible,total-eligible,reversed_count,reversed_count/eligible if eligible else None)
    return dict(status='PASS',absolute_cells=len(rows),rankings=len(report['rankings']),pairwise_rows=len(report['pairwise']),reversal_groups=len(report['reversals']),independent_method='integer-ratio boundary arithmetic; rank sorting; direct enumeration of every comparison; independently grouped absolute-cell metrics',inference='NONE',scientific_review_required=True)
