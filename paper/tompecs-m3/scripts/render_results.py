#!/usr/bin/env python3
"""Render saved, hash-verified campaign reports. No simulation or resampling."""
import csv,gzip,hashlib,itertools,json,math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
R=Path(__file__).resolve().parents[1]; D=R/'evidence/data'
manifest=json.loads((R/'evidence/source-manifest.json').read_text())
for name,record in manifest.items():
 b=(D/name).read_bytes(); assert hashlib.sha256(b).hexdigest()==record['stored_sha256']
 assert hashlib.sha256(gzip.decompress(b)).hexdigest()==record['uncompressed_sha256']
def read(name):return json.loads(gzip.decompress((D/name).read_bytes()))
a=read('c01-absolute_metrics.json.gz'); ranks=read('c01-rankings.json.gz'); rv=read('c01-reversals.json.gz'); im=read('c01-input_manifest.json.gz')
S=['azure_llm_2024','bailian_qwen','burstgpt']; SL=['Azure 2024','Bailian/Qwen','BurstGPT']; K=['kv131072','kv262144']; P=['whole_fcfs_c01','chunked_fcfs_c01','decode_first_c01','slo_gated_c01']; PL=['Whole-FCFS','Chunked-FCFS','Decode-first','SLO-gated']; L=['LOW','PRE_KNEE','KNEE','POST_KNEE','OVERLOAD','HIGH_PRESSURE']
M=['arrival_normalized_weighted_goodput','completion_fraction','token_throughput','emitted_token_throughput','request_throughput','mean_latency','p95_latency','mean_ttft','p95_ttft','mean_tpot','p95_tpot']; ML=['ANWG','Completion','Completed-token throughput','Emitted-token throughput','Request throughput','Mean latency','p95 latency','Mean TTFT','p95 TTFT','Mean TPOT','p95 TPOT']
rows={(r['window'],r['region'],r['profile'],r['policy']):r for r in a}
assert len(rows)==len(a)==5760 and sum(r['reused'] for r in a)==144
assert all(r['metrics']['num_completed']==200 and r['metrics']['num_unfinished']==0 for r in a)
windows={s:sorted({r['window'] for r in a if r['source']==s}) for s in S}
assert all(len(ws)==40 for ws in windows.values())
assert set(rows)=={(w,l,k,p) for s in S for w in windows[s] for l in L for k in K for p in P}
assert all(rows[w,l,k,P[1]]['metrics']==rows[w,l,k,P[2]]['metrics'] for s in S for w in windows[s] for l in L for k in K)
def mean(xs):return math.fsum(xs)/len(xs)
def val(s,k,p,m,l=None):return mean([r['metrics'][m] for r in a if r['source']==s and r['profile']==k and r['policy']==p and (l is None or r['region']==l)])
def write(name,lines):
 frames={
 'absolute-rows.tex':('lllr r r r',r'Source & R & Adaptation & ANWG & Mean & p95 & Throughput'),
 'reversal-rows.tex':('lrrrr',r'Axis & Reversals & Eligible & Unestimable & Total'),
 'tie-rows.tex':('lrrr',r'Endpoint & Tied exact top & Sensitivity changes & Missing'),
 'scenario-rows.tex':('lrrcccccccc',r'Scenario & Studies & Stop & HS & HF & HB & T & CT & O & G & B')}
 cols,head=frames[name]
 text=r'\begin{tabular}{'+cols+r'}\toprule'+'\n'+head+r' \\ \midrule'+'\n'+'\n'.join(lines)+'\n'+r'\bottomrule\end{tabular}'+'\n'
 (R/'tables'/name).write_text(text)
def csvout(name,records):
 with (R/'tables'/name).open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(records[0]),lineterminator='\n');w.writeheader();w.writerows(records)
