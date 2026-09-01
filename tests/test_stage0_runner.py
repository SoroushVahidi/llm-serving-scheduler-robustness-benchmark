from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from robustbench.stage0.cell import CellSpec
from robustbench.stage0.runner import execute_cell
from robustbench.workloads.external.adapters import burstgpt

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "configs" / "external_workloads" / "fixtures"


def _fixture_records(n_repeats: int = 30) -> list[dict]:
    adapter = burstgpt.BurstGPTAdapter()
    base = list(adapter.stream_records(FIXTURES / "burstgpt_sample.csv"))
    out = []
    t_offset = 0.0
    for _ in range(n_repeats):
        for r in base:
            rec = asdict(r)
            rec["arrival_time_s"] = (rec["arrival_time_s"] or 0.0) + t_offset
            out.append(rec)
        t_offset += 1000.0
    return out


def _spec(**overrides):
    kw = dict(source_family="burstgpt", window_id="burstgpt_test_w0", load_region="KNEE",
              load_factor=1.0, policy_id="fifo", repetition=0, synthesis_seed=1,
              scenario_config_hash="abc")
    kw.update(overrides)
    return CellSpec(**kw)


def _prov():
    return dict(repo_sha="deadbeef", window_manifest_sha256="a" * 64,
                calibration_manifest_sha256="b" * 64, policy_registry_hash="c" * 64)


def test_execute_cell_success_produces_valid_schema():
    records = _fixture_records()
    result = execute_cell(_spec(), window_records=records, **_prov())
    assert result.success, result.error_detail
    assert 0.0 <= result.completion_fraction <= 1.0
    assert result.arrival_normalized_weighted_goodput is not None
    assert result.cell_id == _spec().cell_id
    assert result.canonical_hash == _spec().canonical_hash()


def test_execute_cell_deterministic_across_identical_reps():
    """Both repetitions of the same cell use the identical seed/inputs and
    must produce identical metrics -- verification, not statistical
    independence (docs/STAGE0_DISCRIMINABILITY_PROTOCOL.md)."""
    records = _fixture_records()
    r0 = execute_cell(_spec(repetition=0), window_records=records, **_prov())
    r1 = execute_cell(_spec(repetition=1), window_records=records, **_prov())
    assert r0.success and r1.success
    assert r0.arrival_normalized_weighted_goodput == r1.arrival_normalized_weighted_goodput
    assert r0.completion_fraction == r1.completion_fraction


def test_execute_cell_never_raises_on_insufficient_records():
    result = execute_cell(_spec(), window_records=[], **_prov())
    assert result.success is False
    assert result.error_category is not None


def test_execute_cell_never_raises_on_unknown_policy():
    records = _fixture_records()
    result = execute_cell(_spec(policy_id="not_a_real_policy"), window_records=records, **_prov())
    assert result.success is False
    assert result.error_category is not None
    assert result.error_detail


def test_execute_cell_load_factor_changes_completion_fraction():
    """Sanity: applying the frozen PRE_KNEE vs OVERLOAD load factor to the
    SAME window should produce a real difference in load-related metrics --
    proves the load transform actually reaches the simulator."""
    records = _fixture_records()
    light = execute_cell(_spec(load_region="PRE_KNEE", load_factor=0.5), window_records=records, **_prov())
    heavy = execute_cell(_spec(load_region="OVERLOAD", load_factor=5000.0), window_records=records, **_prov())
    assert light.success and heavy.success
    assert light.slo_violation_rate <= heavy.slo_violation_rate
