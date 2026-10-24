"""Persistent, read-only audit of the failed run; never generates studies.

Only the explicitly supplied evidence directory is written. No repair or
recovery is authorized by this program, even when all archived batches pass.
"""
import argparse
import concurrent.futures
import datetime
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import traceback

from diagnose import bh_variants


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def read(path):
    return json.loads(path.read_text())


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def atomic(path, obj):
    temp = path.with_suffix('.tmp')
    with temp.open('w') as stream:
        json.dump(obj, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    temp.replace(path)


def check_batch(item, identity):
    from run import checked_batch
    path, sid, start = item
    metadata = read(path / 'integrity.json')
    # Existing independent referee: raw arrays, masks, identities, decisions,
    # endpoints and sufficient statistics; hashes checked before interpretation.
    checked_batch(path, sid, start, 25, identity)
    changes = []
    with gzip.open(path / 'studies.json.gz', 'rt') as stream:
        records = json.load(stream)
    for rec in records:
        for method in ('historical_screened_BH', 'historical_full_BH'):
            result = rec['methods'][method]
            indices = ([i for i, flag in enumerate(rec['historical']['eligible']) if flag]
                       if method == 'historical_screened_BH' else list(range(165)))
            variants = bh_variants([result['p'][i] for i in indices])
            for name in ('historical', 'exact_bootstrap'):
                different = [i for i, flag in zip(indices, variants[name])
                             if (flag and rec['historical']['supported'][i]) != result['reject'][i]]
                if different:
                    changes.append(dict(scenario=sid, replicate=rec['replicate'],
                                        method=method, interpretation=name,
                                        differing_hypotheses=different))
    return dict(path=str(path), scenario=sid, start=start, count=25,
                integrity_sha256=sha(path / 'integrity.json'),
                artifact_hashes=metadata['hashes'], alternative_decisions=changes)


def audit(root, out):
    sys.dont_write_bytecode = True
    root, out = root.resolve(), out.resolve()
    if out == root or root in out.parents:
        raise ValueError('audit evidence must be outside the preserved deployment')
    out.mkdir(parents=True, exist_ok=True)
    lock = (out / 'audit.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    # Never overwrite a previous audit attempt.
    events = (out / 'batches.jsonl').open('x')
    sys.path.insert(0, str(root / 'code'))
    import numpy
    import scipy
    launch = read(root / 'launch.json')
    environment = dict(python=platform.python_version(), numpy=numpy.__version__, scipy=scipy.__version__)
    if environment != launch['environment']:
        raise ValueError(('frozen environment mismatch', environment, launch['environment']))
    for group, folder in [('files', 'code'), ('historical_reference_files', 'reference')]:
        for name, expected in launch[group].items():
            if sha(root / folder / name) != expected:
                raise ValueError(('frozen file mismatch', folder, name))
    identity = hashlib.sha256(json.dumps(launch, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    run = root / 'runs' / ('stat01-' + identity[:16])
    if read(run / 'launch.json') != launch:
        raise ValueError('run launch differs from deployment launch')
    before = {name: sha(run / name) for name in ('checkpoint.json', 'launch.json', 'failure-907454.json')}
    cp = read(run / 'checkpoint.json')
    if cp['identity'] != identity:
        raise ValueError('checkpoint identity mismatch')
    items, inventory, partials = [], [], []
    for sid in range(len(launch['scenarios'])):
        directory = run / 'batches' / f'scenario-{sid:02d}'
        complete = sorted(p for p in directory.iterdir() if '.part-' not in p.name)
        partials.extend(str(p) for p in directory.iterdir() if '.part-' in p.name)
        for j, path in enumerate(complete):
            if path.name != f'rep-{25*j:06d}':
                raise ValueError(('batch gap', path))
            items.append((path, sid, j * 25))
        inventory.append(dict(scenario=sid, finalized_studies=len(complete)*25,
                              checkpoint_studies=cp['scenarios'][str(sid)]['n']))
    state = dict(status='RUNNING', started=now(), pid=os.getpid(), root=str(root),
                 environment=environment, identity=identity, expected_batches=len(items),
                 expected_studies=len(items)*25, checked_batches=0, checked_studies=0,
                 failed_batches=[], inventory=inventory, partials=partials,
                 alternative_study_counts={}, source_snapshot=before,
                 reuse_authorized=False, recovery_launched=False)
    atomic(out / 'progress.json', state)
    print(json.dumps(dict(event='AUDIT_STARTED', **state)), flush=True)
    affected = {'historical': set(), 'exact_bootstrap': set()}
    # Bound memory and shared-filesystem pressure to two in-flight batches.
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        pending = {}
        todo = iter(items)
        for _ in range(2):
            item = next(todo, None)
            if item:
                pending[pool.submit(check_batch, item, identity)] = item
        while pending:
            done, _ = concurrent.futures.wait(pending, return_when=concurrent.futures.FIRST_COMPLETED)
            for future in done:
                item = pending.pop(future)
                try:
                    result = future.result()
                    for change in result['alternative_decisions']:
                        affected[change['interpretation']].add((change['scenario'], change['replicate']))
                    state['checked_batches'] += 1
                    state['checked_studies'] += 25
                    events.write(json.dumps(result, sort_keys=True) + '\n')
                except Exception:
                    failure = dict(path=str(item[0]), traceback=traceback.format_exc())
                    state['failed_batches'].append(failure)
                    print(json.dumps(dict(event='BATCH_AUDIT_FAILURE', **failure)), flush=True)
                item = next(todo, None)
                if item:
                    pending[pool.submit(check_batch, item, identity)] = item
            state['updated'] = now()
            state['alternative_study_counts'] = {k: len(v) for k, v in affected.items()}
            atomic(out / 'progress.json', state)
            events.flush()
            if state['checked_batches'] and state['checked_batches'] % 25 == 0:
                print(json.dumps(dict(event='AUDIT_PROGRESS', time=now(),
                                      checked_batches=state['checked_batches'],
                                      failed_batches=len(state['failed_batches']))), flush=True)
    events.flush()
    os.fsync(events.fileno())
    events.close()
    state['source_snapshot_unchanged'] = all(sha(run / name) == digest for name, digest in before.items())
    state['status'] = ('COMPLETED_SUCCESS' if not state['failed_batches'] and state['source_snapshot_unchanged'] else 'FAILED')
    state['finished'] = now()
    state['batch_evidence_sha256'] = sha(out / 'batches.jsonl')
    state['interpretation'] = 'Original-validator integrity only. Alternatives are diagnostic; no corrected reuse decision.'
    atomic(out / 'summary.json', state)
    atomic(out / 'progress.json', state)
    print(json.dumps(state, sort_keys=True), flush=True)
    return 0 if state['status'] == 'COMPLETED_SUCCESS' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--original-root', type=Path, required=True)
    parser.add_argument('--evidence-dir', type=Path, required=True)
    args = parser.parse_args()
    try:
        sys.exit(audit(args.original_root, args.evidence_dir))
    except Exception:
        args.evidence_dir.mkdir(parents=True, exist_ok=True)
        atomic(args.evidence_dir / 'audit-failure.json', dict(time=now(), traceback=traceback.format_exc()))
        raise
