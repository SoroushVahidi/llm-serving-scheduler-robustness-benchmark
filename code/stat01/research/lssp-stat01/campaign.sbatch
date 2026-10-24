#!/usr/bin/env bash
#SBATCH --job-name=lssp-stat01-calibration
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
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export CUDA_VISIBLE_DEVICES=''
: "${STAT01_ROOT:?missing deployment root}"
: "${STAT01_RUN_ID:?missing unique run ID}"
: "${STAT01_PYTHON:?missing pinned Python executable}"
run_dir="$STAT01_ROOT/runs/$STAT01_RUN_ID"
mkdir -p "$run_dir"
finish() {
  rc=$?
  printf '%s\n' "$rc" > "$run_dir/slurm.exit"
  date -u +%FT%TZ > "$run_dir/finished_utc.txt"
}
trap finish EXIT
date -u +%FT%TZ > "$run_dir/started_utc.txt"
printf '%s\n' "$$" > "$run_dir/wrapper.pid"
"$STAT01_PYTHON" -u "$STAT01_ROOT/code/run.py" --launch "$STAT01_ROOT/launch.json" \
 --out "$run_dir" --workers 4
