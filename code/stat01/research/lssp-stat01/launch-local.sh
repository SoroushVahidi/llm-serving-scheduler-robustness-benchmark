#!/usr/bin/env bash
set -uo pipefail
cd /home/soroush/repos/llm-serving-scheduler-lssp-stat01
printf '%s\n' "$$" > research/lssp-stat01/evidence/submission-local.pid
date -u +%FT%TZ
ssh -o BatchMode=yes wulver "bash -lc 'bash /project/ikoutis/sv96/github/llm-serving-scheduler-lssp-stat01-454168a00524/submit-once.sh'"
rc=$?
printf '%s\n' "$rc" > research/lssp-stat01/evidence/submission-local.exit
date -u +%FT%TZ
exit "$rc"
