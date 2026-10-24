"""Small hand-derived conformance fixtures plus new invariant checks on saved data.
No enumeration, random search, arbitrary state injection, or campaign reruns.
"""
import argparse,dataclasses,gzip,hashlib,json,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'frozen_c01'))
from engine import simulate
from policies import Config
from validator import validate
from check_invariant import check
POLICIES=('chunked_fcfs_c01','decode_first_c01')
HASHES={'engine.py':'2907a198a3ede133000429c57aec3269faf47ac96e019b19302dcae3ccbc6836',
'policies.py':'d54e96880afb9001dc0fbc19511bb6338367eb828948a48cd68a516e871fdbb1',
'validator.py':'9d0fe6862cfa5952ca89ed421cd1b8b923e03ad09dd7fe50dcb29595d66bb08b'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(o):return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,obj):
    with p.open('x') as f:json.dump(obj,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def normalized(events):
    return [dict(e,intent=sorted(e['intent']),executed=sorted(e['executed'])) for e in events]
def requests(prompts,outputs,arrivals=None):
    return [dict(id=i,arrival=0. if arrivals is None else arrivals[i],prompt=p,output=o,deadline=100.,priority=1.) for i,(p,o) in enumerate(zip(prompts,outputs))]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('out',type=pathlib.Path);ap.add_argument('--budget-root',type=pathlib.Path,required=True);ap.add_argument('--c01-root',type=pathlib.Path,required=True);a=ap.parse_args()
    a.out.mkdir(exist_ok=False)
    for n,h in HASHES.items():assert sha(HERE/'frozen_c01'/n)==sha(a.c01_root/'research/lssp-c01'/n)==h
    # Seven analytical edge cases, not a parameter sweep or witness search.
    cases=[
        ('ordering_only_original',32768,4,requests([513,1],[1,1]),50.),
        ('binding_mixed_1024',1024,4,requests([1024,1,1024],[3,3,3]),50.),
        ('binding_mixed_2048',2048,8,requests([2048,2048,2048,1,2048],[2]*5),50.),
        ('completion_holes_waiting',1024,4,requests([1024,1,1024,1,1024,1],[2,1,4,1,2,1]),50.),
        ('staggered_idle',1024,4,requests([1024,1,1024,1],[2,2,2,1],[0.,.0005,.0015,1.]),50.),
        ('unit_budget',1,8,requests([1,1,1],[1,2,1]),50.),
        ('horizon_censoring',1024,4,requests([1024,1,1024],[20,20,20]),.0025),
    ]
    reports=[]
    for name,b,k,rs,drain in cases:
        cfg=Config(budget=b,kv_capacity=32768*k,drain=drain);runs={}
        for policy in POLICIES:
            events=[];terminal=simulate(rs,policy,cfg,events.append)
            metrics=validate(rs,dataclasses.asdict(cfg),events,terminal)
            invariant=check(rs,dataclasses.asdict(cfg),events)
            runs[policy]=dict(events=events,terminal=terminal,metrics=metrics,invariant=invariant)
        x,y=[runs[p] for p in POLICIES]
        assert normalized(x['events'])==normalized(y['events'])
        assert x['terminal']==y['terminal'] and x['metrics']==y['metrics']
        if name=='ordering_only_original':
            assert x['events'][1]['executed']==[[0,'prefill',512,513],[1,'decode',0,1]]
            assert y['events'][1]['executed']==[[1,'decode',0,1],[0,'prefill',512,513]]
            assert x['terminal']['requests'][0]['completion']==.003
            assert x['terminal']['requests'][1]['completion']==.002
        if name=='binding_mixed_1024':
            assert x['events'][0]['executed']==[[0,'prefill',0,512],[1,'prefill',0,1],[2,'prefill',0,511]]
            assert x['events'][1]['executed']==[[0,'prefill',512,1024],[1,'decode',0,1],[2,'prefill',511,1022]]
            assert x['events'][1]['end']==.002
            assert x['invariant']['binding_resident_offer']>0 and x['invariant']['mixed_older_prefill_later_decode']>0
        if name=='binding_mixed_2048':assert x['invariant']['binding_resident_offer']>0
        if name=='horizon_censoring':assert x['terminal']['unfinished']
        save(a.out/(name+'.json'),dict(name=name,requests=rs,config=dataclasses.asdict(cfg),runs=runs))
        reports.append(dict(name=name,policies=2,raw_order_difference=x['events']!=y['events'],normalized_equal=True,terminal_equal=True,metrics_equal=True,invariant=x['invariant']))
    # Re-read existing results to measure the newly proved invariant; never resimulate.
    manifest=read(a.budget_root/'manifest.json')
    inputs=a.c01_root/'inputs/full-inputs.json'
    assert sha(inputs)==manifest['identity']['frozen_files']['inputs/full-inputs.json']
    cs={c['condition_id']:c for c in read(inputs)['conditions']}
    saved=[];pairs={}
    for result in sorted((a.budget_root/'cells').glob('*/result.json')):
        r=read(result)
        if r['policy'] not in POLICIES:continue
        c=cs[r['condition_id']];assert canon(c['requests'])==c['requests_sha256']==r['requests_sha256']
        journal=result.parent/'events.jsonl.gz';assert sha(journal)==r['journal_sha256']
        with gzip.open(journal,'rt') as f:events=[json.loads(line) for line in f]
        # Existing referee is reused; newly measured assertions are check().
        assert validate(c['requests'],r['config'],events,r['terminal'])==r['metrics']
        invariant=check(c['requests'],r['config'],events)
        key=(r['condition_id'],r['budget']);pairs.setdefault(key,{})[r['policy']]=canon(normalized(events))
        saved.append(dict(path=str(result),result_sha256=sha(result),journal_sha256=sha(journal),policy=r['policy'],condition_id=r['condition_id'],budget=r['budget'],invariant=invariant))
    assert len(saved)==36 and len(pairs)==18
    assert all(len(x)==2 and len(set(x.values()))==1 for x in pairs.values())
    report=dict(status='PASS',method='PROOF_PLUS_IMPLEMENTATION_CONFORMANCE_NOT_SEARCH',source_hashes=HASHES,
        engineering_fixtures=reports,new_fixture_executions=14,new_scientific_campaign_cells=0,
        saved_budget_journals_checked=36,saved_budget_pairs=18,saved_records=saved,
        saved_boundaries=sum(r['invariant']['boundaries'] for r in saved),
        saved_binding_resident_boundaries=sum(r['invariant']['binding_resident_offer'] for r in saved),
        proof_file_sha256=sha(HERE/'PROOF.txt'),search_performed=False,slurm_submitted=False)
    save(a.out/'validation.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('saved_records','engineering_fixtures','source_hashes')},sort_keys=True))
if __name__=='__main__':main()
