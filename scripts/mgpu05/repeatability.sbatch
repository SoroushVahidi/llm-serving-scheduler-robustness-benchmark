#!/bin/bash
#SBATCH --job-name=lssp-mgpu05-pair
#SBATCH --account=ikoutis
#SBATCH --partition=gpu
#SBATCH --qos=standard
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --gres=gpu:a100:1
#SBATCH --time=00:50:00
#SBATCH --no-requeue
# PREPARED ONLY: one reviewed pair, never an array or retry loop.
set -euo pipefail
: "${MGPU05_REPO:?Dedicated clean reviewed checkout}"
: "${MGPU05_OUT_PARENT:?New durable engineering parent}"
: "${MGPU05_EXPECTED_SHA:?Exact reviewed tested commit}"
: "${MGPU05_BLOCK:?One preselected block from design.json, 0..11}"
: "${MGPU05_VENV:?Pinned Wulver vLLM 0.27.1 environment}"
: "${MGPU05_MODEL:?Pinned Qwen snapshot path}"
test -z "${SLURM_ARRAY_JOB_ID:-}"
cd "$MGPU05_REPO"
test "$(git rev-parse HEAD)" = "$MGPU05_EXPECTED_SHA"
test -z "$(git status --porcelain --untracked-files=no)"
export PYTHONPATH="$MGPU05_REPO/src" PYTHONDONTWRITEBYTECODE=1
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export VLLM_USE_FLASHINFER_SAMPLER=0 VLLM_USE_V2_MODEL_RUNNER=1 OMP_NUM_THREADS=4
export LD_LIBRARY_PATH="$MGPU05_VENV/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
mkdir -p "$MGPU05_OUT_PARENT"
trap 'rc=$?; printf "%s batch_exit=%s\n" "$(date -u +%FT%TZ)" "$rc" >> "$MGPU05_OUT_PARENT/job-$SLURM_JOB_ID.bootstrap.log"' EXIT
printf '%s batch_started\n' "$(date -u +%FT%TZ)" >> "$MGPU05_OUT_PARENT/job-$SLURM_JOB_ID.bootstrap.log"
# 2*(1200 readiness + 60 warmup + 123 replay/drain + 45 cleanup) < 2940.
# All-stage bound also covers asset verification and independent analysis.
timeout --signal=TERM --kill-after=45s 2940s "$MGPU05_VENV/bin/python" -u scripts/mgpu05/repeatability.py \
  --expected-sha "$MGPU05_EXPECTED_SHA" --block "$MGPU05_BLOCK" \
  --model-path "$MGPU05_MODEL" --vllm-executable "$MGPU05_VENV/bin/vllm" \
  --out "$MGPU05_OUT_PARENT/job-$SLURM_JOB_ID"
