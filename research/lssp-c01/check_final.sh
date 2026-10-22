#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/../.."
evidence=research/lssp-c01/evidence
printf '%s\n' "$$" > "$evidence/final-validation.pid"
date -u +%FT%TZ
python3 -m pytest -q research/lssp-c01/test_contract.py tests/test_benchmark_synthesis.py tests/test_ranking_portability_phase12_campaign.py tests/test_ranking_portability_phase12_campaign_dry_run.py
rc=$?
if [ "$rc" -eq 0 ]; then
 python3 research/lssp-c01/prepare.py --windows /home/soroush/lssp-c01-cache/windows.json --inputs /home/soroush/lssp-c01-cache/pilot-inputs.json --manifest research/lssp-c01/input_manifest.json
 rc=$?
fi
if [ "$rc" -eq 0 ]; then
 python3 -m compileall -q research/lssp-c01
 rc=$?
fi
if [ "$rc" -eq 0 ]; then
 bash -n research/lssp-c01/pilot.sbatch research/lssp-c01/check_local.sh research/lssp-c01/check_final.sh
 rc=$?
fi
printf '%s\n' "$rc" > "$evidence/final-validation.exit"
date -u +%FT%TZ
exit "$rc"
