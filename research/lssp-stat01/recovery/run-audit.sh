#!/usr/bin/env bash
# Audit only: no study generation, output repair, or Slurm submission.
set -euo pipefail
: "${STAT01_DIAG_ROOT:?separate diagnosis deployment required}"
original=/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-stat01-454168a00524
python=/project/ikoutis/sv96/github/llm-serving-scheduler-robustness-benchmark/.venv312/bin/python
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export CUDA_VISIBLE_DEVICES=''
cd "$STAT01_DIAG_ROOT"
mkdir -p evidence/full-audit
exec > evidence/full-audit/console.log 2>&1
printf '%s\n' "$$" > evidence/full-audit/wrapper.pid
date -u +%FT%TZ > evidence/full-audit/started_utc.txt
finish() {
  rc=$?
  printf '%s\n' "$rc" > evidence/full-audit/audit.exit
  date -u +%FT%TZ > evidence/full-audit/finished_utc.txt
}
trap finish EXIT
timeout 2h nice -n 10 "$python" -u tools/audit_existing.py \
  --original-root "$original" --evidence-dir "$STAT01_DIAG_ROOT/evidence/full-audit"
