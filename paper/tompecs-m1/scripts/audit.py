"""Read-only numerical audit of preserved results; no simulations or resampling.
Run from repository root. External historical inputs are explicitly required.
"""
import collections, hashlib, itertools, json, math, os, statistics
from pathlib import Path
import numpy as np
from scipy.stats import kendalltau
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'paper/tompecs-m1/evidence'
REPOS=Path(os.environ.get('LSSP_REPOS_ROOT',str(ROOT.parent)))
D=ROOT/'dataset/v1.1.0'
inputs={}
def read(p):
    p=Path(p); raw=p.read_bytes(); inputs[str(p)]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}; return json.loads(raw)
metric='arrival_normalized_weighted_goodput'
cells=read(D/'scientific/campaign/consolidated.json')['cells']
w=read(D/'manifests/ranking_portability_pilot_v2_windows_index.json')['windows']
rc=read(D/'scientific/analysis/ranking_correlations.json')
rev=read(D/'scientific/analysis/pairwise_reversals.json')['records'][metric]
policies=rc['policies']; unique=[c for c in cells if c['repetition']==0]
by=collections.defaultdict(list)
for c in unique: by[(c['source_family'],c['load_region'],c['policy_id'])].append(c)
def avg(source,region,policy,m):
    v=[x[m] for x in by[source,region,policy] if x.get(m) is not None and math.isfinite(x[m])]
    return float(np.mean(v)) if v else None
checks={}
keys=[(c['source_family'],c['window_id'],c['load_region'],c['policy_id'],c['repetition']) for c in cells]
checks['unique_execution_keys']=len(keys)==len(set(keys))==18720
pairs=collections.defaultdict(list)
for c in cells:pairs[(c['window_id'],c['load_region'],c['policy_id'])].append(c)
fields=[metric,'completion_fraction','weighted_completion_fraction','slo_violation_rate','weighted_goodput','mean_latency','p95_latency','request_throughput','token_throughput','mean_ttft','p95_ttft','telemetry']
checks['9360_identical_numeric_telemetry_pairs']=len(pairs)==9360 and all(len(v)==2 and all(json.dumps(v[0][f],sort_keys=True)==json.dumps(v[1][f],sort_keys=True) for f in fields) for v in pairs.values())
checks['120_windows_200_requests']=len(w)==120 and all(x['request_count']==200 for x in w)
checks['all_cells_successful']=all(c['success'] for c in cells)
recomputed=[]
for x in rc['comparisons'][metric]:
    a=x['condition_x'].split('::'); b=x['condition_y'].split('::')
    t=float(kendalltau([avg(*a,p,metric) for p in policies],[avg(*b,p,metric) for p in policies]).statistic)
    recomputed.append(dict(condition_x=x['condition_x'],condition_y=x['condition_y'],stored=x['kendall_tau'],recomputed=t,match=math.isclose(t,x['kendall_tau'],abs_tol=1e-12)))
checks['18_independent_kendall_point_estimates']=all(x['match'] for x in recomputed)
supported=[r for r in rev if r['classification']=='SUPPORTED_PRACTICAL_REVERSAL']
# Independent taxonomy from saved differences, margins and interval endpoints.
def classify(r):
    a,b=r['diff_x'],r['diff_y']
    if a is None or b is None:return 'UNDEFINED_UNESTIMABLE'
    if a*b>=0:return 'STABLE_NO_SIGN_CHANGE'
    if r['margin_x']<=.1 or r['margin_y']<=.1:return 'MICROSCOPIC_SIGN_CHANGE'
    if any(ci is None or ci[0]<=0<=ci[1] for ci in [r['ci_x'],r['ci_y']]):return 'UNSUPPORTED_SIGN_CHANGE_WIDE_CI'
    return 'SUPPORTED_PRACTICAL_REVERSAL'
checks['990_independent_classifications_from_saved_intervals']=all(classify(r)==r['classification'] for r in rev)
checks['990_pair_differences_from_cells']=all(all(math.isclose(avg(*r['condition_'+side].split('::'),r['policy_a'],metric)-avg(*r['condition_'+side].split('::'),r['policy_b'],metric),r['diff_'+side],abs_tol=1e-12) for side in ['x','y']) for r in rev)
external=REPOS/'llm-serving-scheduler-lssp-cross-metric-analysis-extension/artifacts/analysis/cross_metric_extension/33729102c2f8867cb521f8557cd51b42d8830811de8dea16cc7ab68d53b61fd9'
cr=read(external/'cross_metric_correlations.json')['records']; dr=read(external/'cross_metric_pairwise_disagreements.json')['records']
lower={'mean_latency','p95_latency','mean_ttft','p95_ttft','slo_violation_rate'}
cm_mismatch=[]; tie_conditions=0
for x in cr:
    lists=[]; winners=[]
    for m in [x['metric_a'],x['metric_b']]:
        vals={p:avg(x['source'],x['region'],p,m) for p in policies}; sign=-1 if m in lower else 1
        vals={p:v*sign for p,v in vals.items() if v is not None};lists.append(vals)
        winners.append(sorted(vals,key=lambda p:(-vals[p],p))[0])
        if len([v for v in vals.values() if v==max(vals.values())])>1: tie_conditions+=1
    common=sorted(lists[0].keys()&lists[1].keys()); t=float(kendalltau([lists[0][p] for p in common],[lists[1][p] for p in common]).statistic)
    if not math.isclose(t,x['kendall_tau_b'],abs_tol=1e-12) or int(winners[0]==winners[1])!=x['top1_agreement']:cm_mismatch.append([x['source'],x['region'],x['metric_a'],x['metric_b'],t,x['kendall_tau_b']])
