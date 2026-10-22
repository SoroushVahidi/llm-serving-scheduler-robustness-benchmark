#!/bin/bash
set -u
cd /home/soroush/repos/llm-serving-scheduler-lssp-v2-p2b || exit 99
run_dir="$1"
mkdir -p "$run_dir"
printf '%s\n' "$$" > "$run_dir/pid"
pwd > "$run_dir/cwd"
date -u +%FT%TZ > "$run_dir/started"
printf 'RUNNING\n' > "$run_dir/status"
printf '%s\n' "CUDA_VISIBLE_DEVICES='' HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src /home/soroush/modal-venv/bin/python -B -m pytest -q -s -p no:cacheprovider tests/serving_v2_p2b" > "$run_dir/command"
CUDA_VISIBLE_DEVICES='' HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src /home/soroush/modal-venv/bin/python -B -m pytest -q -s -p no:cacheprovider tests/serving_v2_p2b > "$run_dir/test.raw.txt" 2>&1
result=$?
printf '%s\n' "$result" > "$run_dir/exit"
date -u +%FT%TZ > "$run_dir/finished"
printf 'CPU_TESTS_EXIT_%s\n' "$result" > "$run_dir/checkpoint"
if [ "$result" = 0 ]; then printf 'COMPLETED_SUCCESS\n'; else printf 'FAILED\n'; fi > "$run_dir/status"
exit "$result"
