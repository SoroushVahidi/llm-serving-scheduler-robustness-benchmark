"""Phase-12D provenance enrichment contract for completed Pilot-V2 results.

This module is intentionally outcome-blind.  It defines only identities that
were fixed by the Phase-10/11/12B contracts or by the exact Phase-12C runtime
configuration.  It never reads scheduler metrics and never executes a policy.

The Phase-12C executor produced scientifically complete rows but left five
provenance fields empty because ``RankingPortabilityCellResult.from_run`` did
not accept them.  Phase-12D repairs that metadata in a derivative namespace;
raw result files remain immutable.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from typing import Mapping, Optional

from ..calibration.stage0_load_calibration import STAGE0_REFERENCE_GPU_CONFIG
from ..simulator.service_model import ServiceModel
from ..workloads.external.benchmark_synthesis import SYNTHESIS_VERSION
from .phase12_campaign import SCIENTIFIC_STATUS_PILOT_V2_SCIENTIFIC
from .schema import validate_cell_result

PROVENANCE_CONTRACT_VERSION = "phase12_provenance_v1"
SIMULATOR_CONFIG_CONTRACT_VERSION = "phase12_simulator_config_v1"

# Fields that were present in the execution schema but left empty by Phase-12C.
REPAIRED_SCHEMA_FIELDS = (
    "window_manifest_sha256",
    "calibration_manifest_sha256",
    "policy_registry_hash",
    "simulator_config_hash",
    "synthesis_version",
)

# Explicit Phase-11 identities added during repair so the historically
# ambiguous generic calibration field cannot hide the distinction between
# raw FIFO calibration output and the final region-assignment artifact that
# actually determines each campaign cell's load.
EXPLICIT_PHASE11_FIELDS = (
    "phase11_raw_fifo_calibration_sha256",
    "phase11_region_assignments_sha256",
)

APPROVED_ENRICHMENT_FIELDS = REPAIRED_SCHEMA_FIELDS + EXPLICIT_PHASE11_FIELDS


def canonical_json_sha256(payload) -> str:
    """SHA-256 over stable sorted compact JSON.

    ``allow_nan=True`` is deliberate: the scientific schema legitimately uses
    NaN for documented undefined conditional metrics.  Canonical JSON hashing
    therefore provides a stable invariance comparison even when raw and
    enriched rows are parsed in separate ``json.load`` calls (two Python NaN
    objects do not compare equal with ordinary dict equality).
    """
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def phase12_simulator_config_payload() -> dict:
    """Exact runtime configuration constructed by Phase-12C.

    ``run_phase12_campaign_shard.py`` calls ``execute_cell`` with one
    ``STAGE0_REFERENCE_GPU_CONFIG``, no explicit service model, and the
    default ``drain_steps=50_000``.  ``execute_cell`` therefore constructs a
    default ``ServiceModel`` and a ``SimulatorConfig`` whose remaining values
    are ``max_steps=None`` and ``warn_on_invalid_action=True``.

    Source-file hashes are separately pinned by the Phase-12B campaign
    manifest; this hash identifies *configuration values*, not source code.
    """
    return {
        "contract_version": SIMULATOR_CONFIG_CONTRACT_VERSION,
        "gpu_configs": [asdict(STAGE0_REFERENCE_GPU_CONFIG)],
        "service_model": asdict(ServiceModel()),
        "simulator_config": {
            "max_steps": None,
            "drain_steps": 50_000,
            "warn_on_invalid_action": True,
        },
    }


def phase12_simulator_config_hash() -> str:
    return canonical_json_sha256(phase12_simulator_config_payload())


def expected_phase12_provenance(campaign_manifest: Mapping) -> dict:
    """Reconstruct outcome-independent provenance from the frozen manifest.

    ``calibration_manifest_sha256`` is defined, by Phase-12D clarification,
    as the hash of the manifest consumed to determine each scientific cell's
    load.  Stage-0's harness used this same semantic convention: the field was
    the SHA-256 of the calibration manifest passed into the cell plan.  For
    Phase-12, cells consume the frozen Phase-11 *region assignments* artifact,
    while the raw FIFO calibration remains upstream source provenance and is
    recorded explicitly in its own field.
    """
    required = (
        "phase10_window_hash",
        "phase11_raw_fifo_hash",
        "phase11_region_assignment_hash",
        "execution_file_hashes",
    )
    missing = [k for k in required if not campaign_manifest.get(k)]
    if missing:
        raise ValueError(f"campaign manifest missing provenance identity keys: {missing}")

    policy_path = "src/robustbench/policies/registry.py"
    execution_hashes = campaign_manifest["execution_file_hashes"]
    if policy_path not in execution_hashes:
        raise ValueError(f"campaign execution_file_hashes missing {policy_path}")

    return {
        "window_manifest_sha256": campaign_manifest["phase10_window_hash"],
        "calibration_manifest_sha256": campaign_manifest["phase11_region_assignment_hash"],
        "policy_registry_hash": execution_hashes[policy_path],
        "simulator_config_hash": phase12_simulator_config_hash(),
        "synthesis_version": SYNTHESIS_VERSION,
        "phase11_raw_fifo_calibration_sha256": campaign_manifest["phase11_raw_fifo_hash"],
        "phase11_region_assignments_sha256": campaign_manifest["phase11_region_assignment_hash"],
    }


def enrich_row_provenance(row: Mapping, expected: Mapping) -> dict:
    """Return a copy with only approved provenance fields enriched.

    Empty/missing approved fields are filled.  A non-empty conflicting value
    is a hard error: Phase-12D is metadata completion, never provenance
    rewriting.
    """
    out = dict(row)
    for field in APPROVED_ENRICHMENT_FIELDS:
        value = expected[field]
        existing = out.get(field)
        if existing not in (None, "") and existing != value:
            raise ValueError(
                f"conflicting provenance for {row.get('cell_id', '<unknown>')} "
                f"field {field}: existing={existing!r}, expected={value!r}"
            )
        out[field] = value
    return out


def masked_non_provenance_view(row: Mapping) -> dict:
    """Copy a row with approved repair fields removed for invariance checks."""
    return {k: v for k, v in row.items() if k not in APPROVED_ENRICHMENT_FIELDS}


def masked_non_provenance_hash(row: Mapping) -> str:
    """Canonical, NaN-safe identity of every non-repair field in a row."""
    return canonical_json_sha256(masked_non_provenance_view(row))


def validate_analysis_admission_row(
    row: Mapping,
    campaign_manifest: Mapping,
    *,
    expected_execution_repo_sha: Optional[str] = None,
) -> list[str]:
    """Stricter admission validation layered above execution-row validity.

    The historical/raw Phase-12C rows remain valid execution artifacts under
    ``validate_cell_result``.  They are not admitted to analysis/release until
    this function also verifies complete, exact provenance.
    """
    problems = list(validate_cell_result(dict(row)))
    if row.get("scientific_status") != SCIENTIFIC_STATUS_PILOT_V2_SCIENTIFIC:
        problems.append(
            "analysis admission requires scientific_status=PILOT_V2_SCIENTIFIC"
        )

    expected = expected_phase12_provenance(campaign_manifest)
    for field in APPROVED_ENRICHMENT_FIELDS:
        value = row.get(field)
        if value in (None, ""):
            problems.append(f"analysis admission provenance field empty: {field}")
        elif value != expected[field]:
            problems.append(
                f"analysis admission provenance mismatch: {field}: "
                f"expected={expected[field]!r}, observed={value!r}"
            )

    if expected_execution_repo_sha is not None:
        if row.get("repo_sha") != expected_execution_repo_sha:
            problems.append(
                f"execution repo_sha mismatch: expected={expected_execution_repo_sha}, "
                f"observed={row.get('repo_sha')}"
            )
    return problems


__all__ = [
    "PROVENANCE_CONTRACT_VERSION",
    "SIMULATOR_CONFIG_CONTRACT_VERSION",
    "REPAIRED_SCHEMA_FIELDS",
    "EXPLICIT_PHASE11_FIELDS",
    "APPROVED_ENRICHMENT_FIELDS",
    "canonical_json_sha256",
    "phase12_simulator_config_payload",
    "phase12_simulator_config_hash",
    "expected_phase12_provenance",
    "enrich_row_provenance",
    "masked_non_provenance_view",
    "masked_non_provenance_hash",
    "validate_analysis_admission_row",
]
