"""File-level, result-blind tests for the Phase-12D repair pipeline.

Uses tiny fabricated shard files in pytest temporary directories only.  It
never resolves or opens the production campaign result namespace.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts/ranking_portability/enrich_phase12_campaign_provenance.py"

sys.path.insert(0, str(REPO_ROOT / "src"))
_spec = importlib.util.spec_from_file_location("phase12d_enrich", SCRIPT)
repair = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(repair)

from robustbench.ranking_portability.phase12_provenance import (  # noqa: E402
    enrich_row_provenance,
    expected_phase12_provenance,
    masked_non_provenance_hash,
)


def _fake_campaign() -> dict:
    return {
        "phase10_window_hash": "a" * 64,
        "phase11_raw_fifo_hash": "b" * 64,
        "phase11_region_assignment_hash": "c" * 64,
        "execution_file_hashes": {"src/robustbench/policies/registry.py": "d" * 64},
    }


def _raw_row(cell_id: str, rep: int) -> dict:
    return {
        "schema_version": "ranking_portability_cell_result_v1",
        "cell_id": cell_id,
        "source_family": "fake",
        "window_id": "fake_w00",
        "load_region": "KNEE",
        "load_factor": 1.0,
        "policy_id": "fifo",
        "repetition": rep,
        "synthesis_seed": 900000,
        "arrival_normalized_weighted_goodput": 1.0,
        "completion_fraction": 1.0,
        "weighted_completion_fraction": 1.0,
        "slo_violation_rate": 0.0,
        "weighted_goodput": 1.0,
        "mean_latency": 1.0,
        "p95_latency": 1.0,
        "mean_ttft": float("nan"),
        "p95_ttft": float("nan"),
        "request_throughput": 1.0,
        "token_throughput": 1.0,
        "telemetry_schema_version": "ranking_portability_telemetry_v1",
        "telemetry": {
            "schema_version": "ranking_portability_telemetry_v1",
            "queue_depth_mean": 0.0,
            "queue_depth_max": 0,
            "batch_saturation_mean": 0.0,
            "batch_saturation_max": 0.0,
            "prefill_decode_contention_fraction": 0.0,
            "kv_occupancy_mean": 1.01,
            "kv_occupancy_max": 1.02,
            "admission_control_activations": 0,
            "preemption_or_reorder_events": 0,
            "token_budget_saturation_fraction": 0.0,
            "n_steps": 2,
        },
        "repo_sha": "e" * 40,
        "window_manifest_sha256": "",
        "calibration_manifest_sha256": "",
        "policy_registry_hash": "",
        "simulator_config_hash": "",
        "synthesis_version": "",
        "environment": {},
        "success": True,
        "error_category": None,
        "error_detail": None,
        "scientific_status": "PILOT_V2_SCIENTIFIC",
    }


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(payload, f, sort_keys=True, separators=(",", ":"), allow_nan=True)
        f.write("\n")


def test_raw_shard_ledger_is_deterministic_and_detects_later_drift(tmp_path, monkeypatch):
    monkeypatch.setattr(repair, "EXPECTED_CELL_COUNT", 2)
    raw_dir = tmp_path / "raw"
    ids = ["fake::fake_w00::KNEE::fifo::rep0", "fake::fake_w00::KNEE::fifo::rep1"]
    _write(raw_dir / "shard_000.json", {ids[0]: _raw_row(ids[0], 0)})
    _write(raw_dir / "shard_001.json", {ids[1]: _raw_row(ids[1], 1)})
    shard_plan = {
        "shards": [
            {"shard_id": 0, "cell_ids": [ids[0]]},
            {"shard_id": 1, "cell_ids": [ids[1]]},
        ]
    }
    ledger1 = repair._build_raw_ledger(raw_dir, {}, shard_plan)
    ledger2 = repair._build_raw_ledger(raw_dir, {}, shard_plan)
    assert ledger1 == ledger2

    ledger_path = tmp_path / "ledger.json"
    repair._atomic_json(ledger_path, ledger1)
    repair._verify_existing_raw_ledger(ledger2, ledger_path)

    # Any byte-level change to a frozen raw shard changes its SHA and must fail
    # the pre-existing ledger comparison, even if its JSON remains parseable.
    with open(raw_dir / "shard_001.json", "a") as f:
        f.write(" \n")
    drifted = repair._build_raw_ledger(raw_dir, {}, shard_plan)
    with pytest.raises(ValueError, match="raw shard ledger mismatch"):
        repair._verify_existing_raw_ledger(drifted, ledger_path)


def test_atomic_json_and_repaired_shard_hash_are_byte_deterministic(tmp_path):
    payload = {
        "cell": _raw_row("fake::fake_w00::KNEE::fifo::rep0", 0),
        "meta": {"z": 3, "a": 1},
    }
    p1 = tmp_path / "a.json"
    p2 = tmp_path / "b.json"
    repair._atomic_json(p1, payload)
    repair._atomic_json(p2, payload)
    assert p1.read_bytes() == p2.read_bytes()
    assert repair._sha256_file(p1) == repair._sha256_file(p2)


def test_enriched_round_trip_preserves_scientific_content_hash():
    raw = _raw_row("fake::fake_w00::KNEE::fifo::rep0", 0)
    enriched = enrich_row_provenance(raw, expected_phase12_provenance(_fake_campaign()))
    raw_loaded = json.loads(json.dumps(raw, allow_nan=True))
    enriched_loaded = json.loads(json.dumps(enriched, allow_nan=True))
    assert masked_non_provenance_hash(raw_loaded) == masked_non_provenance_hash(enriched_loaded)


def test_consolidated_content_hash_is_deterministic_for_frozen_order():
    rows = [
        _raw_row("fake::fake_w00::KNEE::fifo::rep0", 0),
        _raw_row("fake::fake_w00::KNEE::fifo::rep1", 1),
    ]
    first = repair._canonical_sha256(rows)
    second = repair._canonical_sha256(json.loads(json.dumps(rows, allow_nan=True)))
    assert first == second
    # The consolidation contract is explicitly order-sensitive because real
    # output is serialized in the frozen campaign-manifest cell order.
    assert first != repair._canonical_sha256(list(reversed(rows)))
