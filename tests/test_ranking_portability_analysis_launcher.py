"""Fail-closed launcher-gate tests for
`scripts/ranking_portability/run_phase12_analysis.py`, plus one
end-to-end happy path at full frozen MATRIX SHAPE (18,720 fabricated
cells) but toy statistical scale (bootstrap/draw counts overridden --
the CLI never overrides them; only tests do).

Every byte here is synthetic: fabricated manifests, fabricated compact
index, fabricated cell rows (see ranking_portability_analysis_fixtures).
No real campaign artifact, hash, or outcome is touched; the launcher's
pinned real identities are monkeypatched to synthetic stand-ins so the
gate LOGIC is tested, never the real campaign contents.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from robustbench.ranking_portability.analysis.contract import PRIMARY_METRIC
from robustbench.ranking_portability.analysis.matrix_validator import (
    IMMUTABLE_HASH_MANIFEST_KEYS,
)
from robustbench.ranking_portability.phase12_campaign import (
    CAMPAIGN_POLICIES,
    CAMPAIGN_REGIONS,
    CAMPAIGN_SOURCES,
    WINDOWS_PER_SOURCE,
    generate_campaign_cell_specs,
)
from ranking_portability_analysis_fixtures import make_cell_row

REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER_PATH = (
    REPO_ROOT / "scripts" / "ranking_portability" / "run_phase12_analysis.py"
)

_spec = importlib.util.spec_from_file_location(
    "run_phase12_analysis_launcher", LAUNCHER_PATH
)
launcher = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(launcher)

SYNTH_FREEZE = "synthetic-campaign-freeze-" + "0" * 40
SYNTH_FULL_MATRIX = "synthetic-full-matrix-" + "1" * 40
FIXED_HASHES = {k: f"fixture-{k}" for k in IMMUTABLE_HASH_MANIFEST_KEYS}


def _current_head_sha() -> str:
    return (
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT)
        .decode()
        .strip()
    )


def _build_synthetic_world(tmp_path: Path):
    """Fabricates a complete, internally consistent synthetic input world:
    18,720-cell consolidated artifact, campaign manifest, compact window
    index (120 windows with fabricated timestamps + descriptors), and an
    admission manifest whose identities match. Returns a dict of paths
    and the artifact file's SHA-256."""
    window_ids_by_source = {
        s: [f"{s}_w{i:03d}" for i in range(WINDOWS_PER_SOURCE)] for s in CAMPAIGN_SOURCES
    }
    specs = generate_campaign_cell_specs(window_ids_by_source)
    policy_value = {p: 1.0 + 0.05 * i for i, p in enumerate(CAMPAIGN_POLICIES)}
    cells = {}
    for spec in specs:
        cells[spec.cell_id] = make_cell_row(
            source_family=spec.source_family, window_id=spec.window_id,
            load_region=spec.load_region, policy_id=spec.policy_id,
            repetition=spec.repetition, synthesis_seed=7, load_factor=1.0,
            anwg=policy_value[spec.policy_id],
        )
    consolidated = {"campaign_freeze_sha256": SYNTH_FREEZE, "cells": cells}
    artifact_path = tmp_path / "consolidated.json"
    artifact_path.write_text(json.dumps(consolidated, sort_keys=True))
    artifact_sha = hashlib.sha256(artifact_path.read_bytes()).hexdigest()

    assignment_index = {}
    for s in CAMPAIGN_SOURCES:
        for w in window_ids_by_source[s]:
            for r in CAMPAIGN_REGIONS:
                assignment_index[f"{s}::{w}::{r}"] = {
                    "lambda_ref": 1.0, "selected_load_factor": 1.0,
                    "absolute_load_factor": 1.0,
                }
    campaign_manifest = {
        "campaign_freeze_sha256": SYNTH_FREEZE,
        "region_assignment_index": assignment_index,
        **FIXED_HASHES,
    }
    manifest_path = tmp_path / "campaign_manifest.json"
    manifest_path.write_text(json.dumps(campaign_manifest, sort_keys=True))

    compact_index = {
        "windows": [
            {
                "window_id": f"{s}_w{i:03d}",
                "source_family": s,
                "arrival_time_s_min": float(i + 1),
                "descriptor": {
                    "burstiness_b": 0.1 * ((i % 5) + 1),
                    "prompt_tokens_cv": 0.2,
                    "output_tokens_cv": 0.3,
                    "long_context_fraction": 0.1,
                    "concurrency_proxy": 1.0,
                },
            }
            for s in CAMPAIGN_SOURCES for i in range(WINDOWS_PER_SOURCE)
        ]
    }
    compact_path = tmp_path / "compact_index.json"
    compact_path.write_text(json.dumps(compact_index, sort_keys=True))

    admission = {
        "manifest_kind": "ranking_portability_phase12_analysis_input",
        "PHASE12_COMPLETED_CAMPAIGN_VALID": True,
        "PHASE12_ANALYSIS_INPUT_ADMITTED": True,
        "COMPARATIVE_PILOT_V2_RESULTS": "NONE",
        "campaign_freeze_sha256": SYNTH_FREEZE,
        "full_matrix_hash": SYNTH_FULL_MATRIX,
        "consolidated_artifact_sha256": artifact_sha,
        "cell_count": 18720,
    }
    admission_path = tmp_path / "admission.json"
    admission_path.write_text(json.dumps(admission, sort_keys=True))

    return {
        "admission_manifest_path": admission_path,
        "consolidated_artifact_path": artifact_path,
        "campaign_manifest_path": manifest_path,
        "compact_window_index_path": compact_path,
        "artifact_sha": artifact_sha,
        "admission": admission,
    }


