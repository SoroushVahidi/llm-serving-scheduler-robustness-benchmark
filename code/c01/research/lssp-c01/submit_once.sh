#!/usr/bin/env bash
# Run on Wulver; one-shot guard deliberately survives failures.
set -euo pipefail
C01_ROOT=/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-c01-3c8e2d6
C01_RUN_ID=c01-30f3af3717d536cb
C01_PYTHON=/project/ikoutis/sv96/github/llm-serving-scheduler-robustness-benchmark/.venv312/bin/python
cd "$C01_ROOT"
test "$(cat validation.exit)" = 0
if squeue -h -u sv96 -o '%j' | grep -q '^lssp-c01-cm-pilot$'; then
  echo 'Equivalent C01 job already queued/running; refusing submission.' >&2
  exit 1
fi
test ! -e submission.json
test ! -e "runs/$C01_RUN_ID/checkpoint.json"
mkdir submission.lock
mkdir -p logs "runs/$C01_RUN_ID"
date -u +%FT%TZ > submission-start-utc.txt
start_seconds=$SECONDS
sbatch --parsable --chdir="$C01_ROOT" \
 --export="ALL,C01_ROOT=$C01_ROOT,C01_RUN_ID=$C01_RUN_ID,C01_PYTHON=$C01_PYTHON" \
 --output="$C01_ROOT/logs/$C01_RUN_ID-%j.out" \
 --error="$C01_ROOT/logs/$C01_RUN_ID-%j.err" \
 "$C01_ROOT/code/pilot.sbatch" > submission-response.txt
job_id=$(cut -d';' -f1 submission-response.txt)
export C01_SUBMITTED_JOB_ID="$job_id"
"$C01_PYTHON" - <<'PY'
import json,os
from pathlib import Path
job=os.environ['C01_SUBMITTED_JOB_ID']
assert job.isdigit()
Path('submission.json').write_text(json.dumps(dict(job_id=job,submitted_at_utc=Path('submission-start-utc.txt').read_text().strip(),run_id='c01-30f3af3717d536cb',cpus=1,memory='4G',partition='general',qos='standard',account='ikoutis',walltime='02:00:00',gpus=0),indent=2)+'\n')
PY
# Exactly one startup observation, ten seconds after accepted submission.
sleep 10
scontrol show job "$job_id" -o > startup-scontrol.txt
squeue -h -j "$job_id" -o '%i|%T|%R|%M|%l|%C|%m|%P' > startup-squeue.txt
{
 date -u +%FT%TZ
 cat submission.json
 cat startup-squeue.txt
 for f in "logs/$C01_RUN_ID-$job_id.out" "logs/$C01_RUN_ID-$job_id.err" "runs/$C01_RUN_ID/checkpoint.json"; do
   if [ -f "$f" ]; then
     echo "FILE $f"
     head -c 6000 "$f"
     echo
   else
     echo "NOT_YET_CREATED $f"
   fi
 done
} > startup-observation.txt
printf '%s\n' "$((SECONDS-start_seconds))" > startup-monitoring-seconds.txt
date -u +%FT%TZ > startup-monitoring-ended-utc.txt
cat startup-observation.txt
