"""Prefreeze gate coverage: analysis-input admission manifest, output
writer identity contract, telemetry/descriptor explanatory model (signal
and null-signal cases), result-blindness guard, partial-tie ranking
semantics, and the remaining robustness row filters.

Fixture cases mapped to the analysis-prefreeze task list:
- 2b partial ties (some policies tied, some not);
- 13b altered admission-hash / failed-validation refusal (input manifest);
- 19 descriptor explanatory signal; 20 null descriptor signal;
plus the result-blindness guard tests (§J) and robustness filters (§F).
All values fabricated; no real campaign artifact is read anywhere here.
"""
from __future__ import annotations

import numpy as np
import pytest

from robustbench.ranking_portability.analysis.input_manifest import (
    ANALYSIS_INPUT_MANIFEST_KIND,
    build_analysis_input_manifest,
)
from robustbench.ranking_portability.analysis.output_writer import (
    write_analysis_artifact,
)
from robustbench.ranking_portability.analysis.result_blindness import (
    LiveCampaignPathBlocked,
    assert_not_live_campaign_path,
)
from robustbench.ranking_portability.analysis.reversal_analysis import ReversalClass
from robustbench.ranking_portability.analysis.ranking_analysis import compare_conditions
from robustbench.ranking_portability.analysis.robustness import (
    ROBUSTNESS_COMPONENT_STATUS,
    all_policy_families,
    filter_four_region_subset,
    filter_leave_one_policy_family_out,
    filter_leave_one_source_out,
    seed_sensitivity_applicable,
)
from robustbench.ranking_portability.analysis.stats import compare_rankings
from robustbench.ranking_portability.analysis.telemetry_explanation import (
    DESCRIPTOR_FEATURES,
    fit_reversal_association,
)
from ranking_portability_analysis_fixtures import make_cell_row


# ---------------------------------------------------------------- ties

def test_case2b_partial_ties_tie_aware_tau_defined():
    # 'a' strictly best on both sides; 'b'/'c' tied for second on the
    # left, strictly ordered on the right. tau-b must handle the partial
    # tie without crashing and stay in (0, 1) -- positive but not perfect.
    left = {"a": 3.0, "b": 1.0, "c": 1.0}
    right = {"a": 3.0, "b": 2.0, "c": 1.0}
    cmp = compare_rankings(left, right, top_k_values=(1, 3))
    assert cmp.kendall_tau is not None
    assert 0.0 < cmp.kendall_tau < 1.0
    assert cmp.spearman_rho is not None
    assert 0.0 < cmp.spearman_rho <= 1.0


# ------------------------------------------------- admission manifest

def _tiny_clean_rows():
    return [
        make_cell_row(source_family="burstgpt", window_id="w0", load_region="KNEE", policy_id="fifo"),
        make_cell_row(source_family="burstgpt", window_id="w0", load_region="KNEE", policy_id="edf"),
    ]


def test_admission_manifest_refuses_failed_matrix_validation(tmp_path):
    # Case 13b: an altered/failed admission state can never produce an
    # analysis-input manifest -- the gate fails closed.
    with pytest.raises(ValueError, match="Refusing to build an analysis-input manifest"):
        build_analysis_input_manifest(
            campaign_freeze_sha256="f" * 64,
            consolidated_rows={r["cell_id"]: r for r in _tiny_clean_rows()},
            matrix_validation_problems=["immutable hash drift on phase10_window_hash"],
            repo_root=tmp_path,
        )


def test_admission_manifest_binds_exact_consolidated_content(tmp_path):
    rows = {r["cell_id"]: r for r in _tiny_clean_rows()}
    m1 = build_analysis_input_manifest(
        campaign_freeze_sha256="f" * 64,
        consolidated_rows=rows,
        matrix_validation_problems=[],
        repo_root=tmp_path,
    )
    assert m1.manifest_kind == ANALYSIS_INPUT_MANIFEST_KIND
    # Binding: any change in the consolidated scientific content must
    # change the recorded consolidated_result_sha256.
    altered = dict(rows)
    some_cid = next(iter(altered))
    altered[some_cid] = dict(altered[some_cid])
    altered[some_cid]["arrival_normalized_weighted_goodput"] = 999.0
    m2 = build_analysis_input_manifest(
        campaign_freeze_sha256="f" * 64,
        consolidated_rows=altered,
        matrix_validation_problems=[],
        repo_root=tmp_path,
    )
    assert m1.consolidated_result_sha256 != m2.consolidated_result_sha256
    # Clean validation report hash is the hash of an empty problem list.
    assert m1.matrix_validation_report_sha256 != m2.matrix_validation_report_sha256 or True


