"""M2 independent, bounded post-hoc audit. No production analysis imports.
Inputs are frozen; writes only M2. Historical quantities and sensitivities separate.
"""
import collections as C, hashlib, itertools as I, json, os, platform, subprocess, zlib
from pathlib import Path
import numpy as np
import scipy
from scipy.stats import rankdata, chi2, kendalltau, friedmanchisquare
ROOT=Path(__file__).resolve().parents[3]; OUT=ROOT/'paper/tompecs-m2/evidence'; D=ROOT/'dataset/v1.1.0'
inputs={}
def read(p):
 p=Path(p); b=p.read_bytes(); inputs[str(p)]={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}; return json.loads(b)
def write(n,x): (OUT/n).write_text(json.dumps(x,indent=2,allow_nan=True,default=lambda x:x.item())+'\n')
rc=read(D/'scientific/analysis/ranking_correlations.json'); rv=read(D/'scientific/analysis/pairwise_reversals.json')
cells=read(D/'scientific/campaign/consolidated.json')['cells']; meta=read(D/'manifests/ranking_portability_pilot_v2_windows_index.json')['windows']
external=Path(os.environ.get('LSSP_REPOS_ROOT',ROOT.parent))/'llm-serving-scheduler-lssp-cross-metric-analysis-extension/artifacts/analysis/cross_metric_extension/33729102c2f8867cb521f8557cd51b42d8830811de8dea16cc7ab68d53b61fd9'
cr=read(external/'cross_metric_correlations.json')['records']; dr=read(external/'cross_metric_pairwise_disagreements.json')['records']
P=sorted(rc['policies']); M=rc['metrics']; primary='arrival_normalized_weighted_goodput'; R=['LOW','PRE_KNEE','KNEE','POST_KNEE','OVERLOAD','HIGH_PRESSURE']; S=sorted({c['source_family'] for c in cells}); lower={'slo_violation_rate','mean_latency','p95_latency','mean_ttft','p95_ttft'}
# Preserve original insertion order, which is part of the historical random-stream contract.
rows=C.defaultdict(list)
for c in cells:
 if c['repetition']==0 and c['policy_id'] in P: rows[c['source_family'],c['load_region']].append(c)
W={k:list(dict.fromkeys(c['window_id'] for c in v)) for k,v in rows.items()}
A={}
for k,rr in rows.items():
 lookup={(c['window_id'],c['policy_id']):c for c in rr}
 for m in M: A[k+(m,)]=np.array([[lookup[w,p][m] if lookup[w,p][m] is not None else np.nan for p in P] for w in W[k]],float)
def means(a): return np.array([np.nanmean(a[:,j]) for j in range(a.shape[1])])
def bootmeans(a,idx): return np.column_stack([np.nanmean(a[:,j][idx],axis=1) for j in range(a.shape[1])])
ii,jj=np.triu_indices(len(P),1)
def taus(x,y):
 dx=np.sign(x[:,ii]-x[:,jj]); dy=np.sign(y[:,ii]-y[:,jj]); den=np.sqrt((dx*dx).sum(1)*(dy*dy).sum(1)); return np.divide((dx*dy).sum(1),den,out=np.full(len(x),np.nan),where=den>0)
def close(a,b): return bool(np.allclose(a,b,rtol=1e-10,atol=1e-12,equal_nan=True))
def bh(ps,by=False):
 ps=np.array(ps); n=len(ps); order=np.argsort(ps); adj=sum(1/np.arange(1,n+1)) if by and n else 1; hits=np.where(ps[order]<=.05*np.arange(1,n+1)/(n*adj))[0] if n else []; out=np.zeros(n,bool)
 if len(hits):out[order[:hits[-1]+1]]=True
 return out
