#!/bin/bash
#SBATCH --job-name=m3-time01
#SBATCH --partition=general
#SBATCH --qos=standard
#SBATCH --account=ikoutis
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=02:00:00
set -euo pipefail
umask 077
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1
: "${TIME01_ROOT:?}"
TIME01_PYTHON=/project/ikoutis/sv96/github/llm-serving-scheduler-robustness-benchmark/.venv312/bin/python
cd "$TIME01_ROOT"
trap 'rc=$?; printf "%s\n" "$rc" > slurm.exit; date -u +%FT%TZ > finished-utc.txt' EXIT
"$TIME01_PYTHON" -u code/research/m3-time01/campaign.py "$TIME01_ROOT"
