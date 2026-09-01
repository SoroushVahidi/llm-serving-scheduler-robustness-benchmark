from __future__ import annotations

from robustbench.stage0.schema import CellResult, validate_cell_result


def _base_kwargs(**overrides):
    d = dict(
        cell_id="s::w::KNEE::fifo::rep0", canonical_hash="abc123",
        source_family="s", window_id="w", load_region="KNEE", load_factor=10.0,
        policy_id="fifo", repetition=0, synthesis_seed=1,
        arrival_normalized_weighted_goodput=0.9, completion_fraction=0.95,
        slo_violation_rate=0.05, success=True,
        repo_sha="deadbeef", window_manifest_sha256="a" * 64,
        calibration_manifest_sha256="b" * 64, policy_registry_hash="c" * 64,
    )
    d.update(overrides)
    return d


def test_valid_success_cell_has_no_problems():
    assert validate_cell_result(_base_kwargs()) == []


def test_missing_required_field_detected():
    d = _base_kwargs()
    del d["repo_sha"]
    problems = validate_cell_result(d)
    assert any("repo_sha" in p for p in problems)


def test_success_true_with_none_metric_is_invalid():
    d = _base_kwargs(arrival_normalized_weighted_goodput=None)
    problems = validate_cell_result(d)
    assert any("arrival_normalized_weighted_goodput" in p for p in problems)


def test_success_true_with_nan_metric_is_invalid():
    d = _base_kwargs(completion_fraction=float("nan"))
    problems = validate_cell_result(d)
    assert any("completion_fraction" in p for p in problems)


def test_success_false_requires_error_category():
    d = _base_kwargs(success=False, error_category=None,
                      arrival_normalized_weighted_goodput=None,
                      completion_fraction=None, slo_violation_rate=None)
    problems = validate_cell_result(d)
    assert any("error_category" in p for p in problems)


def test_success_false_with_error_category_is_valid():
    d = _base_kwargs(success=False, error_category="SomeError", error_detail="boom",
                      arrival_normalized_weighted_goodput=None,
                      completion_fraction=None, slo_violation_rate=None)
    assert validate_cell_result(d) == []


def test_invalid_repetition_detected():
    d = _base_kwargs(repetition=2)
    problems = validate_cell_result(d)
    assert any("repetition" in p for p in problems)


def test_cell_result_to_dict_roundtrips_through_validator():
    cr = CellResult(cell_id="x", canonical_hash="y", source_family="s", window_id="w",
                     load_region="KNEE", load_factor=1.0, policy_id="fifo", repetition=0,
                     synthesis_seed=1, arrival_normalized_weighted_goodput=1.0,
                     completion_fraction=1.0, slo_violation_rate=0.0, success=True,
                     repo_sha="x", window_manifest_sha256="x", calibration_manifest_sha256="x",
                     policy_registry_hash="x")
    assert validate_cell_result(cr.to_dict()) == []