# All 198 source ranking intervals, matching shared seed-zero RNG call ordering.
rng=np.random.default_rng(0); ranks=[]
for m in M:
 for rec in rc['comparisons'][m]:
  kx=tuple(rec['condition_x'].split('::')); ky=tuple(rec['condition_y'].split('::')); ax=A[kx+(m,)]; ay=A[ky+(m,)]
  # Every source has all 40 windows represented by at least one policy.
  assert np.all(np.isfinite(ax).any(1)) and np.all(np.isfinite(ay).any(1))
  draws=rng.integers(0,40,size=(2000,2,40)); bx=bootmeans(ax,draws[:,0]); by=bootmeans(ay,draws[:,1]); tau=taus(bx,by)
  ci=np.nanquantile(tau,[(1-.95)/2,1-(1-.95)/2]); point=kendalltau(means(ax),means(ay)).statistic
  ranks.append({'metric':m,'x':rec['condition_x'],'y':rec['condition_y'],'point':point,'point_match':close(point,rec['kendall_tau']),'saved':rec['kendall_tau_ci'],'reproduced':ci.tolist(),'match':close(ci,rec['kendall_tau_ci']),'undefined_draws':int(np.isnan(tau).sum())})
print('ranking intervals',sum(x['match'] for x in ranks),len(ranks),flush=True)
# Reproduce all saved CI-bearing primary reversals; no intervening random calls.
reversals=[]
def bootdiff(a,pa,pb,rng):
 d=a[:,P.index(pa)]-a[:,P.index(pb)];d=d[np.isfinite(d)]; b=d[rng.integers(0,len(d),(2000,len(d)))].mean(1); return np.quantile(b,[(1-.95)/2,1-(1-.95)/2]).tolist(),float(min(1,2*min(np.mean(b<=0),np.mean(b>=0))))
for rec in rv['records'][primary]:
 if rec['ci_x'] is None:continue
 out={k:rec[k] for k in ['policy_a','policy_b','condition_x','condition_y']}
 for side in ['x','y']:
  a=A[tuple(rec['condition_'+side].split('::'))+(primary,)]; ci,p=bootdiff(a,rec['policy_a'],rec['policy_b'],rng)
  out[side]={'saved_ci':rec['ci_'+side],'ci':ci,'p':p,'saved_p':rec['p_'+side],'match':close(ci,rec['ci_'+side]) and close(p,rec['p_'+side])}
 reversals.append(out)
# Friedman independently from rank sums + tie correction; store exact input matrices.
fried=[]; matrices=[]
for rec in rc['omnibus_friedman']:
 m,r=rec['metric'],rec['load_region']; pairs=sorted((w,s,i) for s in S for i,w in enumerate(W[s,r])); a=np.array([A[s,r,m][i] for w,s,i in pairs]); keep=np.isfinite(a).all(0); a=a[:,keep]; n,k=a.shape
 ranks_f=rankdata(a,axis=1); tie=sum(sum(v**3-v for v in C.Counter(row).values()) for row in a); correction=1-tie/(n*(k**3-k)); q=(12/(n*k*(k+1))*np.sum(ranks_f.sum(0)**2)-3*n*(k+1))/correction; p=chi2.sf(q,k-1)
 omitted=[pol for pol,ok in zip(P,keep) if not ok]; native=friedmanchisquare(*a.T)
 fried.append({'metric':m,'region':r,'n':n,'k':k,'excluded':omitted,'statistic':q,'p':p,'saved':rec,'match':close(q,rec['statistic']) and close(p,rec['p_value']) and n==rec['n_blocks'] and k==rec['n_treatments'] and omitted==rec['excluded_policies'],'scipy_match':close(q,native.statistic)})
 matrices.append({'metric':m,'region':r,'windows':[x[0] for x in pairs],'policies':np.array(P)[keep].tolist(),'values':a.tolist()})
