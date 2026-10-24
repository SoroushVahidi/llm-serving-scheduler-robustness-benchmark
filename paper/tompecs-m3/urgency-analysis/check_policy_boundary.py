#!/usr/bin/env python3
"""Engineering-only checks on a supplied online state, not a workload run.
The 495ms-aged state is not asserted reachable under the examined contracts.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('candidate',type=Path)
a=p.parse_args()
frozen=a.candidate/'evidence/c01'
launch=json.loads((frozen/'launch.json').read_text())
policy=frozen/'research/lssp-c01/policies.py'
assert hashlib.sha256(policy.read_bytes()).hexdigest()==launch['files']['research/lssp-c01/policies.py']
sys.dont_write_bytecode=True
sys.path.insert(0,str(policy.parent))
from policies import Config,View,plan
assert set(Config.__dataclass_fields__)=={'budget','max_sequences','context','kv_capacity','block','dt','drain'}
assert set(View.__dataclass_fields__)=={'rid','ordinal','arrival','prompt','prefilled','generated','resident','anchor'}
assert 'deadline' not in policy.read_text() and 'estimated' not in policy.read_text()
cfg=Config(budget=1024,kv_capacity=262144)
views=(View(0,0,0.,1,1,1,True,0.),View(1,1,0.,512,0,0,True,None),View(2,2,0.,512,0,0,False,None))
checks=[]
for age,urgent in [(math.nextafter(.495,-math.inf),False),(.495,True),(math.nextafter(.495,math.inf),True)]:
    spans=plan('slo_gated_c01',age,views,cfg)
    if urgent:
        assert spans==[[0,'decode',1,2],[1,'prefill',0,512],[2,'prefill',0,511]]
    else:
        assert spans==[[1,'prefill',0,512],[2,'prefill',0,512]]
    checks.append(dict(age_s=age,urgent=urgent,spans=spans))
r=dict(state='COMPLETED_SUCCESS',engineering_boundary_cases=len(checks),checks=checks,
    scientific_experiments_executed=0,workload_simulation_called=False,policy_modified=False,
    configurable_slo_or_deadline_parameter=False,policy_sha256=hashlib.sha256(policy.read_bytes()).hexdigest())
Path(__file__).with_name('policy-boundary-check.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r,indent=2))
