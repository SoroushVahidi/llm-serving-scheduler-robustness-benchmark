#!/usr/bin/env python3
"""One preselected pair only. No sbatch, loops across blocks, retries or arrays."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

import httpx
from robustbench.mgpu00.provenance import write_new_json
from robustbench.mgpu00.startup import ServerDiagnostics
from robustbench.mgpu05.assets import verify_assets, file_hash
from robustbench.mgpu05.design import MODEL, REVISION, cohort, payload, verify_design
from robustbench.mgpu05.evidence import Journal, digest, seal
from robustbench.mgpu05.offline import analyze
from robustbench.mgpu05.replay import replay

ROOT = Path(__file__).resolve().parents[2]


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def command(executable, model, port, policy):
    if policy not in ('native_fcfs','slai_mgpu00_checked'):
        raise ValueError('Unsupported policy; no fallback')
    cls = 'MeasuredNativeScheduler' if policy=='native_fcfs' else 'MeasuredSlaiScheduler'
    return [str(executable),'serve',str(model),'--served-model-name',MODEL,
        '--revision',REVISION,'--tokenizer-revision',REVISION,'--host','127.0.0.1','--port',str(port),
        '--dtype','bfloat16','--max-model-len','512','--max-num-batched-tokens','4096',
        '--max-num-seqs','16','--gpu-memory-utilization','0.2','--enforce-eager',
        '--no-async-scheduling','--enable-chunked-prefill','--no-enable-prefix-caching',
        '--tensor-parallel-size','1','--pipeline-parallel-size','1','--data-parallel-size','1',
        '--scheduling-policy','fcfs' if policy=='native_fcfs' else 'priority',
        '--long-prefill-token-threshold','0','--scheduler-cls','robustbench.mgpu05.vllm_scheduler.'+cls]


def run_policy(args, block, policy, assets, hardware):
    directory = args.out/policy
    directory.mkdir()
    cache = args.out/('cache-'+policy)  # excluded from each execution's evidence seal
    cache.mkdir()
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        port = sock.getsockname()[1]
    argv = command(args.vllm_executable,args.model_path,port,policy)
    env = dict(os.environ, LSSP_MGPU05_SYNTHETIC='1', LSSP_MGPU05_TIMING_PROVENANCE='physical_candidate',
               LSSP_MGPU00_DECODE_LIMIT='2', VLLM_USE_V2_MODEL_RUNNER='1', VLLM_USE_FLASHINFER_SAMPLER='0',
               HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', TOKENIZERS_PARALLELISM='false',
               VLLM_CACHE_ROOT=str(cache/'vllm'), TORCHINDUCTOR_CACHE_DIR=str(cache/'torch'),
               CUDA_CACHE_PATH=str(cache/'cuda'))
    requests = cohort(block['window'],block['region'])
    warm = [payload('balanced',0,'spread',warmup=True)]
    manifest = dict(schema='mgpu05-execution-v1', stamp='SYNTHETIC_ENGINEERING_ONLY',
                    git_sha=args.expected_sha, plan_sha256=file_hash(args.plan), block=block,
                    policy=policy, payloads=requests, payloads_sha256=digest(requests), warmup=warm,
                    model_path=str(args.model_path), assets=assets, hardware=hardware,
                    command=argv, readiness_timeout_s=1200, utc=datetime.now(timezone.utc).isoformat(),
                    environment={k:env[k] for k in ('LSSP_MGPU05_SYNTHETIC','LSSP_MGPU05_TIMING_PROVENANCE',
                       'LSSP_MGPU00_DECODE_LIMIT','VLLM_USE_V2_MODEL_RUNNER','VLLM_USE_FLASHINFER_SAMPLER',
                       'VLLM_CACHE_ROOT','TORCHINDUCTOR_CACHE_DIR','CUDA_CACHE_PATH','OMP_NUM_THREADS')})
    write_new_json(directory/'manifest.json',manifest)
    diagnostics = ServerDiagnostics(directory,'server')
    started = time.monotonic()
    failure = None
    try:
        diagnostics.start(argv,env)
        with httpx.Client(base_url=f'http://127.0.0.1:{port}',trust_env=False,timeout=3.) as client:
            ready = diagnostics.wait_ready(client,MODEL,1200)
        write_new_json(directory/'startup.json',dict(readiness_seconds=ready,scored=False))
        async def execute():
            async with httpx.AsyncClient(base_url=f'http://127.0.0.1:{port}',trust_env=False,
                      timeout=None,limits=httpx.Limits(max_connections=32,max_keepalive_connections=32)) as client:
                for name, inputs, timeout in [('warmup',warm,60.),('scored',requests,120.)]:
                    journal = Journal(directory/(name+'.jsonl'),synthetic=True)
                    try:
                        await replay(inputs,client=client,journal=journal,timeout_s=timeout)
                    finally:
                        journal.close()
                    # Fail immediately on raw transport failure; full independent validation follows cleanup.
                    from robustbench.mgpu05.evidence import read_journal
                    terminals = [e for e in read_journal(directory/(name+'.jsonl')) if e['kind']=='terminal']
                    if len(terminals)!=len(inputs) or any(e['data']['state']!='STREAM_DONE' for e in terminals):
                        raise RuntimeError(name+' transport failed')
        asyncio.run(execute())
        if diagnostics.process.poll() is not None:
            raise RuntimeError('Server exited before intentional cleanup')
    except BaseException as exc:
        failure = dict(type=type(exc).__name__,error=str(exc))
        raise
    finally:
        try:
            diagnostics.close()
        except BaseException as exc:
            failure = dict(type=type(exc).__name__,error=str(exc),stage='cleanup',prior_failure=failure)
            raise
        finally:
            write_new_json(directory/'run-end.json',dict(elapsed_seconds=time.monotonic()-started,failure=failure))
            if failure:
                seal(directory)
    try:
        result = analyze(directory,verify=False)
        write_new_json(directory/'validation.json',result)
        if result['acceptance']!='PASS':
            raise RuntimeError('Independent measurement/fidelity gate failed')
    except BaseException as exc:
        write_new_json(directory/'validation-error.json',dict(type=type(exc).__name__,error=str(exc)))
        raise
    finally:
        seal(directory)
    print(json.dumps(dict(policy=policy,acceptance=result['acceptance'],evidence=str(directory))),flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--plan',type=Path,default=ROOT/'scripts/mgpu05/design.json')
    p.add_argument('--block',type=int,required=True,choices=range(12))
    p.add_argument('--model-path',type=Path,required=True)
    p.add_argument('--vllm-executable',type=Path)
    p.add_argument('--out',type=Path)
    p.add_argument('--expected-sha',required=True)
    p.add_argument('--check-only',action='store_true')
    args = p.parse_args()
    if git('rev-parse','HEAD')!=args.expected_sha or git('status','--porcelain','--untracked-files=no'):
        raise ValueError('Exact clean tested checkout required')
    plan = verify_design(json.loads(args.plan.read_text()))
    tokenizer, assets = verify_assets(ROOT,args.model_path)
    block = plan['blocks'][args.block]
    if args.check_only:
        print(json.dumps(dict(status='CPU_PREFLIGHT_PASS',block=block,assets=assets),indent=2))
        return
    if not os.environ.get('SLURM_JOB_ID') or os.environ.get('SLURM_ARRAY_JOB_ID'):
        raise ValueError('Single non-array Slurm allocation required')
    if args.out is None or args.out.exists() or args.vllm_executable is None:
        raise ValueError('New output directory and explicit executable required')
    if args.vllm_executable.parent.resolve() != Path(sys.executable).parent.resolve():
        raise ValueError('Server and preflight must use the same Python environment')
    args.out.mkdir(parents=True)
    write_new_json(args.out/'block.json',dict(plan=plan,block=block,assets=assets,
                   git_sha=args.expected_sha,slurm_job_id=os.environ['SLURM_JOB_ID']))
    def terminated(signum, frame):
        raise SystemExit('Terminated by signal '+str(signum))
    signal.signal(signal.SIGTERM,terminated)
    signal.signal(signal.SIGINT,terminated)
    from robustbench.mgpu00.provenance import collect_gpu_provenance
    try:
        hardware = collect_gpu_provenance(args.out/'device')
        seal(args.out/'device')
        for policy in block['policy_order']:
            run_policy(args,block,policy,assets,hardware)
        write_new_json(args.out/'block-result.json',dict(status='PASS',executions=2))
    except BaseException as exc:
        write_new_json(args.out/'block-result.json',dict(status='FAIL',error=str(exc),type=type(exc).__name__))
        raise


if __name__ == '__main__':
    main()