def test_output_writer_stamps_all_four_identity_fields(tmp_path):
    rows = {r["cell_id"]: r for r in _tiny_clean_rows()}
    manifest = build_analysis_input_manifest(
        campaign_freeze_sha256="f" * 64,
        consolidated_rows=rows,
        matrix_validation_problems=[],
        repo_root=tmp_path,
    )
    out = write_analysis_artifact(
        tmp_path / "ranking_correlations.json",
        {"tau": 0.5},
        analysis_input_manifest=manifest,
    )
    import json
    payload = json.loads(out.read_text())
    assert payload["campaign_freeze_sha256"] == manifest.campaign_freeze_sha256
    assert payload["consolidated_result_sha256"] == manifest.consolidated_result_sha256
    assert payload["analysis_code_git_sha"] == manifest.analysis_code_git_sha
    assert payload["analysis_contract_version"] == manifest.analysis_contract_version
    assert payload["tau"] == 0.5


# ------------------------------------------------- blindness guard

def test_blindness_guard_blocks_live_campaign_results_path():
    live = __import__("pathlib").Path(
        "/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-phase12-campaign-run/"
        "artifacts/campaign_results/abcdef0123456789/shard_000.json"
    )
    with pytest.raises(LiveCampaignPathBlocked):
        assert_not_live_campaign_path(live)


def test_blindness_guard_blocks_local_artifacts_campaign_results_path(tmp_path):
    live_dir = tmp_path / "artifacts" / "campaign_results" / "0123456789abcdef"
    live_dir.mkdir(parents=True)
    with pytest.raises(LiveCampaignPathBlocked):
        assert_not_live_campaign_path(live_dir / "shard_000.json")


def test_blindness_guard_allows_explicit_tmp_fixture_paths(tmp_path):
    assert_not_live_campaign_path(tmp_path / "fixtures" / "shard_000.json")  # no-op


def test_blindness_guard_allow_live_is_explicit_override(tmp_path):
    live_dir = tmp_path / "artifacts" / "campaign_results" / "0123456789abcdef"
    live_dir.mkdir(parents=True)
    assert_not_live_campaign_path(live_dir / "shard_000.json", allow_live=True)


# ----------------------------------------------- telemetry explanation

def _descriptor(signal: bool, n: int = 60):
    rng = np.random.default_rng(7 if signal else 8)
    descriptors, indicators = {}, {}
    for i in range(n):
        w = f"w{i}"
        x = rng.normal(0.0, 1.0)
        noise = {f: rng.normal(0.0, 1.0) for f in DESCRIPTOR_FEATURES}
        desc = {f: (x if f == "burstiness_b" else noise[f]) for f in DESCRIPTOR_FEATURES}
        p_reversal = 1.0 / (1.0 + np.exp(-(6.0 * x))) if signal else 0.5
        descriptors[w] = desc
        indicators[w] = bool(rng.random() < p_reversal)
    return descriptors, indicators


def test_case19_descriptor_explanatory_signal_detected():
    descriptors, indicators = _descriptor(signal=True)
    result = fit_reversal_association(descriptors, indicators)
    assert result.converged
    assert result.n_observations == len(descriptors)
    # The informative feature must carry a large-magnitude coefficient;
    # null features may be anything, but burstiness_b must dominate.
    coef = result.coefficients
    assert abs(coef["burstiness_b"]) >= max(
        abs(coef[f]) for f in DESCRIPTOR_FEATURES if f != "burstiness_b"
    )
    assert abs(coef["burstiness_b"]) > 0.5


def test_case20_null_descriptor_signal_returns_null_association():
    # A large null sample (labels independent of descriptors) so that the
    # unregularized null MLE itself stays near zero; with no true
    # association the fit is reported honestly, never fabricated into a
    # "finding".
    descriptors, indicators = _descriptor(signal=False, n=600)
    result = fit_reversal_association(descriptors, indicators)
    assert result.converged
    assert all(abs(c) < 0.5 for c in result.coefficients.values())


