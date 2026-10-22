#!/usr/bin/env python3
"""Checkpointed derivation/recovery. Original deployment is read-only input."""
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
import shutil
import signal
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, os.environ.get('STAT01_FROZEN_CODE', str(HERE.parent)))
import numpy as np
import scipy
from design import SCENARIOS, METHODS, LOOKS, BATCH
from experiment import study
from precision import sufficient as original_sufficient
from rv2_methods import derive, ALL_METHODS
from rv2_reference import validate
from rv2_summary import sufficient, merge, summarize


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def canonical(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def atomic(path, value):
    path = Path(path)
    part = path.with_name(path.name + f'.{os.getpid()}.tmp')
    with part.open('w') as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(part, path)


def event(name, **fields):
    print(json.dumps(dict(event=name, time=stamp(), **fields), sort_keys=True), flush=True)


def load_payload(path):
    with np.load(path / 'raw.npz', allow_pickle=False) as raw:
        y, mask = raw['y'], raw['mask']
    with gzip.open(path / 'studies.json.gz', 'rt') as stream:
        records = json.load(stream)
    return y, mask, records


def verify_source(source, original_identity):
    path = Path(source['path'])
    if sha(path / 'integrity.json') != source['integrity_sha256']:
        raise ValueError('audited source metadata changed')
    meta = read(path / 'integrity.json')
    if (meta['scenario'], meta['start'], meta['count'], meta['identity']) != (
            source['scenario'], source['start'], source['count'], original_identity):
        raise ValueError('audited source identity mismatch')
    if meta['hashes'] != source['artifact_hashes']:
        raise ValueError('source hash manifest mismatch')
    for name, expected in source['artifact_hashes'].items():
        if sha(path / name) != expected:
            raise ValueError('audited source artifact changed: ' + name)
    y, mask, records = load_payload(path)
    if len(records) != source['count'] or len(y) != len(records) or len(mask) != len(records):
        raise ValueError('source count mismatch')
    if original_sufficient(records) != meta['sufficient']:
        raise ValueError('source aggregate mismatch')
    return y, mask, records


def checked_batch(path, sid, start, count, identity, source=None, namespace=1):
    meta = read(path / 'integrity.json')
    if (meta['identity'], meta['scenario'], meta['start'], meta['count']) != (identity, sid, start, count):
        raise ValueError('recovery batch identity mismatch')
    expected_origin = source if source is not None else dict(generated=True, seed_namespace=namespace)
    if meta['origin'] != expected_origin:
        raise ValueError('recovery provenance mismatch')
    if set(meta['hashes']) != {'raw.npz', 'studies.json.gz', 'secondary.json.gz'}:
        raise ValueError('recovery artifact inventory')
    for name, expected in meta['hashes'].items():
        if sha(path / name) != expected:
            raise ValueError('recovery artifact hash mismatch: ' + name)
    if source:
        for name in ('raw.npz', 'studies.json.gz'):
            if meta['hashes'][name] != source['artifact_hashes'][name]:
                raise ValueError('original artifact was not preserved byte for byte')
    y, mask, records = load_payload(path)
    with gzip.open(path / 'secondary.json.gz', 'rt') as stream:
        extra = json.load(stream)
    if not (len(records) == len(y) == len(mask) == len(extra) == count):
        raise ValueError('recovery count mismatch')
    for i, (rec, additions) in enumerate(zip(records, extra)):
        validate(SCENARIOS[sid], y[i], mask[i], rec, additions, sid, start+i, namespace)
    sums = sufficient(records, extra)
    if sums != meta['sufficient']:
        raise ValueError('recovery summary mismatch')
    return sums


def execute_batch(out, sid, start, count, identity, original_identity, source=None, engineering=False):
    path = Path(out) / 'batches' / f'scenario-{sid:02d}' / f'rep-{start:06d}'
    namespace = 0 if engineering else 1
    if path.exists():
        return sid, start, checked_batch(path, sid, start, count, identity, source, namespace), 'RESUMED_VERIFIED'
    part = path.with_name(path.name + f'.part-{os.getpid()}-{time.time_ns()}')
    part.mkdir(parents=True)
    if source:
        y, mask, records = verify_source(source, original_identity)
        for name in ('raw.npz', 'studies.json.gz'):
            shutil.copyfile(Path(source['path']) / name, part / name)
        mode = 'REUSED_AUDITED_ORIGINAL'
    else:
        ys, masks, records = [], [], []
        for rep in range(start, start+count):
            yy, mm, record = study(sid, rep, engineering=engineering)
            ys.append(yy)
            masks.append(mm)
            records.append(record)
        y, mask = np.stack(ys), np.stack(masks)
        np.savez_compressed(part / 'raw.npz', y=y, mask=mask)
        with gzip.open(part / 'studies.json.gz', 'wt') as stream:
            json.dump(records, stream, separators=(',', ':'), allow_nan=False)
        mode = 'GENERATED_MISSING_STUDIES'
    additions = [derive(rec) for rec in records]
    for i, (rec, extra) in enumerate(zip(records, additions)):
        validate(SCENARIOS[sid], y[i], mask[i], rec, extra, sid, start+i, namespace)
    with gzip.open(part / 'secondary.json.gz', 'wt') as stream:
        json.dump(additions, stream, separators=(',', ':'), allow_nan=False)
    meta = dict(identity=identity, original_identity=original_identity, scenario=sid, start=start, count=count,
                validated_at=stamp(), validation_contract='FROZEN_BINARY64_AND_POSTDIAGNOSIS_EXACT_V1',
                origin=source if source is not None else dict(generated=True, seed_namespace=namespace),
                hashes={name:sha(part/name) for name in ('raw.npz', 'studies.json.gz', 'secondary.json.gz')},
                sufficient=sufficient(records, additions))
    atomic(part/'integrity.json', meta)
    # Independent read-back before atomic publication; no failed partial is reused.
    sums = checked_batch(part, sid, start, count, identity, source, namespace)
    if path.exists():
        raise ValueError('immutable recovery output collision')
    os.rename(part, path)
    return sid, start, sums, mode


def preflight(launch):
    spec = read(launch)
    for name, expected in spec['files'].items():
        if sha(HERE/name) != expected:
            raise ValueError('recovery code/protocol hash mismatch: ' + name)
    old_root = Path(spec['original_root']).resolve()
    old = read(old_root/'launch.json')
    if canonical(old) != spec['original_identity'] or old != spec['original_launch']:
        raise ValueError('frozen launch identity mismatch')
    if Path(sys.modules['design'].__file__).resolve().parent != (old_root/'code').resolve():
        raise ValueError('wrong frozen import location')
    for group, folder in [('files','code'),('historical_reference_files','reference')]:
        for name, expected in old[group].items():
            if sha(old_root/folder/name) != expected:
                raise ValueError('frozen code/reference changed: '+name)
    actual_env = dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__)
    if actual_env != old['environment']:
        raise ValueError('pinned environment mismatch')
    if old['scenarios'] != SCENARIOS or old['methods'] != list(METHODS) or spec['methods'] != list(ALL_METHODS):
        raise ValueError('method/design identity mismatch')
    index_path = Path(launch).parent/'source-batches.json'
    audit_path = Path(launch).parent/'source-audit.json'
    if sha(index_path) != spec['source_index_sha256'] or sha(audit_path) != spec['source_audit_sha256']:
        raise ValueError('source reuse evidence changed')
    audit = read(audit_path)
    if audit['status'] != 'COMPLETED_SUCCESS' or audit['failed_batches'] or not audit['source_snapshot_unchanged']:
        raise ValueError('source audit not successful')
    source = read(index_path)
    lookup = {}
    for item in source:
        key = (item['scenario'], item['start'])
        if key in lookup or item['count'] != BATCH:
            raise ValueError('duplicate/invalid source batch')
        # The audited ledger already contains canonical absolute paths. Avoid
        # thousands of redundant shared-filesystem realpath calls at startup.
        source_path = Path(item['path'])
        if not source_path.is_absolute() or '..' in source_path.parts or old_root not in source_path.parents:
            raise ValueError('source outside preserved deployment')
        lookup[key] = item
    if len(source) != audit['checked_batches'] or sum(x['count'] for x in source) != audit['checked_studies']:
        raise ValueError('source audit inventory mismatch')
    for inventory in audit['inventory']:
        sid = inventory['scenario']
        if sorted(start for s, start in lookup if s == sid) != list(range(0, inventory['finalized_studies'], BATCH)):
            raise ValueError('source gap')
    return spec, lookup


