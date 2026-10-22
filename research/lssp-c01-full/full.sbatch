#!/usr/bin/env bash
#SBATCH --job-name=lssp-c01-full
#SBATCH --partition=general
#SBATCH --qos=standard
#SBATCH --account=ikoutis
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=09:00:00
#SBATCH --signal=B:TERM@120
set -euo pipefail
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1
: "${C01_FULL_ROOT:?}"
: "${C01_FULL_RUN:?}"
C01_FULL_PYTHON=/project/ikoutis/sv96/github/llm-serving-scheduler-robustness-benchmark/.venv312/bin/python
run_dir="$C01_FULL_ROOT/runs/$C01_FULL_RUN"
mkdir -p "$run_dir"
finish() { rc=$?; printf '%s\n' "$rc" > "$run_dir/slurm.exit"; date -u +%FT%TZ > "$run_dir/finished_utc.txt"; }
trap finish EXIT
trap 'kill -TERM "$child" 2>/dev/null || true; wait "$child" || exit $?' TERM INT
date -u +%FT%TZ > "$run_dir/started_utc.txt"
"$C01_FULL_PYTHON" -u "$C01_FULL_ROOT/research/lssp-c01-full/campaign.py" --root "$C01_FULL_ROOT" --out "$run_dir" &
child=$!
wait "$child"
