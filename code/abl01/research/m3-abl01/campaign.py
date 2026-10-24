"""Bounded C01 saved-evidence validation/order reconstruction, NOT simulation."""
import argparse,fcntl,gzip,os,pathlib,sys,time,traceback
from support import *
def preflight(root,base=None):
 m=read(root/'manifest.json');base=pathlib.Path(base or m['baseline_root'])
 assert m['experiment']=='M3-ABL01' and m['new_simulation_cells']==0 and not m['missing_simulation_cells']
 for name,h in m['files'].items():assert sha(HERE/name)==h,name
 assert sha(root/'inputs.json')==m['inputs_sha256'] and sha(root/'baseline-index.json')==m['index_sha256']
 for name,h in m['origin_hashes'].items():assert sha(base/name)==h,name
 cs={c['condition_id']:c for c in read(root/'inputs.json')['conditions']};assert len(cs)==720
 for c in cs.values():assert canon(c['requests'])==c['requests_sha256']
 assert len(m['cells'])==len({x['cell_id'] for x in m['cells']})==1440
 for cell in m['cells']:
  i=cell['identity'];scope(i['config']);assert canon(i)==cell['cell_id'] and i['code_sha']==m['code_sha'] and i['policy']==CONTROL
  c=cs[i['condition_id']];assert i['requests_sha256']==c['requests_sha256'] and i['synthesis_seed']==c['synthesis_seed'] and i['load_factor']==c['load_factor']
  for label,policy in [('baseline','slo_gated_c01'),('equivalent_control','chunked_fcfs_c01')]:
   r=cell[label];assert r['policy']==policy and r['profile']==cell['profile']
   assert all(r[k]==c[k] for k in ('condition_id','requests_sha256','synthesis_seed','load_factor','source','window','region'))
 return m,cs,base

def pilot(root,out,base=None):
 m,cs,base=preflight(root,base);chosen=[]
 for source in sorted({c['source'] for c in m['cells']}):
  for profile in sorted({c['profile'] for c in m['cells']}):
   for region in ('LOW','HIGH_PRESSURE'):
    chosen.append(min((c for c in m['cells'] if (c['source'],c['profile'],c['region'])==(source,profile,region)),key=lambda c:c['window']))
 checks=[]
 for cell in chosen:
  c=cs[cell['identity']['condition_id']];cfg=cell['identity']['config']
  a,_,ta=checked_source(base,cell['baseline'],c,cfg)
  b,es,tb=checked_source(base,cell['equivalent_control'],c,cfg,True)
  assert validate(c['requests'],cfg,es,b['terminal'])==b['metrics']
  checks.append(dict(cell_id=cell['cell_id'],baseline_sha256=cell['baseline']['result_sha256'],control_source_sha256=cell['equivalent_control']['result_sha256'],batches=b['terminal']['batches'],reordered_batches=tb['serialized_order_changed_batches']))
 save_new(out,dict(status='PASS',method='saved-journal pilot conformance; no simulations',pairs=len(checks),independently_validated_source_journals=2*len(checks),manifest_sha256=sha(root/'manifest.json'),code_sha=m['code_sha'],checks=checks));print('PILOT_PASS',len(checks),flush=True)

def run(root):
 m,cs,base=preflight(root);execution=read(root/'execution.json');assert execution['validation_status']=='PASS' and execution['manifest_sha256']==sha(root/'manifest.json') and execution['code_sha']==m['code_sha']
 lock=(root/'run.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 (root/'derived-controls').mkdir(exist_ok=False)
 save_new(root/'start.json',dict(utc=stamp(),job_id=os.environ.get('SLURM_JOB_ID'),code_sha=m['code_sha'],manifest_sha256=sha(root/'manifest.json'),execution_sha256=sha(root/'execution.json'),new_simulations=0,source_pairs=1440))
 print('START',stamp(),'1440 reused pairs; 0 simulations',flush=True);start=time.monotonic();derived={}
 for cell in m['cells']:
  if time.monotonic()-start>6300:
   save_new(root/'partial.json',dict(completed=list(derived),missing=[c['cell_id'] for c in m['cells'] if c['cell_id'] not in derived],reason='105-minute reconstruction cutoff'));raise RuntimeError('bounded cutoff; no auto-resubmit')
  cid=cell['cell_id'];c=cs[cell['identity']['condition_id']];cfg=cell['identity']['config']
  baseline,_,bt=checked_source(base,cell['baseline'],c,cfg)
  old,es,t=checked_source(base,cell['equivalent_control'],c,cfg,True)
  folder=root/'derived-controls'/(cid+'.partial');folder.mkdir(exist_ok=False);journal=folder/'events.jsonl.gz'
  with journal.open('xb') as f:
   with gzip.GzipFile(fileobj=f,mode='wb',filename='',mtime=0) as z:
    for e in es:z.write((json.dumps(e,separators=(',',':'),allow_nan=False)+'\n').encode())
  r=dict(cell_id=cid,identity=cell['identity'],manifest_sha256=sha(root/'manifest.json'),provenance='PROVEN_EQUIVALENT_SAVED_EXECUTION_WITH_EXACT_CONTROL_ORDER_RECONSTRUCTION',simulated=False,original_policy='chunked_fcfs_c01',source_result_sha256=cell['equivalent_control']['result_sha256'],source_journal_sha256=cell['equivalent_control']['journal_sha256'],baseline_result_sha256=cell['baseline']['result_sha256'],journal_sha256=sha(journal),terminal=old['terminal'],metrics=old['metrics'],telemetry=t,baseline_telemetry=bt,validated=True)
  assert validate(c['requests'],cfg,events(journal),r['terminal'])==r['metrics']
  save_new(folder/'result.json',r);dest=root/'derived-controls'/cid;assert not dest.exists();folder.rename(dest);derived[cid]=r
  print(json.dumps(dict(event='PAIR_VALIDATED',index=len(derived),cell_id=cid,batches=r['terminal']['batches'],new_simulations=0)),flush=True)
 assert {p.name for p in (root/'derived-controls').iterdir()}==set(derived) and len(derived)==1440
 save_new(root/'reuse-complete.json',dict(status='REUSE_AND_RECONSTRUCTION_VALIDATED',pairs=1440,new_simulations=0,manifest_sha256=sha(root/'manifest.json'),code_sha=m['code_sha'],result_hashes={cid:sha(root/'derived-controls'/cid/'result.json') for cid in derived}))
 from analysis import analyze
 analyze(root,m,derived)
 save_new(root/'complete.json',dict(status='VALIDATION_AND_DESCRIPTIVE_ANALYSIS_COMPLETE',pairs=1440,new_simulations=0,manifest_sha256=sha(root/'manifest.json'),code_sha=m['code_sha'],analysis_verification_sha256=sha(root/'analysis/verification.json'),scientific_review_required=True,finished_utc=stamp()))
 print('COMPLETE1440; scientific review required',stamp(),flush=True)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('root',type=pathlib.Path);a.add_argument('--preflight',action='store_true');a.add_argument('--pilot',type=pathlib.Path);a.add_argument('--base',type=pathlib.Path);v=a.parse_args()
 try:
  if v.pilot:pilot(v.root,v.pilot,v.base)
  elif v.preflight:
   m,cs,b=preflight(v.root,v.base);print(json.dumps(dict(status='PASS',pairs=1440,new_simulations=0,manifest_sha256=sha(v.root/'manifest.json'),code_sha=m['code_sha'])))
  else:run(v.root)
 except Exception:traceback.print_exc();sys.exit(1)
