#!/usr/bin/env bash
# Run on Wulver after engineering validation. One submission, one startup snapshot.
set -euo pipefail
root=/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-stat01-454168a00524
run_id=stat01-f97f91abe5da0bf5
python=/project/ikoutis/sv96/github/llm-serving-scheduler-robustness-benchmark/.venv312/bin/python
cd "$root"
printf '%s\n' "$$" > logs/submission-wrapper.pid
test "$(cat logs/validation.exit)" = 0
test ! -e logs/submitted-job-id.txt
test ! -e "runs/$run_id/checkpoint.json"
# Restrict output to STAT01. Do not query the independent C01 job.
squeue -h -u "$USER" -o '%i|%j|%T' | awk -F'|' '$2 ~ /stat01/ {print}' > logs/existing-stat01-jobs.txt
test ! -s logs/existing-stat01-jobs.txt
"$python" - <<'PY'
import hashlib,json,platform
from pathlib import Path
import numpy,scipy
m=json.loads(Path('launch.json').read_text())
for group,folder in [('files','code'),('historical_reference_files','reference')]:
 for n,h in m[group].items():assert hashlib.sha256((Path(folder)/n).read_bytes()).hexdigest()==h,n
assert dict(python=platform.python_version(),numpy=numpy.__version__,scipy=scipy.__version__)==m['environment']
assert hashlib.sha256(json.dumps(m,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()=='f97f91abe5da0bf5566edcf7f0877e4df226cbea4b4b3966c467a33a970b5700'
PY
mkdir submission.lock
start=$(date +%s)
date -u +%FT%TZ > logs/submitted_utc.txt
sbatch --parsable --chdir "$root" \
 --export "ALL,STAT01_ROOT=$root,STAT01_RUN_ID=$run_id,STAT01_PYTHON=$python" \
 --output "$root/logs/$run_id-%j.out" --error "$root/logs/$run_id-%j.err" \
 "$root/code/campaign.sbatch" > logs/sbatch-response.txt
job=$(cut -d';' -f1 logs/sbatch-response.txt)
[[ "$job" =~ ^[0-9]+$ ]]
printf '%s\n' "$job" > logs/submitted-job-id.txt
# One bounded observation; no repeated polling and no wait for completion.
sleep 10
{
 date -u +%FT%TZ
 printf 'STAT01_JOB_ID=%s\n' "$job"
 squeue -j "$job" -o '%.18i %.12T %.10M %.10l %.6D %R'
 scontrol show job "$job"
 printf '\nSTDOUT_STARTUP\n'
 if [ -e "logs/$run_id-$job.out" ]; then head -n 18 "logs/$run_id-$job.out"; else printf 'Log not created yet (queued job).\n'; fi
 printf '\nSTDERR_STARTUP\n'
 if [ -e "logs/$run_id-$job.err" ]; then head -n 25 "logs/$run_id-$job.err"; else printf 'Error log not created yet.\n'; fi
 printf '\nCHECKPOINT_HEALTH_ONLY\n'
 "$python" - "$root/runs/$run_id" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]);cp=p/'checkpoint.json'
if cp.exists():
 d=json.loads(cp.read_text());print(json.dumps({k:d[k] for k in ['identity','time','status']}));print('Validated study counts:',{s:v['n'] for s,v in d['scenarios'].items()})
else: print('Checkpoint not yet created; runtime initializes it on startup.')
print('Failure artifact names:',[x.name for x in p.glob('failure-*.json')])
print('Environment artifact names:',[x.name for x in p.glob('environment-*.json')])
PY
 printf 'STARTUP_ELAPSED_SECONDS=%s\n' "$(( $(date +%s) - start ))"
} > logs/startup-health.txt 2>&1
cat logs/startup-health.txt
