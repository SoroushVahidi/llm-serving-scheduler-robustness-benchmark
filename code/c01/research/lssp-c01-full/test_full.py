"""Deterministic engineering fixtures only, never new scientific cells."""
import copy, dataclasses, itertools, math, platform
from pathlib import Path
import pytest
from common import read,sha,digest,atomic,cell_id,plan,check_inputs,Config,PILOT
from analysis_full import assessment,counts,rank,summarize,METRICS
from verify_analysis import oracle,ranked,verify
import campaign

@pytest.mark.parametrize('direction',[-1,1])
def test_exact_ten_percent_boundary_neighbors_and_zero(direction):
    # 11 and 10 yield exact 1/10 for higher-is-better; 9 and 10 for lower.
    a=11. if direction==1 else 9.; b=10.
    assert assessment(a,b,direction)[1] is False
    assert assessment(math.nextafter(a,math.inf if direction==1 else -math.inf),b,direction)[1] is True
    assert assessment(math.nextafter(a,-math.inf if direction==1 else math.inf),b,direction)[1] is False
    for x,y in itertools.product([None,0.,1.,9.,10.,11.,math.nextafter(a,math.inf)],repeat=2):
        assert assessment(x,y,direction)==oracle(x,y,direction)

def test_sign_counts_against_explicit_comparisons():
    xs=[assessment(a,b,1) for a,b in [(0.,0.),(1.,1.),(12.,10.),(10.,12.),(None,1.),(11.,10.)]]
    for ys in (None,xs[:3]):
        comparisons=list(itertools.combinations(xs,2) if ys is None else itertools.product(xs,ys))
        valid=[(x,y) for x,y in comparisons if x[2] is not None and y[2] is not None]
        got=counts(xs,ys)
        assert got['total']==len(comparisons) and got['eligible']==len(valid)
        assert got['reversals']==sum(x[0]*y[0]<0 and x[1] and y[1] for x,y in valid)

@pytest.mark.parametrize('v',[{'a':1.,'b':1.,'c':2.,'d':0.},{'a':None,'b':2.},{'a':0.,'b':0.},{'a':1.,'b':math.nextafter(1.,0.)}])
def test_rank_ties_missingness_and_neighbors(v):
    for d in (-1,1):
        r=rank(v,d);assert (r['ranks'],r['top'],r['sensitivity_top'],r['missing'])==ranked(v,d)

@pytest.fixture
def fixture(tmp_path):
    req=[dict(id=0,arrival=0.,prompt=3,output=2,deadline=10.,priority=1.)]
    c=dict(condition_id='s::w::LOW',source='s',window='w',region='LOW',synthesis_seed=123,load_factor=2.,requests=req,requests_sha256=digest(req))
    data={'conditions':[c]};manifest=dict(conditions=[{k:v for k,v in c.items() if k!='requests'}],sources=['s'],regions=['LOW'],windows=[dict(source_family='s',window_id='w',chronology_stratum='EARLY',block=1)],profiles=[dict(name='kv131072',config=dataclasses.asdict(Config())),dict(name='kv262144',config=dataclasses.asdict(Config(kv_capacity=262144)))],policies=['whole_fcfs_c01','chunked_fcfs_c01','decode_first_c01','slo_gated_c01'],expected_cells=8)
    atomic(tmp_path/'inputs.json',data);manifest['input_sha256']=sha(tmp_path/'inputs.json');atomic(tmp_path/'manifest.json',manifest);atomic(tmp_path/'reuse.json',{'cells':[]})
    spec=dict(files={},python_version=platform.python_version(),inputs='inputs.json',manifest='manifest.json',reuse_index='reuse.json')
    return tmp_path,data,manifest,spec

def test_manifest_identity_rejects_duplicate_and_input_changes(fixture):
    root,data,m,s=fixture;assert len(check_inputs(data,m))==8
    bad=copy.deepcopy(data);bad['conditions'][0]['requests'][0]['output']=3
    with pytest.raises(ValueError):check_inputs(bad,m)
    bad=copy.deepcopy(data);bad['conditions']*=2
    with pytest.raises(ValueError):plan(bad,m)

