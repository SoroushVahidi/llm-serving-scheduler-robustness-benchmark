#!/usr/bin/env bash
set -uo pipefail
cd /home/soroush/repos/llm-serving-scheduler-lssp-tompecs-m1
s=/home/soroush/.local/state/lssp-tompecs-m1
printf '%s\n' "$$" > "$s/revised-final.pid"
echo RUNNING > "$s/revised-final.status"
bash paper/tompecs-m1/scripts/build.sh revised manuscript > "$s/revised-final-manuscript.log" 2>&1
rc=$?
if [[ $rc == 0 ]]; then bash paper/tompecs-m1/scripts/build.sh revised acmsmall > "$s/revised-final-acmsmall.log" 2>&1; rc=$?; fi
printf '%s\n' "$rc" > "$s/revised-final.exit"
if [[ $rc == 0 ]]; then echo COMPLETED_SUCCESS; else echo FAILED; fi > "$s/revised-final.status"
