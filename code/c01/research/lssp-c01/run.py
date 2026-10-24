#!/usr/bin/env python3
"""One resumable CPU pilot; external files verified before using any outcome."""
import argparse, dataclasses, datetime, fcntl, gzip, hashlib, json, os, platform, sys, time, traceback
from pathlib import Path
from engine import simulate
from policies import Config
from validator import validate

HERE = Path(__file__).resolve().parent

def read(path): return json.loads(Path(path).read_text())
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def canonical(obj): return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def stamp(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def atomic(path,obj):
    tmp=path.with_name(path.name+f'.{os.getpid()}.tmp')
    with tmp.open('w') as f:
        json.dump(obj,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)

def events(path):
    with gzip.open(path,'rt') as f:
        for line in f: yield json.loads(line)

def checked_cell(directory,condition,profile,policy,identity):
    record=read(directory/'result.json')
    if record['identity']!=identity or record['condition_id']!=condition['condition_id'] or record['profile']!=profile['name'] or record['policy']!=policy:
        raise ValueError('resume identity mismatch')
    if sha(directory/'events.jsonl.gz')!=record['journal_sha256']:
        raise ValueError('resume journal hash mismatch')
    metrics=validate(condition['requests'],profile['config'],events(directory/'events.jsonl.gz'),record['terminal'])
    if metrics!=record['metrics']:raise ValueError('resume metric mismatch')
    return record

def run(inputs,launch,out):
    spec=read(launch)
    for name,expected in spec['files'].items():
        if sha(HERE/name)!=expected: raise ValueError('code/protocol fingerprint mismatch: '+name)
    manifest=read(HERE/'input_manifest.json')
    if sha(inputs)!=manifest['input_sha256'] or spec['input_sha256']!=manifest['input_sha256']:
        raise ValueError('input payload mismatch')
    data=read(inputs)
    if len(data['conditions'])!=len(manifest['conditions']):raise ValueError('condition mismatch')
    for c,m in zip(data['conditions'],manifest['conditions']):
        if canonical(c['requests'])!=m['requests_sha256'] or c['condition_id']!=m['condition_id']:
            raise ValueError('per-condition input mismatch')
    identity=canonical(spec)
    out.mkdir(parents=True,exist_ok=True)
    lock=(out/'run.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if (out/'launch.json').exists() and read(out/'launch.json')!=spec:raise ValueError('run directory collision')
    atomic(out/'launch.json',spec)
    atomic(out/'environment.json',dict(time=stamp(),python=sys.version,platform=platform.platform(),pid=os.getpid(),job_id=os.environ.get('SLURM_JOB_ID'),cpus=os.environ.get('SLURM_CPUS_PER_TASK'),cuda_visible=os.environ.get('CUDA_VISIBLE_DEVICES')))
    checkpoint=dict(identity=identity,status='STARTED',expected_cells=manifest['expected_cells'],completed_cells=[],updated_at=stamp())
    atomic(out/'checkpoint.json',checkpoint)
    print(json.dumps(dict(event='STARTED',time=stamp(),identity=identity,out=str(out),pid=os.getpid())),flush=True)
    for c in data['conditions']:
        for profile in manifest['profiles']:
            for policy in manifest['policies']:
                key=c['condition_id']+'::'+profile['name']+'::'+policy
                directory=out/'cells'/hashlib.sha256(key.encode()).hexdigest()[:24]
                directory.mkdir(parents=True,exist_ok=True)
                if (directory/'result.json').exists():
                    checked_cell(directory,c,profile,policy,identity)
                    state='REUSED_VALIDATED'
                else:
                    # Leftover failed attempts are retained, never overwritten.
                    attempt=str(time.time_ns())
                    journal=directory/f'events.{attempt}.part.gz'
                    print(json.dumps(dict(event='CELL_START',key=key,time=stamp())),flush=True)
                    with gzip.open(journal,'wt') as f:
                        def emit(e):
                            f.write(json.dumps(e,separators=(',',':'),allow_nan=False)+'\n')
                        terminal=simulate(c['requests'],policy,Config(**profile['config']),emit)
                    metrics=validate(c['requests'],profile['config'],events(journal),terminal)
                    if (directory/'events.jsonl.gz').exists():
                        raise ValueError('orphan final journal: manual investigation required')
                    os.rename(journal,directory/'events.jsonl.gz')
                    record=dict(identity=identity,condition_id=c['condition_id'],profile=profile['name'],policy=policy,
                        requests_sha256=c['requests_sha256'],journal_sha256=sha(directory/'events.jsonl.gz'),
                        terminal=terminal,metrics=metrics,validated=True,validated_at=stamp())
                    atomic(directory/'result.json',record)
                    state='NEW_VALIDATED'
                checkpoint['completed_cells'].append(dict(key=key,path=str(directory.relative_to(out)),state=state))
                checkpoint['updated_at']=stamp();atomic(out/'checkpoint.json',checkpoint)
                print(json.dumps(dict(event='CELL_VALIDATED',key=key,count=len(checkpoint['completed_cells']),time=stamp())),flush=True)
    checkpoint['status']='EXECUTION_AND_EVENT_VALIDATION_COMPLETE'
    checkpoint['updated_at']=stamp();atomic(out/'checkpoint.json',checkpoint)
    print(json.dumps(dict(event=checkpoint['status'],cells=len(checkpoint['completed_cells']),time=stamp())),flush=True)
    # Descriptive reporting only after all cells independently validated.
    from analyze import analyze
    analyze(data,manifest,out,identity)
    atomic(out/'complete.json',dict(status='PILOT_COMPLETE',identity=identity,time=stamp(),publication_ready=False,job2_authorized=False))
    return 0

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);p.add_argument('--launch',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    try:
        sys.exit(run(a.inputs,a.launch,a.out))
    except Exception as error:
        # Never claim successful evidence following environment/integrity failure.
        a.out.mkdir(parents=True,exist_ok=True)
        atomic(a.out/f'failure-{os.getpid()}.json',dict(time=stamp(),error=repr(error),traceback=traceback.format_exc()))
        raise
