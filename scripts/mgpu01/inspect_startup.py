#!/usr/bin/env python3
"""Bounded login-node inspection: stdlib only, no GPU or package imports.

Run under timeout 60s; output is a snapshot, not a compute-node I/O benchmark.
Never reads entire weights or recursively scans a cache.
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import time

VENV = Path('/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-real-vllm-prep/.venv-lssp-vllm-0.27.1')
SITE = VENV / 'lib/python3.12/site-packages'
MODEL = Path('/home/sv96/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/7ae557604adf67be50417f59c2c2f167def9a775')
REPO = Path('/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-mgpu00')


def emit(kind, **values):
    print(json.dumps(dict(kind=kind, time_ns=time.time_ns(), **values)), flush=True)


def command(argv):
    start = time.monotonic()
    result = subprocess.run(argv, capture_output=True, text=True, timeout=15)
    emit('command', argv=argv, seconds=time.monotonic()-start,
         returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)


emit('environment', node=platform.node(), python=platform.python_version(),
     venv=str(VENV), model=str(MODEL), note='login-node observation after failure')
emit('entrypoint', python_resolved=str((VENV / 'bin/python').resolve()),
     pyvenv_cfg_exists=(VENV / 'pyvenv.cfg').exists(),
     conda_meta_exists=(VENV / 'conda-meta').is_dir(),
     vllm_entrypoint=(VENV / 'bin/vllm').read_text())
command([str(VENV / 'bin/python'), '--version'])
for path in [MODEL, VENV]:
    command(['findmnt', '-T', str(path), '-n', '-o', 'TARGET,SOURCE,FSTYPE,OPTIONS'])
command(['/apps/slurm/current/bin/sacct', '-n', '-P', '-j', '1434545,1434644',
         '--format=JobID,State,ExitCode,ElapsedRaw,Start,End,AllocTRES,NodeList'])
command(['git', '-C', str(REPO), 'rev-parse', 'HEAD'])
command(['git', '-C', str(REPO), 'show', 'HEAD:scripts/mgpu00/smoke.sbatch'])
for name in ['vllm', 'torch', 'transformers']:
    for path in SITE.glob(name + '-*.dist-info/METADATA'):
        lines = path.read_text().splitlines()
        emit('package', path=str(path), metadata=[s for s in lines if s.startswith(('Name:', 'Version:'))])
for relative, ranges in {
    'vllm/engine/arg_utils.py': [(2599, 2634)],
    'vllm/config/model.py': [(1905, 1960)],
    'vllm/v1/core/sched/scheduler.py': [(890, 920)],
    'vllm/v1/worker/gpu/model_runner.py': [(299, 334)],
    'vllm/model_executor/model_loader/default_loader.py': [(136, 150), (190, 239)],
}.items():
    path = SITE / relative
    data = path.read_bytes()
    lines = data.decode().splitlines()
    emit('installed_source', path=str(path), sha256=hashlib.sha256(data).hexdigest(),
         excerpts=[{'start': a, 'lines': lines[a-1:b]} for a, b in ranges])
for path in sorted(MODEL.iterdir()):
    start = time.monotonic()
    row = dict(path=str(path), symlink=os.readlink(path) if path.is_symlink() else None)
    try:
        row.update(resolved=str(path.resolve(strict=True)), size=path.stat().st_size,
                   mtime_ns=path.stat().st_mtime_ns)
        if path.is_file():
            with path.open('rb') as stream:
                head = stream.read(65536)
                row['head_bytes'] = len(head)
                row['head_sha256'] = hashlib.sha256(head).hexdigest()
                if path.suffix == '.safetensors':
                    length = int.from_bytes(head[:8], 'little')
                    if length > 1024*1024:
                        raise ValueError('Header exceeds bounded 1 MiB inspection')
                    stream.seek(8)
                    header = json.loads(stream.read(length))
                    offsets = [v['data_offsets'] for k, v in header.items() if k != '__metadata__']
                    row.update(header_bytes=length, tensor_count=len(offsets),
                               expected_file_size=8+length+max(b for a,b in offsets))
                    row['size_matches_tensor_offsets'] = row['size'] == row['expected_file_size']
                    stream.seek(max(0, row['size']-65536))
                    tail = stream.read(65536)
                    row['tail_sha256'] = hashlib.sha256(tail).hexdigest()
                elif path.name in ('config.json', 'generation_config.json', 'tokenizer_config.json'):
                    row['json'] = json.loads(head)
    except Exception as exc:
        row['error'] = repr(exc)
    emit('model_file', seconds=time.monotonic()-start, **row)
