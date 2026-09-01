"""Bootstrap smoke test: reused simulator + policy infrastructure runs end to end."""
from __future__ import annotations

from robustbench.core.types import GPUConfig
from robustbench.evaluation.run_policy import run_policy
from robustbench.policies.registry import make_policy, make_policy_library_v2
from robustbench.workloads.synthetic import make_medium_trace


def _gpu_configs():
    return [
        GPUConfig(gpu_id=0, max_active_sequences=8, max_batch_tokens=8, max_kv_tokens=4096),
    ]


def test_fifo_runs_and_produces_metrics():
    requests = make_medium_trace(seed=0)
    metrics = run_policy(make_policy("fifo"), requests, _gpu_configs(), workload_tag="smoke", seed=0)
    assert metrics.num_completed + metrics.num_dropped == len(requests)
    assert metrics.num_completed > 0


def test_edf_runs_and_produces_metrics():
    requests = make_medium_trace(seed=0)
    metrics = run_policy(make_policy("edf"), requests, _gpu_configs(), workload_tag="smoke", seed=0)
    assert metrics.num_completed + metrics.num_dropped == len(requests)


def test_deterministic_rerun():
    requests = make_medium_trace(seed=1)
    m1 = run_policy(make_policy("fifo"), requests, _gpu_configs(), workload_tag="smoke", seed=1)
    m2 = run_policy(make_policy("fifo"), requests, _gpu_configs(), workload_tag="smoke", seed=1)
    assert m1.num_completed == m2.num_completed
    assert m1.num_dropped == m2.num_dropped


def test_two_policies_paired_on_same_trace():
    """Minimal paired multi-policy smoke test: same trace, two policies, no crash/NaN schema corruption."""
    requests = make_medium_trace(seed=2)
    rows = []
    for name in ("fifo", "edf", "weighted_fair_share"):
        policy = make_policy_library_v2(name)
        m = run_policy(policy, requests, _gpu_configs(), workload_tag="smoke", seed=2)
        rows.append({"policy": name, "num_completed": m.num_completed, "num_dropped": m.num_dropped})
    assert len(rows) == 3
    for row in rows:
        assert row["num_completed"] >= 0
        assert row["num_dropped"] >= 0