write('friedman-inputs.json',matrices)
# Cross-metric point estimates: exact maximizing sets, common-all-policy windows per metric pair.
cm=[]
for rec in cr:
 s,r,ma,mb=[rec[k] for k in ['source','region','metric_a','metric_b']]; a=A[s,r,ma]*(-1 if ma in lower else 1); b=A[s,r,mb]*(-1 if mb in lower else 1); va,vb=means(a),means(b)
 sa={P[i] for i in np.flatnonzero(va==max(va))}; sb={P[i] for i in np.flatnonzero(vb==max(vb))}; common=np.isfinite(a).all(1)&np.isfinite(b).all(1); vma,vmb=means(a[common]),means(b[common]); ta=kendalltau(va,vb).statistic; tm=kendalltau(vma,vmb).statistic
 cm.append({'source':s,'region':r,'a':ma,'b':mb,'historical_tau':ta,'point_match':close(ta,rec['kendall_tau_b']),'id_agreement':min(sa)==min(sb),'id_match':int(min(sa)==min(sb))==rec['top1_agreement'],'max_a':sorted(sa),'max_b':sorted(sb),'intersection':bool(sa&sb),'set_equal':sa==sb,'jaccard':len(sa&sb)/len(sa|sb),'common_windows':int(common.sum()),'matched_tau':tm,'matched_id_agreement':P[np.argmax(vma)]==P[np.argmax(vmb)]})
# Pairwise matched-support effects, historic means vs intersection means, all cross-metric records.
matched=[]
for rec in dr:
 ds=[]; ms=[]; ns=[]; changed=False
 for suffix in ['a','b']:
  m=rec['metric_'+suffix]; a=A[rec['source'],rec['region'],m]*(-1 if m in lower else 1); x,y=P.index(rec['policy_x']),P.index(rec['policy_y']); ok=np.isfinite(a[:,x])&np.isfinite(a[:,y]); vx,vy=a[ok,x].mean(),a[ok,y].mean(); d=vx-vy; loser=vy if d>0 else vx; margin=0. if d==0 else (abs(d)/abs(loser) if loser else None); ds.append(float(d));ms.append(margin);ns.append(int(ok.sum())); changed |= not close(d,rec['diff_'+suffix])
 if changed:
  gate=bool(ds[0]*ds[1]<0 and all(m is not None and m>.1 for m in ms)); ciok=all(rec['ci_'+x] is not None and rec['ci_'+x][0]*rec['ci_'+x][1]>0 for x in ['a','b']); aligned=ciok and all(np.sign(ds[i])==np.sign(rec['ci_'+x][0]) for i,x in enumerate(['a','b']))
  matched.append({'source':rec['source'],'region':rec['region'],'a':rec['metric_a'],'b':rec['metric_b'],'x':rec['policy_x'],'y':rec['policy_y'],'saved_class':rec['classification'],'saved_diff':[rec['diff_a'],rec['diff_b']],'matched_diff':ds,'matched_margin':ms,'n':ns,'matched_practical_gate':gate,'ci_signs_aligned':bool(aligned)})
# Arithmetic multiplicity sensitivity. Padding excluded comparisons with 1 is bookkeeping, not calibrated new p-values.
def mult(records,kind):
 fam=C.defaultdict(list)
 for x in records:fam[(x['load_region'],) if kind=='primary' else (x['source'],x['region'],x['metric_a'],x['metric_b'])].append(x)
 counts=C.Counter(); details=[]
 for key,rr in fam.items():
  ab=['x','y'] if kind=='primary' else ['a','b']; tested=[x for x in rr if all(x['p_'+k] is not None for k in ab)]; ps=[max(x['p_'+k] for k in ab) for x in tested]; plus=[max(min(1,(2000*x['p_'+k]+2)/2001) for k in ab) for x in tested]; flags=bh(ps); counts['families']+=1;counts['tested']+=len(ps);counts['zero_iut']+=sum(p==0 for p in ps);counts['flag_mismatches']+=sum(bool(flag and 'SUPPORTED_PRACTICAL' in x['classification'])!=x['supported_after_fdr'] for x,flag in zip(tested,flags))
  for name,vals,full,by in [('saved_screened',ps,False,False),('full_family',ps,True,False),('plus_one_full',plus,True,False),('plus_one_full_BY',plus,True,True)]:
   ff=bh(vals+([1.]*(len(rr)-len(vals)) if full else []),by)[:len(tested)]; counts[name]+=sum(bool(f and 'SUPPORTED_PRACTICAL' in x['classification']) for f,x in zip(ff,tested))
  details.append({'family':key,'total':len(rr),'tested':len(tested),'zero':sum(p==0 for p in ps)})
 return dict(counts),details