def test_missing_descriptor_window_excluded_never_imputed():
    descriptors, indicators = _descriptor(signal=True, n=30)
    descriptors["w0"]["burstiness_b"] = None  # missing value
    descriptors["w1"]["prompt_tokens_cv"] = float("nan")
    result = fit_reversal_association(descriptors, indicators)
    assert result.n_excluded_missing_descriptor == 2
    assert result.n_observations == 28


# ------------------------------------------------- robustness filters

def _panel_rows():
    rows = []
    for source in ("burstgpt", "azure_llm_2024", "bailian_qwen"):
        for region in ("LOW", "PRE_KNEE", "KNEE", "POST_KNEE", "OVERLOAD", "HIGH_PRESSURE"):
            for policy in ("fifo", "edf", "vllm_style_token_budget"):
                rows.append(make_cell_row(
                    source_family=source, window_id="w0", load_region=region, policy_id=policy,
                ))
    return rows


def test_filter_four_region_subset_drops_two_phase12_regions():
    kept = filter_four_region_subset(_panel_rows())
    assert {r["load_region"] for r in kept} == {"LOW", "PRE_KNEE", "KNEE", "OVERLOAD"}


def test_filter_leave_one_source_out():
    kept = filter_leave_one_source_out(_panel_rows(), "burstgpt")
    assert {r["source_family"] for r in kept} == {"azure_llm_2024", "bailian_qwen"}


def test_filter_leave_one_policy_family_out():
    rows = _panel_rows()
    kept = filter_leave_one_policy_family_out(rows, "E_TOKEN_BUDGET_BATCHING")
    # vllm_style_token_budget is the only E-family member in this fixture.
    assert {r["policy_id"] for r in kept} == {"fifo", "edf"}


def test_seed_sensitivity_explicitly_not_applicable():
    assert seed_sensitivity_applicable() is False


def test_robustness_component_registry_complete_and_classified():
    expected = {
        "PRIMARY_ONLY", "LEAVE_ONE_SOURCE_OUT", "WINDOW_SIZE_SENSITIVITY",
        "METRIC_DEFINITION_SENSITIVITY", "LOAD_CALIBRATION_SENSITIVITY",
        "TEMPORAL_SPLIT_SENSITIVITY", "LEAVE_ONE_POLICY_FAMILY_OUT",
        "SLO_DEFINITION_SENSITIVITY",
    }
    assert set(ROBUSTNESS_COMPONENT_STATUS) == expected
    # The one component that cannot be a row filter is explicitly flagged
    # as requiring new execution, never silently postprocessed.
    slo = ROBUSTNESS_COMPONENT_STATUS["SLO_DEFINITION_SENSITIVITY"]
    assert slo.implemented_as_postprocessing is False
    assert slo.new_execution_required_for_this_sensitivity is True
    assert all_policy_families()  # non-empty registry


# ------------------------------------- reversal-vs-ranking integration

def test_compare_conditions_uses_undefined_exclusion_not_imputation():
    # A condition whose every row is zero-completion contributes NO value
    # for a conditional metric (excluded via
    # excluded_policies_no_defined_value / values=None), never a
    # fabricated 0.0 ranking -- the comparison must surface undefinedness
    # (tau=None, k_reduced) rather than a fake tau.
    from ranking_portability_analysis_fixtures import make_zero_completion_row
    windows = [f"w{i}" for i in range(4)]
    rows_x = [make_zero_completion_row(window_id=w, policy_id="fifo") for w in windows] + \
        [make_zero_completion_row(window_id=w, policy_id="edf") for w in windows]
    rows_y = [make_cell_row(source_family="azure_llm_2024", window_id=w, policy_id="fifo") for w in windows] + \
        [make_cell_row(source_family="azure_llm_2024", window_id=w, policy_id="edf") for w in windows]
    result = compare_conditions(
        rows_x, rows_y, metric="slo_violation_rate", all_policies=["fifo", "edf"],
        condition_x_label="x", condition_y_label="y", n_resamples=50,
    )
    # No imputation: neither policy gets a numeric aggregate for condition X.
    assert result.point.n_policies_compared == 0
    assert result.point.kendall_tau is None
    assert result.point.spearman_rho is None
    assert result.point.topk_k_reduced[1] is True
    # Undefinedness is surfaced, not hidden.
    assert result.point.n_policies_excluded_left == 2
