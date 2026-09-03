"""LSSP dataset-release table/config contract (docs/LSSP_DATASET_RELEASE_SCHEMA.md).

Extends the pre-existing generic `docs/DATASET_V2_SCHEMA.md` bootstrap
design (table naming/join-key/provenance-completeness conventions) with
the LSSP-specific structure actually frozen for Phase-12: explicit
per-(source, window, region) load assignments as their own table (Phase-11
provenance), a `scheduler_outcomes` row schema that IS
`robustbench.ranking_portability.schema.RankingPortabilityCellResult`
(reused verbatim, not reinvented), and a campaign-freeze-identity-keyed
provenance contract instead of DATASET_V2_SCHEMA.md's more generic
`experiment_version`/`config_hash` fields.

Nothing in this module computes, stores, or requires a real scheduler
outcome value.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from ..ranking_portability.schema import (
    CELL_SCHEMA_VERSION,
    REQUIRED_TOP_LEVEL_FIELDS,
    validate_cell_result,
)

#: Release-version naming. DATASET_V2_SCHEMA.md's "Dataset v2" name refers to
#: the broader robustness-benchmark project's *generic* schema bootstrap and
#: predates the LSSP/Phase-12 campaign identity entirely (no campaign-freeze
#: SHA, no cell_id format, no six-region grid) -- it is prior art for table
#: conventions, not the release this contract describes. This is a new,
#: LSSP-specific release line, versioned independently.
LSSP_DATASET_RELEASE_VERSION = "lssp_dataset_v1"

#: The eight logical tables/configs (docs/LSSP_DATASET_RELEASE_SCHEMA.md §D).
LSSP_DATASET_TABLES = (
    "workload_windows",
    "workload_descriptors",
    "load_region_assignments",
    "policy_registry",
    "scheduler_outcomes",
    "telemetry",
    "analysis_metadata",
    "extension_configs",
)

#: Tables buildable now, directly from already-frozen Phase-10/11/12B
#: manifests -- none of these carry a scheduler outcome value.
STATIC_TABLES_BUILDABLE_PREFREEZE = (
    "workload_windows",
    "workload_descriptors",
    "load_region_assignments",
    "policy_registry",
)

#: scheduler_outcomes/telemetry require a validated consolidated Phase-12
#: artifact that does not exist yet (schema-only until then).
RESULT_DEPENDENT_TABLES = ("scheduler_outcomes", "telemetry")

#: analysis_metadata carries identity references only, populated once the
#: analysis-prefreeze and consolidator artifacts exist; never real outcomes.
IDENTITY_ONLY_TABLES = ("analysis_metadata",)

#: TraceLab / synthetic-stress-envelope configs -- included only if/when the
#: separate reuse audit (docs/EXPERIMENT_REUSE_AUDIT_20260902.md, on branch
#: research/lssp-phase12-reuse-audit-20260902) determines they are
#: scientifically compatible with the LSSP core release. Not populated here.
EXTENSION_CONFIG_NAMES = ("tracelab_ood", "synthetic_stress_envelope")


# ---------------------------------------------------------------------------
# Row-level provenance field classification (docs/LSSP_DATASET_RELEASE_SCHEMA.md §E)
# ---------------------------------------------------------------------------

class FieldCategory:
    IDENTIFIER = "IDENTIFIER"
    SCIENTIFIC_INPUT = "SCIENTIFIC_INPUT"
    OUTCOME = "OUTCOME"
    PROVENANCE_METADATA = "PROVENANCE_METADATA"


#: scheduler_outcomes row field -> category. Field names are exactly
#: `RankingPortabilityCellResult`'s fields (reused, not renamed) plus the
#: release-level identity fields this contract adds on top.
SCHEDULER_OUTCOMES_FIELD_CATEGORY: dict[str, str] = {
    # Identifiers
    "cell_id": FieldCategory.IDENTIFIER,
    "source_family": FieldCategory.IDENTIFIER,
    "window_id": FieldCategory.IDENTIFIER,
    "load_region": FieldCategory.IDENTIFIER,
    "policy_id": FieldCategory.IDENTIFIER,
    "repetition": FieldCategory.IDENTIFIER,
    # Scientific inputs (fixed before any cell is executed; not derived from
    # an outcome)
    "load_factor": FieldCategory.SCIENTIFIC_INPUT,
    "synthesis_seed": FieldCategory.SCIENTIFIC_INPUT,
    "synthesis_version": FieldCategory.SCIENTIFIC_INPUT,
    # Outcomes (scheduler-performance-bearing; never present in this
    # prefreeze package)
    "arrival_normalized_weighted_goodput": FieldCategory.OUTCOME,
    "completion_fraction": FieldCategory.OUTCOME,
    "weighted_completion_fraction": FieldCategory.OUTCOME,
    "slo_violation_rate": FieldCategory.OUTCOME,
    "weighted_goodput": FieldCategory.OUTCOME,
    "mean_latency": FieldCategory.OUTCOME,
    "p95_latency": FieldCategory.OUTCOME,
    "mean_ttft": FieldCategory.OUTCOME,
    "p95_ttft": FieldCategory.OUTCOME,
    "request_throughput": FieldCategory.OUTCOME,
    "token_throughput": FieldCategory.OUTCOME,
    "telemetry": FieldCategory.OUTCOME,
    "telemetry_schema_version": FieldCategory.PROVENANCE_METADATA,
    "success": FieldCategory.OUTCOME,
    "error_category": FieldCategory.OUTCOME,
    "error_detail": FieldCategory.OUTCOME,
    # Provenance metadata
    "repo_sha": FieldCategory.PROVENANCE_METADATA,
    "window_manifest_sha256": FieldCategory.PROVENANCE_METADATA,
    "calibration_manifest_sha256": FieldCategory.PROVENANCE_METADATA,
    "policy_registry_hash": FieldCategory.PROVENANCE_METADATA,
    "simulator_config_hash": FieldCategory.PROVENANCE_METADATA,
    "environment": FieldCategory.PROVENANCE_METADATA,
    "scientific_status": FieldCategory.PROVENANCE_METADATA,
    "schema_version": FieldCategory.PROVENANCE_METADATA,
    # Release-level additions (not part of RankingPortabilityCellResult
    # itself; stamped on export)
    "dataset_release_version": FieldCategory.PROVENANCE_METADATA,
    "campaign_freeze_sha256": FieldCategory.PROVENANCE_METADATA,
}

assert set(REQUIRED_TOP_LEVEL_FIELDS) <= set(SCHEDULER_OUTCOMES_FIELD_CATEGORY), (
    "SCHEDULER_OUTCOMES_FIELD_CATEGORY must classify every field the "
    "reused RankingPortabilityCellResult schema requires -- an addition "
    "there without a category here is exactly the kind of drift this "
    "contract exists to catch."
)


# ---------------------------------------------------------------------------
# Frozen campaign identity (ground truth for identifier validation)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FrozenCampaignIdentity:
    campaign_freeze_sha256: str
    full_matrix_hash: str
    expected_cell_count: int
    cell_ids: frozenset
    window_ids: frozenset
    source_families: frozenset
    load_regions: frozenset
    policy_ids: frozenset
    region_assignment_keys: frozenset


def load_frozen_campaign_identity(manifest_path: Path) -> FrozenCampaignIdentity:
    """Reads the (already-committed, already-validated) Phase-12B campaign
    freeze manifest. Read-only: never computes a new campaign matrix, never
    touches a scientific outcome (the freeze manifest contains none)."""
    data = json.loads(Path(manifest_path).read_text())
    cells = data["cells"]
    return FrozenCampaignIdentity(
        campaign_freeze_sha256=data["campaign_freeze_sha256"],
        full_matrix_hash=data["full_matrix_hash"],
        expected_cell_count=data["EXPECTED_PHASE12_CAMPAIGN_CELLS"],
        cell_ids=frozenset(c["cell_id"] for c in cells),
        window_ids=frozenset(c["window_id"] for c in cells),
        source_families=frozenset(c["source_family"] for c in cells),
        load_regions=frozenset(c["load_region"] for c in cells),
        policy_ids=frozenset(c["policy_id"] for c in cells),
        region_assignment_keys=frozenset(data["region_assignment_index"].keys()),
    )


# ---------------------------------------------------------------------------
# scheduler_outcomes row validation
# ---------------------------------------------------------------------------

def validate_scheduler_outcomes_row(
    row: dict, identity: FrozenCampaignIdentity
) -> list[str]:
    """Validates one future scheduler_outcomes row. Delegates all
    metric/telemetry undefined-semantics checking to
    `ranking_portability.schema.validate_cell_result` (reused verbatim --
    never reimplemented, so the NaN/None undefined-metric rule can never
    silently drift between the execution schema and the release schema).
    Adds only release-identity checks on top: right campaign, known cell
    ID, no promoted-from-elsewhere cell.
    """
    problems = list(validate_cell_result(row))

    if row.get("dataset_release_version") != LSSP_DATASET_RELEASE_VERSION:
        problems.append(
            "dataset_release_version missing or does not match "
            f"{LSSP_DATASET_RELEASE_VERSION!r}"
        )

    campaign_sha = row.get("campaign_freeze_sha256")
    if campaign_sha != identity.campaign_freeze_sha256:
        problems.append(
            f"campaign_freeze_sha256 mismatch: row has {campaign_sha!r}, "
            f"frozen identity is {identity.campaign_freeze_sha256!r}"
        )

    cell_id = row.get("cell_id")
    if cell_id not in identity.cell_ids:
        problems.append(f"cell_id {cell_id!r} is not one of the 18,720 frozen cell IDs")

    if row.get("scientific_status") != "PILOT_V2_SCIENTIFIC":
        problems.append(
            "scientific_status must be exactly 'PILOT_V2_SCIENTIFIC' -- a "
            "Stage-0/Phase-12A-smoke row must never be promoted into this table"
        )

    return problems


# ---------------------------------------------------------------------------
# Static (result-independent) tables
# ---------------------------------------------------------------------------

def build_workload_windows_table(windows_index: dict) -> list[dict]:
    """One row per frozen window (120 rows). Source: the already-frozen
    Phase-10 windows-index manifest; no scientific outcome involved."""
    rows = []
    for w in windows_index["windows"]:
        rows.append({
            "workload_window_id": w["window_id"],
            "source_family": w["source_family"],
            "evidence_class": w["evidence_class"],
            "chronology_stratum": w["chronology_stratum"],
            "request_count": w["request_count"],
            "arrival_time_s_min": w["arrival_time_s_min"],
            "arrival_time_s_max": w["arrival_time_s_max"],
            "source_file": w["source_file"],
            "source_file_sha256": w["source_file_sha256"],
            "sampling_algorithm": w["sampling_algorithm"],
            "sampling_seed": w["sampling_seed"],
        })
    return rows


def build_workload_descriptors_table(windows_index: dict) -> list[dict]:
    """One row per window: the embedded `WindowDescriptor`, unmodified."""
    rows = []
    for w in windows_index["windows"]:
        d = dict(w["descriptor"])
        d["workload_window_id"] = d.pop("window_id")
        rows.append(d)
    return rows


def build_load_region_assignments_table(identity_manifest: dict) -> list[dict]:
    """One row per (source, window, region) -- 720 rows -- Phase-11
    provenance, read verbatim from the campaign freeze manifest's
    `region_assignment_index` (itself sourced from the frozen Phase-11
    region-assignment artifact; never recomputed here)."""
    rows = []
    for key, v in identity_manifest["region_assignment_index"].items():
        source_family, window_id, region = key.split("::")
        rows.append({
            "source_family": source_family,
            "workload_window_id": window_id,
            "load_region": region,
            "lambda_ref": v["lambda_ref"],
            "selected_load_factor": v["selected_load_factor"],
            "absolute_load_factor": v["absolute_load_factor"],
            "phase11_region_assignment_hash": identity_manifest["phase11_region_assignment_hash"],
        })
    return rows


def build_policy_registry_table(campaign_policies: list[dict]) -> list[dict]:
    """13 rows: id, fidelity class, PRIMARY-vs-STYLE_APPROXIMATION status.
    `campaign_policies` is the frozen panel
    (docs/RANKING_PORTABILITY_POLICY_PANEL.md), passed in by the caller
    rather than re-derived here so this function has no import-time
    dependency on the policy registry module."""
    return list(campaign_policies)


def compute_aggregate_hash(*payloads: Any) -> str:
    """SHA-256 over the sorted-key JSON of all payloads concatenated --
    same convention as `phase12_campaign.compute_campaign_freeze_identity`."""
    h = hashlib.sha256()
    for p in payloads:
        h.update(json.dumps(p, sort_keys=True, default=str).encode("utf-8"))
    return h.hexdigest()
