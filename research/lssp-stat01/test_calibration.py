"""Engineering validation only; scenario/replicate streams999+ reserved for fixtures."""
import copy,dataclasses,hashlib,importlib.util,json,math,sys,os
from pathlib import Path
import numpy as np
import pytest
from scipy import stats
from design import SCENARIOS,FAMILY,METHODS,generate,truth,temporal,specification,rng,assumptions
from methods import historical,analytic,grouped_bootstrap,adjust,combine,bootstrap_pair,one_sided
from reference import labels,validate_record,correction
from experiment import study
from precision import bound,sufficient,merge_stats,summarize,summarize_stats,DELTA

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,os.environ.get('STAT01_REFERENCE_SRC',str(ROOT/'src')))

@pytest.mark.parametrize('spec',SCENARIOS,ids=lambda x:x['name'])
def test_independent_truth_and_family(spec):
    assert truth(spec)==labels(spec)
    assert len(FAMILY)==165 and len(set(FAMILY))==165
    assert sum(truth(spec)['practical'])<=sum(truth(spec)['sign'])
    if spec['name'] in ('practical_boundary','small_sign_reversal'):
        assert not any(truth(spec)['practical']) and any(truth(spec)['sign'])
    if spec['name'] in ('iid_equal_null','iid_stable_null','iid_near_tie_null','exact_ties_null','block_null','ar_null','selective_null'):
        assert not any(truth(spec)['sign'])


def test_analytic_generator_iid_moments_and_policy_covariance():
    spec=specification('fixture',n=30000)
    y,mask=generate(spec,999,0)
    assert mask.all();assert np.max(np.abs(y.mean(axis=1)-.5))<.005
    covariance=np.cov(y[0].T)
    assert np.max(np.abs(covariance-(.15**2*(.5*np.eye(11)+.5))))<.001

@pytest.mark.parametrize('kind',['ar','block'])
def test_analytic_temporal_covariance(kind):
    spec=specification('fixture',n=5,temporal=kind)
    samples=np.stack([generate(spec,999,i)[0][0,:,0] for i in range(2000)])
    assert np.max(np.abs(np.cov(samples.T)-.15**2*temporal(5,kind)))<.003

@pytest.mark.parametrize('distribution',['t5','lognormal','uniform'])
def test_standardized_innovation_mean_variance(distribution):
    from design import innovations
    x=innovations(np.random.default_rng(18291),(300000,),distribution)
    assert abs(x.mean())<.015 and abs(x.var()-1)<.08


def test_exact_ties_bounded_support_and_missing_rule():
    for sid in (3,15,16):
        spec=SCENARIOS[sid];y,mask=generate(spec,999,sid)
        if sid==3:assert np.all(y==y[:,:,:1])
        if sid==15:
            assert np.array_equal(mask[0,:,0],y[0,:,0]>=.5)
            assert np.array_equal(mask[1,:,1],y[1,:,1]>=.5)
        if sid==16:assert y.min()>0 and y.max()<1

@pytest.mark.parametrize('missing',[False,True])
def test_historical_baseline_matches_frozen_production_on_synthetic_fixture(missing):
    from robustbench.ranking_portability.analysis.reversal_analysis import classify_pairwise_reversal
    from robustbench.ranking_portability.analysis.stats import benjamini_hochberg
    # Only one policy differs by source;18+ overlapping eligible comparisons exercise the stream order.
    spec=specification('fixture',mean='reverse',delta=.3,n=10)
    y,mask=generate(spec,999,25)
    if missing:mask[0,::3,0]=False;mask[1,::4,1]=False
    new,meta=historical(y,mask,np.random.default_rng(42),2000)
    old=[];r=np.random.default_rng(42)
    rows=[[dict(window_id=str(i),policy_id=f'p{j:02d}',score=float(y[s,i,j]) if mask[s,i,j] else None) for i in range(10) for j in range(11)] for s in range(3)]
    for s,t,a,b in FAMILY:
        old.append(classify_pairwise_reversal(rows[s],rows[t],policy_a=f'p{a:02d}',policy_b=f'p{b:02d}',metric='score',rng=r,n_resamples=2000))
    indices=[i for i,x in enumerate(old) if x.p_x is not None and x.p_y is not None]
    expected=[False]*165
    for i,flag in zip(indices,benjamini_hochberg([max(old[i].p_x,old[i].p_y) for i in indices],q=.05)):
        expected[i]=flag and old[i].classification.value=='SUPPORTED_PRACTICAL_REVERSAL'
    assert expected==new['historical_screened_BH']['reject']
    for interval in meta['intervals']:
        o=old[interval['h']]
        assert np.allclose(interval['ci'],[o.ci_x,o.ci_y],rtol=1e-12,atol=1e-14)
        assert interval['p_sides']==[o.p_x,o.p_y]

