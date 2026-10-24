"""Independent referee: no methods/design/generator imports."""
from decimal import Decimal
from itertools import combinations
import math
import numpy as np


def require(ok,message):
    if not ok:raise ValueError(message)


def labels(spec):
    means=[[Decimal(str(x)) for x in row] for row in spec['mu']]
    practical=[];sign=[]
    for s,t in combinations(range(3),2):
        for a,b in combinations(range(11),2):
            xs,xt=means[s][a]/means[s][b],means[t][a]/means[t][b]
            sign.append((xs>1 and xt<1) or (xs<1 and xt>1))
            margins=[abs(means[z][a]-means[z][b])/min(means[z][a],means[z][b]) for z in (s,t)]
            practical.append(sign[-1] and all(v>Decimal('.1') for v in margins))
    return dict(practical=practical,sign=sign,top_sets=[[i for i,v in enumerate(m) if all(v>=w for w in m)] for m in means])


def correction(ps,kind,alpha=.05):
    m=len(ps);order=sorted(range(m),key=lambda j:ps[j]);selected=set()
    if kind=='holm':
        for i,j in enumerate(order):
            if ps[j]*(m-i)>alpha:break
            selected.add(j)
    else:
        constant=sum(1/k for k in range(1,m+1)) if kind=='by' else 1
        k=max([i+1 for i,j in enumerate(order) if ps[j]*m*constant <=alpha*(i+1)]+[0])
        selected=set(order[:k])
    return [j in selected for j in range(m)]


def validate_record(spec,y,mask,rec,expected_sid,expected_rep):
    require(rec['scenario']==expected_sid and rec['replicate']==expected_rep,'replicate identity')
    require(y.shape==mask.shape==(3,spec['n'],11) and np.isfinite(y).all(),'raw shape/values')
    require(mask.dtype==np.bool_,'mask type')
    expected=labels(spec)
    for k in expected:require(expected[k]==rec['truth'][k],'independent truth mismatch')
    require(rec['truth']['fixed_difference']==spec['mu'][0][0]-spec['mu'][0][1],'contrast truth')
    if spec['missing']=='complete':require(mask.all(),'complete scenario missing data')
    if spec['missing']=='selective':
        target=np.ones_like(mask);target[0,:,0]=y[0,:,0]>=spec['mu'][0][0];target[1,:,1]=y[1,:,1]>=spec['mu'][1][1]
        require(np.array_equal(mask,target),'selective mask rule')
    if spec['distributions']==['uniform']*3:require(np.all((0<=y)&(y<=1)),'bounded support')
    ids=[];family=list((s,t,a,b) for s,t in combinations(range(3),2) for a,b in combinations(range(11),2))
    for name,result in rec['methods'].items():
        ps=result['p'];reject=result['reject'];require(len(ps)==len(reject)==165,'complete family')
        require(all(math.isfinite(p) and 0<=p<=1 for p in ps),'p domain')
        if name=='historical_screened_BH':
            elig=rec['historical']['eligible'];indices=[i for i,e in enumerate(elig) if e]
            flags=correction([ps[i] for i in indices],'bh');ids={i for i,f in zip(indices,flags) if f}
            expected_reject=[i in ids and rec['historical']['supported'][i] for i in range(165)]
        else:
            kind='by' if name in ('group_bootstrap_BY','historical_plus1_BY') else 'bh' if name=='historical_full_BH' else 'holm'
            expected_reject=correction(ps,kind)
            if name.startswith('historical'):expected_reject=[x and s for x,s in zip(expected_reject,rec['historical']['supported'])]
        require(expected_reject==reject,'independent multiplicity mismatch')
        r=sum(reject)
        for target in ('practical','sign'):
            alt=expected[target];false=sum(a and not b for a,b in zip(reject,alt));true=r-false
            values={'fdp_'+target:false/max(r,1),'fwer_'+target:float(false>0),
                    'null_fraction_'+target:false/(165-sum(alt)) if sum(alt)<165 else None,
                    'power_'+target:true/sum(alt) if sum(alt) else None}
            for k,v in values.items():require(result['endpoints'][k]==v,'independent error endpoint')
        ci=result['ci'];want=None if ci is None else float(ci[0]<=rec['truth']['fixed_difference']<=ci[1])
        require(result['endpoints']['ci_coverage']==want,'coverage endpoint')
        require(all(v is None or (math.isfinite(v) and 0<=v<=1) for v in result['endpoints'].values()),'bounded endpoint domain')
    require(len(rec['methods'])==8,'method inventory')
    return True
