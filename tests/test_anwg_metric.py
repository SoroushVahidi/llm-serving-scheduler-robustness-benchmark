"""Stage-0 primary metric (ANWG) correctness tests, per
docs/STAGE0_METRIC_DEFINITIONS.md and
docs/STAGE0_DISCRIMINABILITY_PROTOCOL.md ("Primary metric for the pilot").

Tests `arrival_normalized_weighted_goodput` directly against
`compute_metrics` with hand-built toy requests -- no simulator, no
frozen data -- so the metric's arithmetic is verified in isolation from
everything else in the Stage-0 pipeline.

ANWG = sum(priority_i * 1[met SLO]_i for i in COMPLETED)
       / sum(priority_i for i in ALL ARRIVALS)

(priority defaults to 1.0 when a request's priority is 0, per
`_request_weight`/existing `weighted_goodput` convention.)
"""
from __future__ import annotations

import math

from robustbench.core.metrics import compute_metrics
from robustbench.core.types import CompletedRequest, Request


def _req(rid, priority=1.0, arrival=0.0, deadline=100.0):
    return Request(
        request_id=rid, arrival_time=arrival, prompt_tokens=10,
        predicted_output_tokens=10, actual_output_tokens=10,
        slo_deadline=deadline, priority=priority, class_id="t",
    )


def _completed(req, completion_time, admission_time=0.0):
    return CompletedRequest(request=req, admission_time=admission_time,
                             completion_time=completion_time, gpu_id=0)


def test_anwg_perfect_completion_all_slo_met():
    reqs = [_req(i, deadline=100.0) for i in range(5)]
    completed = [_completed(r, completion_time=10.0) for r in reqs]  # well within deadline
    m = compute_metrics(completed, dropped=[], sim_duration=10.0,
                         gpu_utilization_history=[], active_batch_history=[],
                         num_total=5, all_requests=reqs)
    assert m.arrival_normalized_weighted_goodput == 1.0
    assert m.weighted_completion_fraction == 1.0


def test_anwg_zero_completion_all_dropped():
    reqs = [_req(i) for i in range(5)]
    m = compute_metrics([], dropped=list(reqs), sim_duration=10.0,
                         gpu_utilization_history=[], active_batch_history=[],
                         num_total=5, all_requests=reqs)
    assert m.arrival_normalized_weighted_goodput == 0.0


def test_anwg_mixed_slo_success_and_failure():
    reqs = [_req(i, deadline=50.0) for i in range(4)]
    completed = [
        _completed(reqs[0], completion_time=10.0),  # met
        _completed(reqs[1], completion_time=20.0),  # met
        _completed(reqs[2], completion_time=99.0),  # violated (> deadline 50)
    ]
    dropped = [reqs[3]]
    m = compute_metrics(completed, dropped=dropped, sim_duration=10.0,
                         gpu_utilization_history=[], active_batch_history=[],
                         num_total=4, all_requests=reqs)
    # 2 of 4 unit-priority arrivals met SLO -> 2/4 = 0.5
    assert math.isclose(m.arrival_normalized_weighted_goodput, 0.5)


def test_anwg_weighted_by_priority():
    reqs = [
        _req(0, priority=3.0, deadline=100.0),
        _req(1, priority=1.0, deadline=100.0),
        _req(2, priority=1.0, deadline=100.0),
    ]
    completed = [
        _completed(reqs[0], completion_time=10.0),  # met, weight 3
        _completed(reqs[1], completion_time=10.0),  # met, weight 1
        # reqs[2] dropped -> contributes weight 1 to denominator, 0 to numerator
    ]
    m = compute_metrics(completed, dropped=[reqs[2]], sim_duration=10.0,
                         gpu_utilization_history=[], active_batch_history=[],
                         num_total=3, all_requests=reqs)
    # numerator = 3*1 + 1*1 = 4, denominator = 3+1+1 = 5
    assert math.isclose(m.arrival_normalized_weighted_goodput, 4.0 / 5.0)


def test_anwg_zero_priority_falls_back_to_unit_weight():
    reqs = [_req(0, priority=0.0, deadline=100.0)]
    completed = [_completed(reqs[0], completion_time=10.0)]
    m = compute_metrics(completed, dropped=[], sim_duration=10.0,
                         gpu_utilization_history=[], active_batch_history=[],
                         num_total=1, all_requests=reqs)
    assert m.arrival_normalized_weighted_goodput == 1.0  # weight 0 -> treated as 1.0, still full credit


def test_anwg_empty_workload_is_nan_not_zero():
    """num_total == 0 (no arrivals at all) is a degenerate case distinct
    from 'zero completions among nonzero arrivals' (which is a real 0.0,
    tested above) -- must not silently collapse to 0.0."""
    m = compute_metrics([], dropped=[], sim_duration=0.0,
                         gpu_utilization_history=[], active_batch_history=[],
                         num_total=0, all_requests=[])
    assert math.isnan(m.arrival_normalized_weighted_goodput)


def test_anwg_distinguishes_from_conditional_weighted_goodput():
    """weighted_goodput is conditional on completion (denominator = weight
    of COMPLETED only); arrival_normalized_weighted_goodput's denominator
    is weight of ALL arrivals. A run with drops must show
    ANWG < weighted_goodput whenever there are drops, since ANWG's
    denominator is strictly larger while its numerator is identical."""
    reqs = [_req(i, deadline=100.0) for i in range(4)]
    completed = [_completed(reqs[i], completion_time=10.0) for i in range(2)]  # 2 of 4 complete, all met SLO
    dropped = reqs[2:]
    m = compute_metrics(completed, dropped=dropped, sim_duration=10.0,
                         gpu_utilization_history=[], active_batch_history=[],
                         num_total=4, all_requests=reqs)
    assert m.weighted_goodput == 1.0  # 100% of COMPLETED requests met SLO
    assert math.isclose(m.arrival_normalized_weighted_goodput, 0.5)  # only 2 of 4 ARRIVALS succeeded
    assert m.arrival_normalized_weighted_goodput < m.weighted_goodput


def test_anwg_throughput_and_completion_are_not_conflated_with_anwg():
    """Sanity: a run with high request_throughput/completion_fraction but
    poor SLO attainment must show low ANWG -- distinguishes ANWG from raw
    throughput/completion-rate, per docs/STAGE0_METRIC_DEFINITIONS.md."""
    reqs = [_req(i, deadline=5.0) for i in range(3)]  # tight deadline
    completed = [_completed(r, completion_time=50.0) for r in reqs]  # all complete, all LATE
    m = compute_metrics(completed, dropped=[], sim_duration=50.0,
                         gpu_utilization_history=[], active_batch_history=[],
                         num_total=3, all_requests=reqs)
    assert m.completion_fraction == 1.0
    assert m.request_throughput > 0
    assert m.arrival_normalized_weighted_goodput == 0.0  # all completed, none met SLO
