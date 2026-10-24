#!/usr/bin/env python3
"""One checkpointed campaign, with byte-preserving pilot reuse and fail-closed resume."""
import argparse, fcntl, gzip, json, os, platform, signal, sys, time, traceback
from pathlib import Path
from common import HERE,read,sha,digest,atomic,immutable,stamp,check_inputs,check_record,cell_id,simulate,Config,validate,events
STOP=False

def stopped(*_):
    global STOP
    STOP=True

def validate_launch(root,spec):
    for name,expected in spec['files'].items():
        if sha(root/name)!=expected:raise ValueError('launch fingerprint mismatch: '+name)
    if platform.python_version()!=spec['python_version']:raise ValueError('unpinned Python interpreter')

def verify_all(root,out,data,manifest,spec,deadline=None):
    rows=[];identity=digest(spec);reuse={x['key']:x for x in read(root/spec['reuse_index'])['cells']}
    planned=check_inputs(data,manifest);expected_new={cell_id(k) for k,*_ in planned if k not in reuse}
    actual={p.name for p in (out/'cells').iterdir()} if (out/'cells').exists() else set()
    if actual!=expected_new:raise ValueError('incomplete/foreign new cell coverage')
    if set(reuse)-{x[0] for x in planned}:raise ValueError('foreign reused cell')
    for k,c,p,a in planned:
        if STOP or (deadline is not None and time.monotonic()>=deadline):return None
        if k in reuse:
            entry=reuse[k];directory=root/entry['staged_path'];rid=entry['identity'];expected_hash=entry['result_sha256']
        else:directory=out/'cells'/cell_id(k);rid=identity;expected_hash=None
        r=check_record(directory,c,p,a,rid,expected_hash)
        if k in reuse and r['journal_sha256']!=entry['journal_sha256']:raise ValueError('reuse journal identity')
        rows.append(dict(source=c['source'],window=c['window'],region=c['region'],profile=p['name'],policy=a,load_factor=c['load_factor'],synthesis_seed=c['synthesis_seed'],condition_id=c['condition_id'],requests_sha256=c['requests_sha256'],record_identity=rid,result_path=str(directory.relative_to(root)),result_sha256=sha(directory/'result.json'),journal_sha256=r['journal_sha256'],reused=k in reuse,metrics=r['metrics']))
    return rows

def campaign(root,out,spec,schedule_seconds=28800,verify_only=False):
    start=time.monotonic();validate_launch(root,spec)
    manifest=read(root/spec['manifest']);data=read(root/spec['inputs']);planned=check_inputs(data,manifest)
    if sha(root/spec['inputs'])!=manifest['input_sha256']:raise ValueError('input payload fingerprint')
    reuse_doc=read(root/spec['reuse_index']);reuse={x['key']:x for x in reuse_doc['cells']}
    if len(reuse)!=len(reuse_doc['cells']) or set(reuse)-{x[0] for x in planned}:raise ValueError('reuse coverage')
    identity=digest(spec);out.mkdir(parents=True,exist_ok=True)
    lock=(out/'run.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    allowed={cell_id(k) for k,*_ in planned if k not in reuse}
    existing={p.name for p in (out/'cells').iterdir()} if (out/'cells').exists() else set()
    if not existing<=allowed:raise ValueError('foreign existing cell coverage')
    immutable(out/'launch.json',spec)
    if not (out/'environment.json').exists():
        immutable(out/'environment.json',dict(python=sys.version,platform=platform.platform(),job_id=os.environ.get('SLURM_JOB_ID'),launch_identity=identity))
    cp=dict(identity=identity,expected=len(planned),completed=[],status='STARTED',updated_at=stamp())
    def checkpoint(status):
        cp.update(status=status,updated_at=stamp(),reused=sum(x['origin']=='PILOT' for x in cp['completed']),new=len([x for x in cp['completed'] if x['origin']=='FULL']))
        atomic(out/'checkpoint.json',cp)
    if not verify_only:
        checkpoint('RUNNING');print(json.dumps(dict(event='STARTED',identity=identity,time=stamp(),expected=len(planned),reusable=len(reuse))),flush=True)
        for k,c,p,a in planned:
            if STOP or time.monotonic()-start>=schedule_seconds:
                checkpoint('PARTIAL_SAFE_STOP');return 0
            if k in reuse:
                entry=reuse[k];r=check_record(root/entry['staged_path'],c,p,a,entry['identity'],entry['result_sha256'])
                if r['journal_sha256']!=entry['journal_sha256']:raise ValueError('reuse journal fingerprint')
                origin='PILOT'
            else:
                directory=out/'cells'/cell_id(k)
                if directory.exists():check_record(directory,c,p,a,identity)
                else:
                    attempt=out/'attempts'/(cell_id(k)+'-'+str(time.time_ns()));attempt.mkdir(parents=True)
                    journal=attempt/'events.jsonl.gz'
                    print(json.dumps(dict(event='CELL_START',key=k,time=stamp())),flush=True)
                    with gzip.open(journal,'wt') as f:
                        def emit(e):f.write(json.dumps(e,separators=(',',':'),allow_nan=False)+'\n')
                        terminal=simulate(c['requests'],a,Config(**p['config']),emit)
                    with journal.open('rb') as durable:os.fsync(durable.fileno())
                    metrics=validate(c['requests'],p['config'],events(journal),terminal)
                    immutable(attempt/'result.json',dict(identity=identity,condition_id=c['condition_id'],profile=p['name'],policy=a,requests_sha256=c['requests_sha256'],journal_sha256=sha(journal),terminal=terminal,metrics=metrics,validated=True,validated_at=stamp()))
                    directory.parent.mkdir(exist_ok=True);os.rename(attempt,directory)
                    parent_fd=os.open(directory.parent,os.O_RDONLY)
                    try:os.fsync(parent_fd)
                    finally:os.close(parent_fd)
                origin='FULL'
            cp['completed'].append(dict(key=k,origin=origin));checkpoint('RUNNING')
            print(json.dumps(dict(event='CELL_VALIDATED',key=k,origin=origin,count=len(cp['completed']),time=stamp())),flush=True)
        checkpoint('CELLS_COMPLETE_FINAL_VALIDATION_PENDING')
    rows=verify_all(root,out,data,manifest,spec,None if verify_only else start+31200)
    if rows is None:
        checkpoint('CELLS_COMPLETE_ANALYSIS_DEFERRED');return 0
    from analysis_full import write_analysis
    report=write_analysis(rows,manifest,out/'analysis')
    immutable(out/'complete.json',dict(status='EXECUTION_AND_INDEPENDENT_CHECKS_COMPLETE',identity=identity,cells=len(rows),reused=len(reuse),new=len(rows)-len(reuse),validation=report,scientific_review_required=True,publication_ready=False))
    if not verify_only:checkpoint('EXECUTION_AND_INDEPENDENT_CHECKS_COMPLETE')
    print(json.dumps(dict(event='COMPLETE',cells=len(rows),scientific_review_required=True)),flush=True)
    return 0

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--verify-only',action='store_true');a=p.parse_args()
    signal.signal(signal.SIGTERM,stopped);signal.signal(signal.SIGINT,stopped)
    try:sys.exit(campaign(a.root,a.out,read(a.root/'launch.json'),verify_only=a.verify_only))
    except Exception as e:
        atomic(a.out/('failure-'+str(time.time_ns())+'.json'),dict(time=stamp(),error=repr(e),traceback=traceback.format_exc()));raise
