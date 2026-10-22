#!/usr/bin/env bash
set -uo pipefail
cd /home/soroush/repos/llm-serving-scheduler-lssp-tompecs-m1
s=/home/soroush/.local/state/lssp-tompecs-m1
printf '%s\n' "$$" > "$s/revised-reviewed.pid"
echo RUNNING > "$s/revised-reviewed.status"
bash paper/tompecs-m1/scripts/build.sh revised manuscript > "$s/revised-reviewed-manuscript.log" 2>&1
rc=$?
if [[ $rc == 0 ]]; then bash paper/tompecs-m1/scripts/build.sh revised acmsmall > "$s/revised-reviewed-acmsmall.log" 2>&1; rc=$?; fi
printf '%s\n' "$rc" > "$s/revised-reviewed.exit"
if [[ $rc == 0 ]]; then echo COMPLETED_SUCCESS; else echo FAILED; fi > "$s/revised-reviewed.status"
