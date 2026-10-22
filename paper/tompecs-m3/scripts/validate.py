#!/usr/bin/env python3
"""Independent manuscript checks against immutable saved summaries; no experiments."""
import csv,gzip,hashlib,itertools,json,math,re,subprocess
from collections import Counter,defaultdict
from pathlib import Path
import pymupdf
R=Path(__file__).resolve().parents[1];repo=R.parents[1]
def saved(n):return json.loads(gzip.decompress((R/'evidence/data'/n).read_bytes()))
a=saved('c01-absolute_metrics.json.gz');rk=saved('c01-rankings.json.gz');sm=saved('c01-source_mean_rankings.json.gz')
manifest=json.loads((R/'evidence/source-manifest.json').read_text())
for n,z in manifest.items():
 b=(R/'evidence/data'/n).read_bytes();assert hashlib.sha256(b).hexdigest()==z['stored_sha256'];assert hashlib.sha256(gzip.decompress(b)).hexdigest()==z['uncompressed_sha256']
checks={}
def claim(name,ok,detail):
 assert ok,name
 checks[name]=detail
claim('complete_design',len(a)==5760 and len({(x['window'],x['region'],x['profile'],x['policy']) for x in a})==5760,'5760 distinct cells; all planned sources/settings/policies/capacities checked by renderer')
claim('reuse',sum(x['reused'] for x in a)==144,'144 reused; 5616 new')
claim('completion',all(x['metrics']['completion_fraction']==1 and x['metrics']['num_completed']==200 and x['metrics']['num_unfinished']==0 for x in a),'1152000 executions; no censoring')
claim('finite_metrics',all(isinstance(v,(int,float)) and math.isfinite(v) for x in a for v in x['metrics'].values()),'Every saved cell metric finite and defined')
counts={m:sum(x['metric']==m and x['top']==['slo_gated_c01'] for x in rk) for m in ['mean_latency','p95_latency','token_throughput','arrival_normalized_weighted_goodput']}
claim('unique_wins',list(counts.values())==[1146,834,482,1004],counts)
win={s:sum(x['metric']=='mean_latency' and x['source']==s and x['top']==['slo_gated_c01'] for x in rk) for s in ['azure_llm_2024','bailian_qwen','burstgpt']}
claim('wins_by_source',list(win.values())==[480,468,198],win)
# Independent summation of source/capacity aggregate values.
g=defaultdict(list)
for x in a:g[x['source'],x['profile'],x['policy']].append(x['metrics'])
means={k:{m:sum(v[m] for v in vs)/len(vs) for m in vs[0]} for k,vs in g.items()}
deltas=[]
for s in ['azure_llm_2024','bailian_qwen','burstgpt']:
 for k in ['kv131072','kv262144']:
  b=means[s,k,'chunked_fcfs_c01'];z=means[s,k,'slo_gated_c01'];d={m:100*(z[m]/b[m]-1) for m in ['mean_latency','p95_latency','token_throughput','arrival_normalized_weighted_goodput']};deltas.append({'source':s,'capacity':k,**d})
claim('latency_range',(round(min(-x['mean_latency'] for x in deltas),1),round(max(-x['mean_latency'] for x in deltas),1))==(11.3,34.0),deltas)
claim('throughput_range',(round(min(-x['token_throughput'] for x in deltas),2),round(max(-x['token_throughput'] for x in deltas),2))==(1.65,4.01),'throughput reductions')
claim('unfavorable_tail', [round(x['p95_latency'],2) for x in deltas if x['source']=='burstgpt']==[3.72,18.97],'Both BurstGPT capacities worsen')
z=next(x for x in deltas if x['source']=='bailian_qwen' and x['capacity']=='kv131072');claim('unfavorable_goodput',round(-z['arrival_normalized_weighted_goodput'],2)==3.12 and round(-z['mean_latency'],2)==24.05,'Bailian four-resident goodput loss despite lower mean latency')
for s,k,p in g:
 if k=='kv131072':
  lo=means[s,k,p];hi=means[s,'kv262144',p]
  assert hi['mean_latency']<lo['mean_latency'] and hi['p95_latency']<lo['p95_latency'] and hi['token_throughput']>lo['token_throughput']
claim('capacity_direction',True,'All 12 source/adaptation aggregate comparisons improve these three endpoints')
claim('used_KV',[max(x['metrics']['peak_used_kv'] for x in a if x['profile']==k) for k in ['kv131072','kv262144']]==[47872,62880],'Peaks below smaller capacity')
# Full machine-readable tables must reproduce original values, not just rounded displays.
with (R/'tables/all-cell-metrics.csv').open() as f:tab=list(csv.DictReader(f))
assert len(tab)==5760
for r,t in zip(a,tab):
 for k,v in r['metrics'].items():assert float(t[k])==v
for n in ['source-capacity-means.csv','matched-window-differences.csv','chronological-differences.csv','reversal-counts.csv','tie-counts.csv']:
 assert (R/'tables'/n).stat().st_size>0
