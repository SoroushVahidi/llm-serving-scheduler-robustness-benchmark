#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/../.."
evidence=research/lssp-stat01/evidence
printf '%s\n' "$$" > "$evidence/validation.pid"
date -u +%FT%TZ
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
python3 -m pytest -q research/lssp-stat01/test_calibration.py
rc=$?
if [ "$rc" -eq 0 ]; then
 python3 -m compileall -q research/lssp-stat01
 rc=$?
fi
if [ "$rc" -eq 0 ]; then
 python3 research/lssp-stat01/benchmark_fixture.py
 rc=$?
fi
if [ "$rc" -eq 0 ]; then
 bash -n research/lssp-stat01/campaign.sbatch
 rc=$?
fi
printf '%s\n' "$rc" > "$evidence/validation.exit"
date -u +%FT%TZ
exit "$rc"