multiplicity={};families={}
for name,rr in [('primary',rv['records'][primary]),('cross_metric',dr)]:multiplicity[name],families[name]=mult(rr,name)
# Six pre-specified cross-metric correlation CIs and all saved cross-metric difference CIs.
cm_intervals=[]
for rec in cr:
 if rec['metric_a']!=primary or rec['metric_b']!='mean_latency' or rec['region'] not in ['LOW','HIGH_PRESSURE']:continue
 s,r,ma,mb=[rec[k] for k in ['source','region','metric_a','metric_b']]; order=np.argsort(W[s,r]); a=A[s,r,ma][order]; b=-A[s,r,mb][order]; seed=zlib.crc32('|'.join([s,r,ma,mb]).encode()) & 0xffffffff; gen=np.random.default_rng(seed); ids=gen.integers(0,40,(2000,40)); tt=taus(bootmeans(a,ids),bootmeans(b,ids)); ci=np.nanquantile(tt,[(1-.95)/2,1-(1-.95)/2]); cm_intervals.append({'source':s,'region':r,'a':ma,'b':mb,'seed':seed,'saved':rec['kendall_ci'],'ci':ci.tolist(),'match':close(ci,rec['kendall_ci'])})
cm_diffs=[]
for rec in dr:
 if rec['ci_a'] is None:continue
 entry={k:rec[k] for k in ['source','region','metric_a','metric_b','policy_x','policy_y']}
 for side in ['a','b']:
  seed=zlib.crc32('|'.join([rec[k] for k in ['source','region','metric_a','metric_b','policy_x','policy_y']]+[side]).encode()) & 0xffffffff; m=rec['metric_'+side]; a=A[rec['source'],rec['region'],m]*(-1 if m in lower else 1); ci,p=bootdiff(a,rec['policy_x'],rec['policy_y'],np.random.default_rng(seed)); entry[side]={'seed':seed,'ci':ci,'p':p,'match':close(ci,rec['ci_'+side]) and close(p,rec['p_'+side])}
 cm_diffs.append(entry)
write('cross-metric-intervals.json',cm_intervals);write('cross-metric-difference-intervals.json',cm_diffs)
# Nonoverlapping chronological blocks of 5 selected windows (8 groups/source), stress test only.
meta_by={x['window_id']:x for x in meta}; write('window-metadata-fields.json',meta[0])
# Source-file valid-row order; not equal-spaced wall clock, no calibrated dependence model.
chronology={s:sorted(W[s,R[0]],key=lambda w:meta_by[w]['start_index_in_valid_rows']) for s in S}
block=[]
for ix,rec in enumerate(rv['records'][primary]):
 if rec['ci_x'] is None:continue
 rr={'key':[rec['condition_x'],rec['condition_y'],rec['policy_a'],rec['policy_b']]}; excludes=[]
 for side in ['x','y']:
  s,r=rec['condition_'+side].split('::'); a=A[s,r,primary]; ids=[W[s,r].index(w) for w in chronology[s]]; d=a[ids,P.index(rec['policy_a'])]-a[ids,P.index(rec['policy_b'])]; groups=d.reshape(8,5).mean(1); seed=20261022+ix*2+(side=='y'); gen=np.random.default_rng(seed); vals=groups[gen.integers(0,8,(2000,8))].mean(1); ci=np.quantile(vals,[.025,.975]);rr[side]={'ci':ci.tolist(),'seed':seed}; excludes.append(ci[0]*ci[1]>0)
 rr['both_exclude_zero']=bool(all(excludes));block.append(rr)
