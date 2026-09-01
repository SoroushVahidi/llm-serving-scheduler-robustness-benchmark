#!/bin/bash
#SBATCH --job-name=stage0_build_windows
#SBATCH --partition=debug
#SBATCH --account=ikoutis
#SBATCH --qos=debug
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --output=logs/stage0_build_windows_%j.out
#SBATCH --error=logs/stage0_build_windows_%j.err

set -euo pipefail
cd /project/ikoutis/sv96/github/llm-serving-scheduler-robustness-benchmark
mkdir -p logs artifacts/manifests

.venv312/bin/python scripts/build_stage0_windows.py \
  --burstgpt-path /project/ikoutis/sv96/llmserveopt-data/datasets/burstgpt_v2/raw/BurstGPT_without_fails_2.csv \
  --azure-path /project/ikoutis/sv96/llmserveopt-data/datasets/azure_llm_2024/raw/AzureLLMInferenceTrace_conv_2024.csv \
  --bailian-path /project/ikoutis/sv96/llmserveopt-data/datasets/bailian_qwen/raw/qwen_traceB_blksz_16.jsonl \
  --out artifacts/manifests/stage0_windows.json
