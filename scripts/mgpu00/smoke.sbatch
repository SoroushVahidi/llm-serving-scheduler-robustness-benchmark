#!/bin/bash
#SBATCH --job-name=lssp-mgpu00-smoke
#SBATCH --account=ikoutis
#SBATCH --partition=gpu
#SBATCH --qos=standard
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --gres=gpu:a100:1
#SBATCH --time=00:35:00
#SBATCH --no-requeue

# Engineering only. ONE full GPU, one submission, 35/60 GPU-hour hard ceiling.
# MGPU01 compatibility gate currently rejects execution. Do not submit until
# a separately reviewed supported semantic contract replaces that gate.
# Never submit an array or retry automatically. Slurm output is supplied by the
# submitter with --output/--error; no output goes into historical RQ6 directories.
set -euo pipefail
printf '%s stage=batch_shell_started pid=%s\n' "$(date -u +%FT%TZ)" "$$"
: "${MGPU00_REPO:?Set isolated MGPU00 worktree}"
: "${MGPU00_OUT_PARENT:?Set a new engineering output parent}"
: "${MGPU00_EXPECTED_SHA:?Set tested commit}"
MGPU00_VENV=/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-real-vllm-prep/.venv-lssp-vllm-0.27.1
MGPU00_MODEL=/home/sv96/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/7ae557604adf67be50417f59c2c2f167def9a775
cd "$MGPU00_REPO"
test "$(git rev-parse HEAD)" = "$MGPU00_EXPECTED_SHA"
export PYTHONPATH="$MGPU00_REPO/src"
export PYTHONDONTWRITEBYTECODE=1
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export VLLM_USE_FLASHINFER_SAMPLER=0
export LD_LIBRARY_PATH="$MGPU00_VENV/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export OMP_NUM_THREADS=4
mkdir -p "$MGPU00_OUT_PARENT"
trap 'rc=$?; printf "%s stage=batch_exit returncode=%s\n" "$(date -u +%FT%TZ)" "$rc" | tee -a "$MGPU00_OUT_PARENT/job-$SLURM_JOB_ID.bootstrap.log"' EXIT
printf '%s stage=python_launch_requested\n' "$(date -u +%FT%TZ)" | tee -a "$MGPU00_OUT_PARENT/job-$SLURM_JOB_ID.bootstrap.log"
# Independent total process deadline leaves cleanup margin under Slurm's ceiling.
timeout --signal=TERM --kill-after=45s 1950s "$MGPU00_VENV/bin/python" -u scripts/mgpu00/smoke.py \
    --out "$MGPU00_OUT_PARENT/job-$SLURM_JOB_ID" \
    --model-path "$MGPU00_MODEL" --vllm-executable "$MGPU00_VENV/bin/vllm" --diagnostic-minimal \
    --readiness-timeout-s "${MGPU01_READINESS_TIMEOUT_S:-1200}"
