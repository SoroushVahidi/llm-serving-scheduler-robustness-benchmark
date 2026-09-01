#!/bin/bash
#SBATCH --job-name=stage0_merge
#SBATCH --account=ikoutis
#SBATCH --partition=general
#SBATCH --qos=standard
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --output=logs/stage0_pilot/merge_%j.out
#SBATCH --error=logs/stage0_pilot/merge_%j.err
#
# Submit with --dependency=afterany:<stage0_array_job_id> (afterany, not
# afterok -- a merge must still run and report failed cells even if some
# array tasks failed, per section B6's "failed cells remain visible").
# Validates the completed matrix is exactly the expected 1,080 cells (no
# missing/duplicate/extra), then applies the frozen 5-criterion analyzer
# (scripts/stage0/stage0_harness.py validate + a direct call into
# robustbench.stage0.analyzer). Does NOT launch anything further.

set -euo pipefail
cd /project/ikoutis/sv96/github/llm-serving-scheduler-robustness-benchmark
mkdir -p logs/stage0_pilot

OUTPUT_DIR=${STAGE0_OUTPUT_DIR:-results/stage0_pilot_v1}

echo "[$(date -u +%FT%TZ)] validating matrix in $OUTPUT_DIR"
.venv312/bin/python scripts/stage0/stage0_harness.py validate --output-dir "$OUTPUT_DIR" \
  | tee "$OUTPUT_DIR/validation_report.json"

echo "[$(date -u +%FT%TZ)] running 5-criterion analyzer"
.venv312/bin/python - "$OUTPUT_DIR" <<'PYEOF'
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent if "__file__" in dir() else Path(".")
sys.path.insert(0, "src")
from robustbench.stage0.analyzer import analyze_stage0_matrix  # noqa: E402

out_dir = Path(sys.argv[1])
plan = json.load(open(out_dir / "stage0_plan.json"))
cells = []
for c in plan["cells"]:
    p = out_dir / "cells" / (c["cell_id"].replace("::", "__") + ".json")
    if p.exists():
        cells.append(json.load(open(p)))

report = analyze_stage0_matrix(cells)
with open(out_dir / "stage0_analysis_report.json", "w") as f:
    json.dump(report, f, indent=2)
print(json.dumps({"verdict": report["verdict"], "n_cells_successful": report["n_cells_successful"],
                   "n_cells_total": report["n_cells_total"]}, indent=2))
PYEOF

echo "[$(date -u +%FT%TZ)] merge/analyze DONE"
