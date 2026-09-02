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

from robustbench.ranking_portability.analysis.contract import (
    AZURE_2024_CALENDAR_BOUNDARY_EPOCH_SECONDS,
    PRIMARY_METRIC,
)
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
        "azure_boundary_epoch_seconds": AZURE_2024_CALENDAR_BOUNDARY_EPOCH_SECONDS,
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


# --- Gate 7: frozen Azure boundary ---

def test_refuses_on_non_frozen_azure_boundary(synthetic_world, tmp_path):
    with pytest.raises(launcher.GateRefusal, match="azure boundary epoch"):
        launcher.verify_launch_gates(
            **_gate_kwargs(
                synthetic_world, tmp_path,
                azure_boundary_epoch_seconds=1715731200.0 + 3600.0,
            )
        )


def test_frozen_azure_boundary_is_collection_window_midpoint():
    """The frozen boundary is the exact midpoint of the canonical
    2024-05-10..2024-05-19 Azure-2024 collection window
    (docs/EVIDENCE_INDEPENDENCE_PLAN.md): [2024-05-10T00:00Z,
    2024-05-20T00:00Z) -> 2024-05-15T00:00:00Z = 1715731200.0."""
    import datetime
    assert AZURE_2024_CALENDAR_BOUNDARY_EPOCH_SECONDS == 1715731200.0
    as_utc = datetime.datetime.fromtimestamp(
        AZURE_2024_CALENDAR_BOUNDARY_EPOCH_SECONDS, datetime.timezone.utc
    )
    assert as_utc == datetime.datetime(2024, 5, 15, 0, 0, 0, tzinfo=datetime.timezone.utc)


def test_azure_boundary_semantics_before_vs_at_or_after():
    from robustbench.ranking_portability.analysis.temporal_analysis import (
        split_azure_calendar,
    )
    b = AZURE_2024_CALENDAR_BOUNDARY_EPOCH_SECONDS
    groups = split_azure_calendar(
        {"w_before": b - 1.0, "w_at": b, "w_after": b + 1.0},
        boundary_epoch_seconds=b,
    )
    assert groups["BEFORE_BOUNDARY"] == ["w_before"]
    assert sorted(groups["AT_OR_AFTER_BOUNDARY"]) == ["w_after", "w_at"]


# --- Source-specific temporal split isolation (audit section B) ---

def _fabricated_window_meta():
    meta = {}
    for source in CAMPAIGN_SOURCES:
        for i in range(WINDOWS_PER_SOURCE):
            meta[f"{source}_w{i:03d}"] = {
                "source_family": source,
                "arrival_time_s_min": float(i + 1),
                "relative_order": i,
                "descriptor": {},
            }
    return meta


def test_burstgpt_groups_isolated_from_other_sources_timestamps():
    meta = _fabricated_window_meta()
    base = launcher._build_temporal_split_specs(meta, 20.5)
    base_tercile = dict(base["burstgpt"][0][1])
    base_bisect = dict(base["burstgpt"][1][1])
    # Wildly perturb every non-BurstGPT timestamp and order value.
    for w, m in meta.items():
        if m["source_family"] != "burstgpt":
            m["arrival_time_s_min"] = 9e9 + hash(w) % 1000
            m["relative_order"] = 1000 - meta[w]["relative_order"]
    perturbed = launcher._build_temporal_split_specs(meta, 20.5)
    assert dict(perturbed["burstgpt"][0][1]) == base_tercile
    assert dict(perturbed["burstgpt"][1][1]) == base_bisect


def test_azure_groups_isolated_from_other_sources_timestamps():
    meta = _fabricated_window_meta()
    base = launcher._build_temporal_split_specs(meta, 20.5)
    base_cal = dict(base["azure_llm_2024"][0][1])
    for w, m in meta.items():
        if m["source_family"] != "azure_llm_2024":
            m["arrival_time_s_min"] = -1e9 - (hash(w) % 1000)
            m["relative_order"] = 1000 - meta[w]["relative_order"]
    perturbed = launcher._build_temporal_split_specs(meta, 20.5)
    assert dict(perturbed["azure_llm_2024"][0][1]) == base_cal


