from __future__ import annotations

import json
from pathlib import Path

import pytest

from robustbench.real_llm.rq6_slo_metrics import (
    RequestOutcome,
    real_slo_violation_rate,
    scale_request_timing,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = REPO_ROOT / "artifacts/manifests/rq6_real_vllm"


def test_scale_request_timing_identity_at_scale_1():
    arrival, deadline = scale_request_timing(2.0, 5.0, candidate_scale=1.0)
    assert arrival == pytest.approx(2.0)
    assert deadline == pytest.approx(5.0)


def test_scale_request_timing_compresses_arrival_and_slack():
    # base_relative_arrival=4.0, base_slo_deadline=10.0 (slack=6.0), scale=2.0
    arrival, deadline = scale_request_timing(4.0, 10.0, candidate_scale=2.0)
    assert arrival == pytest.approx(2.0)          # 4.0 / 2.0
    assert deadline == pytest.approx(2.0 + 3.0)   # arrival + slack/2.0


def test_scale_request_timing_rejects_nonpositive_scale():
    with pytest.raises(ValueError):
        scale_request_timing(1.0, 2.0, candidate_scale=0.0)


def test_real_slo_violation_rate_fail_closed_no_completions():
    assert real_slo_violation_rate([]) == 1.0
    assert real_slo_violation_rate([RequestOutcome(weight=1.0, slo_deadline_s=1.0, t_done_s=None)]) == 1.0


def test_real_slo_violation_rate_all_met():
    outcomes = [RequestOutcome(weight=1.0, slo_deadline_s=5.0, t_done_s=3.0) for _ in range(10)]
    assert real_slo_violation_rate(outcomes) == pytest.approx(0.0)


def test_real_slo_violation_rate_weighted():
    # 3 completed: weight 1 met, weight 2 met, weight 1 missed -> violation = 1/4
    outcomes = [
        RequestOutcome(weight=1.0, slo_deadline_s=5.0, t_done_s=3.0),
        RequestOutcome(weight=2.0, slo_deadline_s=5.0, t_done_s=4.0),
        RequestOutcome(weight=1.0, slo_deadline_s=5.0, t_done_s=6.0),
    ]
    assert real_slo_violation_rate(outcomes) == pytest.approx(0.25)


def test_real_slo_violation_rate_incomplete_requests_excluded_from_denominator():
    outcomes = [
        RequestOutcome(weight=1.0, slo_deadline_s=5.0, t_done_s=3.0),
        RequestOutcome(weight=1.0, slo_deadline_s=5.0, t_done_s=None),  # never completed
    ]
    # Denominator is weighted *completed* count, per the frozen formula --
    # not weighted arrival count (that is ANWG's denominator, a separate,
    # still-open metric per docs/REAL_SYSTEM_METRIC_MAPPING.md).
    assert real_slo_violation_rate(outcomes) == pytest.approx(0.0)


@pytest.mark.skipif(not MANIFEST_DIR.exists(), reason="RQ6 workload manifests not yet built")
def test_manifest_fields_feed_directly_into_slo_metric():
    """Proves the frozen manifest's weight/slo_deadline fields are exactly
    what real_slo_violation_rate consumes -- no resynthesis, no adapter
    translation layer that could silently drift from stage0_synthesis_v1."""
    paths = sorted(MANIFEST_DIR.glob("rq6_workload_azure_llm_2024_*.json"))
    assert paths, "expected a generated azure_llm_2024 workload manifest"
    with open(paths[-1]) as f:
        manifest = json.load(f)

    reqs = manifest["windows"][0]["requests"][:5]
    outcomes = []
    for r in reqs:
        arrival, deadline = scale_request_timing(
            r["base_relative_arrival_s"], r["base_slo_deadline_s"], candidate_scale=1.0,
        )
        # Simulate every request completing exactly at its scaled deadline
        # (boundary case: t_done == slo_deadline counts as met, per "<=").
        outcomes.append(RequestOutcome(weight=r["weight"], slo_deadline_s=deadline, t_done_s=deadline))

    assert real_slo_violation_rate(outcomes) == pytest.approx(0.0)
    assert all(r["weight"] == 1.0 for r in reqs)  # stage0_synthesis_v1 uniform priority
