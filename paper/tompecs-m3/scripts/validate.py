#!/usr/bin/env python3
"""Offline saved-evidence and manuscript validation; never executes a campaign."""
import argparse,collections,csv,gzip,hashlib,importlib.util,itertools,json,math,pathlib,re,subprocess,sys
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--standalone',action='store_true',help='Validate an extracted manuscript without Git/history checkout checks')
parser.add_argument('--artifact-root',type=pathlib.Path,help='Unchanged rc1 extraction for fresh independent worked-example reconstruction')
parser.add_argument('--report',type=pathlib.Path,help='Write a new validation record without replacing an archived report')
args=parser.parse_args()
ROOT=pathlib.Path(__file__).resolve().parents[1];repo=ROOT.parents[1]
hashes=json.loads((ROOT/'evidence/input-hashes.json').read_text())
def read(n):
 b=gzip.decompress((ROOT/'evidence/inputs'/(n+'.gz')).read_bytes());assert hashlib.sha256(b).hexdigest()==hashes[n]['sha256_uncompressed'];return json.loads(b)
rows=read('c01-absolute_metrics.json');manifest=read('c01-manifest.json')
spec=importlib.util.spec_from_file_location('frozen_oracle',ROOT/'scripts/frozen_verify_analysis.py');oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
reports={k:read('c01-'+k+'.json') for k in ['rankings','ranking_frequencies','pairwise','window_aggregates','source_mean_rankings','reversals']}
result=oracle.verify(rows,manifest,reports)
claims={}
def check(key,actual,expected,tol=0):
 if isinstance(actual,(int,float)) and tol:assert abs(actual-expected)<=tol,(key,actual,expected)
 else:assert actual==expected,(key,actual,expected)
 claims[key]={'actual':actual,'expected':expected,'tolerance':tol,'status':'PASS'}
for m,lo,hi,t in [('mean_latency',.008314,3.893923,5e-7),('p95_latency',.008560,7.300052,5e-7),('token_throughput',332.489,7766.685,.0005),('n_tpot',103,200,0)]:
 vals=[x['metrics'][m] for x in rows];check(m+'_min',min(vals),lo,t);check(m+'_max',max(vals),hi,t)
for k,peak in [('kv131072',47872),('kv262144',62880)]:check(k+'_peak_used',max(x['metrics']['peak_used_kv'] for x in rows if x['profile']==k),peak)
check('cell_count',len(rows),5760);check('request_executions',sum(x['metrics']['num_completed'] for x in rows),1152000)
check('no_unfinished',sum(x['metrics']['num_unfinished'] for x in rows),0)
check('pilot_reuse_cells',sum(x['reused'] for x in rows),144)
D={(r['window'],r['region'],r['profile'],r['policy']):r for r in rows}
check('chunk_decode_metric_equivalence',sum(D[w,l,k,'chunked_fcfs_c01']['metrics']==D[w,l,k,'decode_first_c01']['metrics'] for w,l,k,p in D if p=='chunked_fcfs_c01'),1440)
check('mean_tpot_max_difference',max(abs(D[w,l,k,'chunked_fcfs_c01']['metrics']['mean_tpot']-D[w,l,k,'slo_gated_c01']['metrics']['mean_tpot']) for w,l,k,p in D if p=='chunked_fcfs_c01'),1.80e-16,5e-19)
for s,lo,hi in [('azure_llm_2024',22.525,180.873),('bailian_qwen',17.956,186.580),('burstgpt',102.884,725.020)]:
 v=[x['load_factor'] for x in rows if x['source']==s];check(s+'_factor_min',min(v),lo,.0005);check(s+'_factor_max',max(v),hi,.0005)
ranks=reports['rankings'];sm=reports['source_mean_rankings'];sources=manifest['sources']
index={(x['source'],x['region'],x['profile'],x['metric']):x for x in sm}
counts=collections.Counter()
for sa,sb in itertools.combinations(sources,2):
 for s,l,k,m in index:
  if s!=sa:continue
  a,b=index[sa,l,k,m],index[sb,l,k,m];counts['total']+=1;counts['top_equal']+=a['top']==b['top'];counts['top_intersect']+=bool(set(a['top'])&set(b['top']));counts['rank_equal']+=a['ranks']==b['ranks']
