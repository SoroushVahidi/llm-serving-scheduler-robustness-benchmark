#!/bin/bash
#SBATCH --job-name=wlchar_build
#SBATCH --account=ikoutis
#SBATCH --partition=general
#SBATCH --qos=standard
#SBATCH --array=0-3
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=09:00:00
#SBATCH --output=logs/workload_characterization/build_%A_%a.out
#SBATCH --error=logs/workload_characterization/build_%A_%a.err
#
# Array task per source: builds the deterministic characterization window
# corpus (window sizes 100/200/500, seed 20260910, offset 0 -- see
# docs/WORKLOAD_DISTRIBUTION_CHARACTERIZATION_PROTOCOL.md) and computes
# WorkloadCharacterizationDescriptor rows for each window. Outcome-blind:
# no scheduler policy is ever imported or run. Independent of, and must not
# be run concurrently with anything that touches, the frozen Stage-0
# pipeline's own SLURM jobs (it doesn't share a queue-visible resource with
# them beyond ordinary CPU scheduling).
#
# Raw paths below are read-only references, must match
# configs/workloads/source_registry.yaml exactly (checked by an assertion
# at the top of the python invocation).

set -euo pipefail
cd /project/ikoutis/sv96/github/llm-serving-scheduler-robustness-benchmark
mkdir -p logs/workload_characterization

SOURCES=(burstgpt azure_llm_2024 bailian_qwen tracelab)
RAW_PATHS=(
  "/project/ikoutis/sv96/llmserveopt-data/datasets/burstgpt_v2/raw/BurstGPT_without_fails_2.csv"
  "/project/ikoutis/sv96/llmserveopt-data/datasets/azure_llm_2024/raw/AzureLLMInferenceTrace_conv_2024.csv"
  "/project/ikoutis/sv96/llmserveopt-data/datasets/bailian_qwen/raw/qwen_traceB_blksz_16.jsonl"
  "/project/ikoutis/sv96/llmserveopt-data/tracelab_staging_20260722T192050Z/raw/syfi_coding_trace.jsonl.gz"
)

SOURCE=${SOURCES[$SLURM_ARRAY_TASK_ID]}
RAW_PATH=${RAW_PATHS[$SLURM_ARRAY_TASK_ID]}
OUT_DIR=artifacts/manifests/characterization_fragments

echo "[$(date -u +%FT%TZ)] task=$SLURM_ARRAY_TASK_ID source=$SOURCE raw_path=$RAW_PATH"
echo "hostname=$(hostname)"

.venv312/bin/python scripts/characterization/build_and_describe_windows.py \
  --source "$SOURCE" \
  --raw-path "$RAW_PATH" \
  --out-dir "$OUT_DIR"

echo "[$(date -u +%FT%TZ)] task=$SLURM_ARRAY_TASK_ID source=$SOURCE DONE"