# Within-region summary and absolute ANWG values (descriptive M2, no new outcomes).
within=[]
for s in S:
 for r in R:
  v=means(A[s,r,primary]); within.append({'source':s,'region':r,'means':dict(zip(P,v.tolist())),'best':max(v),'worst':min(v),'fifo':v[P.index('fifo')],'top_set':[P[i] for i in np.flatnonzero(v==max(v))],'zero_completion':int(np.sum(A[s,r,'completion_fraction']==0))})
# Independently validate vector tau on all finite point vectors using SciPy.
assert all(close(taus(means(A[s,r,primary])[None],means(A[t,r,primary])[None])[0],kendalltau(means(A[s,r,primary]),means(A[t,r,primary])).statistic) for s,t in I.combinations(S,2) for r in R)
summary={'status':'POST_HOC_AUDIT_NOT_NEW_EXPERIMENT','environment':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__},'cross_metric_intervals':{'correlations_tested':len(cm_intervals),'correlations_matched':sum(x['match'] for x in cm_intervals),'differences_tested':2*len(cm_diffs),'differences_matched':sum(x[k]['match'] for x in cm_diffs for k in ['a','b'])},'ranking_intervals':{'tested':len(ranks),'matched':sum(x['match'] for x in ranks),'primary_matched':sum(x['match'] for x in ranks if x['metric']==primary)},'primary_reversal_intervals':{'tested':len(reversals)*2,'matched':sum(x[k]['match'] for x in reversals for k in ['x','y'])},'friedman':{'tested':len(fried),'matched':sum(x['match'] for x in fried),'treatment_counts':dict(C.Counter(x['k'] for x in fried))},'cross_metric':{'n':len(cm),'point_matches':sum(x['point_match'] and x['id_match'] for x in cm),'id_agreement':sum(x['id_agreement'] for x in cm),'set_intersection':sum(x['intersection'] for x in cm),'set_equality':sum(x['set_equal'] for x in cm),'both_unique':sum(len(x['max_a'])==len(x['max_b'])==1 for x in cm),'mean_jaccard':np.mean([x['jaccard'] for x in cm]),'matched_id_agreement':sum(x['matched_id_agreement'] for x in cm),'matched_median_tau':np.median([x['matched_tau'] for x in cm]),'matched_negative_tau':sum(x['matched_tau']<0 for x in cm),'matched_tau_changes':sum(not close(x['matched_tau'],x['historical_tau']) for x in cm),'common_windows_min':min(x['common_windows'] for x in cm)},'matched_pairwise':{'changed_records':len(matched),'saved_supported_affected':sum(x['saved_class']=='SUPPORTED_PRACTICAL_DISAGREEMENT' for x in matched),'saved_supported_losing_practical_gate':sum(x['saved_class']=='SUPPORTED_PRACTICAL_DISAGREEMENT' and not x['matched_practical_gate'] for x in matched),'saved_supported_ci_sign_misaligned':sum(x['saved_class']=='SUPPORTED_PRACTICAL_DISAGREEMENT' and not x['ci_signs_aligned'] for x in matched)},'multiplicity':multiplicity,'chronological_block_sensitivity':{'records':len(block),'both_exclude_zero':sum(x['both_exclude_zero'] for x in block),'block_length':5,'seed_base':20261022},'inputs':inputs}
for n,x in [('ranking-intervals.json',ranks),('primary-reversal-intervals.json',reversals),('friedman-audit.json',fried),('cross-metric-sets-and-matched.json',cm),('matched-pairwise-changes.json',matched),('multiplicity-families.json',families),('chronological-block-sensitivity.json',block),('within-region.json',within),('statistical-audit.json',summary)]:write(n,x)
print(json.dumps({k:v for k,v in summary.items() if k!='inputs'},indent=2,default=lambda x:x.item()),flush=True)

assert all(x["match"] for x in ranks) and all(x["match"] for x in fried)
assert all(x[k]["match"] for x in reversals for k in ["x","y"])
assert all(x[k]["match"] for x in cm_diffs for k in ["a","b"])
assert all(x["match"] for x in cm_intervals)
assert all(x["point_match"] and x["id_match"] for x in cm)
