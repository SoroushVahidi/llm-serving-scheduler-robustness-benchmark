#!/bin/bash
#SBATCH --job-name=stage0_pilot
#SBATCH --account=ikoutis
#SBATCH --partition=general
#SBATCH --qos=standard
#SBATCH --array=0-5
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=01:00:00
#SBATCH --output=logs/stage0_pilot/array_%A_%a.out
#SBATCH --error=logs/stage0_pilot/array_%A_%a.err
#
# THE REAL 1,080-CELL STAGE-0 SCIENTIFIC PILOT
# (docs/STAGE0_DISCRIMINABILITY_PROTOCOL.md, launch authorized by
# docs/STAGE0_PRELAUNCH_READINESS_20260901.md, SAFE_TO_LAUNCH_STAGE0=YES).
#
# Runs from the `research/stage0-orchestration-prelaunch-20260901` worktree
# (NOT the original benchmark repo checkout, which does not contain the
# Stage-0 harness) -- WORKTREE_DIR is set by the submitting shell via
# `sbatch --chdir` or the STAGE0_WORKTREE_DIR env var; do not hardcode a
# path here so this script stays usable if the worktree is relocated.
#
# One SLURM array task = one shard, cost-aware balanced (see
# scripts/stage0/stage0_harness.py::shard_cells and
# artifacts/manifests/stage0_policy_cost_estimates.json -- an operational
# scheduling input only, never used by the analyzer or any scientific
# computation). --array=0-5 (6 shards) is derived from a real 54-cell
# timing sample (results/stage0_timing_only/, 3 real windows x 3 regions x
# 6 policies x 1 rep) which found vllm_faithful ~100x slower than the other
# 5 policies (median ~18.2s/cell vs ~0.1-0.2s/cell); with cost-aware
# balancing this splits the real 1,080-cell grid into 6 PERFECTLY balanced
# shards of 180 cells / ~712.5s (~11.9 min) estimated each -- verified
# against the actual frozen plan before submission. --time=01:00:00 gives
# ~5x safety margin over that estimate. Resumable/idempotent: a rerun only
# recomputes cells whose result file is missing or fails schema validation.
# CPU-only. Independent of, and safe to run alongside, the
# workload-characterization pipeline's own jobs.

set -euo pipefail
cd "${STAGE0_WORKTREE_DIR:?set STAGE0_WORKTREE_DIR to the stage0-orchestration-prelaunch worktree path}"
mkdir -p logs/stage0_pilot

OUTPUT_DIR=${STAGE0_OUTPUT_DIR:-results/stage0_v1}
WINDOWS_MANIFEST=${STAGE0_WINDOWS_MANIFEST:-artifacts/manifests/stage0_windows.json}
CALIBRATION_MANIFEST=${STAGE0_CALIBRATION_MANIFEST:-artifacts/manifests/stage0_load_calibration.json}
COST_ESTIMATES=${STAGE0_COST_ESTIMATES:-artifacts/manifests/stage0_policy_cost_estimates.json}
SHARD_COUNT=${SLURM_ARRAY_TASK_COUNT:-$(( ${SLURM_ARRAY_TASK_MAX:-5} - ${SLURM_ARRAY_TASK_MIN:-0} + 1 ))}

echo "[$(date -u +%FT%TZ)] task=$SLURM_ARRAY_TASK_ID / $SHARD_COUNT shards, output_dir=$OUTPUT_DIR"
echo "hostname=$(hostname)"
echo "worktree=$(pwd) head_sha=$(git rev-parse HEAD)"

PYTHONPATH=src /project/ikoutis/sv96/github/llm-serving-scheduler-robustness-benchmark/.venv312/bin/python3 \
  scripts/stage0/stage0_harness.py run \
  --output-dir "$OUTPUT_DIR" \
  --windows-manifest "$WINDOWS_MANIFEST" \
  --calibration-manifest "$CALIBRATION_MANIFEST" \
  --cost-estimates "$COST_ESTIMATES" \
  --shard-index "$SLURM_ARRAY_TASK_ID" \
  --shard-count "$SHARD_COUNT"

echo "[$(date -u +%FT%TZ)] task=$SLURM_ARRAY_TASK_ID DONE"
