#!/usr/bin/env bash
set -uo pipefail
root=/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-stat01-454168a00524
python=/project/ikoutis/sv96/github/llm-serving-scheduler-robustness-benchmark/.venv312/bin/python
cd "$root"
printf '%s\n' "$$" > logs/validation.pid
date -u +%FT%TZ
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export STAT01_REFERENCE_SRC="$root/reference"
"$python" - <<'PY'
import json,hashlib,platform,sys
import numpy,scipy
from pathlib import Path
sys.path.insert(0,'code')
from design import SCENARIOS,METHODS
m=json.loads(Path('launch.json').read_text())
assert m['scenarios']==SCENARIOS and m['methods']==list(METHODS)
for group,folder in [('files','code'),('historical_reference_files','reference')]:
 for name,h in m[group].items():assert hashlib.sha256((Path(folder)/name).read_bytes()).hexdigest()==h,name
assert dict(python=platform.python_version(),numpy=numpy.__version__,scipy=scipy.__version__)==m['environment']
print('Frozen code, protocol, historical reference and numerical environment verified.')
print(m['environment'])
PY
rc=$?
if [ "$rc" -eq 0 ]; then
 "$python" -m pytest -q code/test_calibration.py
 rc=$?
fi
if [ "$rc" -eq 0 ]; then
 "$python" code/benchmark_fixture.py
 rc=$?
fi
if [ "$rc" -eq 0 ]; then
 bash -n code/campaign.sbatch
 rc=$?
fi
printf '%s\n' "$rc" > logs/validation.exit
date -u +%FT%TZ
exit "$rc"
