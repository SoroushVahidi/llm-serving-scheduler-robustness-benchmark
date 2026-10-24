"""Select inputs without outcomes; identity-check and reuse existing fixed results."""
import argparse, collections, dataclasses, datetime, json, pathlib, shutil, subprocess
from support import HERE, sha, canon, save_new
from policies import POLICIES, Config
from timing import Timing


def main():
    ap=argparse.ArgumentParser();ap.add_argument('baseline',type=pathlib.Path);ap.add_argument('out',type=pathlib.Path)
    ap.add_argument('--remote-root',required=True);a=ap.parse_args()
    a.out.mkdir(exist_ok=False); (a.out/'baselines').mkdir()
    f=a.baseline;launch=json.loads((f/'launch.json').read_text())
    for name in ('engine.py','policies.py','validator.py'):
        path='research/lssp-c01/'+name
        assert sha(HERE/'frozen_c01'/name)==sha(f/path)==launch['files'][path]
    assert sha(f/'inputs/full-inputs.json')==launch['files']['inputs/full-inputs.json']
    data=json.loads((f/'inputs/full-inputs.json').read_text())
    for c in data['conditions']: assert canon(c['requests'])==c['requests_sha256']
    oldmanifest=json.loads((f/'research/lssp-c01-full/input_manifest.json').read_text())
    desc=[]
    for c in data['conditions']:
        if c['region']!='LOW':continue
        rs=c['requests']; counts=collections.Counter(r['arrival'] for r in rs)
        desc.append(dict(source=c['source'],window=c['window'],mean_prompt=sum(r['prompt'] for r in rs)/len(rs),
            mean_output=sum(r['output'] for r in rs)/len(rs),burst_fraction=sum(n for n in counts.values() if n>1)/len(rs)))
    chosen=[]; bins=[]
    for source in sorted({d['source'] for d in desc}):
        groups=[[d for d in desc if d['source']==source]]
        assert len(groups[0])==40
        for feature in ('mean_prompt','mean_output','burst_fraction'):
            nxt=[]
            for group in groups:
                group=sorted(group,key=lambda d:(d[feature],d['window']))
                nxt.extend([group[:len(group)//2],group[len(group)//2:]])
            groups=nxt
        for i,g in enumerate(groups):
            assert len(g)==5
            select=sorted(g,key=lambda d:d['window'])[2]['window'];chosen.append(select)
            bins.append(dict(source=source,stratum=i,windows=sorted(d['window'] for d in g),selected=select))
    cs=sorted([c for c in data['conditions'] if c['window'] in chosen and c['region'] in ('LOW','HIGH_PRESSURE')],key=lambda c:c['condition_id'])
    assert len(cs)==48
    save_new(a.out/'inputs.json',dict(conditions=cs))
    save_new(a.out/'selection.json',dict(descriptors=desc,strata=bins,selected_windows=chosen))
    code_sha=subprocess.check_output(['git','-C',str(HERE),'rev-parse','HEAD'],text=True).strip()
    paths=subprocess.check_output(['git','-C',str(HERE),'ls-files','.'],text=True).splitlines()
    files={name:sha(HERE/name) for name in paths}
    timing=Timing(mode='composition-v1').identity()
    index_path=f/'runs/c01-full-167b9074e5711420/analysis/absolute_metrics.json'
    ix={(r['condition_id'],r['profile'],r['policy']):r for r in json.loads(index_path.read_text())}
    cells=[]
    for c in cs:
        for profile in oldmanifest['profiles']:
            cfg=profile['config'];assert cfg==dataclasses.asdict(Config(kv_capacity=cfg['kv_capacity']))
            for policy in POLICIES:
                row=ix[c['condition_id'],profile['name'],policy]
                assert all(row[k]==c[k] for k in ('condition_id','window','source','region','requests_sha256','synthesis_seed','load_factor'))
                old=f/row['result_path']/'result.json'
                assert sha(old)==row['result_sha256']
                r=json.loads(old.read_text());assert r['validated'] and r['metrics']==row['metrics']
                assert r['identity']==row['record_identity'] and r['requests_sha256']==c['requests_sha256']
                ident=dict(code_sha=code_sha,contract='CM-0.1+TIME01-duration-only',timing=timing,
                    config=cfg,policy=policy,condition_id=c['condition_id'],requests_sha256=c['requests_sha256'],
                    synthesis_seed=c['synthesis_seed'],load_factor=c['load_factor'])
                cid=canon(ident);dest=a.out/'baselines'/f'{cid}.json';shutil.copyfile(old,dest)
                cells.append(dict(cell_id=cid,identity=ident,source=c['source'],window=c['window'],region=c['region'],
                    profile=profile['name'],baseline=dict(result_path=row['result_path'],result_sha256=row['result_sha256'],
                    record_identity=r['identity'],journal_sha256=r['journal_sha256'],local_file=f'baselines/{cid}.json')))
    assert len(cells)==384 and len({c['cell_id'] for c in cells})==384
    manifest=dict(experiment='M3-TIME01',objective='Composition-dependent timing sensitivity under CM-0.1',
        code_sha=code_sha,files=files,timing=timing,inputs_sha256=sha(a.out/'inputs.json'),selection_sha256=sha(a.out/'selection.json'),
        cells=cells,missing_cells=[c['cell_id'] for c in cells],completed_cell_reuse=[],
        baseline_run='c01-full-167b9074e5711420',baseline_execution_commit=launch['code_commit'],
        baseline_pilot_execution_commit=launch['pilot_execution_commit'],baseline_launch_sha256=sha(f/'launch.json'),
        baseline_index_sha256=sha(index_path),baseline_root=str(f),
        frozen_full_inputs_sha256=sha(f/'inputs/full-inputs.json'),baseline_config_manifest_sha256=sha(f/'research/lssp-c01-full/input_manifest.json'),
        slurm=dict(account='ikoutis',partition='general',qos='standard',nodes=1,tasks=1,cpus=1,memory='4G',walltime='02:00:00',gpus=0,array=None),
        output_root=a.remote_root,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        validation_status='tests and saved-baseline regression required; see immutable execution.json before submission')
    save_new(a.out/'manifest.json',manifest)
    print(json.dumps(dict(code_sha=code_sha,windows=len(chosen),new_cells=len(cells),reused_baselines=len(cells),manifest_sha256=sha(a.out/'manifest.json'))))
if __name__=='__main__':main()