def test_immutable_restart_stop_and_foreign_cells(fixture,monkeypatch):
    root,data,m,s=fixture;out=root/'run'
    assert campaign.campaign(root,out,s,schedule_seconds=0)==0
    assert read(out/'checkpoint.json')['status']=='PARTIAL_SAFE_STOP' and not (out/'complete.json').exists()
    assert campaign.campaign(root,out,s)==0
    before={str(p):sha(p) for p in (out/'cells').rglob('*') if p.is_file()}
    monkeypatch.setattr(campaign,'simulate',lambda *a:(_ for _ in ()).throw(AssertionError('duplicate simulation')))
    assert campaign.campaign(root,out,s)==0
    assert before=={str(p):sha(p) for p in (out/'cells').rglob('*') if p.is_file()}
    (out/'cells'/'foreign').mkdir()
    with pytest.raises(ValueError,match='coverage'):campaign.verify_all(root,out,data,m,s)

def test_byte_identical_pilot_reuse_and_hash_rejection(fixture,monkeypatch):
    root,data,m,s=fixture;original=root/'old';campaign.campaign(root,original,s)
    entries=[]
    for k,c,p,a in plan(data,m):
        folder=original/'cells'/cell_id(k);r=read(folder/'result.json')
        entries.append(dict(key=k,staged_path=str(folder.relative_to(root)),identity=digest(s),result_sha256=sha(folder/'result.json'),journal_sha256=r['journal_sha256']))
    atomic(root/'reuse.json',{'cells':entries});new={**s,'new_campaign':True}
    monkeypatch.setattr(campaign,'simulate',lambda *a:(_ for _ in ()).throw(AssertionError('recomputed reused cell')))
    campaign.campaign(root,root/'new',new)
    assert read(root/'new/complete.json')['reused']==8
    entries[0]['result_sha256']='0'*64;atomic(root/'reuse.json',{'cells':entries})
    with pytest.raises(ValueError,match='hash'):campaign.campaign(root,root/'bad',new)

def synthetic_rows():
    m=dict(sources=['a','b','c'],regions=['LOW','HIGH'],profiles=[{'name':'small'},{'name':'large'}],policies=['P','Q','R','S'],windows=[dict(source_family=s,window_id=s+str(i),chronology_stratum=['EARLY','MIDDLE','LATE'][i],block=i+1) for s in 'abc' for i in range(3)],expected_cells=144)
    rows=[]
    for s in m['sources']:
        for i in range(3):
            for j,l in enumerate(m['regions']):
                for z,k in enumerate(['small','large']):
                    for p,policy in enumerate(m['policies']):
                        metrics={metric:(None if (i+j+z+p+idx)%17==0 else float((ord(s)+i*j+z+p*(i+1)+idx)%13)) for idx,metric in enumerate(METRICS)}
                        rows.append(dict(source=s,window=s+str(i),region=l,profile=k,policy=policy,metrics=metrics))
    return rows,m

def test_all_analysis_domains_and_independent_corruption_detection():
    rows,m=synthetic_rows();r=summarize(rows,m);assert verify(rows,m,r)['status']=='PASS'
    for table,field in [('reversals','reversals'),('window_aggregates','mean'),('pairwise','difference'),('ranking_frequencies','missing')]:
        bad=copy.deepcopy(r);bad[table][0][field]=999
        with pytest.raises(AssertionError):verify(rows,m,bad)
    bad=copy.deepcopy(r);bad['rankings'].pop()
    with pytest.raises(AssertionError):verify(rows,m,bad)

def test_frozen_implementation_hashes():
    evidence=read(Path(__file__).parent/'evidence/pilot_audit.json')
    for name in ('engine.py','policies.py','validator.py','prepare.py'):
        assert sha(PILOT/name)==evidence['code_hashes'][name]

def test_launch_tampering_and_interrupted_attempt_preservation(fixture):
    root,data,m,s=fixture
    atomic(root/'pinned.json',{'contract':'original'});pinned={**s,'files':{'pinned.json':sha(root/'pinned.json')}}
    atomic(root/'pinned.json',{'contract':'changed'})
    with pytest.raises(ValueError,match='fingerprint'):campaign.campaign(root,root/'bad-launch',pinned)
    out=root/'resumed';orphan=out/'attempts'/'interrupted';orphan.mkdir(parents=True);(orphan/'evidence').write_bytes(b'preserve')
    campaign.campaign(root,out,s)
    assert (orphan/'evidence').read_bytes()==b'preserve'