@pytest.fixture()
def synthetic_world(tmp_path, monkeypatch):
    world = _build_synthetic_world(tmp_path)
    monkeypatch.setattr(launcher, "EXPECTED_CAMPAIGN_FREEZE_SHA256", SYNTH_FREEZE)
    monkeypatch.setattr(launcher, "EXPECTED_FULL_MATRIX_HASH", SYNTH_FULL_MATRIX)
    monkeypatch.setattr(
        launcher, "EXPECTED_CONSOLIDATED_ARTIFACT_SHA256", world["artifact_sha"]
    )
    return world


def _gate_kwargs(world, tmp_path, **overrides):
    out = tmp_path / "artifacts" / "analysis" / "phase12"
    kwargs = {
        "admission_manifest_path": world["admission_manifest_path"],
        "consolidated_artifact_path": world["consolidated_artifact_path"],
        "campaign_manifest_path": world["campaign_manifest_path"],
        "compact_window_index_path": world["compact_window_index_path"],
        "output_dir": out,
        "expected_analysis_git_sha": _current_head_sha(),
        "allow_live": False,
    }
    kwargs.update(overrides)
    return kwargs


# --- Gate 2: admission flags ---

def test_refuses_when_campaign_not_declared_valid(synthetic_world, tmp_path):
    admission = dict(synthetic_world["admission"])
    admission["PHASE12_COMPLETED_CAMPAIGN_VALID"] = False
    synthetic_world["admission_manifest_path"].write_text(json.dumps(admission))
    with pytest.raises(launcher.GateRefusal, match="COMPLETED_CAMPAIGN_VALID"):
        launcher.verify_launch_gates(**_gate_kwargs(synthetic_world, tmp_path))


def test_refuses_when_input_not_admitted(synthetic_world, tmp_path):
    admission = dict(synthetic_world["admission"])
    admission["PHASE12_ANALYSIS_INPUT_ADMITTED"] = False
    synthetic_world["admission_manifest_path"].write_text(json.dumps(admission))
    with pytest.raises(launcher.GateRefusal, match="ANALYSIS_INPUT_ADMITTED"):
        launcher.verify_launch_gates(**_gate_kwargs(synthetic_world, tmp_path))


# --- Gate 3: frozen campaign identity / corrupted admission hashes ---

