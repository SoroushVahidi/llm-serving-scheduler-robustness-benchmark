#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/../.."
evidence=research/lssp-c01/evidence
printf '%s\n' "$$" > "$evidence/local-validation.pid"
date -u +%FT%TZ
python3 -m pytest -q research/lssp-c01/test_contract.py
rc=$?
if [ "$rc" -eq 0 ]; then
 python3 research/lssp-c01/prepare.py --windows /home/soroush/lssp-c01-cache/windows.json --inputs /home/soroush/lssp-c01-cache/pilot-inputs.json --manifest research/lssp-c01/input_manifest.json
 rc=$?
fi
printf '%s\n' "$rc" > "$evidence/local-validation.exit"
date -u +%FT%TZ
exit "$rc"
