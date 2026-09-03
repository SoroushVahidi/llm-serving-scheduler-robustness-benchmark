"""Execute one frozen RQ3 campaign manifest's cells.

Reuses `robustbench.ranking_portability.execute_cell.execute_cell` (the
same per-cell simulator-execution + telemetry + schema-validation path used
for the real Phase-12 campaign) unchanged -- this module only supplies
synthetic requests instead of real-trace-derived ones.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from ..calibration.stage0_load_calibration import STAGE0_REFERENCE_GPU_CONFIG, _rebase_and_scale
from ..policies.registry import make_policy_any
from ..ranking_portability.execute_cell import execute_cell
from .campaign import _git_sha
from .synthetic_families import generate_family_window


def run_cell(cell: Dict[str, Any]) -> Dict[str, Any]:
    """Run one manifest cell dict (as produced by `campaign.build_manifest`)
    and return the `RankingPortabilityCellResult` dict."""
    requests = generate_family_window(cell["family_id"], cell["seed"])
    scaled = _rebase_and_scale(requests, cell["load_factor"])
    policy = make_policy_any(cell["policy_id"], seed=0)
    result = execute_cell(
        cell_id=cell["cell_id"],
        source_family=f"synthetic_{cell['family_id']}",
        window_id=cell["window_id"],
        load_region=cell["load_region"],
        load_factor=cell["load_factor"],
        policy_id=cell["policy_id"],
        repetition=cell["repetition"],
        synthesis_seed=cell["seed"],
        repo_sha=_git_sha(),
        policy=policy,
        requests=scaled,
        gpu_configs=[STAGE0_REFERENCE_GPU_CONFIG],
        scientific_status="RQ3_SYNTHETIC_TO_REAL_TARGETED_CAMPAIGN",
    )
    return result.to_dict()


def run_manifest(manifest: Dict[str, Any], out_dir: Path) -> Dict[str, int]:
    """Run every cell in `manifest`, writing one JSON file per cell under
    `out_dir/<family_id>/<cell_id>.json`. Returns a small progress summary
    (not the results themselves) so callers can validate without holding
    440 result dicts in memory at once."""
    out_dir.mkdir(parents=True, exist_ok=True)
    n_ok, n_failed = 0, 0
    for cell in manifest["cells"]:
        result = run_cell(cell)
        family_dir = out_dir / cell["family_id"]
        family_dir.mkdir(parents=True, exist_ok=True)
        with open(family_dir / f"{cell['cell_id']}.json", "w") as f:
            json.dump(result, f, indent=2, sort_keys=True)
        if result.get("success"):
            n_ok += 1
        else:
            n_failed += 1
    return {"n_cells": len(manifest["cells"]), "n_ok": n_ok, "n_failed": n_failed}
