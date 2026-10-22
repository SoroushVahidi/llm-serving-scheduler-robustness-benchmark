"""Prespecified finite-look MC uncertainty; study is the independent unit."""
import math
import numpy as np
from design import SCENARIOS,METHODS,LOOKS
from experiment import ENDPOINTS

DELTA=.05/(len(SCENARIOS)*len(METHODS)*len(ENDPOINTS)*len(LOOKS))


def bound(values,delta=DELTA):
    x=np.array([v for v in values if v is not None],float);n=len(x)
    if n<2:return dict(n=n,mean=float(x[0]) if n else None,lower=0.,upper=1.,halfwidth=1.,mcse=None)
    mean=float(x.mean());var=float(x.var(ddof=1));log=math.log(4/delta)
    b=math.sqrt(2*var*log/n)+7*log/(3*(n-1))
    return dict(n=n,mean=mean,lower=max(0.,mean-b),upper=min(1.,mean+b),halfwidth=b,mcse=math.sqrt(var/n))


def summarize(records):
    summary={};precise=True
    for name in METHODS:
        rows=[r['methods'][name] for r in records]
        fields={e:bound([r['endpoints'][e] for r in rows]) for e in ENDPOINTS}
        available=rows[0]['assumption_status']!='ABSTAIN_OUTSIDE_DOMAIN'
        required={'fdp_practical':.025,'fwer_practical':.025,'null_fraction_practical':.025,
                  'ci_coverage':.03,'power_practical':.08}
        for key,width in required.items():
            if key=='power_practical' and not any(records[0]['truth']['practical']):continue
            if available and fields[key]['halfwidth']>width:precise=False
        fdr,ci=fields['fdp_practical'],fields['ci_coverage']
        if not available:verdict='ABSTAIN_OUTSIDE_DOMAIN'
        elif fdr['lower']>.05 or (ci['n']>0 and ci['upper']<.95):verdict='CALIBRATION_CONCERN'
        elif fdr['upper']<=.06 and ci['n']>0 and ci['lower']>=.94:verdict='EMPIRICALLY_COMPATIBLE_WITH_TOLERANCE'
        else:verdict='INCONCLUSIVE'
        summary[name]=dict(assumption_status=rows[0]['assumption_status'],endpoints=fields,calibration_screen=verdict)
    return dict(n_studies=len(records),simultaneous_mc_delta_per_endpoint_look=DELTA,
                precision_objective_met=precise,methods=summary)


def sufficient(records):
    out={}
    for m in METHODS:
        out[m]={}
        for e in ENDPOINTS:
            x=np.array([r['methods'][m]['endpoints'][e] for r in records if r['methods'][m]['endpoints'][e] is not None])
            average=float(x.mean()) if len(x) else 0.
            out[m][e]=dict(n=len(x),mean=average,m2=float(np.sum((x-average)**2)))
    return out


def merge_stats(left,right):
    if left is None:return right
    out={}
    for m in METHODS:
        out[m]={}
        for e in ENDPOINTS:
            a,b=left[m][e],right[m][e];n=a['n']+b['n'];delta=b['mean']-a['mean']
            out[m][e]=dict(n=n,mean=a['mean']+delta*b['n']/n if n else 0.,
                          m2=a['m2']+b['m2']+delta**2*a['n']*b['n']/n if n else 0.)
    return out


def summarize_stats(sums,n,spec):
    from design import assumptions,truth
    result={};precise=True
    for m in METHODS:
        fields={}
        for e,ss in sums[m].items():
            size=ss['n'];mean=ss['mean'] if size else None
            variance=ss['m2']/(size-1) if size>1 else None
            log=math.log(4/DELTA)
            half=math.sqrt(2*variance*log/size)+7*log/(3*(size-1)) if size>1 else 1.
            fields[e]=dict(n=size,mean=mean,lower=max(0.,mean-half) if size else 0.,upper=min(1.,mean+half) if size else 1.,halfwidth=half,mcse=math.sqrt(variance/size) if size>1 else None)
        available=assumptions(spec,m)!='ABSTAIN_OUTSIDE_DOMAIN'
        for e,target in [('fdp_practical',.025),('fwer_practical',.025),('null_fraction_practical',.025),('ci_coverage',.03),('power_practical',.08)]:
            if e=='power_practical' and not any(truth(spec)['practical']):continue
            if available and fields[e]['halfwidth']>target:precise=False
        fdr,ci=fields['fdp_practical'],fields['ci_coverage']
        verdict='ABSTAIN_OUTSIDE_DOMAIN' if not available else 'CALIBRATION_CONCERN' if fdr['lower']>.05 or (ci['n'] and ci['upper']<.95) else 'EMPIRICALLY_COMPATIBLE_WITH_TOLERANCE' if fdr['upper']<=.06 and ci['n'] and ci['lower']>=.94 else 'INCONCLUSIVE'
        result[m]=dict(assumption_status=assumptions(spec,m),endpoints=fields,calibration_screen=verdict)
    return dict(n_studies=n,simultaneous_mc_delta_per_endpoint_look=DELTA,precision_objective_met=precise,methods=result)
