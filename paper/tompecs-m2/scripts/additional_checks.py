"""Additional independent classification, margin and dependence diagnostics."""
import collections as C, hashlib,json,math
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];E=ROOT/'paper/tompecs-m2/evidence';D=ROOT/'dataset/v1.1.0';m='arrival_normalized_weighted_goodput'
cells=json.loads((D/'scientific/campaign/consolidated.json').read_text())['cells'];rows=C.defaultdict(list)
for c in cells:
 if c['repetition']==0:rows[c['source_family'],c['load_region'],c['policy_id']].append(c)
def avg(condition,p):return np.mean([x[m] for x in rows[(*condition.split('::'),p)]])
rv=json.loads((D/'scientific/analysis/pairwise_reversals.json').read_text())['records'][m];checks=[];thresholds={str(t):0 for t in [.05,.1,.15,.2]}
for r in rv:
 dd=[];mm=[]
 for side in ['x','y']:
  a,b=[avg(r['condition_'+side],r['policy_'+p]) for p in ['a','b']];d=a-b;l=b if d>0 else a;dd.append(d);mm.append(0 if d==0 else abs(d)/abs(l) if l else None)
 if any(x is None for x in mm):lab='UNDEFINED_UNESTIMABLE'
 elif dd[0]*dd[1]>=0:lab='STABLE_NO_SIGN_CHANGE'
 elif min(mm)<=.1:lab='MICROSCOPIC_SIGN_CHANGE'
 elif all(r['ci_'+side] is not None and r['ci_'+side][0]*r['ci_'+side][1]>0 for side in ['x','y']):lab='SUPPORTED_PRACTICAL_REVERSAL'
 else:lab='UNSUPPORTED_SIGN_CHANGE_WIDE_CI'
 checks.append(lab==r['classification'] and np.allclose(dd,[r['diff_x'],r['diff_y']],atol=1e-12) and np.allclose(mm,[r['margin_x'],r['margin_y']],atol=1e-12))
 for t in thresholds:thresholds[t]+=int(dd[0]*dd[1]<0 and all(x is not None and x>float(t) for x in mm))
windows=json.loads((D/'manifests/ranking_portability_pilot_v2_windows_index.json').read_text())['windows'];dep={}
for source in sorted({x['source_family'] for x in windows}):
 ww=sorted([x for x in windows if x['source_family']==source],key=lambda x:x['start_index_in_valid_rows']);gaps=[b['start_index_in_valid_rows']-a['start_index_in_valid_rows']-a['request_count'] for a,b in zip(ww,ww[1:])];assert len({x['source_file'] for x in ww})==1
 dep[source]={'file':ww[0]['source_file'],'source_file_sha256':ww[0]['source_file_sha256'],'min_gap_valid_rows':min(gaps),'max_gap_valid_rows':max(gaps),'overlaps':sum(g<0 for g in gaps),'sampling_seeds':sorted({x['sampling_seed'] for x in ww}),'window_order':[x['window_id'] for x in ww]}
zero=C.Counter((c['source_family'],c['policy_id']) for c in cells if c['repetition']==0 and c['policy_id'] in json.loads((D/'scientific/analysis/ranking_correlations.json').read_text())['policies'] and c['completion_fraction']==0)
result={'primary_classifications':{'tested':len(checks),'matched':sum(checks)},'point_margin_sensitivity_posthoc_no_new_CIs':thresholds,'dependence':dep,'primary_zero_completion':{str(k):v for k,v in zero.items()}}
(E/'additional-checks.json').write_text(json.dumps(result,indent=2,default=lambda x:x.item())+'\n');print(json.dumps(result,indent=2,default=lambda x:x.item()));assert all(checks)
