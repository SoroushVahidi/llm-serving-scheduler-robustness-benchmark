"""Read-only provenance capture; no simulation or outcome analysis."""
import hashlib,json,subprocess
from pathlib import Path
root=Path('/home/soroush/repos')
items={
'llm-serving-scheduler-lssp-tompecs-m2':['paper/tompecs-m2/M2_STATISTICAL_AUDIT.md','paper/tompecs-m2/M2_REFEREE_REPORT.md','src/robustbench/ranking_portability/execute_cell.py','src/robustbench/simulator/simulator.py','src/robustbench/workloads/external/benchmark_synthesis.py','artifacts/manifests/ranking_portability_phase12_campaign_freeze.json','artifacts/manifests/ranking_portability_pilot_v2_windows_index.json'],
'llm-serving-scheduler-lssp-v2-p2b':['docs/serving-contract/p2b-0.1.0/README.md','docs/serving-contract/p2b-0.1.0/CONTRACT.md'],
'llm-serving-scheduler-lssp-fidelity':['docs/fidelity-review-20261021/REPORT.md'],
'llm-serving-module-intervention-benchmark-shared-state-ext-v2':['experiments/shared_state_erasure_extension_v2/preregistration.json','experiments/shared_state_erasure_extension_v2/window_manifest.json','experiments/shared_state_erasure_extension_v2/results/launch_manifest.json','experiments/shared_state_erasure_extension_v2/results/completeness_report.json','experiments/shared_state_erasure_extension_v2/results/analysis/results.json','src/module_intervention_benchmark/gate1/shared_state_erasure_extension.py']}
result=[]
for repo,paths in items.items():
 p=root/repo
 record={'path':str(p),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=p,text=True).strip(),'files':{}}
 for f in paths:
  q=p/f; record['files'][f]={'sha256':hashlib.sha256(q.read_bytes()).hexdigest(),'bytes':q.stat().st_size}
 result.append(record)
Path('research/lssp-c01/evidence/local_reuse_identity.json').write_text(json.dumps(result,indent=2)+'\n')
