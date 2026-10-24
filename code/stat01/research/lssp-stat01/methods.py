"""Historical procedure plus prospective full-family competitors."""
import warnings
import numpy as np
from scipy import stats
from design import B,ALPHA,FAMILY,POLICY_PAIRS,SOURCE_PAIRS,METHODS,temporal,assumptions

A=np.array([a for a,b in POLICY_PAIRS]);D=np.array([b for a,b in POLICY_PAIRS])

def adjust(p,kind):
    p=np.asarray(p,float);order=np.argsort(p,kind='stable');m=len(p);out=np.zeros(m,bool)
    if not m:return out
    values=p[order]
    if kind=='holm':
        good=values<=ALPHA/(m-np.arange(m));k=next((i for i,x in enumerate(good) if not x),m)
    else:
        q=ALPHA/(sum(1/i for i in range(1,m+1)) if kind=='by' else 1.)
        hits=np.flatnonzero(values<=q*np.arange(1,m+1)/m);k=int(hits[-1]+1) if len(hits) else 0
    out[order[:k]]=True
    return out


def bootstrap_pair(d,r,b=B):
    if not len(d):return None
    z=d[r.integers(0,len(d),size=(b,len(d)))].mean(axis=1)
    lo,hi=np.quantile(z,[.025,.975])
    p=min(1.,2*min(np.mean(z<=0),np.mean(z>=0)))
    return [float(lo),float(hi),float(p)]


