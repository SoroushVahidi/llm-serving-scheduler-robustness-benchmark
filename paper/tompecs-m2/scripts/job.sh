#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/../../.."
name=${1:?job name}; shift
out=paper/tompecs-m2/evidence/validation
session_name=$(tmux display-message -p -t "${TMUX_PANE:-}" '#S' 2>/dev/null || printf 'unknown')
printf 'session=%s\nwindow=%s\npid=%s\nstart=%s\ncommand=' "$session_name" "$name" "$$" "$(date -u --iso-8601=seconds)" > "$out/$name.metadata"
printf '%q ' "$@" >> "$out/$name.metadata"
printf '\n' >> "$out/$name.metadata"
export CUDA_VISIBLE_DEVICES='' HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
"$@" > "$out/$name.log.txt" 2>&1
code=$?
printf '%s\n' "$code" > "$out/$name.exit"
printf 'end=%s\nexit=%s\n' "$(date -u --iso-8601=seconds)" "$code" >> "$out/$name.metadata"
exit "$code"