@pytest.mark.parametrize('method',['bh','by','holm'])
def test_family_adjustment_independent(method):
    for p in ([0.,.0001,.03,.8,1.],[1.]*165,[.001]*165,[0.,0.,1.]):
        assert adjust(p,method).tolist()==correction(p,method)
        if method!='holm':assert adjust(p,method).tolist()==(stats.false_discovery_control(p,method=method)<=.05).tolist()


def test_student_oracle_and_cluster_formulas_against_direct_scipy():
    spec=SCENARIOS[9];y,mask=generate(spec,999,31)
    def independent_p(kind):
        sides=[]
        for s in (0,1):
            pair=[]
            for a,b in ((0,1),(1,0)):
                z=y[s,:,a]-1.1*y[s,:,b]
                if kind=='cluster':z=z.reshape(-1,5).mean(axis=1)
                if kind=='oracle':
                    c=np.zeros(11);c[a]=1;c[b]=-1.1
                    covariance=.15**2*(.5*np.eye(11)+.5)
                    variance=float(c@covariance@c)*np.sum(temporal(40,'block'))/40**2
                    p=stats.norm.sf(z.mean()/math.sqrt(variance))
                else:p=stats.ttest_1samp(z,0,alternative='greater').pvalue
                pair.append(p)
            sides.append(pair)
        return min(1.,2*min(max(sides[0][0],sides[1][1]),max(sides[0][1],sides[1][0])))
    for kind in ('iid','cluster','oracle'):
        result=analytic(y,mask,spec,kind)
        assert result['p'][0]==pytest.approx(independent_p(kind),abs=1e-14)
        z=(y[0,:,0]-y[0,:,1]);z=z.reshape(-1,5).mean(axis=1) if kind=='cluster' else z
        if kind!='oracle':
            ci=stats.t.interval(.95,len(z)-1,loc=z.mean(),scale=stats.sem(z))
            assert np.allclose(result['ci'],ci,rtol=1e-12)


def test_bounded_formula_and_domain_abstention():
    spec=SCENARIOS[16];y,mask=generate(spec,999,1)
    out=analytic(y,mask,spec,'bounded');components=[]
    for s in (0,1):
        components.append([math.exp(-2*40*max(np.mean(y[s,:,a]-1.1*y[s,:,b]),0)**2/2.1**2) for a,b in ((0,1),(1,0))])
    expected=min(1.,2*min(max(components[0][0],components[1][1]),max(components[0][1],components[1][0])))
    assert out['p'][0]==pytest.approx(expected)
    assert not any(analytic(y,mask,SCENARIOS[0],'bounded')['reject'])


def test_orientation_union_multiplicity_not_data_selected():
    pa=np.ones((3,55));pb=np.ones((3,55));pa[0,0]=.01;pb[1,0]=.02
    assert combine(pa,pb)[0]==.04
    pa[0,0]=.001;pb[1,0]=.9
    assert combine(pa,pb)[0]==1.


def test_missing_latent_values_never_used_by_methods():
    spec=SCENARIOS[14];y,mask=generate(spec,999,8);changed=y.copy();changed[~mask]=1e10
    for kind in ('iid','cluster','oracle'):
        assert analytic(y,mask,spec,kind)==analytic(changed,mask,spec,kind)
    assert historical(y,mask,np.random.default_rng(1),100)==historical(changed,mask,np.random.default_rng(1),100)
    assert grouped_bootstrap(y,mask,spec,np.random.default_rng(1),100)==grouped_bootstrap(changed,mask,spec,np.random.default_rng(1),100)


def test_bootstrap_group_members_stay_together_and_resolution():
    spec=specification('fixture',n=10,temporal='block');y,mask=generate(spec,999,22)
    class KnownWeights:
        def multinomial(self,g,p,size):
            assert g==2
            return np.tile([2,0],(size,1))
    out=grouped_bootstrap(y,mask,spec,KnownWeights(),b=10)
    expected=np.mean(y[0,:5,0]-y[0,:5,1])
    assert out['ci']==pytest.approx([expected,expected])
    assert min(out['p'])>=2/11


