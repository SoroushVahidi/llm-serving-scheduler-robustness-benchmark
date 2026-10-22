"""One independent simulated study and prespecified bounded MC endpoints."""
import warnings
import numpy as np
from design import SCENARIOS,METHODS,FAMILY,truth,rng,generate,assumptions
from methods import historical,analytic,grouped_bootstrap,bootstrap_pair

ENDPOINTS=('fdp_practical','fwer_practical','null_fraction_practical','power_practical',
           'fdp_sign','fwer_sign','null_fraction_sign','power_sign','ci_coverage','ci_available',
           'topset_coverage','topset_size_fraction','empirical_topset_coverage','id_correct_fraction',
           'selected_coverage','selected_available')


def endpoints(result,truths,empirical_sets,selected):
    reject=np.array(result['reject'],bool);r=int(reject.sum());out={}
    for target in ('practical','sign'):
        alt=np.array(truths[target]);v=int(np.sum(reject&~alt));nn=int((~alt).sum());na=int(alt.sum())
        out['fdp_'+target]=v/max(r,1);out['fwer_'+target]=float(v>0)
        out['null_fraction_'+target]=v/nn if nn else None
        out['power_'+target]=(r-v)/na if na else None
    ci=result.get('ci');out['ci_available']=float(ci is not None)
    out['ci_coverage']=float(ci[0]<=truths['fixed_difference']<=ci[1]) if ci else None
    candidates=result.get('candidate_sets')
    out['topset_coverage']=float(all(set(t)<=set(c) for t,c in zip(truths['top_sets'],candidates))) if candidates is not None else None
    out['topset_size_fraction']=sum(map(len,candidates))/(3*11) if candidates is not None else None
    out['empirical_topset_coverage']=float(all(set(t)<=set(c) for t,c in zip(truths['top_sets'],empirical_sets)))
    out['id_correct_fraction']=sum(bool(c) and min(c) in t for t,c in zip(truths['top_sets'],empirical_sets))/3
    out['selected_available']=float(bool(selected))
    out['selected_coverage']=sum(selected)/len(selected) if selected else None
    assert set(out)==set(ENDPOINTS)
    return out


def study(sid,rep,b=2000,engineering=False):
    namespace=0 if engineering else 1
    spec=SCENARIOS[sid];y,mask=generate(spec,sid,rep,namespace);tr=truth(spec)
    tr['fixed_difference']=spec['mu'][0][0]-spec['mu'][0][1]
    methods,history=historical(y,mask,rng(sid,rep,2,namespace),b)
    paired=mask[0,:,0]&mask[0,:,1]
    boot=bootstrap_pair(y[0,paired,0]-y[0,paired,1],rng(sid,rep,4,namespace),b)
    unconditional_ci=boot[:2] if boot else None
    selected=[]
    for record in history['intervals']:
        s,t,a,d=FAMILY[record['h']]
        for z,ci in zip((s,t),record['ci']):
            value=spec['mu'][z][a]-spec['mu'][z][d]
            selected.append(float(ci[0]<=value<=ci[1]))
    for name in METHODS[:3]:methods[name].update(ci=unconditional_ci,candidate_sets=None)
    for name,kind in zip(METHODS[3:6],('iid','cluster','oracle')):
        methods[name]=analytic(y,mask,spec,kind)
    methods['group_bootstrap_BY']=grouped_bootstrap(y,mask,spec,rng(sid,rep,3,namespace),b)
    methods['bounded_Hoeffding_Holm']=analytic(y,mask,spec,'bounded')
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',RuntimeWarning);means=np.nanmean(np.where(mask,y,np.nan),axis=1)
    empirical=[np.flatnonzero(row==np.nanmax(row)).tolist() if np.isfinite(row).any() else [] for row in means]
    for name,result in methods.items():
        result['assumption_status']=assumptions(spec,name)
        result['endpoints']=endpoints(result,tr,empirical,selected if name in METHODS[:3] else [])
    record=dict(scenario=sid,replicate=rep,seed_namespace=namespace,truth=tr,methods=methods,historical=history,
                empirical_top_sets=empirical,separate_difference=float(means[0,0]-means[0,1]) if np.isfinite(means[0,:2]).all() else None,
                matched_difference=float(np.mean(y[0,paired,0]-y[0,paired,1])) if paired.any() else None,
                matched_n=int(paired.sum()))
    return y,mask,record
