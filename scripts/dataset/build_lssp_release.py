#!/usr/bin/env python3
"""Deterministic LSSP dataset-release builder
(docs/LSSP_DATASET_RELEASE_SCHEMA.md, docs/LSSP_DATASET_RELEASE_PREFREEZE.md).

Builds the four static tables (workload_windows, workload_descriptors,
load_region_assignments, policy_registry) directly from the already-frozen
Phase-10/11/12B manifests -- none of these carry a scheduler outcome.

Refuses to build `scheduler_outcomes`/`telemetry` unless given:
  --consolidated-input <path>   a consolidated Phase-12 campaign artifact
  --matrix-validation-report <path>  its passing completed-matrix validation report

and refuses both unless their campaign identity matches this repo's frozen
`campaign_freeze_sha256` exactly, and the validation report says the
matrix is complete (18,720/18,720, 0 problems). This script performs no
statistical analysis and does not itself decide whether an outcome is
"good" -- it only ever copies validated rows into the release format.

Output: JSON per table under --out-dir (Parquet export is available when
`pyarrow` is installed; falls back to JSON-only with a note, never fails
the whole build over an optional dependency).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.dataset.lssp_release_contract import (  # noqa: E402
    LSSP_DATASET_RELEASE_VERSION,
    build_load_region_assignments_table,
    build_policy_registry_table,
    build_workload_descriptors_table,
    build_workload_windows_table,
    compute_aggregate_hash,
    load_frozen_campaign_identity,
)

DEFAULT_CAMPAIGN_MANIFEST = (
    REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_campaign_freeze.json"
)
DEFAULT_WINDOWS_INDEX = (
    REPO_ROOT / "artifacts/manifests/ranking_portability_pilot_v2_windows_index.json"
)

# Frozen 13-policy panel (docs/RANKING_PORTABILITY_POLICY_PANEL.md §6).
# Hardcoded here, matching the frozen doc verbatim, rather than importing
# the runtime policy registry -- this table is about the *frozen panel
# identity*, independent of any future registry code change.
CAMPAIGN_POLICY_PANEL = [
    {"policy_id": "fifo", "fidelity_class": "REPOSITORY_NATIVE_CLASSICAL", "panel_status": "PRIMARY"},
    {"policy_id": "edf", "fidelity_class": "REPOSITORY_NATIVE_CLASSICAL", "panel_status": "PRIMARY"},
    {"policy_id": "least_laxity_first", "fidelity_class": "REPOSITORY_NATIVE_CLASSICAL", "panel_status": "PRIMARY"},
    {"policy_id": "estimated_service_time_first", "fidelity_class": "REPOSITORY_NATIVE_CLASSICAL", "panel_status": "PRIMARY"},
    {"policy_id": "weighted_fair_share", "fidelity_class": "REPOSITORY_NATIVE_CLASSICAL", "panel_status": "PRIMARY"},
    {"policy_id": "kv_constrained_online", "fidelity_class": "SIMULATOR_PROXY", "panel_status": "PRIMARY"},
    {"policy_id": "vllm_faithful", "fidelity_class": "FAITHFUL_EXTERNAL", "panel_status": "PRIMARY"},
    {"policy_id": "vllm_chunked_prefill_faithful", "fidelity_class": "FAITHFUL_EXTERNAL", "panel_status": "PRIMARY"},
    {"policy_id": "sarathi_faithful", "fidelity_class": "FAITHFUL_EXTERNAL", "panel_status": "PRIMARY"},
    {"policy_id": "slai_faithful", "fidelity_class": "FAITHFUL_EXTERNAL", "panel_status": "PRIMARY"},
    {"policy_id": "admission_control", "fidelity_class": "REPOSITORY_NATIVE_CLASSICAL", "panel_status": "PRIMARY"},
    {"policy_id": "vllm_style_token_budget", "fidelity_class": "STYLE_APPROXIMATION", "panel_status": "ROBUSTNESS_ONLY"},
    {"policy_id": "scorpio_style_slo_guard", "fidelity_class": "STYLE_APPROXIMATION", "panel_status": "ROBUSTNESS_ONLY"},
]


def _write_table(out_dir: Path, name: str, rows: list[dict]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.json"
    path.write_text(json.dumps({"table": name, "rows": rows}, indent=2, default=str))
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq

        pq.write_table(pa.Table.from_pylist(rows), out_dir / f"{name}.parquet")
    except ImportError:
        pass  # Parquet export optional; JSON is always written.
    return path


def build_static_tables(out_dir: Path, campaign_manifest: Path, windows_index_path: Path) -> dict:
    identity = load_frozen_campaign_identity(campaign_manifest)
    manifest = json.loads(campaign_manifest.read_text())
    windows_index = json.loads(windows_index_path.read_text())

    tables = {
        "workload_windows": build_workload_windows_table(windows_index),
        "workload_descriptors": build_workload_descriptors_table(windows_index),
        "load_region_assignments": build_load_region_assignments_table(manifest),
        "policy_registry": build_policy_registry_table(CAMPAIGN_POLICY_PANEL),
    }

    written = {}
    for name, rows in tables.items():
        path = _write_table(out_dir, name, rows)
        written[name] = {"path": str(path), "n_rows": len(rows)}

    release_manifest = {
        "dataset_release_version": LSSP_DATASET_RELEASE_VERSION,
        "campaign_freeze_sha256": identity.campaign_freeze_sha256,
        "full_matrix_hash": identity.full_matrix_hash,
        "tables_built": written,
        "result_dependent_tables_built": False,
        "scheduler_outcomes_present": False,
    }
    release_manifest["release_manifest_sha256"] = compute_aggregate_hash(release_manifest)
    (out_dir / "release_manifest.json").write_text(json.dumps(release_manifest, indent=2))
    return release_manifest


def build_result_dependent_tables(
    out_dir: Path,
    campaign_manifest: Path,
    consolidated_input: Path,
    matrix_validation_report: Path,
) -> None:
    """Refuses on: wrong campaign identity, incomplete matrix, missing/failed
    validation report. Never inspects outcome *direction* -- only copies
    already-validated rows through unchanged."""
    identity = load_frozen_campaign_identity(campaign_manifest)

    report = json.loads(matrix_validation_report.read_text())
    if report.get("campaign_freeze_sha256") != identity.campaign_freeze_sha256:
        raise SystemExit(
            "REFUSED: matrix-validation-report campaign_freeze_sha256 does not match "
            f"this repo's frozen identity ({identity.campaign_freeze_sha256})"
        )
    if not report.get("matrix_complete") or report.get("n_problems", 1) != 0:
        raise SystemExit(
            "REFUSED: matrix-validation-report does not report a complete, "
            "zero-problem 18,720-cell matrix -- will not build scheduler_outcomes "
            "from an incomplete or invalid campaign"
        )

    consolidated = json.loads(consolidated_input.read_text())
    if consolidated.get("campaign_freeze_sha256") != identity.campaign_freeze_sha256:
        raise SystemExit(
            "REFUSED: consolidated-input campaign_freeze_sha256 does not match "
            f"this repo's frozen identity ({identity.campaign_freeze_sha256})"
        )

    rows = consolidated["cells"]
    if len(rows) != identity.expected_cell_count:
        raise SystemExit(
            f"REFUSED: consolidated input has {len(rows)} rows, expected "
            f"{identity.expected_cell_count}"
        )

    for row in rows:
        row["dataset_release_version"] = LSSP_DATASET_RELEASE_VERSION
        row["campaign_freeze_sha256"] = identity.campaign_freeze_sha256

    _write_table(out_dir, "scheduler_outcomes", rows)
    print(f"Wrote {len(rows)} scheduler_outcomes rows to {out_dir}.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--campaign-manifest", type=Path, default=DEFAULT_CAMPAIGN_MANIFEST)
    ap.add_argument("--windows-index", type=Path, default=DEFAULT_WINDOWS_INDEX)
    ap.add_argument("--consolidated-input", type=Path, default=None,
                     help="Validated consolidated Phase-12 artifact; enables building "
                          "scheduler_outcomes. Omit for a static-tables-only build "
                          "(the only mode this prefreeze package ever runs in).")
    ap.add_argument("--matrix-validation-report", type=Path, default=None)
    args = ap.parse_args()

    manifest = build_static_tables(args.out_dir, args.campaign_manifest, args.windows_index)
    print(json.dumps(manifest, indent=2, default=str))

    if args.consolidated_input:
        if not args.matrix_validation_report:
            raise SystemExit(
                "REFUSED: --consolidated-input requires --matrix-validation-report"
            )
        build_result_dependent_tables(
            args.out_dir, args.campaign_manifest,
            args.consolidated_input, args.matrix_validation_report,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
