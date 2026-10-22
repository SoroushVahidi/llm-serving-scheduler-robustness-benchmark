#!/usr/bin/env bash
set -uo pipefail
cd /home/soroush/repos/llm-serving-scheduler-lssp-tompecs-m1
s=/home/soroush/.local/state/lssp-tompecs-m1
printf 'pid=%s\ncwd=%s\nstart=%s\n' "$$" "$PWD" "$(date -u --iso-8601=seconds)" > "$s/checks.metadata"
export CUDA_VISIBLE_DEVICES='' HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1
python -B -m pytest -q -p no:cacheprovider tests/test_anwg_metric.py tests/test_ranking_portability_analysis_stats.py tests/test_ranking_portability_analysis_ranking.py tests/test_ranking_portability_analysis_reversal.py tests/test_ranking_portability_analysis_sample_complexity.py > "$s/cpu-tests.log" 2>&1
printf '%s\n' "$?" > "$s/cpu-tests.exit"
(cd dataset/v1.1.0; python -B scripts/validate_release.py) > "$s/dataset-validation.log" 2>&1
printf '%s\n' "$?" > "$s/dataset-validation.exit"
python paper/tompecs-m1/scripts/check_references.py > "$s/references.log" 2>&1
printf '%s\n' "$?" > "$s/references.exit"
printf 'finish=%s\n' "$(date -u --iso-8601=seconds)" >> "$s/checks.metadata"