# Archive complete per-cell metrics as readable, identity-linked supplement.
flat=[{k:v for k,v in r.items() if k!='metrics'}|r['metrics'] for r in a];csvout('all-cell-metrics.csv',flat)
agg=[];t=[];latg=[];tputloss=[]
for s,sl in zip(S,SL):
 for k in K:
  for p,pl in zip(P,PL):
   z={m:val(s,k,p,m) for m in M};agg.append(dict(source=s,capacity=k,policy=p,**z))
   if p==P[2]:continue
   label='Chunked / Decode' if p==P[1] else pl
   t.append(f'{sl} & {int(k[2:])//32768} & {label} & {z[M[0]]:.4f} & {z["mean_latency"]:.4f} & {z["p95_latency"]:.4f} & {z["token_throughput"]:.1f} \\\\')
  latg.append(100*(1-val(s,k,P[3],'mean_latency')/val(s,k,P[1],'mean_latency')))
  tputloss.append(100*(1-val(s,k,P[3],'token_throughput')/val(s,k,P[1],'token_throughput')))
write('absolute-rows.tex',t);csvout('source-capacity-means.csv',agg)
axes=['window','source','load','kv','metric','source_mean']; labels=['Within-source windows','Cross-source windows','Inherited settings','KV capacities','Metric choice','Source means']
revs=[]
for axis,label in zip(axes,labels):
 subset=[r for r in rv if r['axis']==axis];z={key:sum(x[key] for x in subset) for key in ['reversals','eligible','total','unestimable']};assert z['eligible']+z['unestimable']==z['total'];revs.append(dict(axis=axis,**z))
write('reversal-rows.tex',[f'{lab} & {r["reversals"]:,} & {r["eligible"]:,} & {r["unestimable"]:,} & {r["total"]:,} \\\\' for r,lab in zip(revs,labels)]);csvout('reversal-counts.csv',revs)
ties=[]
for m,ml in zip(M,ML):
 rr=[r for r in ranks if r['metric']==m];assert len(rr)==1440
 z=dict(metric=m,conditions=1440,tied=sum(len(r['top'])>1 for r in rr),sensitivity_changes=sum(r['top']!=r['sensitivity_top'] for r in rr),missing=sum(r['ranks'] is None for r in rr));ties.append(z)
write('tie-rows.tex',[f'{ml} & {z["tied"]:,} & {z["sensitivity_changes"]:,} & {z["missing"]} \\\\' for z,ml in zip(ties,ML)]);csvout('tie-counts.csv',ties)
# Vector plots. Line styles identify capacity; palette also has shape redundancy.
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.labelsize':11,'axes.titlesize':12,'legend.fontsize':10,'pdf.fonttype':42,'ps.fonttype':42,'axes.spines.top':False,'axes.spines.right':False,'savefig.bbox':'tight'})
colors=['#0072B2','#555555','#009E73','#D55E00']; pm=[0,1,3]
fig,ax=plt.subplots(4,3,figsize=(8.1,7.5),sharex=True)
for i,(m,yl) in enumerate([('mean_latency','Mean latency (s)'),('p95_latency','Mean window p95 (s)'),('token_throughput','Output tokens / sim. s'),(M[0],'ANWG')]):
 for j,s in enumerate(S):
  for pi in pm:
   for ki,k in enumerate(K):
    ax[i,j].plot(range(6),[val(s,k,P[pi],m,l) for l in L],color=colors[pi],linestyle=['-','--'][ki],marker=['o','s','^'][pm.index(pi)],markersize=3,linewidth=1.2,label=f'{PL[pi] if pi!=1 else "Chunked = Decode"}, {4*(ki+1)} residents')
  ax[i,j].grid(alpha=.18); ax[i,j].set_xticks(range(6),['L','Pre','K','Post','O','H'])
  if j==0:ax[i,j].set_ylabel(yl)
  if i==0:ax[i,j].set_title(SL[j])
  if i==3:ax[i,j].set_xlabel('Inherited setting')
