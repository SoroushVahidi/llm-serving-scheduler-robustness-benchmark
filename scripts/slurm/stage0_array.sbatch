#!/bin/bash
#SBATCH --job-name=stage0_pilot
#SBATCH --account=ikoutis
#SBATCH --partition=general
#SBATCH --qos=standard
#SBATCH --array=0-11
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=09:00:00
#SBATCH --output=logs/stage0_pilot/array_%A_%a.out
#SBATCH --error=logs/stage0_pilot/array_%A_%a.err
#
# NOT YET SUBMITTED FOR THE REAL 1,080-CELL RUN as of this commit -- this
# script is prepared/tested (see the smoke run under
# results/stage0_smoke_only/) but launching the real pilot is a deliberate,
# separate, later decision (docs/STAGE0_PRELAUNCH_READINESS_20260901.md).
#
# One SLURM array task = one shard of the plan produced by
# `scripts/stage0/stage0_harness.py plan` (see stage0_plan.json in
# --output-dir). Each task processes cells
# `[task_index::array_size]` (Python slice-stride sharding, matches
# stage0_harness.py's own `--shard-index/--shard-count` semantics) --
# resumable/idempotent: a rerun of the same array only recomputes cells
# whose result file is missing or fails schema validation. CPU-only
# (the simulator is a discrete-event Python simulation, no GPU is used at
# any point in this pipeline). Independent of, and safe to run alongside,
# the workload-characterization pipeline's own jobs (disjoint code paths,
# disjoint output directories).
#
# Default --array=0-11 (12 shards) is a starting point sized from the smoke
# timing (results/stage0_smoke_only/ -- 16 cells in well under a minute on
# one CPU); re-derive the shard count from an actual per-cell timing sample
# of the frozen 200-request windows (not the smoke fixture's tiny window)
# before submitting the real 1,080-cell run, and update this comment.

set -euo pipefail
cd /project/ikoutis/sv96/github/llm-serving-scheduler-robustness-benchmark
mkdir -p logs/stage0_pilot

OUTPUT_DIR=${STAGE0_OUTPUT_DIR:-results/stage0_pilot_v1}
WINDOWS_MANIFEST=${STAGE0_WINDOWS_MANIFEST:-artifacts/manifests/stage0_windows.json}
CALIBRATION_MANIFEST=${STAGE0_CALIBRATION_MANIFEST:-artifacts/manifests/stage0_load_calibration.json}
SHARD_COUNT=${SLURM_ARRAY_TASK_COUNT:-$(( ${SLURM_ARRAY_TASK_MAX:-11} - ${SLURM_ARRAY_TASK_MIN:-0} + 1 ))}

echo "[$(date -u +%FT%TZ)] task=$SLURM_ARRAY_TASK_ID / $SHARD_COUNT shards, output_dir=$OUTPUT_DIR"
echo "hostname=$(hostname)"

.venv312/bin/python scripts/stage0/stage0_harness.py run \
  --output-dir "$OUTPUT_DIR" \
  --windows-manifest "$WINDOWS_MANIFEST" \
  --calibration-manifest "$CALIBRATION_MANIFEST" \
  --shard-index "$SLURM_ARRAY_TASK_ID" \
  --shard-count "$SHARD_COUNT"

echo "[$(date -u +%FT%TZ)] task=$SLURM_ARRAY_TASK_ID DONE"
