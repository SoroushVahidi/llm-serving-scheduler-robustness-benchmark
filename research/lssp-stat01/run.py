#!/usr/bin/env python3
"""Persistent one-job Monte Carlo runner; independent immutable batch validation."""
import argparse,concurrent.futures,datetime,fcntl,gzip,hashlib,json,os,platform,signal,sys,time,traceback
from pathlib import Path
import numpy as np
from design import SCENARIOS,METHODS,LOOKS,BATCH
from experiment import study
from reference import validate_record
from precision import sufficient,merge_stats,summarize_stats

HERE=Path(__file__).resolve().parent

def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def canonical(obj):return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def read(path):return json.loads(Path(path).read_text())
def atomic(path,obj):
    tmp=path.with_name(path.name+f'.{os.getpid()}.tmp')
    with tmp.open('w') as f:
        json.dump(obj,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)

def batch_path(out,sid,start):return out/'batches'/f'scenario-{sid:02d}'/f'rep-{start:06d}'

def checked_batch(path,sid,start,count,identity,engineering=False):
    meta=read(path/'integrity.json')
    if meta['identity']!=identity or (meta['scenario'],meta['start'],meta['count'])!=(sid,start,count):raise ValueError('batch identity')
    for f,h in meta['hashes'].items():
        if sha(path/f)!=h:raise ValueError('batch hash mismatch: '+f)
    with np.load(path/'raw.npz',allow_pickle=False) as raw:
        y,mask=raw['y'],raw['mask']
    with gzip.open(path/'studies.json.gz','rt') as f:records=json.load(f)
    if len(records)!=count or len(y)!=count or len(mask)!=count:raise ValueError('batch count')
    for i,r in enumerate(records):
        if r['seed_namespace']!=(0 if engineering else 1):raise ValueError('seed namespace')
        validate_record(SCENARIOS[sid],y[i],mask[i],r,sid,start+i)
    stats=sufficient(records)
    if stats!=meta['sufficient']:raise ValueError('aggregate mismatch')
    return stats


def execute_batch(out,sid,start,count,identity,engineering=False):
    out=Path(out);path=batch_path(out,sid,start)
    if path.exists():return sid,start,checked_batch(path,sid,start,count,identity,engineering),'REUSED_VALIDATED'
    part=path.with_name(path.name+f'.part-{os.getpid()}-{time.time_ns()}');part.mkdir(parents=True)
    ys=[];masks=[];records=[]
    for rep in range(start,start+count):
        y,mask,record=study(sid,rep,engineering=engineering)
        validate_record(SCENARIOS[sid],y,mask,record,sid,rep)
        ys.append(y);masks.append(mask);records.append(record)
    np.savez_compressed(part/'raw.npz',y=np.stack(ys),mask=np.stack(masks))
    with gzip.open(part/'studies.json.gz','wt') as f:json.dump(records,f,separators=(',',':'),allow_nan=False)
    stats=sufficient(records)
    meta=dict(identity=identity,scenario=sid,start=start,count=count,validated_at=stamp(),
              hashes={f:sha(part/f) for f in ('raw.npz','studies.json.gz')},sufficient=stats)
    atomic(part/'integrity.json',meta)
    # Read-back independent validation before publishing a batch as complete.
    checked_batch(part,sid,start,count,identity,engineering)
    if path.exists():raise ValueError('batch output collision')
    os.rename(part,path)
    return sid,start,stats,'NEW_VALIDATED'


