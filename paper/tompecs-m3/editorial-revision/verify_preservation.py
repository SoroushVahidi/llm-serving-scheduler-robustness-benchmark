"""Check scientific baseline, frozen tracked assets, and the known hydrated file."""
import hashlib,json,subprocess
from pathlib import Path
PAPER=Path(__file__).resolve().parents[1];REPO=PAPER.parents[1]
BASE='dda5fcf0f8f2a6f543e799f20767c9272022afc8';FINALIZATION='1598518c144bba04ff239794f232fbaa53830356'
def git(*args):return subprocess.check_output(['git',*args],cwd=REPO)
assert subprocess.run(['git','merge-base','--is-ancestor',BASE,FINALIZATION],cwd=REPO).returncode==0
scientific=['main.tex','sections','references.bib','figures','tables','evidence/inputs']
assert not git('diff','--name-only',BASE,FINALIZATION,'--',*[str(PAPER.relative_to(REPO)/p) for p in scientific])
frozen=['figures','tables','supplement','evidence/inputs','evidence/input-hashes.json','evidence/numerical-checks.json','major-revision/example-manifest.json','major-revision/example-summary.json','major-revision/example-aggregates.tex','major-revision/example-requests.tex']
paths=git('ls-tree','-r','--name-only',BASE,'--',*[str(PAPER.relative_to(REPO)/p) for p in frozen]).decode().splitlines()
checked={}
for p in paths:
 b=(REPO/p).read_bytes();assert b==git('show',BASE+':'+p),p;checked[p]=hashlib.sha256(b).hexdigest()
expected='73adf7d97f06985ec8f8e1c2f794fd43178433eb198e1c00705e817f4bde9c26'
protected={}
for repo in [REPO,Path('/home/soroush/repos/llm-serving-scheduler-lssp-m3-major-revision')]:
 p=repo/'dataset/v1.1.0/scientific/campaign/consolidated.json';h=hashlib.sha256(p.read_bytes()).hexdigest();assert h==expected;protected[str(p)]=h
changes=git('diff','--name-only',BASE).decode().splitlines()
assert all(p.startswith('paper/tompecs-m3/') or p=='dataset/v1.1.0/scientific/campaign/consolidated.json' for p in changes)
r=dict(status='PASS',baseline=BASE,finalization=FINALIZATION,finalization_descends_from_baseline=True,scientific_source_diff_between_baseline_and_finalization=[],unchanged_files=checked,protected_hydrated_files=protected,branch=git('branch','--show-current').decode().strip(),origin_main=git('rev-parse','origin/main').decode().strip(),experiments_executed=0)
(PAPER/'editorial-revision/preservation.json').write_text(json.dumps(r,indent=2)+'\n')
print('PASS',len(checked),'frozen tracked assets; both hydrated files preserved; ancestry/source comparison')
