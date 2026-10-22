#!/usr/bin/env python3
"""Render M3 exclusively from hash-verified saved summaries; no experiment imports."""
import collections,csv,gzip,hashlib,json,math,pathlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[1]

def read(name):
 b=gzip.decompress((ROOT/'evidence/inputs'/f'{name}.gz').read_bytes())
 assert hashlib.sha256(b).hexdigest()==HASHES[name]['sha256_uncompressed'],name
 return json.loads(b)
HASHES=json.loads((ROOT/'evidence/input-hashes.json').read_text())
for name,rec in HASHES.items():
 assert hashlib.sha256((ROOT/'evidence/inputs'/f'{name}.gz').read_bytes()).hexdigest()==rec['sha256_stored']
 read(name)
R=read('c01-absolute_metrics.json'); ranks=read('c01-rankings.json'); rev=read('c01-reversals.json')
agg=read('c01-window_aggregates.json'); sm=read('c01-source_mean_rankings.json')
S=['azure_llm_2024','bailian_qwen','burstgpt']; SN=['Azure 2024','Bailian/Qwen','BurstGPT']
K=['kv131072','kv262144']; P=['chunked_fcfs_c01','decode_first_c01','whole_fcfs_c01','slo_gated_c01']
PN=['Chunked / Decode','Chunked / Decode','Whole-FCFS','SLO-gated']
L=['LOW','PRE_KNEE','KNEE','POST_KNEE','OVERLOAD','HIGH_PRESSURE']; LS=['L','Pre','K','Post','O','H']
M=['arrival_normalized_weighted_goodput','mean_latency','p95_latency','mean_ttft','token_throughput']
D={(r['window'],r['region'],r['profile'],r['policy']):r for r in R}
assert len(R)==len(D)==5760
assert all(r['metrics']['num_completed']==r['metrics']['num_total']==200 for r in R)
assert all(r['metrics']['num_unfinished']==0 for r in R)
assert sum(r['reused'] for r in R)==144
assert all(D[w,l,k,P[0]]['metrics']==D[w,l,k,P[1]]['metrics'] for w,l,k,p in D if p==P[0])
mean=lambda xs:math.fsum(xs)/len(xs)
G={(s,k,p):{m:mean([r['metrics'][m] for r in R if (r['source'],r['profile'],r['policy'])==(s,k,p)]) for m in M} for s in S for k in K for p in P}
def table(name,headers,rows,spec):
 text='\\begin{tabular}{'+spec+'}\n\\toprule\n'+' & '.join(headers)+' \\\\\n\\midrule\n'
 text+=''.join(' & '.join(map(str,row))+' \\\\\n' for row in rows)+'\\bottomrule\n\\end{tabular}\n'
 (ROOT/'tables'/f'{name}.tex').write_text(text)
