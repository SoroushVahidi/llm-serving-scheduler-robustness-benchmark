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
VALIDATOR_SCRIPT = REPO_ROOT / "scripts/ranking_portability/validate_phase12_completed_campaign.py"

sys.path.insert(0, str(REPO_ROOT / "src"))
_spec = importlib.util.spec_from_file_location("phase12d_enrich", SCRIPT)
repair = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(repair)
_validator_spec = importlib.util.spec_from_file_location("phase12d_completed_validator", VALIDATOR_SCRIPT)
completed_validator = importlib.util.module_from_spec(_validator_spec)
_validator_spec.loader.exec_module(completed_validator)

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


def _phase11_prelaunch_doc(*, aggregate: str | None = None, branch_sha: str | None = None) -> str:
    return f"""# Phase-11 prelaunch freeze

## Frozen identity

- branch SHA: `{branch_sha or "f67c65f2f0b6cef661701e75c14f0a7e6868da4d"}`
- Phase-10 window hash: `0d1aa06ccbee352207327ea369ae75f12e91c0cda006c813a41b381effd29eef`
- compact index hash: `d78ec1087fedae02174ca093a9860c70468be336ccb1d7e6de756c81ba331e53`
- aggregate prelaunch-freeze SHA-256: `{aggregate or completed_validator.EXPECTED["phase11_prelaunch_hash"]}`
- calibration implementation hash: `030ea1760ecc4797ab7a1bab48f8a7af3f59ddba54905d571ece6ef5cb1c8804`
- build script hash: `45e4d7c2d7228ac5f7f421a99f711735f8de0affd3fb97c97da0138a9b19a39c`
- calibration plan hash: `01e403daed3ad0fc2ea92bfd042457198d47740c7ea6bc51edc953268bfd1593`
- candidate factor grid hash: `217e99b5b7ab3e25ca2d89eb29adc997c15a7d5684f05bb339ce301255ae2cd0`
- six-region definition hash: `139be6d2ad6db9bbea8a642ec420ff29228f74b5ab2105fdd520acbbae73f533`
- FIFO policy implementation hash: `431171492d5174caa1358cf2adf76bf699ffb76f252a602ee9ec5ce69ef61381`
- simulator implementation/config hash: `a4fa693aa24c76e87bf0fc023ec88086f727dd926d89b586648c75c182ed1b5e`
- validator/schema hash: `dfb4b7815047852c5bf8d626daed1073380a844158ca54c76d030e47ae28e2b3`
"""


def _patch_phase11_history(monkeypatch, historical_doc: str, *, commit_exists: bool = True) -> None:
    monkeypatch.setattr(completed_validator, "_git_commit_exists", lambda commit: commit_exists)
    monkeypatch.setattr(
        completed_validator,
        "_git_file_bytes",
        lambda commit, relpath: historical_doc.encode("utf-8"),
    )


def test_phase11_prelaunch_identity_is_aggregate_not_markdown_file_hash(tmp_path, monkeypatch):
    doc = _phase11_prelaunch_doc() + "\n<!-- representation-only byte change -->\n"
    path = tmp_path / "RANKING_PORTABILITY_PHASE11_PRELAUNCH_FREEZE.md"
    path.write_text(doc)
    _patch_phase11_history(monkeypatch, doc)

    problems: list[str] = []
    info = completed_validator._verify_phase11_prelaunch_contract(
        path,
        {"phase11_prelaunch_hash": completed_validator.EXPECTED["phase11_prelaunch_hash"]},
        problems,
        cross_bindings=(),
    )

    assert problems == []
    assert info["phase11_prelaunch_contract_identity"] == completed_validator.EXPECTED["phase11_prelaunch_hash"]
    assert info["phase11_prelaunch_document_file_sha256"] != completed_validator.EXPECTED["phase11_prelaunch_hash"]
    assert info["PHASE11_PRELAUNCH_IDENTITY_IS_AGGREGATE_CONTRACT_HASH"] is True


