#!/bin/bash
#SBATCH --job-name=wlchar_merge
#SBATCH --account=ikoutis
#SBATCH --partition=general
#SBATCH --qos=standard
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=logs/workload_characterization/merge_%j.out
#SBATCH --error=logs/workload_characterization/merge_%j.err
#
# Submitted with --dependency=afterok:<build_array_job_id> (see
# docs/OVERNIGHT_WORKLOAD_CHARACTERIZATION_HANDOFF_20260901.md for the exact
# submission command used). Merges all four sources' fragments and runs
# every section-6 distribution-shift analysis
# (docs/WORKLOAD_DISTRIBUTION_CHARACTERIZATION_PROTOCOL.md). Outcome-blind:
# no scheduler policy is ever imported or run. Does NOT auto-launch any
# further experiment afterward.

set -euo pipefail
cd /project/ikoutis/sv96/github/llm-serving-scheduler-robustness-benchmark
mkdir -p logs/workload_characterization

echo "[$(date -u +%FT%TZ)] merge/analyze starting"
echo "hostname=$(hostname)"

.venv312/bin/python scripts/characterization/merge_and_analyze.py \
  --fragments-dir artifacts/manifests/characterization_fragments \
  --results-dir results/workload_distribution_characterization_v1 \
  --manifest-out artifacts/manifests/workload_characterization_windows.json

echo "[$(date -u +%FT%TZ)] merge/analyze DONE"
