#!/usr/bin/env bash
set -uo pipefail
root=/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-c01-full-20261022
py=/project/ikoutis/sv96/github/llm-serving-scheduler-robustness-benchmark/.venv312/bin/python
cd "$root"
export PYTHONDONTWRITEBYTECODE=1
{
 date -u +%FT%TZ
 "$py" -c 'import sys,numpy,scipy;print(sys.version);print("numpy",numpy.__version__,"scipy",scipy.__version__)' || exit $?
 "$py" -m pytest -q research/lssp-c01/test_contract.py research/lssp-c01-full/test_full.py || exit $?
 "$py" research/lssp-c01-full/prepare_full.py --windows /project/ikoutis/sv96/github/llm-serving-scheduler-ranking-portability-windows/artifacts/manifests/ranking_portability_pilot_v2_windows.json --freeze inputs/phase12-freeze.json --pilot-inputs /project/ikoutis/sv96/github/llm-serving-scheduler-lssp-c01-3c8e2d6/inputs/pilot-inputs.json --out inputs/full-inputs.json --manifest research/lssp-c01-full/input_manifest.json || exit $?
 "$py" research/lssp-c01-full/stage_reuse.py --root "$root" --pilot /project/ikoutis/sv96/github/llm-serving-scheduler-lssp-c01-3c8e2d6 || exit $?
 date -u +%FT%TZ
} > prelaunch.txt 2>&1
