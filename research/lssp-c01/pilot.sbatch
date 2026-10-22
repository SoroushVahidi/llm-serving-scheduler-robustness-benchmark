#!/usr/bin/env bash
#SBATCH --job-name=lssp-c01-cm-pilot
#SBATCH --partition=general
#SBATCH --qos=standard
#SBATCH --account=ikoutis
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=02:00:00
#SBATCH --signal=B:TERM@120
# Submit with explicit --chdir, --output and --error paths. No GPU request.
set -euo pipefail
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export CUDA_VISIBLE_DEVICES=''
: "${C01_ROOT:?missing C01_ROOT}"
: "${C01_RUN_ID:?missing C01_RUN_ID}"
: "${C01_PYTHON:?missing pinned Python executable}"
run_dir="$C01_ROOT/runs/$C01_RUN_ID"
mkdir -p "$run_dir"
export C01_RUN_DIR="$run_dir"
finish() {
  rc=$?
  printf '%s\n' "$rc" > "$C01_RUN_DIR/slurm.exit"
  date -u +%FT%TZ > "$C01_RUN_DIR/finished_utc.txt"
}
trap finish EXIT
trap 'exit 143' TERM INT
date -u +%FT%TZ > "$run_dir/started_utc.txt"
printf '%s\n' "$$" > "$run_dir/wrapper.pid"
"$C01_PYTHON" -u "$C01_ROOT/code/run.py" --inputs "$C01_ROOT/inputs/pilot-inputs.json" \
  --launch "$C01_ROOT/launch.json" --out "$run_dir"
