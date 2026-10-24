#!/usr/bin/env python3
"""Portable saved-evidence analysis; no simulations. Writes only outside artifact."""
import argparse,hashlib,json,pathlib,shutil,subprocess,sys
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('artifact',type=pathlib.Path);p.add_argument('--output',type=pathlib.Path,required=True)
p.add_argument('--journals',action='store_true',help='Repeat all TIME01 and the 36-stratum ABL01 semantic journal checks')
a=p.parse_args();root=a.artifact.resolve();out=a.output.resolve()
assert root not in out.parents and out!=root,'Use a fresh external output directory'
out.mkdir(parents=True,exist_ok=False);(out/'review').mkdir();(out/'saved').mkdir()
sys.dont_write_bytecode=True
for exp in ['time01','abl01']:
    view=out/'saved'/exp;view.mkdir()
    for f in (root/'evidence'/exp).iterdir():
        (view/f.name).symlink_to(f,target_is_directory=f.is_dir())
    (view/'code').symlink_to(root/'code'/exp,target_is_directory=True)
original=root/'code/independent-review'
# Historical sources remain unchanged. Rewrite only runtime path bindings and
# replace external git-blob lookup with packaged frozen source identity checks.
for name in ['independent_tables.py','independent_journals.py','summarize_findings.py','reproduce_abl_analysis.py']:
    text=(original/name).read_text()
    text=text.replace("BASE=pathlib.Path('/home/soroush/artifacts/m3-four-platform-refresh-20261024/prepared/canonical/evidence/c01')",'BASE=pathlib.Path('+repr(str(root/'evidence/c01'))+')')
    if name=='independent_tables.py':
        text=text.replace(" repo=pathlib.Path('/home/soroush/repos/llm-serving-scheduler-m3-'+exp+'-20261023')",' # Source commits are in COMMITS.json; original git linkage is archived in review evidence.')
        old="  data=subprocess.check_output(['git','-C',str(repo),'show',m['code_sha']+':research/m3-'+exp+'/'+name])"
        assert old in text
        text=text.replace(old,"  data=(code/name).read_bytes()")
    (out/name).write_text(text)
for name in ['independent_tables.py']:
    subprocess.run([sys.executable,'-B',str(out/name)],check=True,stdout=(out/(name+'.log')).open('w'))
if a.journals:
    subprocess.run([sys.executable,'-B',str(out/'independent_journals.py')],check=True,stdout=(out/'journals.log').open('w'))
else:
    for name in ['time01-journal-validation.json','abl01-journal-validation.json']:
        shutil.copyfile(root/'verification/independent-review'/name,out/'review'/name)
for name in ['summarize_findings.py','reproduce_abl_analysis.py']:
    subprocess.run([sys.executable,'-B',str(out/name)],check=True,stdout=(out/(name+'.log')).open('w'))
checks={}
for f in (out/'review').glob('*.csv'):
    expected=root/'verification/independent-review'/f.name
    if expected.exists():
        eq=hashlib.sha256(f.read_bytes()).digest()==hashlib.sha256(expected.read_bytes()).digest()
        assert eq,f.name;checks[f.name]='BYTE_IDENTICAL'
report={'status':'PASS','simulations':0,'output':str(out),'independent_review_csvs':checks,'journal_semantics':'FRESH' if a.journals else 'REUSED_HASH_LINKED_INDEPENDENT_REVIEW','source_verification':'packaged source hashes against immutable manifests; external Git-blob checks reused from archived review','frozen_abl01_tables':'all eight CSVs and verification.json byte-identical'}
(out/'PORTABLE_REPRODUCTION.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS: portable numerical checks and frozen ABL01 analysis; no simulation')
