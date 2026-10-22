"""Offline P1 evidence/preservation checks; no scheduler or GPU execution."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASE='ee1868618db9afc89160e1d0daf92b54829a80bc'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

preserved=json.loads((ROOT/'docs/fidelity-review-20261021/evidence/preserved-files.json').read_text())
for name,h in preserved.items(): assert sha(ROOT/name)==h,name
old=ROOT/'docs/serving-contract/v2.0.0-draft.1'
seal=json.loads((old/'evidence/SHA256.json').read_text())
for name,h in seal.items(): assert sha(old/name)==h,name
raw_seal=subprocess.check_output(['git','show',BASE+':docs/serving-contract/v2.0.0-draft.1/evidence/SHA256.json'],cwd=ROOT)
assert (old/'evidence/SHA256.json').read_bytes()==raw_seal
history='dataset/v1.1.0/scientific/campaign/consolidated.json'
old_raw=subprocess.check_output(['git','show',BASE+':'+history],cwd=ROOT)
assert sha(ROOT/history)==hashlib.sha256(old_raw).hexdigest()
unchanged=['src/robustbench/mgpu00','src/robustbench/mgpu02','src/robustbench/mgpu05',
           'src/robustbench/mgpu06','src/robustbench/simulator','scripts',
           'docs/study-protocol','tests/mgpu00','tests/mgpu02','tests/mgpu05','tests/mgpu06']
assert not subprocess.check_output(['git','diff',BASE,'--']+unchanged,cwd=ROOT)
matrix=json.loads((HERE/'case-coverage.json').read_text())
assert matrix['source_corpus_sha256']==sha(old/'cases.json')
assert [r['id'] for r in matrix['cases']]==[f'C{i:02}' for i in range(1,33)]
tests='\n'.join(p.read_text() for p in (ROOT/'tests/serving_v2').glob('test_*.py'))
for row in matrix['cases']:
    assert row['status'] in ('P1_EXECUTED','P1_PROJECTION','BLOCKED')
    if row['tests']!='none': assert 'def '+row['tests'].split('[')[0]+'(' in tests
for f in list((ROOT/'src/robustbench/serving_v2').glob('*.py'))+list((ROOT/'tests/serving_v2').glob('*.py')):
    ast.parse(f.read_text())
ref=ast.parse((ROOT/'src/robustbench/serving_v2/reference.py').read_text())
for node in ast.walk(ref):
    if isinstance(node,ast.ImportFrom): assert node.level==0 and not (node.module or '').startswith('robustbench')
    if isinstance(node,ast.Import): assert all(not x.name.startswith('robustbench') for x in node.names)
links=0
for p in HERE.glob('*.md'):
    for target in re.findall(r'\[[^\]]*\]\(([^\s)]+)\)',p.read_text()):
        if '://' not in target and not target.startswith('#'):
            assert (p.parent/target.split('#')[0]).exists(),(p,target)
            links+=1
print(json.dumps({'status':'PASS_DOCUMENTS_AND_PRESERVATION','baseline':BASE,
    'frozen_script_protocol_files':len(preserved),'original_pr5_files':len(seal)+1,
    'historical_raw_bytes':len(old_raw),'historical_sha256':sha(ROOT/history),
    'historical_lfs_filter_anomaly':'unchanged raw bytes; not staged or repaired',
    'unchanged_path_checks':unchanged,'case_status_counts':{s:sum(r['status']==s for r in matrix['cases'])
    for s in ('P1_EXECUTED','P1_PROJECTION','BLOCKED')},'documentation_links':links,
    'oracle_has_no_production_imports':True,'physical_validation':'NOT_VERIFIED'},indent=2))
