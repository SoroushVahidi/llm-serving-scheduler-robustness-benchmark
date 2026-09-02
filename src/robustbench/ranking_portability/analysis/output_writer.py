"""Deterministic machine-readable analysis-output contract (§O of the
analysis-prefreeze task). Every artifact this package writes carries the
same four identity fields, so a later reader can verify exactly which
campaign/consolidation/analysis-code/contract version produced it.

Defines the CANONICAL relative paths future real artifacts will use
(`artifacts/analysis/phase12/*`) as data only -- this module never writes
there itself and takes no default path; callers (tests, and any future
production run) always pass an explicit directory.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from .input_manifest import AnalysisInputManifest

CANONICAL_ARTIFACT_RELATIVE_PATHS = {
    "ranking_correlations": "artifacts/analysis/phase12/ranking_correlations.json",
    "topk_overlap": "artifacts/analysis/phase12/topk_overlap.json",
    "pairwise_reversals": "artifacts/analysis/phase12/pairwise_reversals.json",
    "sample_complexity": "artifacts/analysis/phase12/sample_complexity.json",
    "temporal_robustness": "artifacts/analysis/phase12/temporal_robustness.json",
    "telemetry_explanation": "artifacts/analysis/phase12/telemetry_explanation.json",
}


def write_analysis_artifact(
    output_path: Path,
    payload: Mapping,
    *,
    analysis_input_manifest: AnalysisInputManifest,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    full_payload = {
        "campaign_freeze_sha256": analysis_input_manifest.campaign_freeze_sha256,
        "consolidated_result_sha256": analysis_input_manifest.consolidated_result_sha256,
        "analysis_code_git_sha": analysis_input_manifest.analysis_code_git_sha,
        "analysis_contract_version": analysis_input_manifest.analysis_contract_version,
        **payload,
    }
    with open(output_path, "w") as f:
        json.dump(full_payload, f, sort_keys=True, indent=2, default=str)
    return output_path
