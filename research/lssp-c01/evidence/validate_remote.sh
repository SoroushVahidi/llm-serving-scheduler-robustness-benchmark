#!/usr/bin/env bash
set -uo pipefail
cd /project/ikoutis/sv96/github/llm-serving-scheduler-lssp-c01-3c8e2d6
printf '%s\n' "$$" > validation.pid
date -u +%FT%TZ
C01_PYTHON=/project/ikoutis/sv96/github/llm-serving-scheduler-robustness-benchmark/.venv312/bin/python
"$C01_PYTHON" -m pytest -q code/test_contract.py
rc=$?
if [ "$rc" -eq 0 ]; then
 "$C01_PYTHON" - <<'PY'
import hashlib,json,sys
from pathlib import Path
assert sys.version_info[:2]==(3,12)
spec=json.loads(Path('launch.json').read_text())
for name,expected in spec['files'].items():
 assert hashlib.sha256((Path('code')/name).read_bytes()).hexdigest()==expected,name
assert hashlib.sha256(Path('inputs/pilot-inputs.json').read_bytes()).hexdigest()==spec['input_sha256']
print('REMOTE_CODE_INPUT_FINGERPRINT_PASS')
print(sys.version)
PY
 rc=$?
fi
printf '%s\n' "$rc" > validation.exit
date -u +%FT%TZ
exit "$rc"
