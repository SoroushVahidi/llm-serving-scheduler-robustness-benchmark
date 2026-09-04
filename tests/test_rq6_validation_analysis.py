"""Tests for robustbench.real_llm.rq6_validation_analysis.

Every numeric fixture in this file is SYNTHETIC_FIXTURE_NOT_SCIENTIFIC_
EVIDENCE: fabricated to exercise the analysis code's arithmetic and control
flow, never a real RQ6 measurement. No real calibration or validation output
is read here.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from robustbench.real_llm.rq6_validation_analysis import (
    apply_family_fdr,
    condition_effect,
    reversal_analysis,
    stable_control_analysis,
)

SYNTHETIC_FIXTURE_NOT_SCIENTIFIC_EVIDENCE = True

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_MANIFEST_PATH = REPO_ROOT / "configs/real_vllm/rq6_validation_manifest_v1_20260903.json"


def _rng():
    return np.random.default_rng(1234)


# ---------------------------------------------------------------------------
# condition_effect: bootstrap point/CI/p-value/winner
# ---------------------------------------------------------------------------

def test_condition_effect_clear_positive_effect_excludes_zero():
    # SLAI uniformly beats vLLM by +0.2 ANWG on every one of 40 synthetic windows.
    per_window_diff = {f"w{i:02d}": 0.2 for i in range(40)}
    result = condition_effect(per_window_diff, condition_label="synthetic::x", rng=_rng())
    assert result.point_estimate == pytest.approx(0.2)
    assert result.excludes_zero is True
    assert result.winner == "slai_faithful"
    assert result.ci_lo > 0


def test_condition_effect_clear_negative_effect_excludes_zero():
    per_window_diff = {f"w{i:02d}": -0.15 for i in range(40)}
    result = condition_effect(per_window_diff, condition_label="synthetic::y", rng=_rng())
    assert result.excludes_zero is True
    assert result.winner == "vllm_faithful"
    assert result.ci_hi < 0


def test_condition_effect_balanced_around_zero_does_not_exclude_zero():
    # Deterministic, exactly mean-zero fixture (half +1.0, half -1.0 across
    # 40 windows) so the bootstrap CI is centered on 0 by construction,
    # rather than relying on a specific noisy-random seed that could land
    # significant by chance.
    per_window_diff = {f"w{i:02d}": (1.0 if i % 2 == 0 else -1.0) for i in range(40)}
    result = condition_effect(per_window_diff, condition_label="synthetic::balanced", n_resamples=500, rng=_rng())
    assert result.point_estimate == pytest.approx(0.0)
    assert result.excludes_zero is False
    assert result.winner is None


def test_condition_effect_n_windows_recorded():
    per_window_diff = {f"w{i:02d}": 0.1 for i in range(17)}
    result = condition_effect(per_window_diff, condition_label="synthetic::n", rng=_rng())
    assert result.n_windows == 17


# ---------------------------------------------------------------------------
# reversal_analysis: sign flip detection + simulator-agreement (only
# computed when the caller supplies simulator-selected winners)
# ---------------------------------------------------------------------------

def test_reversal_analysis_detects_sign_flip_and_agreement():
    per_window_diff_x = {f"w{i:02d}": 0.3 for i in range(40)}   # slai wins condition x
    per_window_diff_y = {f"w{i:02d}": -0.3 for i in range(40)}  # vllm wins condition y
    result = reversal_analysis(
        per_window_diff_x, per_window_diff_y,
        condition_x_label="azure_llm_2024::HIGH_PRESSURE", condition_y_label="burstgpt::HIGH_PRESSURE",
        simulator_selected_x_winner="slai_faithful", simulator_selected_y_winner="vllm_faithful",
        rng=_rng(),
    )
    assert result.sign_flip_observed is True
    assert result.both_conditions_supported is True
    assert result.agrees_with_simulator_selected_direction is True


def test_reversal_analysis_disagreement_with_simulator_direction():
    per_window_diff_x = {f"w{i:02d}": 0.3 for i in range(40)}
    per_window_diff_y = {f"w{i:02d}": -0.3 for i in range(40)}
    result = reversal_analysis(
        per_window_diff_x, per_window_diff_y,
        condition_x_label="x", condition_y_label="y",
        simulator_selected_x_winner="vllm_faithful",  # deliberately swapped
        simulator_selected_y_winner="slai_faithful",
        rng=_rng(),
    )
    assert result.sign_flip_observed is True
    assert result.agrees_with_simulator_selected_direction is False


def test_reversal_analysis_no_sign_flip():
    per_window_diff_x = {f"w{i:02d}": 0.3 for i in range(40)}
    per_window_diff_y = {f"w{i:02d}": 0.25 for i in range(40)}
    result = reversal_analysis(
        per_window_diff_x, per_window_diff_y,
        condition_x_label="x", condition_y_label="y",
        simulator_selected_x_winner="slai_faithful", simulator_selected_y_winner="slai_faithful",
        rng=_rng(),
    )
    assert result.sign_flip_observed is False


def test_reversal_analysis_agreement_undefined_when_not_both_supported():
    per_window_diff_x = {f"w{i:02d}": 0.3 for i in range(40)}
    # Deterministic mean-zero fixture for condition y (CI must include 0).
    per_window_diff_y = {f"w{i:02d}": (1.0 if i % 2 == 0 else -1.0) for i in range(40)}
    result = reversal_analysis(
        per_window_diff_x, per_window_diff_y,
        condition_x_label="x", condition_y_label="y",
        simulator_selected_x_winner="slai_faithful", simulator_selected_y_winner="vllm_faithful",
        rng=_rng(),
    )
    assert result.both_conditions_supported is False
    assert result.agrees_with_simulator_selected_direction is None


# ---------------------------------------------------------------------------
# stable_control_analysis: same-sign check
# ---------------------------------------------------------------------------

def test_stable_control_same_sign_both_conditions():
    x = {f"w{i:02d}": 0.1 for i in range(40)}
    y = {f"w{i:02d}": 0.05 for i in range(40)}
    result = stable_control_analysis(x, y, condition_x_label="x", condition_y_label="y", rng=_rng())
    assert result.same_sign_both_conditions is True


def test_stable_control_different_sign_flags_instability():
    x = {f"w{i:02d}": 0.1 for i in range(40)}
    y = {f"w{i:02d}": -0.05 for i in range(40)}
    result = stable_control_analysis(x, y, condition_x_label="x", condition_y_label="y", rng=_rng())
    assert result.same_sign_both_conditions is False


# ---------------------------------------------------------------------------
# apply_family_fdr: reused benjamini_hochberg over the frozen 4-test family
# ---------------------------------------------------------------------------

def test_apply_family_fdr_rejects_small_p_values():
    p_values = [0.001, 0.002, 0.5, 0.9]
    rejected = apply_family_fdr(p_values, q=0.05)
    assert len(rejected) == 4
    assert rejected[0] is True
    assert rejected[3] is False


def test_apply_family_fdr_default_q_is_0_05():
    p_values = [0.5, 0.6, 0.7, 0.8]
    rejected = apply_family_fdr(p_values)
    assert all(r is False for r in rejected)


# ---------------------------------------------------------------------------
# Simulator-direction wiring: `agrees_with_simulator_selected_direction`
# must be mechanically derivable from the manifest's recovered, hash-
# verified FROZEN_SIMULATOR_EVIDENCE (Phase-12 pairwise-reversal record,
# not a real-vLLM result) plus a (synthetic, labeled) real-side effect --
# never manually entered. This test reads the actual recovered labels from
# the validation manifest (not a hardcoded duplicate), so a future edit to
# the manifest's winner fields is caught here if the wiring silently
# breaks.
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not VALIDATION_MANIFEST_PATH.exists(), reason="validation manifest not present")
def test_simulator_winner_labels_are_resolved_not_unresolved_in_manifest():
    with open(VALIDATION_MANIFEST_PATH) as f:
        manifest = json.load(f)
    reversal = manifest["case_selection"]["reversal_case"]
    assert reversal["simulator_selected_winner_x"] == "slai_faithful"
    assert reversal["simulator_selected_winner_y"] == "vllm_faithful"
    assert reversal["simulator_winner_recovery"]["status"] == "RECOVERED_AND_HASH_VERIFIED"
    # FROZEN_SIMULATOR_EVIDENCE, not a real-vLLM result: sign convention
    # sanity check on the recovered diff values themselves.
    assert reversal["simulator_diff_x"] > 0  # slai_faithful wins condition_x
    assert reversal["simulator_diff_y"] < 0  # vllm_faithful wins condition_y


@pytest.mark.skipif(not VALIDATION_MANIFEST_PATH.exists(), reason="validation manifest not present")
def test_reversal_analysis_wired_from_manifest_recovered_winners_agreement_case():
    """FROZEN_SIMULATOR_EVIDENCE for the winner labels (read from the
    manifest, real Phase-12 data); the per-window real-side diffs below are
    SYNTHETIC_FIXTURE_NOT_SCIENTIFIC_EVIDENCE (no real-vLLM RQ6 result
    exists yet) -- this only checks that agreement is computed mechanically
    from whatever winners the manifest names, not hand-entered."""
    with open(VALIDATION_MANIFEST_PATH) as f:
        manifest = json.load(f)
    reversal = manifest["case_selection"]["reversal_case"]

    # Synthetic real-side data that happens to agree with the (real,
    # recovered) simulator direction.
    per_window_diff_x = {f"w{i:02d}": 0.3 for i in range(40)}
    per_window_diff_y = {f"w{i:02d}": -0.3 for i in range(40)}
    result = reversal_analysis(
        per_window_diff_x, per_window_diff_y,
        condition_x_label=reversal["condition_x"], condition_y_label=reversal["condition_y"],
        simulator_selected_x_winner=reversal["simulator_selected_winner_x"],
        simulator_selected_y_winner=reversal["simulator_selected_winner_y"],
        rng=_rng(),
    )
    assert result.agrees_with_simulator_selected_direction is True

    # Same synthetic real-side data, but simulator winners swapped (as if
    # the recovery had gone the other way) -- agreement must flip to False,
    # proving this is mechanically derived, not a constant.
    result_swapped = reversal_analysis(
        per_window_diff_x, per_window_diff_y,
        condition_x_label=reversal["condition_x"], condition_y_label=reversal["condition_y"],
        simulator_selected_x_winner=reversal["simulator_selected_winner_y"],
        simulator_selected_y_winner=reversal["simulator_selected_winner_x"],
        rng=_rng(),
    )
    assert result_swapped.agrees_with_simulator_selected_direction is False