def run(out, launch, workers=4, hours=8.75):
    if not 1 <= workers <= 4 or not 0 < hours <= 8.75:
        raise ValueError('resource limit')
    spec, source = preflight(launch)
    out = Path(out).resolve()
    old_root = Path(spec['original_root']).resolve()
    if out == old_root or old_root in out.parents:
        raise ValueError('output would modify original deployment')
    if out.parent != (Path(launch).resolve().parent/'runs'):
        raise ValueError('output must be in the separate recovery deployment runs directory')
    out.mkdir(parents=True, exist_ok=True)
    lock = (out/'run.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
    identity = canonical(spec)
    if (out/'launch.json').exists() and read(out/'launch.json') != spec:
        raise ValueError('run identity collision')
    atomic(out/'launch.json', spec)
    atomic(out/f'environment-{os.getpid()}.json', dict(time=stamp(), pid=os.getpid(), python=sys.version,
        numpy=np.__version__, scipy=scipy.__version__, job_id=os.environ.get('SLURM_JOB_ID'), cpus=os.environ.get('SLURM_CPUS_PER_TASK')))
    state = {sid:dict(n=0, sums=None, status='ACTIVE', last_look=None) for sid in range(len(SCENARIOS))}
    stop = [False]
    signal.signal(signal.SIGUSR1, lambda *_:stop.__setitem__(0, True))
    deadline = time.monotonic()+hours*3600
    counts = dict(reused_studies=0, generated_studies=0)
    def checkpoint(status):
        atomic(out/'checkpoint.json', dict(identity=identity, status=status, time=stamp(), **counts,
            scenarios={str(s):{k:v for k,v in x.items() if k != 'sums'} for s,x in state.items()}))
    def accept(sid, start, sums):
        x = state[sid]
        if x['status'] != 'ACTIVE' or start != x['n']:
            raise ValueError('batch gap or output beyond stopping')
        x['sums'] = merge(x['sums'], sums)
        x['n'] += BATCH
        counts['reused_studies' if (sid,start) in source else 'generated_studies'] += BATCH
        if x['n'] in LOOKS:
            report = summarize(x['sums'], x['n'], SCENARIOS[sid])
            atomic(out/f'look-s{sid:02d}-n{x["n"]:05d}.json', report)
            x['last_look'] = x['n']
            if report['precision_objective_met']:
                x['status'] = 'PRECISION_STOP_ORIGINAL_EIGHT'
            elif x['n'] == LOOKS[-1]:
                x['status'] = 'MAXIMUM_COUNT'
            if x['status'] != 'ACTIVE' and any(s == sid and start >= x['n'] for s,start in source):
                raise ValueError('source archive contradicts preserved stopping rule')
    checkpoint('RESUME_VALIDATION')
    for sid in state:
        files = sorted((out/'batches'/f'scenario-{sid:02d}').glob('rep-*'))
        for path in files:
            if '.part-' in path.name:
                continue
            start = int(path.name.split('-')[1])
            accept(sid, start, checked_batch(path, sid, start, BATCH, identity, source.get((sid,start))))
    checkpoint('RUNNING')
    event('RECOVERY_STARTED', identity=identity, workers=workers, **counts)
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        pending, busy = {}, set()
        while True:
            available = sorted((sid for sid,x in state.items() if x['status'] == 'ACTIVE' and sid not in busy), key=lambda sid:(state[sid]['n'],sid))
            while available and len(pending) < workers and not stop[0] and time.monotonic() < deadline:
                sid = available.pop(0)
                start = state[sid]['n']
                busy.add(sid)
                future = pool.submit(execute_batch, str(out), sid, start, BATCH, identity,
                                     spec['original_identity'], source.get((sid,start)))
                pending[future] = sid
                event('BATCH_START', scenario=sid, start=start, origin='audited' if (sid,start) in source else 'missing')
            if not pending:
                break
            done, _ = concurrent.futures.wait(pending, return_when=concurrent.futures.FIRST_COMPLETED)
            for future in done:
                sid, start, sums, mode = future.result()
                pending.pop(future)
                busy.remove(sid)
                accept(sid,start,sums)
                checkpoint('RUNNING')
                event('BATCH_VALIDATED', scenario=sid, studies=state[sid]['n'], mode=mode)
    incomplete = any(x['status'] == 'ACTIVE' for x in state.values())
    if not incomplete and counts['reused_studies'] != sum(x['count'] for x in source.values()):
        raise ValueError('not all audited originals accounted for')
    status = ('TIME_BUDGET_PARTIAL' if incomplete else 'COMPLETE_WITH_ORIGINAL_PRECISION_GAPS'
              if any(x['status'] == 'MAXIMUM_COUNT' for x in state.values()) else 'COMPLETE_ORIGINAL_PRECISION_OBJECTIVES')
    checkpoint(status)
    atomic(out/'completion.json', dict(status=status, identity=identity, time=stamp(), **counts,
        secondary_registration='POST_DIAGNOSIS', scientific_status='REQUIRES_INDEPENDENT_REVIEW_NOT_CALIBRATION_SUCCESS'))
    event(status, **counts)
    return 2 if incomplete else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--launch', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    try:
        if args.check_only:
            manifest, sources = preflight(args.launch)
            event('PREFLIGHT_PASS', identity=canonical(manifest), reusable_studies=sum(x['count'] for x in sources.values()))
        else:
            sys.exit(run(args.out, args.launch, args.workers))
    except Exception:
        # A bad --out must never cause exception handling to write to an input.
        if args.out.resolve().parent == args.launch.resolve().parent/'runs':
            args.out.mkdir(parents=True, exist_ok=True)
            atomic(args.out/f'failure-{os.getpid()}.json', dict(time=stamp(), traceback=traceback.format_exc()))
        raise
