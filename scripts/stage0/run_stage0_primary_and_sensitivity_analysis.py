#!/usr/bin/env python3
"""Runs the frozen Stage-0 five-criterion analyzer (robustbench.stage0.analyzer,
UNCHANGED by this repair) against the real completed 1,080-cell matrix under
three conventions for slo_violation_rate at completion_fraction==0.0:

  UNDEFINED  -- the actual, on-disk data (this repair's decision: NaN, no
               imputation). This is the PRIMARY analysis.
  FORCE_ZERO -- counterfactual: slo_violation_rate = 0.0 at zero completion.
  FORCE_ONE  -- counterfactual: slo_violation_rate = 1.0 at zero completion.

FORCE_ZERO/FORCE_ONE are in-memory substitutions only -- never written back
to results/stage0_v1/cells/*.json. This is a mandatory sensitivity check
(docs/STAGE0_ZERO_COMPLETION_METRIC_AMENDMENT_20260901.md, section E): if
the overall verdict differs across the three conventions, the final
Stage-0 status must be reported as STAGE0_INCONCLUSIVE regardless of what
the primary (UNDEFINED) convention alone would yield.

Does not modify analyzer.py, any threshold, or any result file. Does not
launch anything.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, "src")
from robustbench.stage0.analyzer import analyze_stage0_matrix  # noqa: E402


def _load_cells(out_dir: Path) -> list[dict]:
    plan = json.load(open(out_dir / "stage0_plan.json"))
    cells = []
    for c in plan["cells"]:
        p = out_dir / "cells" / (c["cell_id"].replace("::", "__") + ".json")
        cells.append(json.load(open(p)))
    return cells


def _apply_convention(cells: list[dict], convention: str) -> list[dict]:
    out = copy.deepcopy(cells)
    for c in out:
        if c.get("success") and c.get("completion_fraction") == 0.0:
            svr = c.get("slo_violation_rate")
            is_nan = isinstance(svr, float) and svr != svr
            if convention == "FORCE_ZERO" and is_nan:
                c["slo_violation_rate"] = 0.0
            elif convention == "FORCE_ONE" and is_nan:
                c["slo_violation_rate"] = 1.0
            # UNDEFINED: leave as-is (NaN, the real on-disk value)
    return out


def main() -> None:
    out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "results/stage0_v1")
    cells = _load_cells(out_dir)

    results = {}
    for convention in ("UNDEFINED", "FORCE_ZERO", "FORCE_ONE"):
        conv_cells = _apply_convention(cells, convention)
        report = analyze_stage0_matrix(conv_cells)
        results[convention] = report

    primary = results["UNDEFINED"]
    verdicts = {k: v["verdict"] for k, v in results.items()}
    verdict_robust = len(set(verdicts.values())) == 1

    final = {
        "primary_convention": "UNDEFINED",
        "primary_report": primary,
        "sensitivity": {
            k: {
                "verdict": v["verdict"],
                "criterion_4": next(c for c in v["criteria"] if c["criterion"] == 4),
            }
            for k, v in results.items()
        },
        "verdicts_by_convention": verdicts,
        "verdict_robust_to_convention": verdict_robust,
        "final_stage0_status": (
            primary["verdict"] if verdict_robust else "STAGE0_INCONCLUSIVE"
        ),
    }

    with open(out_dir / "stage0_analysis_report.json", "w") as f:
        json.dump(primary, f, indent=2)
    with open(out_dir / "stage0_analysis_report_with_sensitivity.json", "w") as f:
        json.dump(final, f, indent=2)

    print(json.dumps(final, indent=2))


if __name__ == "__main__":
    main()
