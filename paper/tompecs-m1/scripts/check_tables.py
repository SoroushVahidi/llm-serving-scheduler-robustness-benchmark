"""Reproduce four historical table-data payloads without writing originals."""
from pathlib import Path
import importlib.util,json
root=Path(__file__).resolve().parents[3];p=root/'paper/scripts/generate_phase12_tables_figures.py'
s=importlib.util.spec_from_file_location('old_table_generator',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
d=m.load_verified(root/'dataset/v1.1.0/scientific/analysis')
res={'rq1_rq2_portability':m.build_rq1(d['ranking_correlations.json'],d['topk_overlap.json'],root),'rq3_reversals':m.build_rq3(d['pairwise_reversals.json'],root),'rq4_sample_complexity':m.build_rq4(d['sample_complexity.json'],root),'rq5_temporal_robustness':m.build_rq5(d['temporal_robustness.json'],d['ranking_correlations.json'],d['telemetry_explanation.json'],root)}
checks={}
for key,value in res.items():
 old=json.loads((root/'paper/generated/table_data'/f'{key}.json').read_text())
 for v in [old,value]:
  for k in ['generated_at','generation_script_git_sha']:v.pop(k,None)
 checks[key]=old==value
(root/'paper/tompecs-m1/evidence/table-regeneration.json').write_text(json.dumps(checks,indent=2)+'\n');print(checks)
if not all(checks.values()):raise SystemExit(1)