looks=[saved(f'stat-final-s{i:02d}.json.gz') for i in range(18)]
claim('stat_count',sum(z['n_studies'] for z in looks)==134000,'All 18 final looks')
claim('stat_stops',[i for i,z in enumerate(looks) if z['precision_objective_met']]==[0,1,2,3,16,17],'Six precision stops; twelve maximum-count stops with gaps')
c=Counter(r['calibration_screen'] for z in looks for r in z['original_prespecified']['methods'].values());claim('stat_screens',sorted(c.values())==[9,16,45,74],dict(c))
statclaims=[(0,'legacy_source_screened_BH','fdp_practical',.09025),(8,'legacy_source_screened_BH','fdp_practical',.918),(10,'legacy_source_screened_BH','fdp_practical',.980375),(8,'legacy_source_screened_BH','ci_coverage',.647625),(10,'legacy_source_screened_BH','ci_coverage',.564875),(8,'historical_full_BH','fdp_practical',.51875),(10,'historical_full_BH','fdp_practical',.778625),(0,'group_bootstrap_BY','ci_coverage',.88775),(17,'bounded_Hoeffding_Holm','power_practical',.052632),(10,'cluster_t_Holm','ci_coverage',.86),(11,'cluster_t_Holm','ci_coverage',.864375)]
for sid,m,e,expected in statclaims:
 got=looks[sid]['expanded_postdiagnosis']['methods'][m]['endpoints'][e]['mean'];assert round(got,6)==expected,(sid,m,e,got)
z=looks[0]['expanded_postdiagnosis']['methods']['legacy_source_screened_BH']['endpoints']['fdp_practical'];assert [round(z[k],5) for k in ['lower','upper']]==[.06878,.11172]
for sid,z in enumerate(looks):
 assert z['expanded_postdiagnosis']['delta_per_endpoint_look']==.05/(18*17*16*5)
 assert z['original_prespecified']['simultaneous_mc_delta_per_endpoint_look']==.05/(18*8*16*5)
 assert len(z['original_prespecified']['methods'])==8 and len(z['expanded_postdiagnosis']['methods'])==17
with (R/'tables/stat-all-endpoints.csv').open() as f:st=list(csv.DictReader(f))
assert len(st)==7200
for t in st:
 z=looks[int(t['scenario_id'])][t['family']]['methods'][t['method']]['endpoints'][t['endpoint']]
 for k in ['mean','lower','upper','halfwidth','mcse','n']:
  if z[k] is None:assert t[k]==''
  else:assert float(t[k])==z[k]
claim('stat_full_supplement',True,'7200 rows exactly reproduce all original/expanded endpoint means, bounds, counts and MCSEs')
# Citations, labels and expected source scope.
tex='\n'.join(p.read_text() for p in [R/'main.tex',*sorted((R/'sections').glob('*.tex'))])
keys=re.findall(r'^@\w+\{([^,]+),',(R/'references.bib').read_text(),re.M);cited={k for x in re.findall(r'\\cite\w*\{([^}]+)\}',tex) for k in x.split(',')}
assert len(keys)==len(set(keys))==21 and cited==set(keys),(keys,cited-set(keys),set(keys)-cited)
labels=re.findall(r'\\label\{([^}]+)\}',tex);refs=re.findall(r'\\ref\{([^}]+)\}',tex);assert len(labels)==len(set(labels)) and set(refs)<=set(labels)
for name in re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}',tex):assert (R/name).is_file()
assert tex.count('\\Description{')==4 and tex.count('\\reviewitem{')==4
assert 'Answer to RQ1' in tex and 'Answer to RQ2' in tex and 'Answer to RQ3' in tex
for banned in ['36 confirmed','native GPU rankings are','isolated arrival-load effect is established','four distinct mechanisms validated','population sample complexity is']:
 assert banned not in tex
claim('citations_structure',True,{'bibliography_entries':21,'cited':len(cited),'figures':4,'labels':len(labels),'author_review_items':4})
pdfs={}
for mode in ['manuscript','acmsmall']:
 p=R/'pdf'/f'm3-{mode}.pdf';doc=pymupdf.open(p);log=(R/'build'/mode/f'm3-{mode}.log').read_text();assert 'undefined references' not in log and not re.search(r'Citation .* undefined',log)
 warnings=re.findall(r'Overfull \\hbox \(([^)]+)\)',log);assert not warnings,warnings
 txt='\n'.join(pg.get_text() for pg in doc);assert all(s in txt for s in ['RQ1','RQ2','RQ3','AUTHOR REVIEW REQUIRED','134,000','5,760'])
 pdfs[mode]={'pages':len(doc),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'overfull_hboxes':0,'undefined_citations_or_references':0,'figure_pages':[i+1 for i,p in enumerate(doc) if 'Fig.' in p.get_text()]}
# Every inherited tracked file is checked against the exact base tree, with the known LFS anomaly documented.
base='6b2eedd7aa254986b85c1bb901587641cbeac8b0';changed=subprocess.check_output(['git','diff',base,'--name-only'],cwd=repo,text=True).splitlines();changed=[x for x in changed if not x.startswith('paper/tompecs-m3/')];assert set(changed)<={'dataset/v1.1.0/scientific/campaign/consolidated.json'}
lfs=repo/'dataset/v1.1.0/scientific/campaign/consolidated.json';assert hashlib.sha256(lfs.read_bytes()).hexdigest()=='73adf7d97f06985ec8f8e1c2f794fd43178433eb198e1c00705e817f4bde9c26'
result={'status':'PASS','scope':'Manuscript/saved-summary verification; no new simulations or raw-journal replay','checks':checks,'pdfs':pdfs,'frozen_saved_artifacts':len(manifest),'inherited_diff':changed,'preservation':'All inherited tracked content unchanged except the pre-existing hydrated LFS status, whose byte hash matches the reviewed original.'}
(R/'evidence/manuscript-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':'PASS','checks':len(checks),'citations':21,'pdfs':pdfs},indent=2))