def run(out,launch,workers=4,hours=8.75):
    spec=read(launch)
    for name,expected in spec['files'].items():
        if sha(HERE/name)!=expected:raise ValueError('code/design hash mismatch: '+name)
    if spec['scenarios']!=SCENARIOS or spec['methods']!=list(METHODS):raise ValueError('design mismatch')
    engineering=spec.get('engineering_only',False)
    import scipy
    if not engineering:
        expected=spec['environment']
        if (np.__version__,scipy.__version__,platform.python_version())!=(expected['numpy'],expected['scipy'],expected['python']):
            raise ValueError('frozen numerical environment mismatch')
        for name,expected_hash in spec['historical_reference_files'].items():
            if sha(HERE.parent/'reference'/name)!=expected_hash:raise ValueError('historical reference hash mismatch')
    identity=canonical(spec);out.mkdir(parents=True,exist_ok=True)
    lock=(out/'run.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if (out/'launch.json').exists() and read(out/'launch.json')!=spec:raise ValueError('output identity collision')
    atomic(out/'launch.json',spec)
    import scipy
    atomic(out/f'environment-{os.getpid()}.json',dict(time=stamp(),pid=os.getpid(),python=sys.version,numpy=np.__version__,scipy=scipy.__version__,platform=platform.platform(),job_id=os.environ.get('SLURM_JOB_ID'),cpus=os.environ.get('SLURM_CPUS_PER_TASK')))
    state={sid:dict(n=0,sums=None,status='ACTIVE',last_look=None) for sid in range(len(SCENARIOS))}
    deadline=time.monotonic()+hours*3600
    stop=[False]
    signal.signal(signal.SIGUSR1,lambda *_:stop.__setitem__(0,True))
    def checkpoint(status):
        atomic(out/'checkpoint.json',dict(identity=identity,time=stamp(),status=status,scenarios={str(s):{k:v for k,v in x.items() if k!='sums'} for s,x in state.items()}))
    checkpoint('INITIALIZING_RESUME_VALIDATION')
    # Reconstruct authority from independently verified immutable batches, not a mutable checkpoint.
    for sid,x in state.items():
        files=sorted((out/'batches'/f'scenario-{sid:02d}').glob('rep-*')) if (out/'batches'/f'scenario-{sid:02d}').exists() else []
        complete=[p for p in files if '.part-' not in p.name]
        for p in complete:
            start=int(p.name.split('-')[1])
            if start!=x['n'] or x['status']!='ACTIVE':raise ValueError('batch gap or batch beyond prespecified stopping')
            st=checked_batch(p,sid,start,BATCH,identity,engineering);x['sums']=merge_stats(x['sums'],st);x['n']+=BATCH
            if x['n'] in LOOKS:
                summary=summarize_stats(x['sums'],x['n'],SCENARIOS[sid]);x['last_look']=x['n']
                atomic(out/f'look-s{sid:02d}-n{x["n"]:05d}.json',summary)
                if summary['precision_objective_met']:x['status']='PRECISION_STOP'
                elif x['n']==LOOKS[-1]:x['status']='MAXIMUM_COUNT'
    checkpoint('RUNNING')
    print(json.dumps(dict(event='STARTED',time=stamp(),identity=identity,workers=workers,pid=os.getpid(),out=str(out))),flush=True)
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        pending={};busy=set()
        while True:
            active=[s for s,x in state.items() if x['status']=='ACTIVE' and s not in busy]
            active.sort(key=lambda s:(state[s]['n'],s))
            while active and len(pending)<workers and not stop[0] and time.monotonic()<deadline:
                sid=active.pop(0);start=state[sid]['n'];busy.add(sid)
                f=pool.submit(execute_batch,str(out),sid,start,BATCH,identity,engineering);pending[f]=(sid,start)
                print(json.dumps(dict(event='BATCH_START',scenario=sid,start=start,time=stamp())),flush=True)
            if not pending:break
            done,_=concurrent.futures.wait(pending,return_when=concurrent.futures.FIRST_COMPLETED)
            for f in done:
                sid,start,stats,mode=f.result();pending.pop(f);busy.remove(sid);x=state[sid]
                if start!=x['n']:raise ValueError('unexpected batch index')
                x['sums']=merge_stats(x['sums'],stats);x['n']+=BATCH
                if x['n'] in LOOKS:
                    summary=summarize_stats(x['sums'],x['n'],SCENARIOS[sid]);x['last_look']=x['n']
                    atomic(out/f'look-s{sid:02d}-n{x["n"]:05d}.json',summary)
                    if summary['precision_objective_met']:x['status']='PRECISION_STOP'
                    elif x['n']==LOOKS[-1]:x['status']='MAXIMUM_COUNT'
                checkpoint('RUNNING')
                print(json.dumps(dict(event='BATCH_VALIDATED',scenario=sid,studies=x['n'],state=x['status'],mode=mode,time=stamp())),flush=True)
    incomplete=any(x['status']=='ACTIVE' for x in state.values())
    status='TIME_BUDGET_PARTIAL' if incomplete else 'COMPLETE_WITH_PRECISION_GAPS' if any(x['status']=='MAXIMUM_COUNT' for x in state.values()) else 'COMPLETE_PRECISION_OBJECTIVES'
    checkpoint(status)
    atomic(out/'completion.json',dict(status=status,time=stamp(),identity=identity,scientific_interpretation='REQUIRES_AUTHOR_REVIEW_NOT_UNIVERSAL_VALIDATION'))
    print(json.dumps(dict(event=status,time=stamp())),flush=True)
    return 0 if not incomplete else 2

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--launch',type=Path,required=True);p.add_argument('--workers',type=int,default=4);a=p.parse_args()
    try:sys.exit(run(a.out,a.launch,a.workers))
    except Exception as e:
        a.out.mkdir(parents=True,exist_ok=True)
        atomic(a.out/f'failure-{os.getpid()}.json',dict(time=stamp(),error=repr(e),traceback=traceback.format_exc()))
        raise
