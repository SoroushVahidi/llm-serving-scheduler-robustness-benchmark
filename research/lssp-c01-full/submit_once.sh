#!/usr/bin/env bash
# One attempt only: persistent lock is deliberately retained on every failure.
set -euo pipefail
: "${C01_FULL_ROOT:?}"
: "${C01_FULL_RUN:?}"
cd "$C01_FULL_ROOT"
test "$(cat prelaunch.exit)" = 0
test "$(cat final-tests.exit)" = 0
test "$(cat launch-check.exit)" = 0
test ! -e submission-response.txt
if squeue -h -u sv96 -o '%j' | grep -q '^lssp-c01-full$'; then echo 'Equivalent active job; refusing.' >&2; exit 1; fi
mkdir submission.lock
mkdir -p logs "runs/$C01_FULL_RUN"
date -u +%FT%TZ > submission-start-utc.txt
sbatch --parsable --chdir="$C01_FULL_ROOT" --export="ALL,C01_FULL_ROOT=$C01_FULL_ROOT,C01_FULL_RUN=$C01_FULL_RUN" \
 --output="$C01_FULL_ROOT/logs/$C01_FULL_RUN-%j.out" --error="$C01_FULL_ROOT/logs/$C01_FULL_RUN-%j.err" \
 "$C01_FULL_ROOT/research/lssp-c01-full/full.sbatch" > submission-response.txt
cat submission-response.txt
