"""Frozen STAT01 design. Synthetic-only, no historical/corpus data imports."""
from fractions import Fraction
from functools import lru_cache
import itertools
import numpy as np

MASTER=2026102201
B=2000
ALPHA=.05
POLICY_PAIRS=list(itertools.combinations(range(11),2))
SOURCE_PAIRS=list(itertools.combinations(range(3),2))
FAMILY=[(s,t,a,b) for s,t in SOURCE_PAIRS for a,b in POLICY_PAIRS]
METHODS=('historical_screened_BH','historical_full_BH','historical_plus1_BY',
         'iid_t_Holm','cluster_t_Holm','oracle_normal_Holm','group_bootstrap_BY','bounded_Hoeffding_Holm')
LOOKS=(500,1000,2000,4000,8000)
BATCH=25


def specification(name,mean='equal',delta=0.,temporal='iid',rho=.5,sigma=(.15,.15,.15),
                  distributions=('normal',)*3,missing='complete',n=40):
    mu=np.full((3,11),.5)
    if mean=='stable':mu[:]=[round(.5+.01*j,6) for j in range(11)]
    if mean=='near':mu[:]=[round(.5+.0002*j,6) for j in range(11)]
    if mean=='reverse':
        mu[0,:2]=[round(.5+delta/2,6),round(.5-delta/2,6)]
        mu[1,:2]=mu[0,:2][::-1]
    if mean=='boundary':mu[0,:2]=[.55,.5];mu[1,:2]=[.5,.55]
    return dict(name=name,mu=mu.tolist(),temporal=temporal,rho=rho,sigma=list(sigma),
                distributions=list(distributions),missing=missing,n=n)

SCENARIOS=[
 specification('iid_equal_null'),specification('iid_stable_null',mean='stable'),
 specification('iid_near_tie_null',mean='near'),specification('exact_ties_null',rho=1.),
 specification('practical_boundary',mean='boundary'),
 specification('small_sign_reversal',mean='reverse',delta=.03),
 specification('medium_reversal',mean='reverse',delta=.10),
 specification('large_reversal',mean='reverse',delta=.30),
 specification('block_null',temporal='block'),
 specification('block_reversal',mean='reverse',delta=.15,temporal='block'),
 specification('ar_null',temporal='ar'),
 specification('ar_reversal',mean='reverse',delta=.15,temporal='ar'),
 specification('unequal_variances',mean='reverse',delta=.15,sigma=(.08,.25,.15)),
 specification('mixed_distributions',mean='reverse',delta=.15,sigma=(.08,.25,.15),distributions=('normal','t5','lognormal')),
 specification('mcar_reversal',mean='reverse',delta=.15,missing='mcar'),
 specification('selective_null',missing='selective'),
 specification('bounded_reversal',mean='reverse',delta=.30,sigma=(.08,)*3,distributions=('uniform',)*3),
 specification('bounded_reversal_n400',mean='reverse',delta=.30,sigma=(.08,)*3,distributions=('uniform',)*3,n=400),
]


def rng(scenario,replicate,stream,namespace=1):
    return np.random.default_rng(np.random.SeedSequence([MASTER,namespace,scenario,replicate,stream]))

@lru_cache(None)
def temporal(n,kind):
    i=np.arange(n)
    if kind=='iid':return np.eye(n)
    if kind=='ar':return .7**np.abs(i[:,None]-i[None,:])
    if kind=='block':return .7*(i[:,None]//5==i[None,:]//5)+.3*np.eye(n)
    raise ValueError(kind)

@lru_cache(None)
def factor(n,kind):return np.linalg.cholesky(temporal(n,kind))

def innovations(r,shape,kind):
    if kind=='normal':return r.standard_normal(shape)
    if kind=='t5':return r.standard_t(5,shape)*np.sqrt(3/5)
    if kind=='lognormal':return (np.exp(r.standard_normal(shape))-np.exp(.5))/np.sqrt(np.exp(2)-np.exp(1))
    if kind=='uniform':return r.uniform(-np.sqrt(3),np.sqrt(3),shape)
    raise ValueError(kind)

def generate(spec,sid,rep,namespace=1):
    r=rng(sid,rep,0,namespace);n=spec['n'];mu=np.array(spec['mu']);rho=spec['rho'];y=np.empty((3,n,11))
    for s in range(3):
        common=innovations(r,(n,1),spec['distributions'][s])
        private=innovations(r,(n,11),spec['distributions'][s])
        u=np.sqrt(rho)*common+np.sqrt(1-rho)*private
        # Avoid an unnecessary dense identity multiplication for IID windows.
        residual=u if spec['temporal']=='iid' else factor(n,spec['temporal'])@u
        y[s]=mu[s]+spec['sigma'][s]*residual
    mask=np.ones(y.shape,dtype=bool)
    if spec['missing']=='mcar':mask=rng(sid,rep,1,namespace).random(y.shape)<.8
    if spec['missing']=='selective':
        mask[0,:,0]=y[0,:,0]>=mu[0,0];mask[1,:,1]=y[1,:,1]>=mu[1,1]
    return y,mask


def truth(spec):
    m=[[Fraction(str(x)) for x in row] for row in spec['mu']];q=Fraction(11,10)
    sign=[];practical=[]
    for s,t,a,b in FAMILY:
        sign.append((m[s][a]-m[s][b])*(m[t][a]-m[t][b])<0)
        practical.append((m[s][a]>q*m[s][b] and m[t][b]>q*m[t][a]) or
                         (m[s][b]>q*m[s][a] and m[t][a]>q*m[t][b]))
    tops=[[j for j,x in enumerate(row) if x==max(row)] for row in m]
    return dict(sign=sign,practical=practical,top_sets=tops)


def assumptions(spec,method):
    normal=all(x=='normal' for x in spec['distributions'])
    nonselect=spec['missing']!='selective'
    independent=spec['temporal']=='iid'
    if method=='bounded_Hoeffding_Holm':
        return 'FINITE_SAMPLE_VALID' if spec['distributions']==['uniform']*3 and independent and nonselect else 'ABSTAIN_OUTSIDE_DOMAIN'
    if method=='iid_t_Holm' and normal and independent and nonselect:return 'FINITE_SAMPLE_VALID'
    if method=='cluster_t_Holm' and normal and spec['temporal'] in ('iid','block') and nonselect:return 'FINITE_SAMPLE_VALID'
    if method=='oracle_normal_Holm' and normal and nonselect:return 'VALID_ORACLE_NOT_DEPLOYABLE'
    return 'DIAGNOSTIC_NO_FINITE_SAMPLE_GUARANTEE'
