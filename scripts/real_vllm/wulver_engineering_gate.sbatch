#!/bin/bash
#SBATCH --job-name=lssp-wulver-rq6-eng
#SBATCH --account=ikoutis
#SBATCH --partition=debug_gpu
#SBATCH --qos=debug
#SBATCH --gres=gpu:a100_10g:1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --output=artifacts/real_vllm/engineering/wulver_gate_20260902/slurm-%j.out
#SBATCH --error=artifacts/real_vllm/engineering/wulver_gate_20260902/slurm-%j.err

set -euo pipefail

REPO="${REPO:-/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-real-vllm-prep}"
VENV="${VENV:-${REPO}/.venv-lssp-vllm-0.27.1}"
MODEL="${MODEL:-Qwen/Qwen2.5-0.5B-Instruct}"
OUT_ROOT="${OUT_ROOT:-${REPO}/artifacts/real_vllm/engineering/wulver_gate_20260902}"
OUT_DIR="${OUT_DIR:-${OUT_ROOT}/job_${SLURM_JOB_ID}}"

cd "$REPO"
mkdir -p "$OUT_DIR"

export PYTHONPATH="$REPO/src${PYTHONPATH:+:$PYTHONPATH}"
export LD_LIBRARY_PATH="$VENV/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export VLLM_USE_FLASHINFER_SAMPLER=0
export TOKENIZERS_PARALLELISM=false
export HF_HOME="${HF_HOME:-/mmfs1/home/sv96/.cache/huggingface}"

{
  echo "STAMP=ENGINEERING_ONLY_NOT_SCIENTIFIC_EVIDENCE"
  echo "SLURM_JOB_ID=${SLURM_JOB_ID:-}"
  echo "SLURM_JOB_PARTITION=${SLURM_JOB_PARTITION:-}"
  echo "SLURMD_NODENAME=${SLURMD_NODENAME:-}"
  echo "REPO=$REPO"
  echo "VENV=$VENV"
  echo "MODEL=$MODEL"
  git rev-parse HEAD
  "$VENV/bin/python" -c 'import vllm; print(vllm.__version__)'
  nvidia-smi
} | tee "$OUT_DIR/prologue.txt"

"$VENV/bin/python" scripts/real_vllm/wulver_engineering_gate.py \
  --repo "$REPO" \
  --venv "$VENV" \
  --out-dir "$OUT_DIR" \
  --model "$MODEL" \
  --dtype bfloat16 \
  --tensor-parallel-size 1 \
  --max-model-len 1024 \
  --gpu-memory-utilization 0.65

find "$OUT_DIR" -type f ! -name artifact_sha256s.txt -print0 | sort -z | xargs -0 sha256sum > "$OUT_DIR/artifact_sha256s.txt"