def test_bailian_groups_isolated_from_other_sources_order_metadata():
    meta = _fabricated_window_meta()
    base = launcher._build_temporal_split_specs(meta, 20.5)
    base_rel = dict(base["bailian_qwen"][0][1])
    for w, m in meta.items():
        if m["source_family"] != "bailian_qwen":
            m["relative_order"] = 5000 + (hash(w) % 500)
            m["arrival_time_s_min"] = 3e9 + (hash(w) % 1000)
    perturbed = launcher._build_temporal_split_specs(meta, 20.5)
    assert dict(perturbed["bailian_qwen"][0][1]) == base_rel


def test_temporal_groups_preserve_40_window_source_membership():
    meta = _fabricated_window_meta()
    specs = launcher._build_temporal_split_specs(meta, 20.5)
    for source, splits in specs.items():
        for _name, groups, _sens in splits:
            members = sorted(w for ws in groups.values() for w in ws)
            assert len(members) == WINDOWS_PER_SOURCE
            assert all(w.startswith(f"{source}_w") for w in members)


# --- Reversal bootstrap p-value + BH family semantics (audit section E) ---

def test_bootstrap_sign_pvalue_extremes():
    import numpy as np
    from robustbench.ranking_portability.analysis.reversal_analysis import (
        _bootstrap_diff_ci,
    )
    all_pos = {f"w{i}": {"a": 2.0, "b": 1.0} for i in range(10)}
    lo, hi, p = _bootstrap_diff_ci(
        all_pos, "a", "b", n_resamples=500, ci_level=0.95,
        rng=np.random.default_rng(0),
    )
    assert lo > 0 and hi > 0
    assert p <= 0.05  # a constant positive difference is maximally significant

    symmetric = {
        "w0": {"a": 2.0, "b": 1.0}, "w1": {"a": 1.0, "b": 2.0},
        "w2": {"a": 2.0, "b": 1.0}, "w3": {"a": 1.0, "b": 2.0},
    }
    lo2, hi2, p2 = _bootstrap_diff_ci(
        symmetric, "a", "b", n_resamples=500, ci_level=0.95,
        rng=np.random.default_rng(0),
    )
    assert lo2 <= 0 <= hi2
    assert p2 > 0.5  # zero-mean difference is maximally insignificant


def test_reversal_bh_family_membership_and_iut_pvalue():
    """One clearly reversing pair (10x margins both directions) and one
    stable pair: only the pair reaching the statistical-support stage is a
    family member; its IUT p-value max(p_x, p_y) is tiny and BH-rejected;
    the stable pair carries no reversal hypothesis."""
    import numpy as np
    from robustbench.ranking_portability.analysis.omnibus import apply_fdr_family
    from robustbench.ranking_portability.analysis.reversal_analysis import (
        ReversalClass,
        classify_pairwise_reversal,
    )
    rows_x, rows_y = [], []
    for i in range(10):
        # a beats b 10:1 in source X
        rows_x.append(make_cell_row(source_family="burstgpt", window_id=f"x{i}",
                                    policy_id="fifo", repetition=0, anwg=10.0))
        rows_x.append(make_cell_row(source_family="burstgpt", window_id=f"x{i}",
                                    policy_id="edf", repetition=0, anwg=1.0))
        # b beats a 10:1 in source Y (clear supported reversal)
        rows_y.append(make_cell_row(source_family="azure_llm_2024", window_id=f"y{i}",
                                    policy_id="fifo", repetition=0, anwg=1.0))
        rows_y.append(make_cell_row(source_family="azure_llm_2024", window_id=f"y{i}",
                                    policy_id="edf", repetition=0, anwg=10.0))
        # a beats c in both (stable)
        rows_x.append(make_cell_row(source_family="burstgpt", window_id=f"x{i}",
                                    policy_id="least_laxity_first", repetition=0, anwg=0.5))
        rows_y.append(make_cell_row(source_family="azure_llm_2024", window_id=f"y{i}",
                                    policy_id="least_laxity_first", repetition=0, anwg=0.5))
    rng = np.random.default_rng(0)
    rev = classify_pairwise_reversal(rows_x, rows_y, policy_a="fifo", policy_b="edf",
                                     metric=PRIMARY_METRIC, n_resamples=200, rng=rng)
    assert rev.classification == ReversalClass.SUPPORTED_PRACTICAL_REVERSAL
    assert rev.p_x is not None and rev.p_y is not None
    p_pair = max(rev.p_x, rev.p_y)
    stable = classify_pairwise_reversal(rows_x, rows_y, policy_a="fifo",
                                        policy_b="least_laxity_first",
                                        metric=PRIMARY_METRIC, n_resamples=200, rng=rng)
    assert stable.classification == ReversalClass.STABLE_NO_SIGN_CHANGE
    assert stable.p_x is None and stable.p_y is None
    # Family = tests that reached the support stage: only the reversing pair.
    fdr = apply_fdr_family("anwg::KNEE", [p_pair])
    assert fdr.rejected == [True]


