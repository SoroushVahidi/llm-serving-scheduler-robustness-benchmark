"""Analysis-input freeze manifest (§G of the analysis-prefreeze task).

Statistical analysis must never read arbitrary shard files directly --
it consumes exactly one thing: a consolidated result that has already
passed `matrix_validator.validate_completed_campaign`. This module
defines that immutable input-identity record and the gate function that
refuses to proceed without one.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping

from .contract import ANALYSIS_CONTRACT_VERSION

ANALYSIS_INPUT_MANIFEST_KIND = "phase12_analysis_input_manifest_v1"


def _canonical_sha256(payload) -> str:
    blob = json.dumps(payload, sort_keys=True, default=str).encode()
    return hashlib.sha256(blob).hexdigest()


@dataclass(frozen=True)
class AnalysisInputManifest:
    manifest_kind: str
    campaign_freeze_sha256: str
    consolidated_result_sha256: str
    matrix_validation_report_sha256: str
    analysis_code_git_sha: str
    analysis_contract_version: str
    metric_definitions_version: str
    policy_panel_identity_sha256: str

    def to_dict(self) -> dict:
        return asdict(self)


def build_analysis_input_manifest(
    *,
    campaign_freeze_sha256: str,
    consolidated_rows: Mapping[str, dict],
    matrix_validation_problems: list,
    repo_root: Path,
    metric_definitions_version: str = "ranking_portability_metric_definitions_v1",
) -> AnalysisInputManifest:
    """Refuses (raises) unless the matrix validation report it is given
    is CLEAN (no problems) -- an analysis-input manifest can never be
    built "optimistically" against a matrix that failed independent
    validation."""
    if matrix_validation_problems:
        raise ValueError(
            "Refusing to build an analysis-input manifest: matrix validation "
            f"reported {len(matrix_validation_problems)} problem(s), e.g. "
            f"{matrix_validation_problems[:3]}. Analysis must not begin."
        )

    consolidated_sha = _canonical_sha256(
        {cid: consolidated_rows[cid] for cid in sorted(consolidated_rows)}
    )
    validation_report_sha = _canonical_sha256({"problems": matrix_validation_problems})

    try:
        git_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo_root
        ).decode().strip()
    except Exception:  # noqa: BLE001 -- tests may run outside a git checkout
        git_sha = "UNKNOWN"

    from .contract import ALL_CAMPAIGN_POLICIES, PRIMARY_POLICIES, STYLE_APPROXIMATION_POLICIES
    panel_sha = _canonical_sha256({
        "all": list(ALL_CAMPAIGN_POLICIES),
        "primary": list(PRIMARY_POLICIES),
        "style_approximation": list(STYLE_APPROXIMATION_POLICIES),
    })

    return AnalysisInputManifest(
        manifest_kind=ANALYSIS_INPUT_MANIFEST_KIND,
        campaign_freeze_sha256=campaign_freeze_sha256,
        consolidated_result_sha256=consolidated_sha,
        matrix_validation_report_sha256=validation_report_sha,
        analysis_code_git_sha=git_sha,
        analysis_contract_version=ANALYSIS_CONTRACT_VERSION,
        metric_definitions_version=metric_definitions_version,
        policy_panel_identity_sha256=panel_sha,
    )
