#!/bin/bash
#SBATCH --job-name=lssp-rq6-calibration
#SBATCH --account=ikoutis
#SBATCH --partition=gpu
#SBATCH --qos=low
#SBATCH --gres=gpu:a100_10g:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=04:00:00
#SBATCH --array=0-119%4
#SBATCH --output=artifacts/real_vllm/calibration/rq6/slurm_logs/slurm-%A_%a.out
#SBATCH --error=artifacts/real_vllm/calibration/rq6/slurm_logs/slurm-%A_%a.err

set -euo pipefail

REPO="${REPO:?set REPO to the checked-out repo path}"
VENV="${VENV:?set VENV to the validated real-vLLM venv path}"
MODEL="${MODEL:-Qwen/Qwen2.5-0.5B-Instruct}"
CALIBRATION_MANIFEST_HASH="${CALIBRATION_MANIFEST_HASH:?set to configs/real_vllm/rq6_calibration_manifest_v2_20260903.json's sha256}"
OUT_DIR="${OUT_DIR:-${REPO}/artifacts/real_vllm/calibration/rq6/${CALIBRATION_MANIFEST_HASH}}"

cd "$REPO"
mkdir -p "$OUT_DIR" artifacts/real_vllm/calibration/rq6/slurm_logs

export PYTHONPATH="$REPO/src${PYTHONPATH:+:$PYTHONPATH}"
export LD_LIBRARY_PATH="$VENV/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export VLLM_USE_FLASHINFER_SAMPLER=0
export TOKENIZERS_PARALLELISM=false
export HF_HOME="${HF_HOME:-/mmfs1/home/sv96/.cache/huggingface}"

# Distinct port per array task on the same node, so %4-concurrent tasks
# scheduled on the same node never collide.
PORT=$((8100 + SLURM_ARRAY_TASK_ID % 100))

{
  echo "STAMP=RQ6_REAL_VLLM_CALIBRATION"
  echo "SLURM_JOB_ID=${SLURM_JOB_ID:-}"
  echo "SLURM_ARRAY_JOB_ID=${SLURM_ARRAY_JOB_ID:-}"
  echo "SLURM_ARRAY_TASK_ID=${SLURM_ARRAY_TASK_ID:-}"
  echo "SLURMD_NODENAME=${SLURMD_NODENAME:-}"
  echo "REPO=$REPO"
  echo "VENV=$VENV"
  echo "MODEL=$MODEL"
  echo "PORT=$PORT"
  git rev-parse HEAD
  nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv
} | tee "$OUT_DIR/prologue_task${SLURM_ARRAY_TASK_ID}.txt"

"$VENV/bin/python" scripts/real_vllm/run_rq6_calibration.py \
  --array-index "$SLURM_ARRAY_TASK_ID" \
  --model "$MODEL" \
  --vllm-executable "$VENV/bin/vllm" \
  --port "$PORT" \
  --gpu-memory-utilization 0.65 \
  --max-model-len 32768 \
  --calibration-manifest configs/real_vllm/rq6_calibration_manifest_v2_20260903.json \
  --out-dir "$OUT_DIR"
