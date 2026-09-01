from __future__ import annotations

from dataclasses import dataclass

from robustbench.calibration.stage0_load_calibration import (
    BISECTION_LOG_HI,
    BISECTION_LOG_LO,
    LOAD_REGION_MULTIPLIERS,
    _classify_sanity_notes,
    calibrate_window,
)
from robustbench.workloads.synthetic import make_small_debug_trace


@dataclass
class _FakeMetrics:
    completion_fraction: float
    slo_violation_rate: float
    num_completed: int = 1
    num_dropped: int = 0


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


def test_pre_knee_trivial_underload_alone_does_not_block_plausible():
    """Regression test for docs/STAGE0_LOAD_CALIBRATION_AUDIT_20260901.md:
    a PRE_KNEE region with completion_fraction~=1.0 and slo_violation_rate~=0
    (the mathematically expected outcome of a correctly calibrated PRE_KNEE,
    given the achievable violation-rate granularity at real Stage-0 window
    sizes) must NOT by itself make plausible=False -- it is recorded as an
    informational note only."""
    m_pre = _FakeMetrics(completion_fraction=1.0, slo_violation_rate=0.0)
    m_over = _FakeMetrics(completion_fraction=1.0, slo_violation_rate=0.05)  # well past 2x threshold
    blocking, informational = _classify_sanity_notes(m_pre, m_over, lambda_ref=10.0)
    assert blocking == []
    assert any("trivially underloaded" in n for n in informational)


def test_overload_little_pressure_still_blocks_plausible():
    """The OVERLOAD-little-pressure, malfunction, and pinned-lambda_ref
    checks are unchanged by the PRE_KNEE fix -- they must still gate
    plausible=False."""
    m_pre = _FakeMetrics(completion_fraction=1.0, slo_violation_rate=0.0)
    m_over = _FakeMetrics(completion_fraction=1.0, slo_violation_rate=0.005)  # < 2x threshold (0.01)
    blocking, informational = _classify_sanity_notes(m_pre, m_over, lambda_ref=10.0)
    assert any("little more pressure" in n for n in blocking)


def test_overload_malfunction_blocks_plausible():
    m_pre = _FakeMetrics(completion_fraction=1.0, slo_violation_rate=0.0)
    m_over = _FakeMetrics(completion_fraction=float("nan"), slo_violation_rate=0.0,
                           num_completed=0, num_dropped=0)
    blocking, _ = _classify_sanity_notes(m_pre, m_over, lambda_ref=10.0)
    assert any("malfunction" in n for n in blocking)


def test_pinned_lambda_ref_blocks_plausible():
    m_pre = _FakeMetrics(completion_fraction=1.0, slo_violation_rate=0.0)
    m_over = _FakeMetrics(completion_fraction=1.0, slo_violation_rate=0.05)
    blocking, _ = _classify_sanity_notes(m_pre, m_over, lambda_ref=10 ** BISECTION_LOG_LO)
    assert any("pinned to a search-range bound" in n for n in blocking)
    blocking, _ = _classify_sanity_notes(m_pre, m_over, lambda_ref=10 ** BISECTION_LOG_HI)
    assert any("pinned to a search-range bound" in n for n in blocking)


def test_fully_healthy_calibration_has_no_blocking_notes():
    m_pre = _FakeMetrics(completion_fraction=1.0, slo_violation_rate=0.0)
    m_over = _FakeMetrics(completion_fraction=0.9, slo_violation_rate=0.1)
    blocking, informational = _classify_sanity_notes(m_pre, m_over, lambda_ref=10.0)
    assert blocking == []
    assert informational != []  # PRE_KNEE trivial note still recorded, just non-blocking