fig.legend(*ax[0,0].get_legend_handles_labels(),loc='upper center',bbox_to_anchor=(.5,1.07),ncol=3,frameon=False)
fig.tight_layout();fig.savefig(R/'figures/absolute.pdf',metadata={'CreationDate':None,'ModDate':None});plt.close(fig)
# Matched windows: average six matched differences per window, then plot all 40.
fig,ax=plt.subplots(2,3,figsize=(8.1,4.5));matched=[]
for j,s in enumerate(S):
 for ki,k in enumerate(K):
  for w in windows[s]:
   dif={m:mean([rows[w,l,k,P[3]]['metrics'][m]-rows[w,l,k,P[1]]['metrics'][m] for l in L]) for m in ['mean_latency','p95_latency','token_throughput',M[0]]}
   matched.append(dict(source=s,window=w,capacity=k,**dif))
  z=[r for r in matched if r['source']==s and r['capacity']==k]
  for i,m in enumerate(['p95_latency','token_throughput']):
   ax[i,j].scatter([r['mean_latency'] for r in z],[r[m] for r in z],s=17,marker=['o','^'][ki],facecolors=['#0072B2','none'][ki],edgecolors=['#0072B2','#D55E00'][ki],linewidths=.7,alpha=.8,label=f'{4*(ki+1)} residents')
 for i in range(2):
  ax[i,j].axhline(0,color='.4',lw=.7);ax[i,j].axvline(0,color='.4',lw=.7);ax[i,j].grid(alpha=.15);ax[i,j].set_xlabel('Mean-latency difference (s)')
 ax[0,j].set_title(SL[j])
ax[0,0].set_ylabel('Window-p95 difference (s)');ax[1,0].set_ylabel('Throughput difference\n(tokens / simulated s)');ax[0,2].legend(frameon=False)
fig.tight_layout();fig.savefig(R/'figures/matched.pdf',metadata={'CreationDate':None,'ModDate':None});plt.close(fig);csvout('matched-window-differences.csv',matched)
# Chronological block descriptive sensitivity: all six settings and both capacities.
fig,ax=plt.subplots(1,3,figsize=(8.1,2.6));wr={w['window_id']:w for w in im['windows']};chron=[]
for j,s in enumerate(S):
 for ki,k in enumerate(K):
  for li,l in enumerate(L):
   vals=[]
   for b in range(4):
    ws=[w for w in windows[s] if wr[w]['block']==b+1];assert len(ws)==10
    v=mean([rows[w,l,k,P[3]]['metrics'][M[0]]-rows[w,l,k,P[1]]['metrics'][M[0]] for w in ws]);vals.append(v);chron.append(dict(source=s,capacity=k,region=l,block=b+1,difference=v))
   ax[j].plot(range(1,5),vals,color=plt.cm.viridis(li/5),ls=['-','--'][ki],lw=.9,alpha=.8)
 ax[j].axhline(0,color='.4',lw=.7);ax[j].set_title(SL[j]);ax[j].set_xticks(range(1,5));ax[j].set_xlabel('Ten-window block')
