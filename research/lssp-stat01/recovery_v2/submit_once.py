"""Submit the single authorized recovery only after pinned gates; fail closed."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import datetime


def main():
    root=Path(__file__).resolve().parents[1]
    launch=json.loads((root/'launch.json').read_text())
    if root != Path(launch['recovery_root']).resolve():
        raise ValueError('recovery deployment location')
    lock=(root/'submission.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if (root/'submission-intent.json').exists():
        raise ValueError('submission already attempted; manual review required')
    if (root/'logs/tests-pinned.exit').read_text().strip() != '0':
        raise ValueError('pinned tests not passed')
    if hashlib.sha256((root/'logs/tests-pinned.txt').read_bytes()).hexdigest() != launch['validation']['pinned_log_sha256']:
        raise ValueError('test evidence changed')
    identity=hashlib.sha256(json.dumps(launch,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    runid='stat01-recovery-v2-'+identity[:16]
    env={k:v for k,v in os.environ.items() if not k.startswith('SBATCH_')}
    env.update(STAT01_FROZEN_CODE=launch['original_root']+'/code',
               PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    with (root/'logs/preflight.txt').open('x') as stream:
        subprocess.run([sys.executable,str(root/'code/rv2_run.py'),'--launch',str(root/'launch.json'),
            '--out',str(root/'runs'/runid),'--check-only'],env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)
    active=subprocess.check_output(['squeue','-h','-u','sv96','-n','lssp-stat01-recovery-v2'],text=True)
    if active.strip():
        raise ValueError('an active recovery job already exists: '+active.strip())
    command=['sbatch','--parsable','--chdir='+str(root),
             '--export=ALL,STAT01_RECOVERY_ROOT='+str(root)+',STAT01_RECOVERY_ID='+runid,
             '--output='+str(root/'logs'/f'{runid}-%j.out'),
             '--error='+str(root/'logs'/f'{runid}-%j.err'),str(root/'code/recovery.sbatch')]
    record=dict(identity=identity,run_id=runid,command=command,
                time=datetime.datetime.now(datetime.timezone.utc).isoformat(),code_commit=launch['code_commit'])
    with (root/'submission-intent.json').open('x') as stream:
        json.dump(record,stream,indent=2,sort_keys=True);stream.write('\n');stream.flush();os.fsync(stream.fileno())
    result=subprocess.run(command,env=env,text=True,capture_output=True)
    record.update(returncode=result.returncode,stdout=result.stdout,stderr=result.stderr)
    with (root/'submission.json').open('x') as stream:
        json.dump(record,stream,indent=2,sort_keys=True);stream.write('\n')
    print(json.dumps(record,sort_keys=True),flush=True)
    if result.returncode:
        raise SystemExit(result.returncode)
    if not result.stdout.strip().split(';')[0].isdigit():
        raise ValueError('unrecognized submission response; do not resubmit')


if __name__ == '__main__':
    main()
