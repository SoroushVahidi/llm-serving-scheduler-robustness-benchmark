"""Read-only CPU preservation/document checks. No model or scheduler execution."""
import ast,hashlib,json,re,subprocess
from pathlib import Path
from robustbench.serving_v2.p2b.reference import validate
H=Path(__file__).resolve().parent
R=H.parents[2]
BASE='df4b13d269d64a949a9dd910b6a65e61718dbc29'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
seals={}
for name in ('v2.0.0-draft.1','p1-0.1.0','p2a-0.1.0'):
    folder=H.parent/name
    seal=json.loads((folder/'evidence/SHA256.json').read_text())
    for path,digest in seal.items():
        assert sha((folder if name.startswith('v2.') else R)/path)==digest,path
    rel=str((folder/'evidence/SHA256.json').relative_to(R))
    assert subprocess.check_output(['git','show',BASE+':'+rel],cwd=R)==(R/rel).read_bytes()
    seals[name]=len(seal)+1
preserved=json.loads((R/'docs/fidelity-review-20261021/evidence/preserved-files.json').read_text())
for path,digest in preserved.items():assert sha(R/path)==digest,path
old='dataset/v1.1.0/scientific/campaign/consolidated.json'
raw=subprocess.check_output(['git','show',BASE+':'+old],cwd=R)
assert sha(R/old)==hashlib.sha256(raw).hexdigest()
# All previously tracked files remain unchanged; the inherited filter anomaly
# above is checked by bytes rather than through its LFS clean filter.
changed=subprocess.check_output(['git','diff',BASE,'--name-only'],cwd=R,text=True).splitlines()
allowed=('src/robustbench/serving_v2/p2b/','tests/serving_v2_p2b/','docs/serving-contract/p2b-0.1.0/')
assert all(p==old or p.startswith(allowed) for p in changed),changed
counts=json.loads((H/'evidence/final/counts.json').read_text())
nodes=(H/'evidence/final/test-nodes.txt').read_text().splitlines()
assert len(nodes)==len(set(nodes))==counts['passed']==counts['distinct']
assert counts['inherited']==508 and counts['failed']==counts['skipped']==0
for path,digest in json.loads((H/'evidence/final/tested-source-hashes.json').read_text()).items():assert sha(R/path)==digest,path
for path in list((R/'src/robustbench/serving_v2/p2b').glob('*.py'))+list((R/'tests/serving_v2_p2b').glob('*.py')):
    ast.parse(path.read_text())
result=validate(json.loads((H/'evidence/final/native-control-fixture.json').read_text()),
                json.loads((H/'evidence/final/independent-intents.json').read_text()))
assert result.valid and result.complete and not result.transport_closed,result
links=0
for p in H.glob('*.md'):
    for target in re.findall(r'\[[^\]]*\]\(([^\s)]+)\)',p.read_text()):
        if '://' not in target and not target.startswith('#'):
            assert (p.parent/target.split('#')[0]).exists(),(p,target)
            links+=1
assert (H/'evidence/final/exit').read_text().strip()=='0'
assert (H/'evidence/final/status').read_text().strip()=='COMPLETED_SUCCESS'
print(json.dumps(dict(status='PASS_PRESERVATION_AND_CPU_CONFORMANCE',baseline=BASE,
    inherited_seals=seals,frozen_files=len(preserved),historical_bytes=len(raw),historical_sha256=sha(R/old),
    lfs_anomaly='unchanged bytes, unstaged',counts=counts,fixture=result.__dict__,links=links),indent=2))
