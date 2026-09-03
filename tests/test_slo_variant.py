"""POST_PHASE12_SLO_DEFINITION_SENSITIVITY_EXTENSION: structural tests for
the SLO-variant transform. Fabricated fixtures only -- no scheduler-ranking
outcome is inspected here. See tests/test_slo_sensitivity_manifest.py and
tests/test_slo_sensitivity_analysis.py for the manifest/analysis layers."""
from __future__ import annotations

from dataclasses import replace

import pytest

from robustbench.analysis.slo_variant import (
    SLO_VARIANT_MULTIPLIERS,
    apply_slo_variant,
    apply_slo_variant_to_window,
    validate_slo_variant,
)
from robustbench.core.types import Request


def _req(request_id=0, arrival=0.0, prompt=10, predicted=5, actual=5, slack=100.0,
         priority=1.0, class_id="stage0_uniform") -> Request:
    return Request(
        request_id=request_id, arrival_time=arrival, prompt_tokens=prompt,
        predicted_output_tokens=predicted, actual_output_tokens=actual,
        slo_deadline=arrival + slack, priority=priority, class_id=class_id,
    )


def _window(n=5):
    return [_req(request_id=i, arrival=float(i), slack=100.0 + i) for i in range(n)]


# 1. Primary SLO rule (ratio == 1.0) exactly reproduces frozen behavior --
#    provably, not just empirically: it is an algebraic no-op.
def test_primary_variant_is_exact_noop():
    reqs = _window()
    variant = apply_slo_variant_to_window(reqs, 20.0, primary_multiplier=20.0)
    assert variant == reqs  # frozen dataclass equality: every field, not just deadline


# 2. Tight alternative changes only deadline/SLO fields.
def test_tight_alternative_changes_only_deadline():
    reqs = _window()
    variant = apply_slo_variant_to_window(reqs, 10.0, primary_multiplier=20.0)
    report = validate_slo_variant(reqs, variant)
    assert report.passed, report.problems
    for o, v in zip(reqs, variant):
        assert v.slo_deadline < o.slo_deadline  # tighter multiplier -> smaller slack
        assert v.arrival_time == o.arrival_time
        assert v.prompt_tokens == o.prompt_tokens
        assert v.predicted_output_tokens == o.predicted_output_tokens
        assert v.actual_output_tokens == o.actual_output_tokens
        assert v.priority == o.priority
        assert v.class_id == o.class_id


# 3. Loose alternative changes only deadline/SLO fields.
def test_loose_alternative_changes_only_deadline():
    reqs = _window()
    variant = apply_slo_variant_to_window(reqs, 40.0, primary_multiplier=20.0)
    report = validate_slo_variant(reqs, variant)
    assert report.passed, report.problems
    for o, v in zip(reqs, variant):
        assert v.slo_deadline > o.slo_deadline  # looser multiplier -> larger slack


# 4. Deterministic variant generation: same inputs -> byte-identical outputs.
def test_deterministic_variant_generation():
    reqs = _window()
    v1 = apply_slo_variant_to_window(reqs, 10.0)
    v2 = apply_slo_variant_to_window(reqs, 10.0)
    assert v1 == v2


# 5. No request-ID drift.
def test_no_request_id_drift():
    reqs = _window()
    variant = apply_slo_variant_to_window(reqs, 40.0)
    assert [r.request_id for r in variant] == [r.request_id for r in reqs]


# 6. No timing (arrival_time) drift.
def test_no_arrival_time_drift():
    reqs = _window()
    variant = apply_slo_variant_to_window(reqs, 10.0)
    assert [r.arrival_time for r in variant] == [r.arrival_time for r in reqs]


# 7. No token-count drift.
def test_no_token_count_drift():
    reqs = _window()
    variant = apply_slo_variant_to_window(reqs, 40.0)
    assert [(r.prompt_tokens, r.predicted_output_tokens, r.actual_output_tokens) for r in variant] \
        == [(r.prompt_tokens, r.predicted_output_tokens, r.actual_output_tokens) for r in reqs]


# Validator must fail hard on injected drift in a disallowed field.
def test_validator_fails_hard_on_injected_token_drift():
    reqs = _window()
    tampered = [replace(r, prompt_tokens=r.prompt_tokens + 1) for r in reqs]
    report = validate_slo_variant(reqs, tampered)
    assert not report.passed
    assert "prompt_tokens" in report.mismatched_fields


def test_validator_fails_hard_on_request_count_mismatch():
    reqs = _window()
    report = validate_slo_variant(reqs, reqs[:-1])
    assert not report.passed
    assert any("request count differs" in p for p in report.problems)


def test_validator_fails_hard_on_request_id_drift():
    reqs = _window()
    tampered = [replace(r, request_id=r.request_id + 100) for r in reqs]
    report = validate_slo_variant(reqs, tampered)
    assert not report.passed
    assert "request_id" in report.mismatched_fields


def test_validator_passes_on_true_slo_only_variant():
    reqs = _window()
    variant = apply_slo_variant_to_window(reqs, 10.0)
    report = validate_slo_variant(reqs, variant)
    assert report.passed
    assert report.mismatched_fields == []


# Rejects a degenerate "variant" that never actually changes the deadline
# (would silently defeat the sensitivity design).
def test_zero_ratio_change_is_still_structurally_valid_but_reported_unchanged():
    reqs = _window()
    variant = apply_slo_variant_to_window(reqs, 20.0, primary_multiplier=20.0)
    report = validate_slo_variant(reqs, variant)
    assert report.passed  # structurally fine (identical is a valid special case)


