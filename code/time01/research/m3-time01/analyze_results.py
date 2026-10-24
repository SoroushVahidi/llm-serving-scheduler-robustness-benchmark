"""Post-completion read-only verification and preregistered descriptive analysis."""
import argparse, collections, csv, itertools, json, pathlib
from fractions import Fraction
from support import save_new,sha
from campaign import preflight,checked,read
from policies import POLICIES

METRICS={'mean_latency':-1,'p95_latency':-1,'token_throughput':1,'request_throughput':1,
         'emitted_token_throughput':1,'completion_fraction':1,'arrival_normalized_weighted_goodput':1,
         'mean_ttft':-1,'p95_ttft':-1,'mean_tpot':-1,'p95_tpot':-1}

def advantage(a,b,direction):
    if a is None or b is None:return None
    x,y=Fraction(a),Fraction(b)
    sign=(x>y)-(x<y); sign*=direction
    loser=b if sign>=0 else a
    if loser==0:return None
    return sign,abs(x-y)/abs(Fraction(loser))

def reversal(a,b,c,d,direction):
    x,y=advantage(a,b,direction),advantage(c,d,direction)
    return None if x is None or y is None else (x[0]*y[0]<0 and x[1]>Fraction(1,10) and y[1]>Fraction(1,10))

def ranking(values,direction):
    if any(v is None for v in values.values()):return None
    return {p:1+sum(direction*v>direction*x for v in values.values())+(sum(v==x for v in values.values())-1)/2 for p,x in values.items()}

def csv_new(path,rows):
    if not rows:return
    with path.open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

