from __future__ import annotations

import inspect
import json

import pytest

from robustbench.ranking_portability import calibration
from robustbench.ranking_portability.calibration import (
    CALIBRATION_PROTOCOL_VERSION,
    REGION_FACTORS,
    REGION_SEQUENCE,
    CalibrationRecord,
    assign_fifo_regions,
    build_calibration_records,
    validate_policy_independence,
)


def test_region_factors_are_exact_and_ordered():
    assert REGION_SEQUENCE == ("LOW", "PRE_KNEE", "KNEE", "POST_KNEE", "OVERLOAD", "HIGH_PRESSURE")
    assert REGION_FACTORS == {
        "LOW": 0.5,
        "PRE_KNEE": 0.8,
        "KNEE": 1.0,
        "POST_KNEE": 1.1,
        "OVERLOAD": 1.2,
        "HIGH_PRESSURE": 1.5,
    }


def test_monotonic_normal_response_assigns_regions_in_order():
    factor_pressure = {
        0.5: 0.3,
        0.8: 0.6,
        1.0: 1.0,
        1.1: 1.35,
        1.2: 1.7,
        1.5: 2.5,
    }
    rows = assign_fifo_regions(factor_pressure)
    assert [row["region"] for row in rows] == list(REGION_SEQUENCE)
    assert rows[0]["target_pressure"] == pytest.approx(0.5)
    assert rows[-1]["target_pressure"] == pytest.approx(1.5)


def test_flat_response_uses_midpoint_fallback():
    rows = assign_fifo_regions({0.5: 1.0, 0.8: 1.0, 1.0: 1.0, 1.1: 1.0, 1.2: 1.0, 1.5: 1.0})
    assert all(row["actual_achieved_pressure"] == 1.0 for row in rows)
    assert all(row["status"] == "exact_match" for row in rows)


def test_abrupt_knee_response_maps_to_nearest_region():
    factor_pressure = {
        0.5: 0.10,
        0.8: 0.11,
        1.0: 0.12,
        1.1: 0.40,
        1.2: 0.80,
        1.5: 0.90,
    }
    rows = assign_fifo_regions(factor_pressure)
    assert rows[3]["region"] == "POST_KNEE"
    assert rows[4]["region"] == "OVERLOAD"


def test_zero_completion_point_is_recorded_as_exact():
    factor_pressure = {0.5: 0.0, 0.8: 0.0, 1.0: 0.0, 1.1: 0.0, 1.2: 0.0, 1.5: 0.0}
    rows = assign_fifo_regions(factor_pressure)
    assert all(row["actual_achieved_pressure"] == 0.0 for row in rows)
    assert all(row["status"] == "exact_match" for row in rows)


def test_unreachable_high_pressure_target_is_capped_at_boundary():
    rows = assign_fifo_regions({0.5: 0.01, 0.8: 0.02, 1.0: 0.03})
    assert rows[-1]["region"] == "HIGH_PRESSURE"
    assert rows[-1]["status"] == "interpolated"


def test_deterministic_tie_breaks_on_earlier_factor():
    factor_pressure = {0.5: 1.0, 0.8: 1.0, 1.0: 0.0, 1.1: 1.0, 1.2: 0.0, 1.5: 1.0}
    rows = assign_fifo_regions(factor_pressure)
    assert rows[0]["region"] == "LOW"
    assert rows[1]["region"] == "PRE_KNEE"


def test_calibration_is_independent_of_non_fifo_policy_names():
    source = inspect.getsource(calibration)
    validate_policy_independence(source)
    assert "EDF" not in source
    assert "SARATHI" not in source


def test_reproducible_serialization_is_stable():
    rows = build_calibration_records(
        source="synthetic",
        window_id="w123",
        factor_pressure={0.5: 0.2, 0.8: 0.4, 1.0: 0.8, 1.1: 1.0, 1.2: 1.6, 1.5: 2.1},
        protocol_hash=CALIBRATION_PROTOCOL_VERSION,
        window_freeze_hash="abc123",
        simulator_sha="sim-001",
    )
    payload = json.dumps([r.to_dict() for r in rows], sort_keys=True)
    parsed = json.loads(payload)
    assert len(parsed) == 6
    assert parsed[0]["region"] == "LOW"


def test_frozen_window_hash_mismatch_is_rejected():
    with pytest.raises(ValueError):
        CalibrationRecord.validate_window_freeze_hash("expected", "actual")