def test_rng_streams_replay_and_independent_validation_corruptions():
    y,mask,a=study(7,999,b=100,engineering=True);yy,mm,b=study(7,999,b=100,engineering=True)
    assert np.array_equal(y,yy) and np.array_equal(mask,mm) and a==b
    assert validate_record(SCENARIOS[7],y,mask,a,7,999)
    for field in ('truth','reject','replicate','p','metric'):
        bad=copy.deepcopy(a)
        if field=='truth':bad['truth']['practical'][0]=not bad['truth']['practical'][0]
        if field=='reject':bad['methods']['iid_t_Holm']['reject'][0]=not bad['methods']['iid_t_Holm']['reject'][0]
        if field=='replicate':bad['replicate']=1
        if field=='p':bad['methods']['iid_t_Holm']['p'][0]=1.1
        if field=='metric':bad['methods']['iid_t_Holm']['endpoints']['fdp_practical']=.123
        with pytest.raises(ValueError):validate_record(SCENARIOS[7],y,mask,bad,7,999)


def test_monte_carlo_bounds_optional_look_allocation_and_merge():
    x=[0,0,1,0,1]*100
    result=bound(x)
    log=math.log(4/DELTA);variance=sum((v-np.mean(x))**2 for v in x)/(len(x)-1)
    expected=math.sqrt(2*variance*log/len(x))+7*log/(3*(len(x)-1))
    assert result['halfwidth']==pytest.approx(expected)
    assert DELTA==.05/(18*8*16*5)
    records=[study(7,999+i,b=30,engineering=True)[2] for i in range(3)]
    combined=merge_stats(sufficient(records[:1]),sufficient(records[1:]))
    whole=sufficient(records)
    for m in METHODS:
        for e in whole[m]:
            assert combined[m][e]==pytest.approx(whole[m][e])
    assert summarize_stats(whole,3,SCENARIOS[7])['precision_objective_met'] is False
    summary=summarize(records);sums=summarize_stats(whole,3,SCENARIOS[7])
    for m in METHODS:
        for e in whole[m]:assert sums['methods'][m]['endpoints'][e]==pytest.approx(summary['methods'][m]['endpoints'][e])


def test_checkpoint_roundtrip_hash_and_identity(tmp_path,monkeypatch):
    import run as runner
    original=runner.study
    # Noncampaign engineering stream; deliberately small resampling count.
    def fixture(sid,rep,engineering=False):
        y,mask,r=original(sid,999+rep,b=30,engineering=True);r['replicate']=rep;return y,mask,r
    monkeypatch.setattr(runner,'study',fixture)
    a=runner.execute_batch(str(tmp_path),7,0,2,'fixture-identity',engineering=True)
    monkeypatch.setattr(runner,'study',lambda *a: (_ for _ in ()).throw(AssertionError('duplicate generation')))
    b=runner.execute_batch(str(tmp_path),7,0,2,'fixture-identity',engineering=True)
    assert a[:3]==b[:3] and b[-1]=='REUSED_VALIDATED'
    path=runner.batch_path(tmp_path,7,0)
    with pytest.raises(ValueError,match='identity'):runner.checked_batch(path,7,0,2,'other',engineering=True)
    with (path/'raw.npz').open('ab') as f:f.write(b'corrupt')
    with pytest.raises(ValueError,match='hash mismatch'):runner.checked_batch(path,7,0,2,'fixture-identity',engineering=True)

@pytest.mark.parametrize('sid',range(18),ids=lambda i:SCENARIOS[i]['name'])
def test_every_scenario_methods_and_independent_integrity(sid):
    y,mask,record=study(sid,17,b=64,engineering=True)
    assert record['seed_namespace']==0
    assert validate_record(SCENARIOS[sid],y,mask,record,sid,17)


def test_engineering_and_campaign_streams_are_disjoint():
    y,mask=generate(SCENARIOS[0],0,0,namespace=1)
    yy,mm=generate(SCENARIOS[0],0,0,namespace=0)
    assert not np.array_equal(y,yy)
    assert np.array_equal(y,generate(SCENARIOS[0],0,0,namespace=1)[0])


def test_all_missing_and_exact_tie_rank_sets():
    spec=SCENARIOS[0];y=np.full((3,40,11),.5);mask=np.ones_like(y,dtype=bool)
    for kind in ('iid','cluster','oracle'):
        result=analytic(y,mask,spec,kind)
        assert result['candidate_sets']==[list(range(11))]*3
        empty=analytic(y,np.zeros_like(mask),spec,kind)
        assert empty['ci'] is None and not any(empty['reject'])
    group=grouped_bootstrap(y,np.zeros_like(mask),spec,np.random.default_rng(6),b=20)
    assert group['ci'] is None and group['p']==[1.]*165


