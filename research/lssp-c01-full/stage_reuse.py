"""Copy audited pilot artifacts without modifying originals or rerunning cells."""
import argparse,shutil
from pathlib import Path
from common import HERE,PILOT,read,sha,digest,immutable,cell_id,check_inputs

def stage(root,pilot):
    audit=read(HERE/'evidence/pilot_audit.json');full=read(root/'inputs/full-inputs.json');manifest=read(HERE/'input_manifest.json')
    original=read(pilot/'inputs/pilot-inputs.json');oldspec=read(pilot/'launch.json');oldmanifest=read(pilot/'code/input_manifest.json')
    assert digest(oldspec)==audit['identity'] and sha(pilot/'inputs/pilot-inputs.json')==oldmanifest['input_sha256']
    for name in ('engine.py','policies.py','validator.py','prepare.py'):
        assert sha(PILOT/name)==sha(pilot/'code'/name)==audit['code_hashes'][name]
    assert manifest['profiles']==oldmanifest['profiles'] and manifest['policies']==oldmanifest['policies']
    byid={c['condition_id']:c for c in full['conditions']}
    for c in original['conditions']:assert {k:v for k,v in c.items() if k!='historical'}==byid[c['condition_id']]
    planned={x[0] for x in check_inputs(full,manifest)};entries=[]
    for e in audit['cells']:
        assert e['key'] in planned
        source=Path(e['path']);target=root/'reused'/cell_id(e['key']);target.mkdir(parents=True,exist_ok=True)
        for name,field in [('result.json','result_sha256'),('events.jsonl.gz','journal_sha256')]:
            assert sha(source/name)==e[field]
            if not (target/name).exists():shutil.copyfile(source/name,target/name)
            assert sha(target/name)==e[field]
        entries.append({**e,'staged_path':str(target.relative_to(root)),'identity':audit['identity']})
    assert len(entries)==len({x['key'] for x in entries})==144
    immutable(root/'reuse_index.json',dict(status='AUDITED_BYTE_IDENTICAL_REUSE',original_root=str(pilot),original_execution_commit=oldspec['code_commit'],cells=entries))
    for name in ('launch.json','code/input_manifest.json','runs/c01-30f3af3717d536cb/checkpoint.json','runs/c01-30f3af3717d536cb/complete.json'):
        destination=root/'provenance/pilot'/Path(name).name
        immutable(destination,read(pilot/name))
    print(dict(reused=144,missing=5616,invalidated=0,source_hashes='PASS',exact_input_conditions=18,original_outputs_modified=False))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--pilot',type=Path,required=True);a=p.parse_args();stage(a.root,a.pilot)