def csvout(name,rows):
 with (ROOT/'supplement'/f'{name}.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
rows=[]
for s,sn in zip(S,SN):
 for k in K:
  for p in [P[0],P[2],P[3]]:
   g=G[s,k,p];rows.append([sn if p==P[0] else '',str(int(k[2:])//32768) if p==P[0] else '',PN[P.index(p)],f'{g[M[0]]:.4f}',f'{g[M[1]]:.4f}',f'{g[M[2]]:.4f}',f'{g[M[4]]:.1f}'])
table('absolute',['Source','Slots','Adaptation','ANWG','Mean (s)','p95 (s)','Tokens/s'],rows,'ll l rrrr')
cr=[]
for r in R:cr.append({**{k:r[k] for k in ['source','window','region','profile','policy','load_factor','reused','requests_sha256','result_sha256','journal_sha256']},**r['metrics']})
csvout('c01-all-cells',cr)
csvout('c01-source-capacity-means',[dict(source=s,profile=k,policy=p,**v) for (s,k,p),v in G.items()])
csvout('c01-window-aggregates',agg)
rows=[];axes=['window','source','load','kv','metric','source_mean']
labels=['Within-source windows','Cross-source windows','Inherited settings','KV capacities','Metric pairs','Source means']
revcounts={}
for axis,label in zip(axes,labels):
 g=[x for x in rev if x['axis']==axis];t={key:sum(x[key] for x in g) for key in ['reversals','eligible','total','unestimable']};revcounts[axis]=t
 rows.append([label]+[f'{t[key]:,}' for key in ['reversals','eligible','total','unestimable']])
table('reversals',['Comparison axis','Reversals','Eligible','Total','Unestimable'],rows,'lrrrr')
assert revcounts['source_mean']==dict(reversals=0,eligible=2376,total=2376,unestimable=0)
assert revcounts['window']['reversals']==34394 and revcounts['metric']['reversals']==11795
csvout('c01-reversal-groups',[{**x,'labels':'|'.join(x['labels'])} for x in rev])
metrics=list(dict.fromkeys(r['metric'] for r in ranks));ties={};tr=[]
for m in metrics:
 g=[x for x in ranks if x['metric']==m];ties[m]=dict(total=len(g),tied=sum(len(x['top'])>1 for x in g),slo_unique=sum(x['top']==[P[3]] for x in g),near_changed=sum(x['top']!=x['sensitivity_top'] for x in g),missing=sum(bool(x['missing']) for x in g))
 tr.append({'metric':m,**ties[m]})
csvout('c01-ties',tr)
table('ties',['Endpoint','Exact top tie','SLO unique top','Near-tie change'],[[label]+[f'{ties[m][key]:,}' for key in ['tied','slo_unique','near_changed']] for m,label in [('arrival_normalized_weighted_goodput','ANWG'),('mean_latency','Mean latency'),('p95_latency','p95 latency'),('token_throughput','Token throughput'),('completion_fraction','Completion'),('mean_tpot','Mean TPOT'),('p95_tpot','p95 TPOT')]],'lrrr')
# Journal-ready vector figures; line style and marker distinguish capacity and policy.
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'ps.fonttype':42,'axes.labelsize':8,'legend.fontsize':8,'xtick.labelsize':8,'ytick.labelsize':8})
colors={P[0]:'#0072B2',P[2]:'#737373',P[3]:'#D55E00'}
fig,axs=plt.subplots(4,3,figsize=(6.2,7.2),sharex=True,layout='constrained')
for j,(s,sn) in enumerate(zip(S,SN)):
 for i,(m,yl) in enumerate([('mean_latency','Mean latency (s)'),('p95_latency','Mean window p95 (s)'),('token_throughput','Output tokens / sim. s'),('arrival_normalized_weighted_goodput','ANWG')]):
  ax=axs[i,j]
  for p in [P[0],P[2],P[3]]:
   for ki,k in enumerate(K):
    vals=[mean([r['metrics'][m] for r in R if (r['source'],r['region'],r['profile'],r['policy'])==(s,l,k,p)]) for l in L]
    ax.plot(range(6),vals,color=colors[p],ls='-' if ki==0 else '--',marker='o' if ki==0 else 's',markersize=2.5,lw=1,label=PN[P.index(p)]+f' ({4+4*ki} slots)')
  ax.grid(axis='y',alpha=.2);ax.set_ylim(bottom=0)
  if j==0:ax.set_ylabel(yl)
  if i==0:ax.set_title(sn,fontweight='bold')
  ax.set_xticks(range(6),LS)
  if i==3:ax.set_xlabel('Inherited arrival/deadline setting')
handles,labs=axs[0,0].get_legend_handles_labels();fig.legend(handles,labs,loc='outside lower center',ncol=3,frameon=False)
fig.savefig(ROOT/'figures/absolute.pdf',metadata={'CreationDate':None});plt.close(fig)
# All 40 per-source windows: average six matched setting deltas within each window.
fig,axs=plt.subplots(2,3,figsize=(6.2,4.7),layout='constrained');diffrows=[]
for ki,k in enumerate(K):
 for mi,(m,label) in enumerate([('mean_latency','Mean latency difference (s)'),('p95_latency','Window p95 difference (s)'),('token_throughput','Throughput difference\n(tokens / simulated s)')]):
  ax=axs[ki,mi]
  for s,sn,c in zip(S,SN,['#0072B2','#009E73','#CC79A7']):
   vals=[]
   for w in sorted({r['window'] for r in R if r['source']==s}):
    delta=mean([D[w,l,k,P[3]]['metrics'][m]-D[w,l,k,P[0]]['metrics'][m] for l in L]);vals.append(delta)
    diffrows.append(dict(source=s,window=w,profile=k,metric=m,slo_minus_chunked=delta))
   ax.step(sorted(vals),np.arange(1,41)/40,where='post',c=c,lw=1.3,label=sn)
  ax.axvline(0,color='black',ls=':',lw=.8);ax.set_ylim(0,1.03);ax.grid(alpha=.15);ax.set_xlabel(label)
  ax.set_title(f'{4+ki*4} slots\n'+('Lower favors SLO' if mi<2 else 'Higher favors SLO'),fontsize=8)
  if mi==0:ax.set_ylabel('Fraction of 40 windows')
h,l=axs[0,0].get_legend_handles_labels();fig.legend(h,l,loc='outside lower center',ncol=3,frameon=False)
fig.savefig(ROOT/'figures/matched.pdf',metadata={'CreationDate':None});plt.close(fig);csvout('c01-matched-window-differences',diffrows)
# Chronological diagnostic retains all four blocks, settings and capacities.
fig,axs=plt.subplots(1,3,figsize=(6.2,2.65),sharey=True,layout='constrained')
blocks=[x for x in agg if x['scope']=='block'];print('block scope groups',sorted({str(x['group']) for x in blocks}))
if blocks:
 for ax,s,sn in zip(axs,S,SN):
  for ki,k in enumerate(K):
   for li,l in enumerate(L):
    sub={ (str(x['group']),x['policy']):x['mean'] for x in blocks if x['source']==s and x['profile']==k and x['region']==l and x['metric']==M[0]}
    keys=sorted({key[0] for key in sub});vals=[sub[b,P[3]]-sub[b,P[0]] for b in keys]
    ax.plot(range(1,5),vals,color=plt.get_cmap('viridis')(li/5),ls='-' if ki==0 else '--',lw=.9,marker='o' if ki==0 else 's',markersize=2)
  ax.axhline(0,c='black',lw=.7);ax.set_title(sn);ax.set_xticks(range(1,5));ax.set_xlabel('Ten-window block');ax.grid(alpha=.15)
 axs[0].set_ylabel('SLO − Chunked ANWG')
 # Colorbar communicates ordered inherited labels without twelve legend entries.
 cb=fig.colorbar(plt.cm.ScalarMappable(norm=plt.Normalize(0,5),cmap='viridis'),ax=axs,shrink=.85,pad=.02);cb.set_ticks(range(6),labels=LS);cb.ax.tick_params(labelsize=7)
 fig.savefig(ROOT/'figures/chronology.pdf',metadata={'CreationDate':None})
plt.close(fig)
# Full 18 × (8+17) × 16 endpoint table, preserving family and availability.
cp=read('stat-checkpoint.json');launch=read('stat-launch.json');stat=[];final={};scenarios=[];screenrows=[]
short={'calibration_concern':'C','inconclusive':'I','empirical_compatibility_with_tolerance':'E','outside_domain_abstention':'A'}
methods=launch['original_launch']['methods'];print('original methods',methods)
for sid in range(18):
 n=cp['scenarios'][str(sid)]['n'];x=read(f'stat-look-s{sid:02d}-n{n:05d}.json');final[sid]=x
 spec=launch['original_launch']['scenarios'][sid];name=spec['name'];scenarios.append(dict(sid=sid,name=name,n=n,stop=cp['scenarios'][str(sid)]['status']))
 for fam in ['original_prespecified','expanded_postdiagnosis']:
  for method,v in x[fam]['methods'].items():
   for endpoint,ev in v['endpoints'].items():stat.append(dict(scenario_id=sid,scenario=name,studies=n,family=fam,method=method,endpoint=endpoint,**ev))
 screenrows.append([str(sid),name.replace('_','\\_'),f'{n:,}','P' if sid in [0,1,2,3,16,17] else 'M']+[x['original_prespecified']['methods'][m]['calibration_screen'] for m in methods])
print('screen values',sorted({v for row in screenrows for v in row[4:]}))
# Canonical labels in frozen outputs are uppercase; map by content.
def screen(v):
 if 'CONCERN' in v.upper():return 'C'
 if 'INCONCLUSIVE' in v.upper():return 'I'
 if 'ABST' in v.upper():return 'A'
 if 'COMPAT' in v.upper():return 'E'
 raise ValueError(v)
for row in screenrows:row[4:]=[screen(v) for v in row[4:]]
table('stat-scenarios',['ID','Scenario','Studies','Stop','H-S','H-F','H-BY','t','c-t','O','G','Hf'],screenrows,'rlrrcccccccc')
csvout('stat01-all-endpoints',stat);csvout('stat01-stopping',scenarios)
rows=[]
for sid,label in [(0,'IID equal null'),(8,'Independent-block null'),(10,'AR(0.7) null')]:
 es=final[sid]['expanded_postdiagnosis']['methods']['legacy_source_screened_BH']['endpoints'];f=es['fdp_practical'];c=es['ci_coverage']
 rows.append([label,f"{f['mean']:.5f}",f"[{f['lower']:.5f}, {f['upper']:.5f}]",f"{c['mean']:.5f}",f"[{c['lower']:.5f}, {c['upper']:.5f}]"])
table('calibration',['Scenario','FDR','MC bounds','Coverage','MC bounds'],rows,'lrrrr')
# Exact narrative anchors used by validation and manual text review.
changes=[]
for s in S:
 for k in K:
  a,b=G[s,k,P[3]],G[s,k,P[0]]
  changes.append(dict(source=s,profile=k,**{m:100*(a[m]/b[m]-1) for m in M}))
assert all(x['mean_latency']<0 and x['token_throughput']<0 for x in changes)
assert all(x['p95_latency']>0 for x in changes if x['source']=='burstgpt')
checks=dict(status='PASS',input_files=len(HASHES),cells=len(R),matched_equivalent=1440,all_complete=True,request_executions=5760*200,reversal_counts=revcounts,ties=ties,aggregate_percent_changes=changes,stat_studies=sum(x['n'] for x in scenarios),stat_endpoint_rows=len(stat),screen_counts=dict(collections.Counter(v for row in screenrows for v in row[4:])))
assert checks['stat_studies']==134000 and len(stat)==7200
assert checks['screen_counts']==dict(C=45,I=74,E=9,A=16)
(ROOT/'evidence/numerical-checks.json').write_text(json.dumps(checks,indent=2)+'\n')
print('PASS: pinned inputs, complete coverage, equivalence, descriptive figures/tables, 7200 STAT endpoints')
