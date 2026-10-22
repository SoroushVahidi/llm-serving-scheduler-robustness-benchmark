"""CPU/document checks only. Writes nothing unless caller redirects stdout."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
from robustbench.serving_v2.p2a.reference import validate

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASE='810b987dd873215d1a872eca83fd5c50770ca434'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

prior={}
for version in ('v2.0.0-draft.1','p1-0.1.0'):
    folder=HERE.parent/version
    seal=json.loads((folder/'evidence/SHA256.json').read_text())
    for name,digest in seal.items():
        target=folder/name if version.startswith('v2.') else ROOT/name
        assert sha(target)==digest,name
    original=subprocess.check_output(['git','show',BASE+':'+str((folder/'evidence/SHA256.json').relative_to(ROOT))],cwd=ROOT)
    assert original==(folder/'evidence/SHA256.json').read_bytes()
    prior[version]=len(seal)+1
preserved=json.loads((ROOT/'docs/fidelity-review-20261021/evidence/preserved-files.json').read_text())
for name,digest in preserved.items():assert sha(ROOT/name)==digest,name
paths=['src/robustbench/mgpu00','src/robustbench/mgpu02','src/robustbench/mgpu05',
       'src/robustbench/mgpu06','src/robustbench/simulator','src/robustbench/serving_v2/ledger.py',
       'src/robustbench/serving_v2/reference.py','src/robustbench/serving_v2/__init__.py',
       'tests/mgpu00','tests/mgpu02','tests/mgpu05','tests/mgpu06','tests/serving_v2',
       'scripts','docs/study-protocol']
assert not subprocess.check_output(['git','diff',BASE,'--']+paths,cwd=ROOT)
history=ROOT/'dataset/v1.1.0/scientific/campaign/consolidated.json'
raw=subprocess.check_output(['git','show',BASE+':'+str(history.relative_to(ROOT))],cwd=ROOT)
assert hashlib.sha256(raw).hexdigest()==sha(history)
for path in list((ROOT/'src/robustbench/serving_v2/p2a').glob('*.py'))+list((ROOT/'tests/serving_v2_p2a').glob('*.py')):
    ast.parse(path.read_text())
ref=ast.parse((ROOT/'src/robustbench/serving_v2/p2a/reference.py').read_text())
for node in ast.walk(ref):
    if isinstance(node,ast.ImportFrom):
        assert node.module in ('dataclasses','reference','pins'),node.module
    if isinstance(node,ast.Import):assert all(x.name=='json' for x in node.names)
links=0
for path in HERE.glob('*.md'):
    for target in re.findall(r'\[[^\]]*\]\(([^\s)]+)\)',path.read_text()):
        if '://' not in target and not target.startswith('#'):
            assert (path.parent/target.split('#')[0]).exists(),(path,target)
            links+=1
fixture=json.loads((HERE/'evidence/native-cpu-fixture.json').read_text())
result=validate(fixture)
assert result.valid and result.complete and not result.transport_closed,result
nodes=(HERE/'evidence/test-nodes.txt').read_text().splitlines()
assert len(nodes)==len(set(nodes))==508
assert sum(n.startswith('tests/serving_v2_p2a/') for n in nodes)==93
assert '508 passed' in (HERE/'evidence/cpu-regression.raw.txt').read_text()
manifest=json.loads((HERE/'manifest.json').read_text())
assert manifest['counts']==dict(existing=415,new=93,passed=508,failed=0,skipped=0)
print(json.dumps(dict(status='PASS_CPU_DOCUMENTS_PRESERVATION',baseline=BASE,
    inherited_seals=prior,frozen_script_protocol_files=len(preserved),
    unchanged_paths=paths,historical_raw_bytes=len(raw),historical_sha256=sha(history),
    historical_lfs_anomaly='preserved, unstaged; raw bytes equal baseline',
    distinct_test_nodes=len(nodes),documentation_links=links,
    independent_fixture=result.__dict__),indent=2))
