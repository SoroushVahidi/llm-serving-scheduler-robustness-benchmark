"""Tests for the Phase-12C real `--execute` path
(scripts/ranking_portability/run_phase12_campaign_shard.py). Uses a tiny,
hand-built, synthetic 2-window/1-region/2-policy/2-rep fixture (8 cells)
-- NEVER the real 18,720-cell campaign manifest -- so these tests run in a
fraction of a second and never touch real scientific data or expensive
FAITHFUL_EXTERNAL policies.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "ranking_portability" / "run_phase12_campaign_shard.py"

sys.path.insert(0, str(REPO_ROOT / "src"))

_spec = importlib.util.spec_from_file_location("run_phase12_campaign_shard", SCRIPT_PATH)
runner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(runner)


def _fake_record(rid: int, arrival: float, in_tok: int = 10, out_tok: int = 3) -> dict:
    return {
        "source_dataset": "faketest", "source_version": "v0", "source_record_id": f"r{rid}",
        "derived_record_id": f"d{rid}", "source_license": "test", "source_url": "http://x",
        "conversion_version": "test_v1",
        "arrival_time_s": arrival, "input_tokens": in_tok, "output_tokens": out_tok,
    }


def _fake_window(window_id: str, n: int = 6) -> dict:
    records = [_fake_record(i, float(i)) for i in range(n)]
    return {"window_id": window_id, "records": records}


@pytest.fixture()
def fake_full_windows(tmp_path, monkeypatch) -> Path:
    payload = {
        "content_sha256": "TEST_HASH_NOT_REAL",
        "windows": [_fake_window("fakesrc_w00"), _fake_window("fakesrc_w01")],
    }
    p = tmp_path / "fake_full_windows.json"
    p.write_text(json.dumps(payload))
    monkeypatch.setattr(runner, "EXPECTED_PHASE10_WINDOW_HASH", "TEST_HASH_NOT_REAL")
    return p


def _fake_campaign_and_shard(tmp_path, n_windows=2, policies=("fifo", "edf"), region="KNEE", reps=(0, 1)):
    freeze_sha = "fakefreezesha0000000000000000000000000000000000000000000000"
    window_ids = [f"fakesrc_w0{i}" for i in range(n_windows)]
    window_identities = {wid: "fakehash" for wid in window_ids}
    region_assignment_index = {
        f"fakesrc::{wid}::{region}": {"lambda_ref": 1.0, "selected_load_factor": 1.0, "absolute_load_factor": 1.0}
        for wid in window_ids
    }
    cells = []
    for wid in window_ids:
        for pid in policies:
            for rep in reps:
                cells.append({
                    "cell_id": f"fakesrc::{wid}::{region}::{pid}::rep{rep}",
                    "source_family": "fakesrc", "window_id": wid, "load_region": region,
                    "policy_id": pid, "repetition": rep, "synthesis_seed": 900000,
                    "region_assignment_key": f"fakesrc::{wid}::{region}",
                    "scientific_status": "PILOT_V2_SCIENTIFIC",
                })
    campaign = {
        "campaign_freeze_sha256": freeze_sha,
        "window_identities": window_identities,
        "region_assignment_index": region_assignment_index,
        "cells": cells,
    }
    shard = {
        "shard_id": 0, "cell_ids": [c["cell_id"] for c in cells],
        "cell_count": len(cells), "policy_composition": {},
    }
    shard_plan = {"campaign_manifest_freeze_sha256": freeze_sha, "shard_count": 1, "shards": [shard]}

    manifest_path = tmp_path / "fake_campaign.json"
    shard_plan_path = tmp_path / "fake_shard_plan.json"
    manifest_path.write_text(json.dumps(campaign))
    shard_plan_path.write_text(json.dumps(shard_plan))
    return manifest_path, shard_plan_path, campaign, shard, cells


def test_exact_frozen_cells_executed_all_valid(tmp_path, fake_full_windows, monkeypatch):
    manifest_path, shard_plan_path, campaign, shard, cells = _fake_campaign_and_shard(tmp_path)
    monkeypatch.setattr(runner, "CAMPAIGN_OUTPUT_ROOT", tmp_path / "campaign_results")
    monkeypatch.setattr(runner, "SMOKE_OUTPUT_PATH", tmp_path / "not_a_real_smoke_path.json")

    _, _, shard_loaded, shard_cells = runner._load_shard(manifest_path, shard_plan_path, 0)
    rc = runner._execute(campaign, shard_loaded, shard_cells, fake_full_windows)
    assert rc == 0

    out_path = runner._output_path(campaign, 0)
    with open(out_path) as f:
        checkpoint = json.load(f)
    assert set(checkpoint.keys()) == {c["cell_id"] for c in cells}
    for cid, row in checkpoint.items():
        assert row["success"] is True
        assert row["scientific_status"] == "PILOT_V2_SCIENTIFIC"
        assert runner._is_valid_checkpoint_row(row)


def test_resume_idempotence_skips_already_valid_cells(tmp_path, fake_full_windows, monkeypatch):
    manifest_path, shard_plan_path, campaign, shard, cells = _fake_campaign_and_shard(tmp_path)
    monkeypatch.setattr(runner, "CAMPAIGN_OUTPUT_ROOT", tmp_path / "campaign_results")
    monkeypatch.setattr(runner, "SMOKE_OUTPUT_PATH", tmp_path / "not_a_real_smoke_path.json")

    _, _, shard_loaded, shard_cells = runner._load_shard(manifest_path, shard_plan_path, 0)
    runner._execute(campaign, shard_loaded, shard_cells, fake_full_windows)
    out_path = runner._output_path(campaign, 0)
    first_mtime_content = out_path.read_text()

    # Second run: everything should be skipped (n_computed == 0), file content unchanged.
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc2 = runner._execute(campaign, shard_loaded, shard_cells, fake_full_windows)
    assert rc2 == 0
    assert "computed_this_run=0" in buf.getvalue()
    assert f"skipped_already_valid={len(cells)}" in buf.getvalue()
    assert out_path.read_text() == first_mtime_content


def test_invalid_existing_checkpoint_row_is_not_silently_accepted(tmp_path, fake_full_windows, monkeypatch):
    manifest_path, shard_plan_path, campaign, shard, cells = _fake_campaign_and_shard(tmp_path)
    monkeypatch.setattr(runner, "CAMPAIGN_OUTPUT_ROOT", tmp_path / "campaign_results")
    monkeypatch.setattr(runner, "SMOKE_OUTPUT_PATH", tmp_path / "not_a_real_smoke_path.json")

    _, _, shard_loaded, shard_cells = runner._load_shard(manifest_path, shard_plan_path, 0)
    out_path = runner._output_path(campaign, 0)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    target_cid = cells[0]["cell_id"]
    # A garbage/corrupt pre-existing row for one cell -- must NOT be trusted.
    fake_checkpoint = {target_cid: {"success": True, "cell_id": target_cid}}  # missing required fields
    out_path.write_text(json.dumps(fake_checkpoint))

    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = runner._execute(campaign, shard_loaded, shard_cells, fake_full_windows)
    assert rc == 0
    assert "computed_this_run=8" in buf.getvalue()  # ALL 8 recomputed, including the "invalid-but-present" one

    with open(out_path) as f:
        checkpoint = json.load(f)
    assert runner._is_valid_checkpoint_row(checkpoint[target_cid])
    assert checkpoint[target_cid].get("arrival_normalized_weighted_goodput") is not None


def test_two_repetitions_share_identical_scientific_inputs_and_outputs(tmp_path, fake_full_windows, monkeypatch):
    manifest_path, shard_plan_path, campaign, shard, cells = _fake_campaign_and_shard(tmp_path)
    monkeypatch.setattr(runner, "CAMPAIGN_OUTPUT_ROOT", tmp_path / "campaign_results")
    monkeypatch.setattr(runner, "SMOKE_OUTPUT_PATH", tmp_path / "not_a_real_smoke_path.json")

    _, _, shard_loaded, shard_cells = runner._load_shard(manifest_path, shard_plan_path, 0)
    runner._execute(campaign, shard_loaded, shard_cells, fake_full_windows)
    out_path = runner._output_path(campaign, 0)
    with open(out_path) as f:
        checkpoint = json.load(f)

    for wid in ("fakesrc_w00", "fakesrc_w01"):
        for pid in ("fifo", "edf"):
            r0 = checkpoint[f"fakesrc::{wid}::KNEE::{pid}::rep0"]
            r1 = checkpoint[f"fakesrc::{wid}::KNEE::{pid}::rep1"]
            for field in ("arrival_normalized_weighted_goodput", "completion_fraction", "synthesis_seed", "load_factor"):
                assert r0[field] == r1[field], f"{wid}/{pid}/{field} differs between rep0/rep1"
            assert r0["telemetry"] == r1["telemetry"]


def test_no_cross_shard_execution_shard_isolation(tmp_path, fake_full_windows, monkeypatch):
    manifest_path, shard_plan_path, campaign, shard, cells = _fake_campaign_and_shard(tmp_path)
    monkeypatch.setattr(runner, "CAMPAIGN_OUTPUT_ROOT", tmp_path / "campaign_results")
    monkeypatch.setattr(runner, "SMOKE_OUTPUT_PATH", tmp_path / "not_a_real_smoke_path.json")

    # Build a second, disjoint fake shard (shard_id=1) with different cells.
    shard1_cells = [dict(c, cell_id=c["cell_id"] + "::shard1marker") for c in cells[:2]]
    campaign2 = dict(campaign, cells=campaign["cells"] + shard1_cells)
    shard1 = {"shard_id": 1, "cell_ids": [c["cell_id"] for c in shard1_cells], "cell_count": 2, "policy_composition": {}}

    _, _, shard0_loaded, shard0_cells = runner._load_shard(manifest_path, shard_plan_path, 0)
    runner._execute(campaign2, shard0_loaded, shard0_cells, fake_full_windows)
    shard0_out = runner._output_path(campaign2, 0)
    shard1_out = runner._output_path(campaign2, 1)

    assert shard0_out.exists()
    assert not shard1_out.exists()  # shard 1 was never touched by running shard 0

    runner._execute(campaign2, shard1, shard1_cells, fake_full_windows)
    with open(shard0_out) as f:
        shard0_content = json.load(f)
    with open(shard1_out) as f:
        shard1_content = json.load(f)
    assert set(shard0_content.keys()).isdisjoint(set(shard1_content.keys()))


def test_output_path_never_collides_with_smoke_path(tmp_path):
    manifest_path, shard_plan_path, campaign, shard, cells = _fake_campaign_and_shard(tmp_path)
    out_path = runner._output_path(campaign, 0)
    assert out_path.resolve() != runner.SMOKE_OUTPUT_PATH.resolve()
    assert "campaign_results" in str(out_path)


def test_full_windows_hash_mismatch_stops_execution(tmp_path, monkeypatch):
    manifest_path, shard_plan_path, campaign, shard, cells = _fake_campaign_and_shard(tmp_path)
    monkeypatch.setattr(runner, "CAMPAIGN_OUTPUT_ROOT", tmp_path / "campaign_results")
    bad_windows_path = tmp_path / "bad_windows.json"
    bad_windows_path.write_text(json.dumps({"content_sha256": "WRONG", "windows": []}))
    # EXPECTED_PHASE10_WINDOW_HASH still the real production value here.
    _, _, shard_loaded, shard_cells = runner._load_shard(manifest_path, shard_plan_path, 0)
    with pytest.raises(ValueError, match="hash mismatch"):
        runner._execute(campaign, shard_loaded, shard_cells, bad_windows_path)


def test_dry_run_still_never_executes(tmp_path):
    manifest_path, shard_plan_path, campaign, shard, cells = _fake_campaign_and_shard(tmp_path)
    _, _, shard_loaded, shard_cells = runner._load_shard(manifest_path, shard_plan_path, 0)
    rc = runner._dry_run(campaign, shard_loaded, shard_cells)
    assert rc == 0
    out_path = runner._output_path(campaign, 0)
    assert not out_path.exists()  # dry-run creates the parent dir only, never the file