check('source_mean_top_comparisons',dict(counts),dict(total=396,top_equal=307,top_intersect=323,rank_equal=247))
groups=collections.defaultdict(list)
for x in ranks:groups[x['window'],x['region'],x['profile']].append(x)
counts=collections.Counter()
for group in groups.values():
 for a,b in itertools.combinations(group,2):
  counts['total']+=1;counts['top_equal']+=a['top']==b['top'];counts['top_intersect']+=bool(set(a['top'])&set(b['top']))
check('metric_top_comparisons',dict(counts),dict(total=79200,top_equal=27915,top_intersect=57602))
for source,n in [('azure_llm_2024',480),('bailian_qwen',468),('burstgpt',198)]:check(source+'_unique_mean_winner',sum(x['source']==source and x['metric']=='mean_latency' and x['top']==['slo_gated_c01'] for x in ranks),n)
for scope,expected in [('block',[(8,-.012,.203),(24,-.03,.233),(0,.015,.3275)]),('stratum',[(6,None,None),(20,None,None),(0,None,None)])]:
 for source,(negative,lo,hi) in zip(['azure_llm_2024','bailian_qwen','burstgpt'],expected):
  gg={(x['region'],x['profile'],x['group'],x['policy']):x['mean'] for x in reports['window_aggregates'] if x['source']==source and x['scope']==scope and x['metric']=='arrival_normalized_weighted_goodput'}
  diffs=[v-gg[l,k,b,'chunked_fcfs_c01'] for (l,k,b,p),v in gg.items() if p=='slo_gated_c01'];check(source+'_'+scope+'_negative',sum(v<0 for v in diffs),negative)
  if lo is not None:check(source+'_'+scope+'_min',min(diffs),lo,5e-5);check(source+'_'+scope+'_max',max(diffs),hi,5e-5)
# Values stated outside generated tables, retaining original/expanded families.
cp=read('stat-checkpoint.json');final={i:read(f'stat-look-s{i:02d}-n{cp["scenarios"][str(i)]["n"]:05d}.json') for i in range(18)}
check('stat_total',sum(x['n_studies'] for x in final.values()),134000)
for sid,method,endpoint,value,tol in [
 (4,'legacy_source_screened_BH','fdp_practical',.395,5e-7),(6,'legacy_source_screened_BH','fdp_practical',.73316,5e-6),
 (8,'historical_full_BH','fdp_practical',.51875,5e-7),(10,'historical_full_BH','fdp_practical',.778625,5e-7),
 (0,'group_bootstrap_BY','ci_coverage',.88775,5e-7),(10,'group_bootstrap_BY','ci_coverage',.759875,5e-7),
 (10,'cluster_t_Holm','ci_coverage',.8600,5e-7),(11,'cluster_t_Holm','ci_coverage',.864375,5e-7),
 (16,'bounded_Hoeffding_Holm','power_practical',0,0),(17,'bounded_Hoeffding_Holm','power_practical',.052632,5e-7)]:
  check(f'stat_{sid}_{method}_{endpoint}',final[sid]['expanded_postdiagnosis']['methods'][method]['endpoints'][endpoint]['mean'],value,tol)
for sid,n in [(14,1676),(15,202)]:check(f'stat_{sid}_cluster_coverage_n',final[sid]['original_prespecified']['methods']['cluster_t_Holm']['endpoints']['ci_coverage']['n'],n)
# Exact CSV-vs-saved input identity, including all numerical endpoint fields.
with (ROOT/'supplement/stat01-all-endpoints.csv').open() as f:
 csvrows=list(csv.DictReader(f))
check('stat_csv_rows',len(csvrows),7200)
for row in csvrows:
 endpoint=final[int(row['scenario_id'])][row['family']]['methods'][row['method']]['endpoints'][row['endpoint']]
 for key,value in endpoint.items():assert (row[key]=='' if value is None else float(row[key])==value),(row,key)