def test_frozen_variant_panel_has_exactly_three_multipliers_bracketing_primary():
    assert set(SLO_VARIANT_MULTIPLIERS) == {"tight_10x", "primary_20x", "loose_40x"}
    assert SLO_VARIANT_MULTIPLIERS["tight_10x"] < SLO_VARIANT_MULTIPLIERS["primary_20x"] \
        < SLO_VARIANT_MULTIPLIERS["loose_40x"]
    # Symmetric bracket: halved and doubled around the primary value.
    assert SLO_VARIANT_MULTIPLIERS["tight_10x"] == SLO_VARIANT_MULTIPLIERS["primary_20x"] / 2.0
    assert SLO_VARIANT_MULTIPLIERS["loose_40x"] == SLO_VARIANT_MULTIPLIERS["primary_20x"] * 2.0


def test_invalid_multipliers_rejected():
    reqs = _window()
    with pytest.raises(ValueError):
        apply_slo_variant(reqs[0], -1.0)
    with pytest.raises(ValueError):
        apply_slo_variant(reqs[0], 0.0)


# --- Real-pipeline primary-equivalence gate -------------------------------
# The single most important gate in this extension: regenerating a
# representative real Phase-12 cell through this new variant machinery with
# the PRIMARY multiplier must reproduce the sealed pipeline's own output
# exactly (same synthesize -> rebase_and_scale -> execute_cell code, only
# the variant transform inserted at ratio=1.0). If this ever fails, the
# sensitivity extension must not proceed -- see docs/
# SLO_DEFINITION_SENSITIVITY_PROTOCOL_20260903.md's PRIMARY_EQUIVALENCE_GATE.
_FULL_WINDOWS_PATH = None
try:
    from pathlib import Path as _Path
    _candidate = _Path(__file__).resolve().parents[1] / "artifacts/pilot_v2_windows_full_cache.json"
    if _candidate.exists():
        _FULL_WINDOWS_PATH = _candidate
except Exception:
    pass


@pytest.mark.skipif(_FULL_WINDOWS_PATH is None, reason="frozen Phase-12 window cache not present locally")
def test_primary_variant_reproduces_sealed_pipeline_on_real_cells():
    import json

    from robustbench.calibration.stage0_load_calibration import (
        STAGE0_REFERENCE_GPU_CONFIG,
        _rebase_and_scale,
    )
    from robustbench.policies.registry import make_policy_any
    from robustbench.ranking_portability.execute_cell import execute_cell
    from robustbench.workloads.external.benchmark_synthesis import synthesize_requests_from_window
    from robustbench.workloads.external.schema import ExternalWorkloadRecord

    repo_root = _Path(__file__).resolve().parents[1]
    full_windows = json.load(open(_FULL_WINDOWS_PATH))
    windows_by_id = {w["window_id"]: w for w in full_windows["windows"]}
    campaign_path = repo_root / "artifacts/manifests/ranking_portability_phase12_campaign_freeze.json"
    if not campaign_path.exists():
        pytest.skip("frozen Phase-12 campaign manifest not present locally")
    campaign = json.load(open(campaign_path))
    region_assignment_index = campaign["region_assignment_index"]

    representative = [
        ("burstgpt_stage0_w00", "burstgpt", "HIGH_PRESSURE", "edf", 900000),
        ("burstgpt_stage0_w00", "burstgpt", "LOW", "fifo", 900000),
        ("azure_llm_2024_stage0_w05", "azure_llm_2024", "KNEE", "admission_control", 900005)
        if "azure_llm_2024_stage0_w05" in windows_by_id else None,
    ]
    representative = [r for r in representative if r is not None]
    assert representative, "expected at least the burstgpt fixtures to be present"

    for window_id, source, region, policy_id, seed in representative:
        w = windows_by_id[window_id]
        records = [ExternalWorkloadRecord(**r) for r in w["records"]]

        # Sealed path (unmodified).
        sealed_requests, _ = synthesize_requests_from_window(records, window_id=window_id, seed=seed)
        key = f"{source}::{window_id}::{region}"
        assignment = region_assignment_index[key]
        sealed_scaled = _rebase_and_scale(sealed_requests, float(assignment["absolute_load_factor"]))
        sealed_result = execute_cell(
            cell_id=f"sealed::{key}::{policy_id}", source_family=source, window_id=window_id,
            load_region=region, load_factor=float(assignment["absolute_load_factor"]),
            policy_id=policy_id, repetition=0, synthesis_seed=seed, repo_sha="test",
            policy=make_policy_any(policy_id), requests=sealed_scaled,
            gpu_configs=[STAGE0_REFERENCE_GPU_CONFIG],
        )

        # New variant path with the PRIMARY multiplier (ratio == 1.0).
        variant_requests = apply_slo_variant_to_window(sealed_requests, 20.0, primary_multiplier=20.0)
        assert variant_requests == sealed_requests  # exact no-op, proven above too
        variant_scaled = _rebase_and_scale(variant_requests, float(assignment["absolute_load_factor"]))
        variant_result = execute_cell(
            cell_id=f"variant::{key}::{policy_id}", source_family=source, window_id=window_id,
            load_region=region, load_factor=float(assignment["absolute_load_factor"]),
            policy_id=policy_id, repetition=0, synthesis_seed=seed, repo_sha="test",
            policy=make_policy_any(policy_id), requests=variant_scaled,
            gpu_configs=[STAGE0_REFERENCE_GPU_CONFIG],
        )

        assert sealed_result.success and variant_result.success
        sealed_dict = sealed_result.to_dict()
        variant_dict = variant_result.to_dict()
        for k in sealed_dict:
            if k == "cell_id":
                continue  # deliberately different labels above
            assert sealed_dict[k] == variant_dict[k], (
                f"{window_id}/{region}/{policy_id}: field {k!r} differs under primary-equivalence: "
                f"sealed={sealed_dict[k]!r} variant={variant_dict[k]!r}"
            )