ax[0].set_ylabel('ANWG difference\nSLO-gated minus Chunked')
fig.tight_layout();fig.savefig(R/'figures/chronology.pdf',metadata={'CreationDate':None,'ModDate':None});plt.close(fig);csvout('chronological-differences.csv',chron)
# Full original and expanded endpoint summaries, with availability and distinct bounds.
methods=['historical_screened_BH','historical_full_BH','historical_plus1_BY','iid_t_Holm','cluster_t_Holm','oracle_normal_Holm','group_bootstrap_BY','bounded_Hoeffding_Holm']
short=['H-screen','H-full','H+BY','IID-t','Cluster-t','Oracle','Group-BY','Bounded']
scenar=['IID equal null','IID stable null','IID near ties','Exact policy ties','Practical boundary','Small sign reversal','Medium reversal','Large reversal','Block null','Block reversal','AR null','AR reversal','Unequal variances','Mixed distributions','MCAR reversal','Selective null','Bounded, n40','Bounded, n400']
looks=[read(f'stat-final-s{i:02d}.json.gz') for i in range(18)]; assert sum(z['n_studies'] for z in looks)==134000
stat=[];screenrows=[];sym={'CALIBRATION_CONCERN':'C','INCONCLUSIVE':'I','EMPIRICALLY_COMPATIBLE_WITH_TOLERANCE':'E','ABSTAIN_OUTSIDE_DOMAIN':'A'}
for sid,z in enumerate(looks):
 screens=[z['original_prespecified']['methods'][m]['calibration_screen'] for m in methods]
 # Map explicit statuses without inventing a meaning.
 for x in screens:
  if x not in sym:
   if 'COMPATIB' in x:sym[x]='E'
   else:raise ValueError(x)
 screenrows.append(f'{sid}: {scenar[sid]} & {z["n_studies"]:,} & {"P" if z["precision_objective_met"] else "M"} & '+' & '.join(sym[x] for x in screens)+r' \\')
 for family in ['original_prespecified','expanded_postdiagnosis']:
  for m,rec in z[family]['methods'].items():
   for endpoint,stats in rec['endpoints'].items():stat.append(dict(scenario_id=sid,scenario=scenar[sid],studies=z['n_studies'],family=family,method=m,endpoint=endpoint,**stats))
write('scenario-rows.tex',screenrows);csvout('stat-all-endpoints.csv',stat)
fig,ax=plt.subplots(1,3,figsize=(8.1,3.0),sharey=True)
show=['legacy_source_screened_BH',*methods[1:7]];lab=['Legacy source','Full BH','Plus-one BY','IID-t Holm','Cluster-t Holm','Oracle Holm','Group BY']
for j,sid in enumerate([0,8,10]):
 for i,m in enumerate(show):
  z=looks[sid]['expanded_postdiagnosis']['methods'][m]['endpoints']['fdp_practical']
  ax[j].errorbar(z['mean'],6-i,xerr=[[z['mean']-z['lower']],[z['upper']-z['mean']]],fmt='o',markersize=3,color='#0072B2',lw=1,capsize=2)
 ax[j].axvline(.05,color='#D55E00',ls='--',lw=1);ax[j].set_xlim(-.025,1.025);ax[j].set_xlabel('Practical FDR');ax[j].set_title(scenar[sid]);ax[j].grid(axis='x',alpha=.2)
ax[0].set_yticks(range(7),list(reversed(lab)))
fig.tight_layout();fig.savefig(R/'figures/calibration.pdf',metadata={'CreationDate':None,'ModDate':None});plt.close(fig)
# Direct numerical claims used in main text. Rounded display values have no inference role.
claims={'cells':len(a),'reused_cells':sum(r['reused'] for r in a),'new_cells':sum(not r['reused'] for r in a),'matched_equivalent_conditions':1440,'completed_request_executions':sum(r['metrics']['num_completed'] for r in a),'latency_improvement_percent':latg,'throughput_loss_percent':tputloss,'reversals':revs,'ties':ties,'stat_studies':sum(z['n_studies'] for z in looks),'stat_precision_stops':[i for i,z in enumerate(looks) if z['precision_objective_met']]}
(R/'evidence/numerical-claims.json').write_text(json.dumps(claims,indent=2)+'\n')
assert revs[-1]['reversals']==0 and revs[-1]['eligible']==2376
assert [z['reversals'] for z in revs]==[34394,109913,920,350,11795,0]
assert round(min(latg),1)==11.3 and round(max(latg),1)==34.0
assert round(min(tputloss),2)==1.65 and round(max(tputloss),2)==4.01
print('PASS: saved hashes, full Cartesian coverage, reuse, completion, equivalence, headline trade-offs, reversal denominators; rendered 4 vector figures and complete tabular supplements.')
