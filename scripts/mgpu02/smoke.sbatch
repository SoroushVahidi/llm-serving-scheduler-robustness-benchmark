#!/bin/bash
#SBATCH --job-name=lssp-mgpu02-smoke
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
# Prepared only in MGPU02. User review/authorization is required before submission.
# Both mechanisms enforce mgpu02-whole-prefill-v1; no general chunked-SLAI claim.
# Never submit an array or retry automatically. Slurm output is supplied by the
# submitter with --output/--error; no output goes into historical RQ6 directories.
set -euo pipefail
printf '%s stage=batch_shell_started pid=%s\n' "$(date -u +%FT%TZ)" "$$"
: "${MGPU02_REPO:?Set isolated MGPU02 worktree}"
: "${MGPU02_OUT_PARENT:?Set a new engineering output parent}"
: "${MGPU02_EXPECTED_SHA:?Set tested commit}"
MGPU02_VENV=/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-real-vllm-prep/.venv-lssp-vllm-0.27.1
MGPU02_MODEL=/home/sv96/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/7ae557604adf67be50417f59c2c2f167def9a775
cd "$MGPU02_REPO"
test "$(git rev-parse HEAD)" = "$MGPU02_EXPECTED_SHA"
test -z "$(git status --porcelain --untracked-files=no)"
export PYTHONPATH="$MGPU02_REPO/src"
export PYTHONDONTWRITEBYTECODE=1
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export VLLM_USE_FLASHINFER_SAMPLER=0 VLLM_USE_V2_MODEL_RUNNER=1
export LD_LIBRARY_PATH="$MGPU02_VENV/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export OMP_NUM_THREADS=4
mkdir -p "$MGPU02_OUT_PARENT"
trap 'rc=$?; printf "%s stage=batch_exit returncode=%s\n" "$(date -u +%FT%TZ)" "$rc" | tee -a "$MGPU02_OUT_PARENT/job-$SLURM_JOB_ID.bootstrap.log"' EXIT
printf '%s stage=python_launch_requested\n' "$(date -u +%FT%TZ)" | tee -a "$MGPU02_OUT_PARENT/job-$SLURM_JOB_ID.bootstrap.log"
# Independent total process deadline leaves cleanup margin under Slurm's ceiling.
timeout --signal=TERM --kill-after=45s 1950s "$MGPU02_VENV/bin/python" -u scripts/mgpu02/smoke.py \
    --out "$MGPU02_OUT_PARENT/job-$SLURM_JOB_ID" \
    --model-path "$MGPU02_MODEL" --vllm-executable "$MGPU02_VENV/bin/vllm" --diagnostic-minimal \
    --readiness-timeout-s "${MGPU02_READINESS_TIMEOUT_S:-1200}"