def test_phase11_prelaunch_wrong_embedded_aggregate_identity_fails(tmp_path, monkeypatch):
    doc = _phase11_prelaunch_doc(aggregate="f" * 64)
    path = tmp_path / "RANKING_PORTABILITY_PHASE11_PRELAUNCH_FREEZE.md"
    path.write_text(doc)
    _patch_phase11_history(monkeypatch, doc)

    problems: list[str] = []
    completed_validator._verify_phase11_prelaunch_contract(
        path,
        {"phase11_prelaunch_hash": completed_validator.EXPECTED["phase11_prelaunch_hash"]},
        problems,
        cross_bindings=(),
    )

    assert any("aggregate identity mismatch" in p for p in problems)


def test_phase11_prelaunch_wrong_finalization_commit_document_fails(tmp_path, monkeypatch):
    current_doc = _phase11_prelaunch_doc()
    historical_doc = current_doc + "\n<!-- wrong historical representation -->\n"
    path = tmp_path / "RANKING_PORTABILITY_PHASE11_PRELAUNCH_FREEZE.md"
    path.write_text(current_doc)
    _patch_phase11_history(monkeypatch, historical_doc)

    problems: list[str] = []
    completed_validator._verify_phase11_prelaunch_contract(
        path,
        {"phase11_prelaunch_hash": completed_validator.EXPECTED["phase11_prelaunch_hash"]},
        problems,
        cross_bindings=(),
    )

    assert any("differs from finalization commit" in p for p in problems)


def test_phase11_prelaunch_conflicting_campaign_manifest_identity_fails(tmp_path, monkeypatch):
    doc = _phase11_prelaunch_doc()
    path = tmp_path / "RANKING_PORTABILITY_PHASE11_PRELAUNCH_FREEZE.md"
    path.write_text(doc)
    _patch_phase11_history(monkeypatch, doc)

    problems: list[str] = []
    completed_validator._verify_phase11_prelaunch_contract(
        path,
        {"phase11_prelaunch_hash": "0" * 64},
        problems,
        cross_bindings=(),
    )

    assert any("phase12_campaign_manifest" in p for p in problems)


def test_phase11_prelaunch_cross_binding_identity_fails_on_disagreement(tmp_path, monkeypatch):
    doc = _phase11_prelaunch_doc()
    path = tmp_path / "RANKING_PORTABILITY_PHASE11_PRELAUNCH_FREEZE.md"
    path.write_text(doc)
    disagreeing = tmp_path / "disagreeing.md"
    disagreeing.write_text("- Phase-11 prelaunch freeze hash: `" + "1" * 64 + "`\n")
    _patch_phase11_history(monkeypatch, doc)

    problems: list[str] = []
    completed_validator._verify_phase11_prelaunch_contract(
        path,
        {"phase11_prelaunch_hash": completed_validator.EXPECTED["phase11_prelaunch_hash"]},
        problems,
        cross_bindings=(("synthetic_binding", disagreeing, "Phase-11 prelaunch freeze hash"),),
    )

    assert any("synthetic_binding" in p for p in problems)


def test_raw_fifo_and_region_assignment_identities_remain_file_hashes(tmp_path):
    compact_index = tmp_path / "compact.json"
    raw_fifo = tmp_path / "raw_fifo.json"
    region_assignments = tmp_path / "region_assignments.json"
    compact_index.write_text("compact\n")
    raw_fifo.write_text("raw\n")
    region_assignments.write_text("region\n")

    checks = completed_validator._file_artifact_identity_checks(
        compact_index,
        raw_fifo,
        region_assignments,
    )

    assert "phase11_prelaunch_hash" not in checks
    assert checks["phase11_raw_fifo_hash"] == completed_validator._sha256_file(raw_fifo)
    assert checks["phase11_region_assignment_hash"] == completed_validator._sha256_file(region_assignments)
    raw_fifo.write_text("raw changed\n")
    assert checks["phase11_raw_fifo_hash"] != completed_validator._sha256_file(raw_fifo)