def analyze(root,out):
    m,conditions=preflight(root);complete=read(root/'complete.json')
    assert complete['cells']==384 and complete['manifest_sha256']==sha(root/'manifest.json') and complete['code_sha']==m['code_sha']
    actual={p.name for p in (root/'cells').iterdir()}
    assert actual==set(m['missing_cells'])
    records={};cell_rows=[];paired=[];telemetry_rows=[]
    for cell in m['cells']:
        cid=cell['cell_id'];assert sha(root/'cells'/cid/'result.json')==complete['result_hashes'][cid]
        new=checked(root,m,cell,conditions);old=read(root/cell['baseline']['local_file'])
        key=(cell['source'],cell['window'],cell['region'],cell['profile'],cell['identity']['policy'])
        records[key]={'fixed':old['metrics'],'composition-v1':new['metrics']}
        meta=dict(cell_id=cid,source=key[0],window=key[1],region=key[2],profile=key[3],policy=key[4])
        for mode,r in [('fixed',old),('composition-v1',new)]:
            cell_rows.append(dict(**meta,mode=mode,**r['metrics']))
        for metric in METRICS:
            a,b=old['metrics'][metric],new['metrics'][metric]
            paired.append(dict(**meta,metric=metric,fixed=a,variable=b,difference=None if a is None or b is None else b-a,
                relative_change=None if a in (None,0) or b is None else (b-a)/abs(a)))
        t=new['telemetry'];flat={f'{group}_{k}':v for group in ('duration','composition','urgency','admission') for k,v in t[group].items()}
        telemetry_rows.append(dict(**meta,**flat))
    source_rows=[];source_values={}
    for source,region,profile,policy in sorted({(k[0],k[2],k[3],k[4]) for k in records}):
        rows=[v for k,v in records.items() if (k[0],k[2],k[3],k[4])==(source,region,profile,policy)]
        assert len(rows)==8
        key=(source,'SOURCE_MEAN',region,profile,policy);source_values[key]={}
        for mode in ('fixed','composition-v1'):
            source_values[key][mode]={}
            for metric in METRICS:
                vals=[r[mode][metric] for r in rows if r[mode][metric] is not None]
                mean=sum(vals)/len(vals) if len(vals)==8 else None
                source_values[key][mode][metric]=mean
                source_rows.append(dict(source=source,region=region,profile=profile,policy=policy,mode=mode,metric=metric,
                    n_windows=8,n_observed=len(vals),mean=mean,min=min(vals) if vals else None,max=max(vals) if vals else None))
    comparisons=[];ranks=[]
    for level,panel in [('window',records),('source_mean',source_values)]:
        for group in sorted({k[:4] for k in panel}):
            for metric,direction in METRICS.items():
                vals={mode:{p:panel[group+(p,)][mode][metric] for p in POLICIES} for mode in ('fixed','composition-v1')}
                rs={mode:ranking(v,direction) for mode,v in vals.items()}
                tops={mode:None if rr is None else '|'.join(p for p in POLICIES if rr[p]==min(rr.values())) for mode,rr in rs.items()}
                for p in POLICIES:
                    ranks.append(dict(level=level,source=group[0],window=group[1],region=group[2],profile=group[3],metric=metric,policy=p,
                        fixed_rank=None if rs['fixed'] is None else rs['fixed'][p],variable_rank=None if rs['composition-v1'] is None else rs['composition-v1'][p],
                        fixed_top_set=tops['fixed'],variable_top_set=tops['composition-v1'],
                        top_set_changed=None if None in tops.values() else tops['fixed']!=tops['composition-v1']))
                for a,b in itertools.combinations(POLICIES,2):
                    x,y=vals['fixed'][a],vals['fixed'][b];u,v=vals['composition-v1'][a],vals['composition-v1'][b]
                    old,new=advantage(x,y,direction),advantage(u,v,direction)
                    comparisons.append(dict(level=level,source=group[0],window=group[1],region=group[2],profile=group[3],metric=metric,policy_a=a,policy_b=b,
                        fixed_a=x,fixed_b=y,variable_a=u,variable_b=v,
                        fixed_a_minus_b=None if x is None or y is None else x-y,variable_a_minus_b=None if u is None or v is None else u-v,
                        fixed_margin=None if old is None else str(old[1]),variable_margin=None if new is None else str(new[1]),
                        strict_practical_reversal=reversal(x,y,u,v,direction)))
    reversal_counts=[]
    for level in ('window','source_mean'):
        for metric in METRICS:
            xs=[r['strict_practical_reversal'] for r in comparisons if r['level']==level and r['metric']==metric]
            reversal_counts.append(dict(level=level,metric=metric,reversals=sum(x is True for x in xs),eligible=sum(x is not None for x in xs),total=len(xs),unestimable=sum(x is None for x in xs)))
    aggregate=[]
    for metric in METRICS:
        for policy in POLICIES:
            rows=[r for r in paired if r['metric']==metric and r['policy']==policy]
            assert len(rows)==96
            vals=[r['difference'] for r in rows if r['difference'] is not None]
            aggregate.append(dict(metric=metric,policy=policy,n_cells=len(rows),n_observed=len(vals),mean_paired_difference=sum(vals)/len(vals) if len(vals)==len(rows) else None))
    # All verification happens before any report files are created.
    out.mkdir(exist_ok=False)
    for name,rows in [('cells',cell_rows),('paired-differences',paired),('source-means',source_rows),('rankings',ranks),('policy-comparisons',comparisons),('reversal-counts',reversal_counts),('telemetry',telemetry_rows),('aggregate-paired',aggregate)]:
        csv_new(out/(name+'.csv'),rows)
    save_new(out/'verification.json',dict(status='PASS',cells=384,manifest_sha256=sha(root/'manifest.json'),code_sha=m['code_sha'],
        independent_event_timing_and_metric_reconstruction=True,original_policy_replay=True,
        inference='DESCRIPTIVE_FINITE_SELECTED_CORPUS',scientific_review_required=True,
        unfinished_cells=sum(v['composition-v1']['num_unfinished']>0 for v in records.values())))
    print('PASS:384 records independently validated; descriptive reports written; scientific review remains required')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('root',type=pathlib.Path);ap.add_argument('output',type=pathlib.Path);args=ap.parse_args();analyze(args.root,args.output)
