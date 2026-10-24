"""One frozen, non-overwriting M3-TIME01 CPU campaign."""
import argparse, datetime, fcntl, gzip, json, os, pathlib, platform, sys, time, traceback
from support import HERE, sha, canon, save_new, verify_policy
from policies import Config
from timing import Timing
from timed_engine import simulate
from timed_validator import validate, quantile

def stamp(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def read(p): return json.loads(pathlib.Path(p).read_text())

def preflight(root):
    m=read(root/'manifest.json')
    assert m['experiment']=='M3-TIME01' and len(m['cells'])==384
    assert len(set(m['missing_cells']))==384 and set(m['missing_cells'])=={c['cell_id'] for c in m['cells']}
    for name,digest in m['files'].items(): assert sha(HERE/name)==digest, name
    assert sha(root/'inputs.json')==m['inputs_sha256']
    assert sha(root/'selection.json')==m['selection_sha256']
    conditions={c['condition_id']:c for c in read(root/'inputs.json')['conditions']}
    assert len(conditions)==48
    for c in conditions.values(): assert canon(c['requests'])==c['requests_sha256']
    for cell in m['cells']:
        i=cell['identity'];c=conditions[i['condition_id']]
        assert canon(i)==cell['cell_id'] and i['code_sha']==m['code_sha'] and i['timing']==m['timing']
        assert i['requests_sha256']==c['requests_sha256'] and i['synthesis_seed']==c['synthesis_seed'] and i['load_factor']==c['load_factor']
        b=cell['baseline'];assert sha(root/b['local_file'])==b['result_sha256']
        record=read(root/b['local_file'])
        assert record['identity']==b['record_identity'] and record['validated']
    return m,conditions

def telemetry(events,requests,cfg,policy,terminal):
    ds=[e['timing']['duration'] for e in events]
    totals={k:sum(e['timing']['urgency'][k] for e in events) for k in ('ready','critical','selected_critical','omitted')}
    return dict(duration=dict(n=len(ds),min=min(ds) if ds else None,max=max(ds) if ds else None,
        mean=sum(ds)/len(ds) if ds else None,p50=quantile(ds,.5),p95=quantile(ds,.95)),
        composition=dict(prefill_tokens=sum(e['timing']['prefill_tokens'] for e in events),
            decode_tokens=sum(e['timing']['decode_tokens'] for e in events),
            mixed_batches=sum(e['timing']['prefill_tokens']>0 and e['timing']['decode_tokens']>0 for e in events),
            prefill_only_batches=sum(e['timing']['prefill_tokens']>0 and e['timing']['decode_tokens']==0 for e in events),
            decode_only_batches=sum(e['timing']['prefill_tokens']==0 and e['timing']['decode_tokens']>0 for e in events)),
        urgency=dict(**totals,max_age=max((e['timing']['urgency']['max_age'] for e in events),default=0.)),
        admission=verify_policy(requests,cfg,policy,events,terminal))

def checked(root,m,c,conditions):
    folder=root/'cells'/c['cell_id'];r=read(folder/'result.json')
    assert r['cell_id']==c['cell_id'] and r['identity']==c['identity'] and r['manifest_sha256']==sha(root/'manifest.json')
    assert r['validated'] and sha(folder/'events.jsonl.gz')==r['journal_sha256']
    with gzip.open(folder/'events.jsonl.gz','rt') as f:events=[json.loads(line) for line in f]
    rs=conditions[c['identity']['condition_id']]['requests'];cfg=c['identity']['config']
    assert validate(rs,cfg,events,r['terminal'],m['timing'])==r['metrics']
    assert telemetry(events,rs,cfg,c['identity']['policy'],r['terminal'])==r['telemetry']
    return r

def main():
    ap=argparse.ArgumentParser();ap.add_argument('root',type=pathlib.Path);ap.add_argument('--preflight',action='store_true');a=ap.parse_args()
    m,cs=preflight(a.root)
    if a.preflight:
        print(json.dumps(dict(status='PASS',cells=384,code_sha=m['code_sha'],manifest_sha256=sha(a.root/'manifest.json'))));return
    ex=read(a.root/'execution.json')
    assert ex['manifest_sha256']==sha(a.root/'manifest.json') and ex['validation_status']=='PASS'
    assert ex['code_sha']==m['code_sha'] and ex['new_cells']==384
    # This invocation never resumes implicitly or replaces any prior valid output.
    lock=(a.root/'run.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    (a.root/'cells').mkdir(exist_ok=False)
    save_new(a.root/'run-start.json',dict(started_utc=stamp(),job_id=os.environ.get('SLURM_JOB_ID'),
        code_sha=m['code_sha'],manifest_sha256=sha(a.root/'manifest.json'),execution_sha256=sha(a.root/'execution.json'),
        python=sys.version,executable=sys.executable,platform=platform.platform()))
    print(json.dumps(dict(event='START',utc=stamp(),code_sha=m['code_sha'],manifest_sha256=sha(a.root/'manifest.json'),cells=384)),flush=True)
    start=time.monotonic();done=[];timing=Timing(**m['timing'])
    for cell in m['cells']:
        if time.monotonic()-start>5400:
            save_new(a.root/'partial.json',dict(completed=done,missing=[c['cell_id'] for c in m['cells'] if c['cell_id'] not in done],reason='90-minute scheduling cutoff'))
            raise RuntimeError('campaign scheduling cutoff reached')
        cid=cell['cell_id'];i=cell['identity'];rs=cs[i['condition_id']]['requests'];cfg=i['config']
        dest=a.root/'cells'/cid;stage=a.root/'cells'/(cid+'.partial');stage.mkdir(exist_ok=False)
        es=[];t0=time.monotonic();terminal=simulate(rs,i['policy'],Config(**cfg),es.append,timing)
        metrics=validate(rs,cfg,es,terminal,m['timing']);telem=telemetry(es,rs,cfg,i['policy'],terminal)
        journal=stage/'events.jsonl.gz'
        with journal.open('xb') as raw:
            with gzip.GzipFile(fileobj=raw,filename='',mode='wb',mtime=0) as z:
                for e in es:z.write((json.dumps(e,separators=(',',':'),allow_nan=False)+'\n').encode())
        r=dict(cell_id=cid,identity=i,manifest_sha256=sha(a.root/'manifest.json'),baseline=cell['baseline'],
            terminal=terminal,metrics=metrics,telemetry=telem,journal_sha256=sha(journal),validated=True,
            elapsed_seconds=time.monotonic()-t0,finished_utc=stamp())
        save_new(stage/'result.json',r)
        # Read bytes back before promoting; no silent replacement even on restart.
        with gzip.open(journal,'rt') as f:reread=[json.loads(line) for line in f]
        assert validate(rs,cfg,reread,terminal,m['timing'])==metrics
        assert not dest.exists();stage.rename(dest);done.append(cid)
        print(json.dumps(dict(event='CELL',index=len(done),cell_id=cid,batches=terminal['batches'],
            completed=metrics['num_completed'],elapsed_seconds=r['elapsed_seconds'])),flush=True)
    actual={p.name for p in (a.root/'cells').iterdir()}
    assert actual==set(m['missing_cells'])==set(done)
    save_new(a.root/'complete.json',dict(status='EXECUTION_VALIDATED',cells=len(done),
        code_sha=m['code_sha'],manifest_sha256=sha(a.root/'manifest.json'),finished_utc=stamp(),
        result_hashes={cid:sha(a.root/'cells'/cid/'result.json') for cid in done},
        analysis_pending=True,scientific_review_required=True))
    print(json.dumps(dict(event='COMPLETE',cells=len(done),analysis_pending=True)),flush=True)

if __name__=='__main__':
    try:main()
    except Exception:
        traceback.print_exc();sys.exit(1)