def test_refuses_on_corrupted_admission_campaign_hash(synthetic_world, tmp_path):
    admission = dict(synthetic_world["admission"])
    admission["campaign_freeze_sha256"] = "corrupted-" + SYNTH_FREEZE
    synthetic_world["admission_manifest_path"].write_text(json.dumps(admission))
    with pytest.raises(launcher.GateRefusal, match="campaign_freeze_sha256 mismatch"):
        launcher.verify_launch_gates(**_gate_kwargs(synthetic_world, tmp_path))


def test_refuses_on_corrupted_admission_full_matrix_hash(synthetic_world, tmp_path):
    admission = dict(synthetic_world["admission"])
    admission["full_matrix_hash"] = "corrupted"
    synthetic_world["admission_manifest_path"].write_text(json.dumps(admission))
    with pytest.raises(launcher.GateRefusal, match="full_matrix_hash mismatch"):
        launcher.verify_launch_gates(**_gate_kwargs(synthetic_world, tmp_path))


def test_refuses_on_corrupted_admission_consolidated_hash(synthetic_world, tmp_path):
    admission = dict(synthetic_world["admission"])
    admission["consolidated_artifact_sha256"] = "corrupted"
    synthetic_world["admission_manifest_path"].write_text(json.dumps(admission))
    with pytest.raises(launcher.GateRefusal, match="consolidated_artifact_sha256 mismatch"):
        launcher.verify_launch_gates(**_gate_kwargs(synthetic_world, tmp_path))


# --- Gate 4: admitted-artifact file identity ---

def test_refuses_on_tampered_consolidated_artifact(synthetic_world, tmp_path):
    artifact = synthetic_world["consolidated_artifact_path"]
    payload = json.loads(artifact.read_text())
    payload["cells"] = {}  # tamper after admission
    artifact.write_text(json.dumps(payload, sort_keys=True))
    with pytest.raises(launcher.GateRefusal, match="file bytes SHA-256 mismatch"):
        launcher.verify_launch_gates(**_gate_kwargs(synthetic_world, tmp_path))


# --- Gate 5: analysis-code identity ---

def test_refuses_on_analysis_git_sha_mismatch(synthetic_world, tmp_path):
    with pytest.raises(launcher.GateRefusal, match="analysis-code git SHA mismatch"):
        launcher.verify_launch_gates(
            **_gate_kwargs(
                synthetic_world, tmp_path,
                expected_analysis_git_sha="0" * 40,
            )
        )


# --- Gate 6: output namespace ---

def test_refuses_output_dir_outside_analysis_namespace(synthetic_world, tmp_path):
    with pytest.raises(launcher.GateRefusal, match="canonical analysis namespace"):
        launcher.verify_launch_gates(
            **_gate_kwargs(synthetic_world, tmp_path, output_dir=tmp_path / "elsewhere")
        )


def test_refuses_nonempty_output_dir(synthetic_world, tmp_path):
    out = tmp_path / "artifacts" / "analysis" / "phase12"
    out.mkdir(parents=True)
    (out / "stale.json").write_text("{}")
    with pytest.raises(launcher.GateRefusal, match="non-empty"):
        launcher.verify_launch_gates(**_gate_kwargs(synthetic_world, tmp_path))


def test_refuses_output_dir_overlapping_input(synthetic_world, tmp_path):
    artifact = synthetic_world["consolidated_artifact_path"]
    out = artifact.parent / "artifacts" / "analysis" / "phase12"
    # Move the artifact under the output dir to force overlap.
    nested = out / "input.json"
    out.mkdir(parents=True)
    artifact.replace(nested)
    world = dict(synthetic_world, consolidated_artifact_path=nested)
    with pytest.raises(launcher.GateRefusal, match="overlaps the admitted input"):
        launcher.verify_launch_gates(**_gate_kwargs(world, tmp_path))


def test_blindness_guard_blocks_live_input_without_allow_live(synthetic_world, tmp_path):
    from robustbench.ranking_portability.analysis.result_blindness import (
        LiveCampaignPathBlocked,
    )
    live = tmp_path / "artifacts" / "campaign_results" / "x" / "consolidated.json"
    with pytest.raises(LiveCampaignPathBlocked):
        launcher.verify_launch_gates(
            **_gate_kwargs(synthetic_world, tmp_path, consolidated_artifact_path=live)
        )


