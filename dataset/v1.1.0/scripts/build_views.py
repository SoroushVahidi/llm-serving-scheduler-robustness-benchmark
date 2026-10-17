#!/usr/bin/env python3
"""Build losslessly checkable Parquet views of the frozen LSSP v1.1.0 inputs.

This script runs no simulation and no statistical analysis. It never edits the
seven canonical scientific files. Run validate_release.py after building.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
SCI = ROOT / "scientific"
OUT = ROOT / "data" / "tables"
EXPECTED_MATRIX_SHA = "73adf7d97f06985ec8f8e1c2f794fd43178433eb198e1c00705e817f4bde9c26"

POLICIES = [
    ("fifo", "REPOSITORY_NATIVE_CLASSICAL", "PRIMARY"),
    ("edf", "REPOSITORY_NATIVE_CLASSICAL", "PRIMARY"),
    ("least_laxity_first", "REPOSITORY_NATIVE_CLASSICAL", "PRIMARY"),
    ("estimated_service_time_first", "REPOSITORY_NATIVE_CLASSICAL", "PRIMARY"),
    ("weighted_fair_share", "REPOSITORY_NATIVE_CLASSICAL", "PRIMARY"),
    ("kv_constrained_online", "SIMULATOR_PROXY", "PRIMARY"),
    ("vllm_faithful", "FAITHFUL_EXTERNAL", "PRIMARY"),
    ("vllm_chunked_prefill_faithful", "FAITHFUL_EXTERNAL", "PRIMARY"),
    ("sarathi_faithful", "FAITHFUL_EXTERNAL", "PRIMARY"),
    ("slai_faithful", "FAITHFUL_EXTERNAL", "PRIMARY"),
    ("admission_control", "REPOSITORY_NATIVE_CLASSICAL", "PRIMARY"),
    ("vllm_style_token_budget", "STYLE_APPROXIMATION", "ROBUSTNESS_ONLY"),
    ("scorpio_style_slo_guard", "STYLE_APPROXIMATION", "ROBUSTNESS_ONLY"),
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name: str, rows: list[dict]) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.parquet"
    columns = sorted({key for row in rows for key in row})
    table = pa.Table.from_pylist([{key: row.get(key) for key in columns} for row in rows])
    for column in ("error_category", "error_detail"):
        if column in table.column_names and pa.types.is_null(table.schema.field(column).type):
            index = table.column_names.index(column)
            table = table.set_column(index, column, pa.array([None] * len(rows), type=pa.string()))
    pq.write_table(table, path, compression="zstd", row_group_size=2048, write_page_index=True)
    return {"path": str(path.relative_to(ROOT)), "rows": len(rows), "sha256": digest(path)}


def main() -> None:
    matrix_path = SCI / "campaign" / "consolidated.json"
    assert digest(matrix_path) == EXPECTED_MATRIX_SHA, "frozen matrix hash mismatch"
    cells = json.loads(matrix_path.read_text())["cells"]
    assert len(cells) == 18720
    outputs: dict[str, dict] = {}

    # Preserve each original top-level field; encode the always-empty JSON
    # environment object as text because Parquet cannot write struct<>.
    outcome_rows = []
    for cell in cells:
        row = dict(cell)
        row["environment_json"] = json.dumps(row.pop("environment"), sort_keys=True, separators=(",", ":"))
        outcome_rows.append(row)
    outputs["scheduler_outcomes"] = write("scheduler_outcomes", outcome_rows)

    groups: dict[tuple[str, str, str, str], dict[int, dict]] = defaultdict(dict)
    for cell in cells:
        key = (cell["source_family"], cell["window_id"], cell["load_region"], cell["policy_id"])
        assert cell["repetition"] not in groups[key]
        groups[key][cell["repetition"]] = cell
    configs = []
    for key, reps in sorted(groups.items()):
        assert set(reps) == {0, 1}
        left, right = reps[0], reps[1]
        scientific_left = {k: v for k, v in left.items() if k not in ("cell_id", "repetition")}
        scientific_right = {k: v for k, v in right.items() if k not in ("cell_id", "repetition")}
        assert scientific_left == scientific_right, f"verification passes differ: {key}"
        configs.append({
            "source_family": key[0], "window_id": key[1], "load_region": key[2], "policy_id": key[3],
            "load_factor": left["load_factor"], "synthesis_seed": left["synthesis_seed"],
            "cell_id_rep0": left["cell_id"], "cell_id_rep1": right["cell_id"],
            "deterministic_passes_equal": True,
        })
    assert len(configs) == 9360
    outputs["unique_configurations"] = write("unique_configurations", configs)

    windows = json.loads((ROOT / "manifests" / "ranking_portability_pilot_v2_windows_index.json").read_text())["windows"]
    assert len(windows) == 120
    # Window descriptors contain source-specific optional keys. JSON text
    # preserves omitted-versus-null distinctions that Arrow structs erase.
    window_view = []
    for window in windows:
        row = dict(window)
        row["descriptor_json"] = json.dumps(row.pop("descriptor"), sort_keys=True, separators=(",", ":"))
        window_view.append(row)
    outputs["workload_windows"] = write("workload_windows", window_view)

    assignments = json.loads((ROOT / "manifests" / "ranking_portability_phase11_region_assignments.json").read_text())["assignments"]
    assert len(assignments) == 720
    assignments_view = [{**row, "source_family": row["source"], "load_region": row["region"]} for row in assignments]
    outputs["load_region_assignments"] = write("load_region_assignments", assignments_view)

    frozen = json.loads((ROOT / "manifests" / "ranking_portability_phase12_campaign_freeze.json").read_text())
    assert set(frozen["campaign_policies"]) == {p[0] for p in POLICIES}
    panel = [{"policy_id": pid, "fidelity_class": fidelity, "panel_status": status} for pid, fidelity, status in POLICIES]
    outputs["policy_registry"] = write("policy_registry", panel)

    analysis_map = {
        "pairwise_reversals": "records", "ranking_correlations": "comparisons",
        "sample_complexity": "per_source_metric", "telemetry_explanation": "records",
        "temporal_robustness": "records", "topk_overlap": "comparisons",
    }
    for name, key in analysis_map.items():
        data = json.loads((SCI / "analysis" / f"{name}.json").read_text())
        source = data[key]
        if isinstance(source, dict):
            rows = []
            for metric, values in source.items():
                for value in values:
                    row = dict(value)
                    row["_source_keys"] = sorted(value)
                    row.setdefault("metric", metric)
                    assert row["metric"] == metric
                    rows.append(row)
        else:
            rows = [{**value, "_source_keys": sorted(value)} for value in source]
        outputs[name] = write(name, rows)

    manifest = {
        "release_version": "1.1.0",
        "source_matrix_sha256": EXPECTED_MATRIX_SHA,
        "pyarrow_version": pa.__version__,
        "views": outputs,
        "notes": "Convenience tables only; original scientific JSON files remain authoritative. All rows are checked independently by validate_release.py.",
    }
    path = ROOT / "validation" / "view_build_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: v["rows"] for k, v in outputs.items()}, indent=2))


if __name__ == "__main__":
    main()
