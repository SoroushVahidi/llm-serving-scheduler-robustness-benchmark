#!/usr/bin/env bash
#SBATCH --job-name=lssp-stat01-recovery-v2
#SBATCH --partition=general
#SBATCH --qos=standard
#SBATCH --account=ikoutis
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=09:00:00
#SBATCH --no-requeue
set -euo pipefail
: "${STAT01_RECOVERY_ROOT:?separate deployment required}"
: "${STAT01_RECOVERY_ID:?manifest identity required}"
export STAT01_FROZEN_CODE=/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-stat01-454168a00524/code
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export CUDA_VISIBLE_DEVICES=''
python=/project/ikoutis/sv96/github/llm-serving-scheduler-robustness-benchmark/.venv312/bin/python
run="$STAT01_RECOVERY_ROOT/runs/$STAT01_RECOVERY_ID"
mkdir -p "$run"
finish() {
  rc=$?
  printf '%s\n' "$rc" > "$run/slurm.exit"
  date -u +%FT%TZ > "$run/finished_utc.txt"
}
trap finish EXIT
date -u +%FT%TZ > "$run/started_utc.txt"
printf '%s\n' "$$" > "$run/wrapper.pid"
"$python" -u "$STAT01_RECOVERY_ROOT/code/rv2_run.py" \
  --launch "$STAT01_RECOVERY_ROOT/launch.json" --out "$run" --workers 4
