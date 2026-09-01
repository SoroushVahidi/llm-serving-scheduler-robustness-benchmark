from __future__ import annotations

from robustbench.calibration.stage0_load_calibration import (
    LOAD_REGION_MULTIPLIERS,
    calibrate_window,
)
from robustbench.workloads.synthetic import make_small_debug_trace


def test_calibrate_window_produces_ordered_regions():
    requests = make_small_debug_trace(seed=1)
    cal = calibrate_window(requests, window_id="w0", source_family="synthetic")
    regions = cal.load_regions
    assert regions["PRE_KNEE"] < regions["KNEE"] < regions["OVERLOAD"]
    assert regions["KNEE"] == cal.lambda_ref
    for name, mult in LOAD_REGION_MULTIPLIERS.items():
        assert regions[name] == cal.lambda_ref * mult


def test_calibrate_window_deterministic():
    requests = make_small_debug_trace(seed=1)
    c1 = calibrate_window(requests, window_id="w0", source_family="synthetic")
    c2 = calibrate_window(requests, window_id="w0", source_family="synthetic")
    assert c1.lambda_ref == c2.lambda_ref
    assert c1.sanity == c2.sanity


def test_calibrate_window_sanity_report_has_expected_keys():
    requests = make_small_debug_trace(seed=1)
    cal = calibrate_window(requests, window_id="w0", source_family="synthetic")
    for key in (
        "pre_knee_completion_fraction",
        "pre_knee_slo_violation_rate",
        "knee_completion_fraction",
        "knee_slo_violation_rate",
        "overload_completion_fraction",
        "overload_slo_violation_rate",
        "plausible",
        "notes",
    ):
        assert key in cal.sanity