def _tiny_runner(tmp_path,monkeypatch,precise):
    import concurrent.futures
    import run as runner
    import experiment
    scenario=SCENARIOS[7]
    monkeypatch.setattr(runner,'HERE',tmp_path)
    monkeypatch.setattr(runner,'SCENARIOS',[scenario]);monkeypatch.setattr(experiment,'SCENARIOS',[scenario])
    monkeypatch.setattr(runner,'LOOKS',(2,));monkeypatch.setattr(runner,'BATCH',1)
    monkeypatch.setattr(runner.concurrent.futures,'ProcessPoolExecutor',concurrent.futures.ThreadPoolExecutor)
    original=experiment.study
    monkeypatch.setattr(runner,'study',lambda sid,rep,engineering=False:original(sid,rep,b=32,engineering=engineering))
    monkeypatch.setattr(runner,'summarize_stats',lambda sums,n,spec:dict(precision_objective_met=precise,n_studies=n))
    fixture=tmp_path/'fingerprint.txt';fixture.write_text('frozen')
    launch=tmp_path/'test-launch.json'
    runner.atomic(launch,dict(files={'fingerprint.txt':runner.sha(fixture)},scenarios=[scenario],methods=list(METHODS),engineering_only=True))
    return runner,launch

@pytest.mark.parametrize('precise',[True,False])
def test_full_runner_stopping_and_resume(tmp_path,monkeypatch,precise):
    runner,launch=_tiny_runner(tmp_path,monkeypatch,precise)
    assert runner.run(tmp_path/'out',launch,workers=2)==0
    status=runner.read(tmp_path/'out'/'completion.json')['status']
    assert status==('COMPLETE_PRECISION_OBJECTIVES' if precise else 'COMPLETE_WITH_PRECISION_GAPS')
    assert runner.read(tmp_path/'out'/'checkpoint.json')['scenarios']['0']['n']==2
    monkeypatch.setattr(runner,'study',lambda *a,**kw: (_ for _ in ()).throw(AssertionError('rerun completed study')))
    assert runner.run(tmp_path/'out',launch,workers=2)==0


def test_runner_time_budget_and_source_failure(tmp_path,monkeypatch):
    runner,launch=_tiny_runner(tmp_path,monkeypatch,True)
    assert runner.run(tmp_path/'out',launch,workers=2,hours=0)==2
    assert runner.read(tmp_path/'out'/'completion.json')['status']=='TIME_BUDGET_PARTIAL'
    assert runner.read(tmp_path/'out'/'checkpoint.json')['scenarios']['0']['last_look'] is None
    (tmp_path/'fingerprint.txt').write_text('changed')
    with pytest.raises(ValueError,match='hash mismatch'):runner.run(tmp_path/'out',launch,workers=2)


def test_oracle_variance_on_observed_ar_submatrix():
    spec=SCENARIOS[11];y,mask=generate(spec,999,44)
    mask[:,::3,0]=False;mask[:,1::5,1]=False
    out=analytic(y,mask,spec,'oracle');side=[]
    for s in (0,1):
        use=np.flatnonzero(mask[s,:,0]&mask[s,:,1]);R=.7**np.abs(use[:,None]-use[None,:])
        component=[]
        for a,b in ((0,1),(1,0)):
            se=math.sqrt(.15**2*(1+1.1**2-2*1.1*.5)*R.sum()/len(use)**2)
            component.append(stats.norm.sf(np.mean(y[s,use,a]-1.1*y[s,use,b])/se))
        side.append(component)
    expected=min(1.,2*min(max(side[0][0],side[1][1]),max(side[0][1],side[1][0])))
    assert out['p'][0]==pytest.approx(expected,abs=1e-14)


def test_group_null_centering_formula_independently():
    spec=specification('fixture',n=10);y,mask=generate(spec,999,54)
    class Fixed:
        def multinomial(self,g,p,size):return np.tile([2,0],(size,1))
    out=grouped_bootstrap(y,mask,spec,Fixed(),b=10);side=[]
    for s in (0,1):
        pp=[]
        for a,b in ((0,1),(1,0)):
            obs=np.mean(y[s,:,a]-1.1*y[s,:,b]);resample=np.mean(y[s,:5,a]-1.1*y[s,:5,b])
            pp.append((1+10*int(resample-obs>=obs))/11)
        side.append(pp)
    assert out['p'][0]==min(1.,2*min(max(side[0][0],side[1][1]),max(side[0][1],side[1][0])))
