#!/bin/bash
#SBATCH --job-name=m3-abl01-reuse
#SBATCH --account=ikoutis
#SBATCH --partition=general
#SBATCH --qos=standard
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=02:00:00
#SBATCH --no-requeue
set -euo pipefail
umask 077
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1
: "${ABL01_ROOT:?}"
cd "$ABL01_ROOT"
trap 'rc=$?; printf "%s\n" "$rc" > slurm.exit; date -u +%FT%TZ > finished-utc.txt' EXIT
/project/ikoutis/sv96/github/llm-serving-scheduler-robustness-benchmark/.venv312/bin/python -u code/research/m3-abl01/campaign.py "$ABL01_ROOT"