def test_gates_pass_on_consistent_synthetic_world(synthetic_world, tmp_path):
    admission = launcher.verify_launch_gates(**_gate_kwargs(synthetic_world, tmp_path))
    assert admission["PHASE12_ANALYSIS_INPUT_ADMITTED"] is True


# --- Happy path: end-to-end over the full fabricated matrix, toy stats scale ---

def test_happy_path_writes_six_stamped_artifacts_and_never_touches_input(
    synthetic_world, tmp_path
):
    world = synthetic_world
    out = tmp_path / "artifacts" / "analysis" / "phase12"
    launcher.verify_launch_gates(**_gate_kwargs(world, tmp_path))

    with open(world["consolidated_artifact_path"]) as f:
        consolidated = json.load(f)
    with open(world["campaign_manifest_path"]) as f:
        campaign_manifest = json.load(f)
    with open(world["compact_window_index_path"]) as f:
        compact_index = json.load(f)

    from robustbench.ranking_portability.phase12_campaign import (
        load_campaign_window_ids,
    )
    window_ids_by_source = load_campaign_window_ids(compact_index)
    report = launcher.validate_completed_campaign(
        manifest=campaign_manifest,
        consolidated_rows=consolidated["cells"],
        window_ids_by_source=window_ids_by_source,
        expected_immutable_hashes=FIXED_HASHES,
    )
    assert report.valid, report.problems

    input_manifest = launcher.build_analysis_input_manifest(
        campaign_freeze_sha256=SYNTH_FREEZE,
        consolidated_rows=consolidated["cells"],
        matrix_validation_problems=report.problems,
        repo_root=REPO_ROOT,
    )

    window_meta = {
        w["window_id"]: {
            "source_family": w["source_family"],
            "arrival_time_s_min": w["arrival_time_s_min"],
            "descriptor": w["descriptor"],
        }
        for w in compact_index["windows"]
    }
    for source, wids in window_ids_by_source.items():
        for i, wid in enumerate(wids):
            window_meta[wid]["relative_order"] = i

    input_bytes_before = world["consolidated_artifact_path"].read_bytes()
    written = launcher.run_analysis(
        rows=list(consolidated["cells"].values()),
        window_meta=window_meta,
        analysis_input_manifest=input_manifest,
        output_dir=out,
        azure_boundary_epoch_seconds=20.5,
        n_resamples=8,
        draws_per_n=4,
        metrics=(PRIMARY_METRIC,),
    )
    assert world["consolidated_artifact_path"].read_bytes() == input_bytes_before

    assert set(written) == {
        "ranking_correlations", "topk_overlap", "pairwise_reversals",
        "sample_complexity", "temporal_robustness", "telemetry_explanation",
    }
    for path in written.values():
        payload = json.loads(Path(path).read_text())
        assert payload["campaign_freeze_sha256"] == SYNTH_FREEZE
        assert payload["consolidated_result_sha256"] == (
            input_manifest.consolidated_result_sha256
        )
        assert payload["analysis_code_git_sha"] == _current_head_sha()
        assert payload["analysis_contract_version"] == (
            input_manifest.analysis_contract_version
        )

    # Synthetic sanity: distinct fabricated per-policy values give a
    # perfectly portable ranking (tau = 1) in every comparison -- this
    # asserts the plumbing, not any real outcome.
    ranking = json.loads(Path(written["ranking_correlations"]).read_text())
    for rec in ranking["comparisons"][PRIMARY_METRIC]:
        assert rec["kendall_tau"] == pytest.approx(1.0)
    reversals = json.loads(Path(written["pairwise_reversals"]).read_text())
    classes = {
        r["classification"] for r in reversals["records"][PRIMARY_METRIC]
    }
    assert classes == {"STABLE_NO_SIGN_CHANGE"}