# Bibliography completeness and final TeX build diagnostics.
tex='\n'.join(p.read_text() for p in [ROOT/'main.tex',ROOT/'tables/time01.tex',*sorted((ROOT/'sections').glob('*.tex'))])
keys=set(re.findall(r'@\w+\{([^,]+),',(ROOT/'references.bib').read_text()))
cited={k for v in re.findall(r'\\cite\w*\{([^}]+)\}',tex) for k in v.split(',')}
assert cited==keys,{'uncited':keys-cited,'undefined':cited-keys}
labels=re.findall(r'\\label\{([^}]+)\}',tex);refs=re.findall(r'\\(?:ref|eqref)\{([^}]+)\}',tex)
assert len(labels)==len(set(labels)) and set(refs)<=set(labels)
builds={}
for mode in ['manuscript','acmsmall']:
 log=(ROOT/f'build/{mode}/m3-{mode}.log').read_text()
 assert 'Output written on' in log
 for bad in ['Overfull','LaTeX Error','Fatal error','undefined references','undefined citations','Citation `','multiply defined','Rerun to get']:
  assert bad not in log,(mode,bad)
 blg=(ROOT/f'build/{mode}/m3-{mode}.blg').read_text();assert 'error message' not in blg
 allowed={'empty address in vidur2024','empty publisher in maurer2009','empty address in maurer2009'}
 bib_warnings=re.findall(r'Warning--([^\n]+)',blg);assert set(bib_warnings)<=allowed,bib_warnings
 builds[mode]={'status':'PASS','pages':int(re.search(r'\((\d+) pages',log).group(1)),'overfull_boxes':0,'unresolved_references':0,'bibliography_optional_metadata_advisories':bib_warnings,'template_warning':'ACM reference-format block suppressed in author-review draft'}
assert all(b['pages'] <= 30 for b in builds.values()),builds
# Checkout preservation is a separate check in standalone archives.
changed=[]
history_scope='NOT_RUN_STANDALONE' if args.standalone else 'CHECKED'
if not args.standalone:
 # No tracked historical change beyond the known pre-existing hydrated-LFS anomaly.
 changed=subprocess.check_output(['git','diff','--name-only','6b2eedd7aa254986b85c1bb901587641cbeac8b0'],cwd=repo,text=True).splitlines()
 assert all(p.startswith('paper/tompecs-m3/') or p=='dataset/v1.1.0/scientific/campaign/consolidated.json' for p in changed),changed
 old=repo/'dataset/v1.1.0/scientific/campaign/consolidated.json'
 h=hashlib.sha256(old.read_bytes()).hexdigest();check('historical_consolidated_sha256',h,'73adf7d97f06985ec8f8e1c2f794fd43178433eb198e1c00705e817f4bde9c26')
example_path=ROOT/'major-revision/example-verification.json'
if args.artifact_root:
 subprocess.run([sys.executable,str(ROOT/'major-revision/verify_example.py'),str(args.artifact_root),'--report',str(example_path)],check=True,stdout=subprocess.DEVNULL)
example=json.loads(example_path.read_text());assert example['status']=='PASS'
for name,digest in example['support_sha256'].items():
 assert hashlib.sha256((ROOT/'major-revision'/name).read_bytes()).hexdigest()==digest,name
example_scope='FRESH_EVENT_RECONSTRUCTION' if args.artifact_root else 'SAVED_REPORT_AND_SUPPORT_HASHES_ONLY'
report=dict(status='PASS',independent_oracle=result,claims=claims,citation_keys=len(keys),labels=len(labels),builds=builds,historical_changes=changed,historical_checkout_check=history_scope,worked_example_check=example_scope,experiments_executed=0)
(args.report or ROOT/'evidence/validation/validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(f'PASS: independent full C01 report oracle; {len(claims)} narrative checks; 7200 endpoint rows; {len(keys)} references; both builds; historical preservation')