def historical(y,mask,r,b=B):
    obs=np.where(mask,y,np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',RuntimeWarning);means=np.nanmean(obs,axis=1)
    p=np.ones(165);plus=np.ones(165);eligible=np.zeros(165,bool);supported=np.zeros(165,bool)
    intervals=[]
    for h,(s,t,a,d) in enumerate(FAMILY):
        vals=[(means[z,a],means[z,d]) for z in (s,t)]
        if not np.isfinite(vals).all():continue
        diffs=[a0-b0 for a0,b0 in vals]
        if diffs[0]*diffs[1]>=0:continue
        losers=[min(a0,b0) for a0,b0 in vals]
        if any(l==0 for l in losers) or any(abs(v)/abs(l)<=.1 for v,l in zip(diffs,losers)):continue
        eligible[h]=True;boots=[]
        for z in (s,t):
            use=mask[z,:,a]&mask[z,:,d];boots.append(bootstrap_pair(y[z,use,a]-y[z,use,d],r,b))
        if any(x is None for x in boots):
            # Historical NaN IUT is omitted from BH rank slots.
            eligible[h]=False;continue
        p[h]=max(x[2] for x in boots)
        plus[h]=max(min(1.,(b*x[2]+2)/(b+1)) for x in boots)
        supported[h]=all(x[0]*x[1]>0 for x in boots)
        intervals.append(dict(h=h,ci=[x[:2] for x in boots],p_sides=[x[2] for x in boots],point=diffs))
    selected=np.zeros(165,bool);selected[eligible]=adjust(p[eligible],'bh')
    return dict(historical_screened_BH=dict(p=p.tolist(),reject=(selected&supported).tolist()),
                historical_full_BH=dict(p=p.tolist(),reject=(adjust(p,'bh')&supported).tolist()),
                historical_plus1_BY=dict(p=plus.tolist(),reject=(adjust(plus,'by')&supported).tolist())),dict(eligible=eligible.tolist(),supported=supported.tolist(),intervals=intervals)


def one_sided(mean,se,df=None):
    mean=np.asarray(mean);se=np.asarray(se)
    z=np.divide(mean,se,out=np.zeros_like(mean),where=se>0)
    p=stats.norm.sf(z) if df is None else stats.t.sf(z,np.maximum(df,1))
    p=np.where(se==0,np.where(mean>0,0.,1.),p)
    p=np.where(np.isinf(se),1.,p)
    return p


def pair_data(y,mask):
    valid=mask[:,A]&mask[:,D]
    av=np.where(valid,y[:,A],0.);bv=np.where(valid,y[:,D],0.)
    return valid,av,bv


def combine(pab,pba):
    return np.concatenate([np.minimum(1.,2*np.minimum(np.maximum(pab[s],pba[t]),np.maximum(pba[s],pab[t]))) for s,t in SOURCE_PAIRS])


def candidate_sets(pzero,pnegative):
    result=[];threshold=ALPHA/(3*11*10)
    for s in range(3):
        excluded=set()
        for k,(a,b) in enumerate(POLICY_PAIRS):
            if pzero[s,k]<=threshold:excluded.add(b)
            if pnegative[s,k]<=threshold:excluded.add(a)
        result.append([j for j in range(11) if j not in excluded])
    return result


def analytic(y,mask,spec,kind):
    p_ab=[];p_ba=[];pzero=[];pneg=[];cis=[]
    if kind=='bounded' and assumptions(spec,'bounded_Hoeffding_Holm')=='ABSTAIN_OUTSIDE_DOMAIN':
        return dict(p=[1.]*165,reject=[False]*165,ci=None,candidate_sets=None)
    for s in range(3):
        ys,ms=y[s],mask[s]
        if kind=='cluster':
            ms=ms.reshape(-1,5,11).all(axis=1)
            ys=ys.reshape(-1,5,11).mean(axis=1)
        valid,av,bv=pair_data(ys,ms);count=valid.sum(axis=0);den=np.maximum(count,1)
        z=np.stack((av-bv,av-1.1*bv,bv-1.1*av))
        mean=z.sum(axis=1)/den
        if kind=='oracle':
            rr=temporal(spec['n'],spec['temporal'])
            if spec['temporal']=='iid':tfactor=1/den
            else:tfactor=np.sum(valid*(rr@valid),axis=0)/den**2
            variance=np.array([2*(1-spec['rho']),2.21-2.2*spec['rho'],2.21-2.2*spec['rho']])[:,None]*spec['sigma'][s]**2*tfactor
            se=np.sqrt(np.maximum(variance,0));se[:,count==0]=np.inf;df=None;q=stats.norm.ppf(.975)
        elif kind=='bounded':
            width=np.array([2.,2.1,2.1])[:,None]
            pp=np.exp(-2*count*np.maximum(mean,0)**2/width**2);pp[:,count==0]=1.
            pn=np.exp(-2*count*np.maximum(-mean[0],0)**2/4);pn[count==0]=1.
            half=2*np.sqrt(np.log(40)/(2*den));half[count==0]=np.inf
        else:
            var=np.sum(np.where(valid[None,:,:],(z-mean[:,None,:])**2,0),axis=1)/np.maximum(count-1,1)
            se=np.sqrt(var/den);se[:,count<2]=np.inf;df=count-1;q=stats.t.ppf(.975,np.maximum(df,1))
        if kind!='bounded':
            pp=one_sided(mean,se,df);pn=one_sided(-mean[0],se[0],df)
            half=q*se[0]
        pzero.append(pp[0]);pneg.append(pn);p_ab.append(pp[1]);p_ba.append(pp[2])
        ci=[float(mean[0,0]-half[0]),float(mean[0,0]+half[0])] if np.isfinite(half[0]) else None
        cis.append(ci)
    p=combine(np.array(p_ab),np.array(p_ba))
    return dict(p=p.tolist(),reject=adjust(p,'holm').tolist(),ci=cis[0],candidate_sets=candidate_sets(np.array(pzero),np.array(pneg)))


def grouped_bootstrap(y,mask,spec,r,b=B):
    pab=[];pba=[];ci=None
    n=spec['n'];g=n//5
    for s in range(3):
        valid,av,bv=pair_data(y[s],mask[s]);den=np.maximum(valid.sum(axis=0),1)
        obs_a=av.sum(axis=0)/den;obs_b=bv.sum(axis=0)/den
        weights=np.repeat(r.multinomial(g,np.full(g,1/g),size=b),5,axis=1).astype(float)
        counts=weights@valid.astype(float)
        ma=(weights@av)/np.maximum(counts,1);mb=(weights@bv)/np.maximum(counts,1)
        broken=(counts==0).any(axis=0)|(valid.sum(axis=0)==0)
        pa=(1+((ma-1.1*mb)-(obs_a-1.1*obs_b)>=obs_a-1.1*obs_b).sum(axis=0))/(b+1)
        pb=(1+((mb-1.1*ma)-(obs_b-1.1*obs_a)>=obs_b-1.1*obs_a).sum(axis=0))/(b+1)
        pa[broken]=pb[broken]=1.;pab.append(pa);pba.append(pb)
        if s==0 and not broken[0]:ci=np.quantile(ma[:,0]-mb[:,0],[.025,.975]).tolist()
    p=combine(np.array(pab),np.array(pba))
    return dict(p=p.tolist(),reject=adjust(p,'by').tolist(),ci=ci,candidate_sets=None)
