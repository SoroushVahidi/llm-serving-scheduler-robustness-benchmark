"""Predeclared descriptive pilot summaries. No p-values, CIs or full-corpus claims."""
import csv, itertools, math
from run import atomic, checked_cell

METRICS={'arrival_normalized_weighted_goodput':1,'completion_fraction':1,'mean_latency':-1,
         'mean_ttft':-1,'mean_tpot':-1,'token_throughput':1,'request_throughput':1}

def ranks(values):
    if any(x is None for x in values): return None
    return [1+sum(y>x for y in values)+(sum(y==x for y in values)-1)/2 for x in values]

def spearman(a,b):
    a,b=ranks(a),ranks(b)
    if a is None or b is None:return None
    ma,mb=sum(a)/len(a),sum(b)/len(b)
    den=math.sqrt(sum((x-ma)**2 for x in a)*sum((y-mb)**2 for y in b))
    return sum((x-ma)*(y-mb) for x,y in zip(a,b))/den if den else None

def top(values,tol=0.):
    observed={p:v for p,v in values.items() if v is not None}
    if not observed:return []
    m=max(observed.values());return sorted(p for p,v in observed.items() if abs(v-m)<=tol*max(1.,abs(m)))

def relative(a,b):
    return None if a is None or b is None else (a-b)/max(abs(a),abs(b),1e-12)

def historical_margin(a,b):
    if a is None or b is None or min(abs(a),abs(b)) == 0:
        return None
    return abs(a-b)/min(abs(a),abs(b))  # primary ANWG, larger is better


def analyze(data,manifest,out,identity):
    # Resume/checkpoint content must not determine which cells enter an analysis.
    import hashlib
    records={};absolute=[];rankings=[]
    for c in data['conditions']:
        for profile in manifest['profiles']:
            values={m:{} for m in METRICS}
            for policy in manifest['policies']:
                key=c['condition_id']+'::'+profile['name']+'::'+policy
                directory=out/'cells'/hashlib.sha256(key.encode()).hexdigest()[:24]
                r=checked_cell(directory,c,profile,policy,identity)
                records[c['condition_id'],profile['name'],policy]=r['metrics']
                row=dict(source=c['source'],window=c['window'],region=c['region'],profile=profile['name'],policy=policy,**r['metrics'])
                for name,value in c['historical'][policy].items(): row['historical_'+name]=value
                absolute.append(row)
                for m,direction in METRICS.items():
                    v=r['metrics'][m];values[m][policy]=None if v is None else v*direction
            for m,v in values.items():
                rankings.append(dict(condition_id=c['condition_id'],profile=profile['name'],metric=m,
                                     oriented_scores=v,top_exact=top(v),top_tolerance=top(v,1e-12),
                                     average_ranks=dict(zip(v,ranks(list(v.values())) or [None]*len(v))),
                                     missing_policies=[p for p,x in v.items() if x is None],support_windows=1))
    assert len(absolute)==manifest['expected_cells']
    with (out/'absolute_metrics.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(absolute[0]));writer.writeheader();writer.writerows(absolute)
    atomic(out/'rankings.json',rankings)
    agreement=[]
    for profile in manifest['profiles']:
        for a,b in itertools.combinations(data['conditions'],2):
            if not (a['source']==b['source'] or a['region']==b['region']):continue
            for m,direction in METRICS.items():
                va={p:records[a['condition_id'],profile['name'],p][m] for p in manifest['policies']}
                vb={p:records[b['condition_id'],profile['name'],p][m] for p in manifest['policies']}
                common=[p for p in va if va[p] is not None and vb[p] is not None]
                x=[direction*va[p] for p in common];y=[direction*vb[p] for p in common]
                agreement.append(dict(a=a['condition_id'],b=b['condition_id'],profile=profile['name'],metric=m,
                    matched_policy_count=len(common),spearman=spearman(x,y) if len(common)>1 else None,
                    support='one selected window per source; not temporal replication'))
    atomic(out/'rank_agreement.json',agreement)
    cross_metric=[]
    for c in data['conditions']:
        for profile in manifest['profiles']:
            rr=[r for r in rankings if r['condition_id']==c['condition_id'] and r['profile']==profile['name']]
            for a,b in itertools.combinations(rr,2):
                complete=not a['missing_policies'] and not b['missing_policies']
                cross_metric.append(dict(condition_id=c['condition_id'],profile=profile['name'],a=a['metric'],b=b['metric'],
                    complete_policy_support=complete,
                    top_set_intersects=bool(set(a['top_exact'])&set(b['top_exact'])) if complete else None,
                    tolerance_top_set_intersects=bool(set(a['top_tolerance'])&set(b['top_tolerance'])) if complete else None))
    atomic(out/'cross_metric_top_sets.json',cross_metric)
    by_source_region={(c['source'],c['region']):c for c in data['conditions']}
    adaptation={v:k for k,v in manifest['historical_policy_mapping'].items()}
    comparisons=[]
    for old in data['historical_comparisons']:
        x=by_source_region[tuple(old['condition_x'].split('::'))]
        y=by_source_region[tuple(old['condition_y'].split('::'))]
        pa,pb=adaptation[old['policy_a']],adaptation[old['policy_b']]
        for profile in manifest['profiles']:
            m='arrival_normalized_weighted_goodput'
            vx=[records[x['condition_id'],profile['name'],p][m] for p in (pa,pb)]
            vy=[records[y['condition_id'],profile['name'],p][m] for p in (pa,pb)]
            dx,dy=relative(*vx),relative(*vy)
            comparisons.append(dict(historical_record=old,profile=profile['name'],adaptations=[pa,pb],
                absolute_x=vx,absolute_y=vy,pilot_relative_difference_x=dx,pilot_relative_difference_y=dy,
                pilot_opposite_sign=dx*dy<0,
                pilot_historical_margin_x=historical_margin(*vx),pilot_historical_margin_y=historical_margin(*vy),
                pilot_historical_margin_screen=None if historical_margin(*vx) is None or historical_margin(*vy) is None else dx*dy<0 and min(historical_margin(*vx),historical_margin(*vy))>.10,
                alternative_max_denominator_screen=dx*dy<0 and min(abs(dx),abs(dy))>=.10,
                full_36_persistence_status='NOT_EVALUABLE_PILOT_SUPPORT',matched_windows_per_source=1,
                stable_control_candidate=not old['supported_after_fdr']))
    atomic(out/'historical_comparison_descriptive.json',comparisons)
    sensitivity=[]
    for c in data['conditions']:
        for p in manifest['policies']:
            baseline=records[c['condition_id'],'kv131072',p];alternative=records[c['condition_id'],'kv262144',p]
            sensitivity.append(dict(condition_id=c['condition_id'],policy=p,deltas={m:None if baseline[m] is None or alternative[m] is None else alternative[m]-baseline[m] for m in METRICS}))
    atomic(out/'kv_sensitivity.json',sensitivity)
    atomic(out/'analysis_status.json',dict(status='DESCRIPTIVE_PILOT_ONLY',validated_cells=len(absolute),
        historical_supported_records=36,full_corpus_persistence='NOT_EVALUABLE_PILOT_SUPPORT',
        confidence_intervals=None,p_values=None,temporal_stability='NOT_EVALUABLE_ONE_WINDOW_PER_SOURCE',
        independence_assumed=False,publication_readiness='NOT_ESTABLISHED',job2='REQUIRES_RESULT_REVIEW_AND_AUTHORIZATION'))
