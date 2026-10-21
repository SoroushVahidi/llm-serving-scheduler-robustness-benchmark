#!/bin/bash
#SBATCH --job-name=lssp-rq6-validation
#SBATCH --account=ikoutis
#SBATCH --partition=gpu
#SBATCH --qos=low
#SBATCH --gres=gpu:a100_10g:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:45:00
#SBATCH --array=0-239%4
#SBATCH --output=artifacts/real_vllm/validation/rq6/slurm_logs/slurm-%A_%a.out
#SBATCH --error=artifacts/real_vllm/validation/rq6/slurm_logs/slurm-%A_%a.err

# RQ6_REAL_VLLM_SCIENTIFIC_VALIDATION launcher. One array task = one
# (policy, source, window_id) cell of the frozen 240-cell task matrix
# (configs/real_vllm/rq6_validation_manifest_v1_20260903.json). Submitting
# this array IS launching the scientific campaign -- do not sbatch this file
# as part of a prefreeze/engineering task; see
# docs/RQ6_REAL_VLLM_VALIDATION_PREFREEZE_20260903.md's launch checklist and
# explicit "no scientific RQ6 validation has yet been launched" statement.

set -euo pipefail

REPO="${REPO:?set REPO to the checked-out repo path}"
VENV="${VENV:?set VENV to the validated real-vLLM venv path}"
MODEL="${MODEL:-Qwen/Qwen2.5-0.5B-Instruct}"
VALIDATION_MANIFEST_HASH="${VALIDATION_MANIFEST_HASH:?set to the sha256 of configs/real_vllm/rq6_validation_manifest_v1_20260903.json}"
CALIBRATION_MANIFEST_HASH="${CALIBRATION_MANIFEST_HASH:?set to the sha256 of configs/real_vllm/rq6_calibration_manifest_v2_20260903.json}"
OUT_DIR="${OUT_DIR:-${REPO}/artifacts/real_vllm/validation/rq6/${VALIDATION_MANIFEST_HASH}}"
CALIBRATION_DIR="${CALIBRATION_DIR:-${REPO}/artifacts/real_vllm/calibration/rq6/${CALIBRATION_MANIFEST_HASH}}"

cd "$REPO"
mkdir -p "$OUT_DIR" artifacts/real_vllm/validation/rq6/slurm_logs

if [ ! -d "$CALIBRATION_DIR" ]; then
  echo "FATAL: calibration dependency directory does not exist: $CALIBRATION_DIR" >&2
  echo "The 120-task RQ6 calibration campaign must complete and validate before this array may run." >&2
  exit 1
fi

export PYTHONPATH="$REPO/src${PYTHONPATH:+:$PYTHONPATH}"
export LD_LIBRARY_PATH="$VENV/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export VLLM_USE_FLASHINFER_SAMPLER=0
export TOKENIZERS_PARALLELISM=false
export HF_HOME="${HF_HOME:-/mmfs1/home/sv96/.cache/huggingface}"

# Port strategy (Section 7 CRITICAL requirement): NOT the calibration
# launcher's PORT=8100+task_id%100 arithmetic, which collided whenever two
# array indices shared a residue mod 100 on the same node (task 19 vs 119 --
# see docs/LSSP_NEW_CHAT_HANDOFF_20260903.md). Port selection is delegated
# entirely to run_rq6_validation.py (robustbench.real_llm.port_alloc.
# allocate_port), which asks the OS for a currently-free ephemeral port at
# process start, right before it invokes `vllm serve` -- correct by
# construction for any number of concurrently-scheduled array tasks on one
# node, and retried internally (--server-start-retries) if the assigned
# port loses a bind race before vLLM starts. The selected port is recorded
# in the output JSON's `selected_port` field, not computed or logged here.

{
  echo "STAMP=RQ6_REAL_VLLM_SCIENTIFIC_VALIDATION"
  echo "SLURM_JOB_ID=${SLURM_JOB_ID:-}"
  echo "SLURM_ARRAY_JOB_ID=${SLURM_ARRAY_JOB_ID:-}"
  echo "SLURM_ARRAY_TASK_ID=${SLURM_ARRAY_TASK_ID:-}"
  echo "SLURMD_NODENAME=${SLURMD_NODENAME:-}"
  echo "REPO=$REPO"
  echo "VENV=$VENV"
  echo "MODEL=$MODEL"
  echo "VALIDATION_MANIFEST_HASH=$VALIDATION_MANIFEST_HASH"
  echo "CALIBRATION_MANIFEST_HASH=$CALIBRATION_MANIFEST_HASH"
  git rev-parse HEAD
  nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv
} | tee "$OUT_DIR/prologue_task${SLURM_ARRAY_TASK_ID}.txt"

"$VENV/bin/python" scripts/real_vllm/run_rq6_validation.py \
  --array-index "$SLURM_ARRAY_TASK_ID" \
  --model "$MODEL" \
  --vllm-executable "$VENV/bin/vllm" \
  --gpu-memory-utilization 0.65 \
  --max-model-len 32768 \
  --validation-manifest configs/real_vllm/rq6_validation_manifest_v1_20260903.json \
  --calibration-dir "$CALIBRATION_DIR" \
  --out-dir "$OUT_DIR"
