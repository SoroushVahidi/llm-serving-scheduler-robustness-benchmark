#!/usr/bin/env bash
set -uo pipefail
cd /home/soroush/repos/llm-serving-scheduler-lssp-tompecs-m1
s=/home/soroush/.local/state/lssp-tompecs-m1
printf '%s\n' "$$" > "$s/baseline.pid"
printf 'RUNNING\n' > "$s/baseline.status"
bash paper/tompecs-m1/scripts/build.sh baseline manuscript > "$s/baseline-manuscript.log" 2>&1
rc=$?
if [[ $rc == 0 ]]; then bash paper/tompecs-m1/scripts/build.sh baseline acmsmall > "$s/baseline-acmsmall.log" 2>&1; rc=$?; fi
printf '%s\n' "$rc" > "$s/baseline.exit"
if [[ $rc == 0 ]]; then echo COMPLETED_SUCCESS; else echo FAILED; fi > "$s/baseline.status"