# --- Telemetry reversal-site rule semantics (audit section F) ---

def _site_rows(x_vals, y_vals, *, xa=10.0, xb=1.0, ya=1.0, yb=10.0):
    rows = []
    for i, (av, bv) in enumerate(x_vals):
        rows.append(make_cell_row(source_family="burstgpt", window_id=f"x{i}",
                                  policy_id="fifo", repetition=0, anwg=av))
        rows.append(make_cell_row(source_family="burstgpt", window_id=f"x{i}",
                                  policy_id="edf", repetition=0, anwg=bv))
    for i, (av, bv) in enumerate(y_vals):
        rows.append(make_cell_row(source_family="azure_llm_2024", window_id=f"y{i}",
                                  policy_id="fifo", repetition=0, anwg=av))
        rows.append(make_cell_row(source_family="azure_llm_2024", window_id=f"y{i}",
                                  policy_id="edf", repetition=0, anwg=bv))
    return rows


def test_reversal_site_rule_flags_margin_passing_sign_flips():
    rows = _site_rows([(10.0, 1.0)] * 5, [(1.0, 10.0)] * 5)
    ind = launcher._window_reversal_sites(
        rows, region="KNEE", source_x="burstgpt", source_y="azure_llm_2024",
        policy_a="fifo", policy_b="edf",
    )
    assert len(ind) == 10 and all(ind.values())  # every window is a site


def test_reversal_site_rule_excludes_microscopic_margins():
    # Window-level margins ~1% (<= 10% frozen gate): excluded, never sites.
    rows = _site_rows([(1.0, 0.99)] * 5, [(0.99, 1.0)] * 5)
    ind = launcher._window_reversal_sites(
        rows, region="KNEE", source_x="burstgpt", source_y="azure_llm_2024",
        policy_a="fifo", policy_b="edf",
    )
    assert ind == {}


def test_reversal_site_rule_excludes_zero_loser_unestimable():
    rows = _site_rows([(10.0, 0.0)] * 5, [(0.0, 10.0)] * 5)
    ind = launcher._window_reversal_sites(
        rows, region="KNEE", source_x="burstgpt", source_y="azure_llm_2024",
        policy_a="fifo", policy_b="edf",
    )
    assert ind == {}


def test_reversal_site_rule_no_flip_means_not_sites():
    rows = _site_rows([(10.0, 1.0)] * 5, [(10.0, 1.0)] * 5)  # same direction
    ind = launcher._window_reversal_sites(
        rows, region="KNEE", source_x="burstgpt", source_y="azure_llm_2024",
        policy_a="fifo", policy_b="edf",
    )
    assert len(ind) == 10 and not any(ind.values())


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
    # Every reversal record carries the frozen BH-family fields; with no
    # sign change anywhere, no reversal hypothesis exists, so nothing is
    # FDR-rejected or supported.
    for r in reversals["records"][PRIMARY_METRIC]:
        assert r["bh_fdr_p_pair_iut"] is None
        assert r["bh_fdr_rejected_within_metric_loadregion_family"] is None
        assert r["supported_after_fdr"] is False
        assert r["fdr_family"].startswith(f"{PRIMARY_METRIC}::")

    # Friedman scope (frozen: "across sources, block = window, per metric
    # x load region"): every omnibus record pools all 3x40 = 120 windows.
    for rec in ranking["omnibus_friedman"]:
        assert rec["n_blocks"] == 3 * WINDOWS_PER_SOURCE

    # Sample-complexity scope (frozen: per source x metric; ladder top
    # n=40 = the per-source window count): exactly one experiment per
    # source x metric, and at n=40 (all of a source's windows) recovery
    # is trivially exact.
    sc = json.loads(Path(written["sample_complexity"]).read_text())
    assert len(sc["per_source_metric"]) == len(CAMPAIGN_SOURCES)
    for rec in sc["per_source_metric"]:
        n40 = [p for p in rec["points"] if p["n"] == WINDOWS_PER_SOURCE]
        assert n40 and n40[0]["p_exact_recovery"] == 1.0
