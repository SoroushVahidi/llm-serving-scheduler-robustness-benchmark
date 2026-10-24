"""Freeze exact C01 input/result reuse identities; no simulation or outcomes tuning."""
import argparse,pathlib,subprocess,shutil,collections
from support import *
def prepare(base,out,remote_base,remote_root):
 out.mkdir(exist_ok=False)
 launch=read(base/'launch.json');oldm=read(base/'research/lssp-c01-full/input_manifest.json')
 index_path=base/'runs/c01-full-167b9074e5711420/analysis/absolute_metrics.json';index=read(index_path)
 full=base/'inputs/full-inputs.json';data=read(full)
 assert sha(full)==launch['files']['inputs/full-inputs.json']
 for name in ('engine.py','policies.py','validator.py'):
  path='research/lssp-c01/'+name;assert sha(HERE/'frozen_c01'/name)==sha(base/path)==launch['files'][path]
 assert len(data['conditions'])==720 and len(index)==5760
 ix={(r['condition_id'],r['profile'],r['policy']):r for r in index};assert len(ix)==5760
 code=subprocess.check_output(['git','-C',str(HERE),'rev-parse','HEAD'],text=True).strip()
 files={n:sha(HERE/n) for n in subprocess.check_output(['git','-C',str(HERE),'ls-files','.'],text=True).splitlines()}
 cells=[];sources=collections.Counter();windows=set();regions=set()
 for c in sorted(data['conditions'],key=lambda c:c['condition_id']):
  assert canon(c['requests'])==c['requests_sha256'];windows.add((c['source'],c['window']));regions.add(c['region'])
  assert [r['id'] for r in c['requests']]==list(range(len(c['requests'])))
  assert [r['arrival'] for r in c['requests']]==sorted(r['arrival'] for r in c['requests'])
  for p in oldm['profiles']:
   cfg=p['config'];scope(cfg);rows={}
   for policy in ('slo_gated_c01','chunked_fcfs_c01'):
    row=ix[c['condition_id'],p['name'],policy]
    assert all(row[k]==c[k] for k in ('condition_id','window','source','region','requests_sha256','synthesis_seed','load_factor'))
    r=read(base/row['result_path']/'result.json');assert sha(base/row['result_path']/'result.json')==row['result_sha256']
    assert r['validated'] and r['metrics']==row['metrics'] and r['identity']==row['record_identity'] and r['requests_sha256']==c['requests_sha256']
    rows[policy]=row
   identity=dict(experiment='M3-ABL01',code_sha=code,contract='CM-0.1',policy=CONTROL,config=cfg,condition_id=c['condition_id'],requests_sha256=c['requests_sha256'],synthesis_seed=c['synthesis_seed'],load_factor=c['load_factor'],reuse_method='PROVED_NONBINDING_EQUIVALENCE_ORDER_RECONSTRUCTION',source_record_sha256=rows['chunked_fcfs_c01']['result_sha256'])
   cells.append(dict(cell_id=canon(identity),identity=identity,source=c['source'],window=c['window'],region=c['region'],profile=p['name'],baseline=rows['slo_gated_c01'],equivalent_control=rows['chunked_fcfs_c01']))
   sources[c['source']]+=1
 assert len(windows)==120 and len(regions)==6 and len(cells)==1440 and set(sources.values())=={480}
 shutil.copyfile(full,out/'inputs.json');shutil.copyfile(index_path,out/'baseline-index.json')
 origin_paths=['launch.json','inputs/full-inputs.json','research/lssp-c01-full/input_manifest.json','runs/c01-full-167b9074e5711420/analysis/absolute_metrics.json','runs/c01-full-167b9074e5711420/complete.json']
 m=dict(experiment='M3-ABL01',created_utc=stamp(),code_sha=code,files=files,inputs_sha256=sha(out/'inputs.json'),index_sha256=sha(out/'baseline-index.json'),baseline_root=remote_base,output_root=remote_root,origin_hashes={n:sha(base/n) for n in origin_paths},baseline_run='c01-full-167b9074e5711420',baseline_code_sha=launch['code_commit'],baseline_pilot_code_sha=launch['pilot_execution_commit'],profiles=oldm['profiles'],cells=cells,new_simulation_cells=0,reused_slo_baselines=1440,reused_equivalent_controls=1440,missing_simulation_cells=[],new_order_reconstructions=1440,regions=sorted(regions),source_counts=dict(sources),slurm=dict(account='ikoutis',partition='general',qos='standard',cpus=1,memory='4G',walltime='02:00:00',gpus=0),inference='DESCRIPTIVE_FINITE_SELECTED_CORPUS')
 save_new(out/'manifest.json',m)
 print('FROZEN',canon(m),'1440 baseline/control pairs; 0 missing simulations')
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('base',type=pathlib.Path);a.add_argument('out',type=pathlib.Path);a.add_argument('--remote-base',required=True);a.add_argument('--remote-root',required=True);v=a.parse_args();prepare(v.base,v.out,v.remote_base,v.remote_root)
