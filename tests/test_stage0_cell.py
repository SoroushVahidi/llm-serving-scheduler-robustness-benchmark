from __future__ import annotations

import pytest

from robustbench.stage0.cell import (
    STAGE0_LOAD_REGIONS,
    STAGE0_N_REPETITIONS,
    STAGE0_POLICIES,
    CellSpec,
    expand_cell_grid,
)


def _fake_manifests(n_sources=3, n_windows_per_source=10):
    windows = []
    calibrations = []
    for s in range(n_sources):
        source = f"source{s}"
        for w in range(n_windows_per_source):
            window_id = f"{source}_w{w:02d}"
            windows.append({"window_id": window_id, "source_family": source, "records": []})
            calibrations.append({
                "window_id": window_id, "lambda_ref": 10.0 + w,
                "load_regions": {"PRE_KNEE": 8.0 + w, "KNEE": 10.0 + w, "OVERLOAD": 12.0 + w},
            })
    return {"windows": windows}, {"calibrations": calibrations}


def test_expand_cell_grid_produces_exactly_1080_cells_for_frozen_shape():
    windows_manifest, calibration_manifest = _fake_manifests(3, 10)
    cells = expand_cell_grid(windows_manifest, calibration_manifest)
    assert len(cells) == 3 * 10 * len(STAGE0_LOAD_REGIONS) * len(STAGE0_POLICIES) * STAGE0_N_REPETITIONS
    assert len(cells) == 1080


def test_cell_ids_are_unique():
    windows_manifest, calibration_manifest = _fake_manifests(3, 10)
    cells = expand_cell_grid(windows_manifest, calibration_manifest)
    ids = [c.cell_id for c in cells]
    assert len(ids) == len(set(ids))


def test_canonical_hashes_are_unique():
    windows_manifest, calibration_manifest = _fake_manifests(3, 10)
    cells = expand_cell_grid(windows_manifest, calibration_manifest)
    hashes = [c.canonical_hash() for c in cells]
    assert len(hashes) == len(set(hashes))


def test_canonical_hash_deterministic_across_calls():
    spec = CellSpec(source_family="s", window_id="w", load_region="KNEE", load_factor=10.0,
                     policy_id="fifo", repetition=0, synthesis_seed=1, scenario_config_hash="abc")
    assert spec.canonical_hash() == spec.canonical_hash()


def test_canonical_hash_differs_for_different_repetition():
    spec0 = CellSpec(source_family="s", window_id="w", load_region="KNEE", load_factor=10.0,
                      policy_id="fifo", repetition=0, synthesis_seed=1, scenario_config_hash="abc")
    spec1 = CellSpec(source_family="s", window_id="w", load_region="KNEE", load_factor=10.0,
                      policy_id="fifo", repetition=1, synthesis_seed=1, scenario_config_hash="abc")
    assert spec0.canonical_hash() != spec1.canonical_hash()
    assert spec0.cell_id != spec1.cell_id


def test_expand_cell_grid_raises_on_window_missing_calibration():
    windows_manifest, calibration_manifest = _fake_manifests(1, 2)
    calibration_manifest["calibrations"].pop()  # remove one window's calibration
    with pytest.raises(ValueError, match="no load-calibration entry"):
        expand_cell_grid(windows_manifest, calibration_manifest)


def test_repetitions_are_verification_reps_not_independent_seeds():
    """Both repetitions of the same cell must share the SAME synthesis_seed
    -- per docs/STAGE0_DISCRIMINABILITY_PROTOCOL.md, repetition verifies
    deterministic rerun, it is not an independent statistical sample."""
    windows_manifest, calibration_manifest = _fake_manifests(1, 1)
    cells = expand_cell_grid(windows_manifest, calibration_manifest)
    by_combo = {}
    for c in cells:
        key = (c.source_family, c.window_id, c.load_region, c.policy_id)
        by_combo.setdefault(key, []).append(c)
    for key, reps in by_combo.items():
        seeds = {r.synthesis_seed for r in reps}
        assert seeds == {reps[0].synthesis_seed}, f"{key}: reps use different seeds {seeds}"