checks['990_independent_cross_metric_tau_and_top1']=not cm_mismatch
slo=REPOS/'llm-serving-scheduler-lssp-slo-sensitivity-extension/artifacts/analysis/slo_sensitivity/424b332ff860870ae062db3360c18170476c19b462eb895dff69cd0d88b22c6d/full'
sr=read(slo/'ranking_robustness.json');sp=read(slo/'reversal_persistence.json');ss=read(slo/'slo_sensitivity_status.json')
temporal=read(D/'scientific/analysis/temporal_robustness.json')['records']
sc=read(D/'scientific/analysis/sample_complexity.json');ted=read(D/'scientific/analysis/telemetry_explanation.json'); te=ted['records']
cal=read(D/'manifests/ranking_portability_phase11_raw_fifo_calibration.json')['cells']
robust_means={k:statistics.mean(x['kendall_tau'] for x in rows) for k,rows in ted['robustness']['strata'].items()}
summary={'scope':'offline verification of preserved outputs; no new scientific execution or bootstrap confidence intervals', 'checks':checks,'source_window_counts':dict(collections.Counter(x['source_family'] for x in w)),'chronology':dict(collections.Counter(x['chronology_stratum'] for x in w)),'chronology_by_source':{s:dict(collections.Counter(x['chronology_stratum'] for x in w if x['source_family']==s)) for s in sorted({x['source_family'] for x in w})},'executions':len(cells),'unique_configurations':len(pairs),'zero_completion_unique':sum(c['completion_fraction']==0 for c in unique),'primary_zero_completion_unique':sum(c['completion_fraction']==0 for c in unique if c['policy_id'] in policies),'policies_all':sorted({c['policy_id'] for c in cells}),'policies_primary':policies,'reversals':{'counts':dict(collections.Counter(r['classification'] for r in rev)),'supported_pairs':dict(collections.Counter(r['policy_a']+' / '+r['policy_b'] for r in supported)),'supported_by_region':dict(collections.Counter(r['load_region'] for r in supported)),'all_involve_burstgpt':all('burstgpt' in r['condition_x']+r['condition_y'] for r in supported),'supported_after_fdr':sum(r['supported_after_fdr'] for r in supported)},'kendall':recomputed,'friedman_records':len(rc['omnibus_friedman']),'cross_metric':{'n':len(cr),'median_tau':statistics.median(x['kendall_tau_b'] for x in cr),'min_tau':min(x['kendall_tau_b'] for x in cr),'max_tau':max(x['kendall_tau_b'] for x in cr),'negative_tau':sum(x['kendall_tau_b']<0 for x in cr),'top1_agreement':sum(x['top1_agreement'] for x in cr),'policy_metric_sides_with_tied_maximum':tie_conditions,'class_counts':dict(collections.Counter(x['classification'] for x in dr)),'supported_fdr':sum(x['supported_after_fdr'] for x in dr),'independent_mismatches':cm_mismatch},'slo':{'status':ss,'median_tau':statistics.median(x['kendall_tau_b'] for x in sr),'top1_changes':sum(x['top1_agreement']==0 for x in sr),'nontrivial_persistence':dict(collections.Counter(x['persistence'] for x in sp if x['variant']!='primary_20x'))},'temporal':temporal,'sample_complexity':sc,'calibration':{'records':len(cal),'zero_completion':sum(x['completion_fraction']==0 for x in cal)},'robustness_means':robust_means,'telemetry_usable':sum(x['converged'] and x['n_observations']>=20 for x in te),'inputs':inputs}
OUT.mkdir(exist_ok=True);(OUT/'numerical-audit.json').write_text(json.dumps(summary,indent=2,allow_nan=True)+'\n')
# Keep compact row-level cross-metric evidence for review, not replace original artifacts.
(OUT/'cross-metric-point-records.json').write_text('[\n'+',\n'.join(json.dumps(row,sort_keys=True) for row in cr)+'\n]\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ['inputs','temporal','sample_complexity','kendall']},indent=2));print('CHECKS',sum(checks.values()),'passed',sum(not v for v in checks.values()),'failed')

if not all(checks.values()): raise SystemExit("Numerical audit failure; inspect JSON")
