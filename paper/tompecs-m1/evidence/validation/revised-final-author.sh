#!/usr/bin/env bash
set -uo pipefail
cd /home/soroush/repos/llm-serving-scheduler-lssp-tompecs-m1
s=/home/soroush/.local/state/lssp-tompecs-m1
printf '%s\n' "$$" > "$s/revised-final-author.pid"
echo RUNNING > "$s/revised-final-author.status"
bash paper/tompecs-m1/scripts/build.sh revised manuscript > "$s/revised-final-author-manuscript.log" 2>&1
rc=$?
if [[ $rc == 0 ]]; then bash paper/tompecs-m1/scripts/build.sh revised acmsmall > "$s/revised-final-author-acmsmall.log" 2>&1; rc=$?; fi
printf '%s\n' "$rc" > "$s/revised-final-author.exit"
if [[ $rc == 0 ]]; then echo COMPLETED_SUCCESS; else echo FAILED; fi > "$s/revised-final-author.status"
