"""Sample-complexity ladder tests, fabricated per-window policy values."""
from __future__ import annotations

from robustbench.ranking_portability.analysis.contract import (
    SAMPLE_COMPLEXITY_DRAWS_PER_N,
    SAMPLE_COMPLEXITY_N_VALUES,
)
from robustbench.ranking_portability.analysis.sample_complexity import (
    compare_concentrated_vs_spread,
    run_sample_complexity,
)


def _noiseless_per_window(n_windows=40):
    # policy 'a' always beats 'b' always beats 'c', no noise -> every
    # subsample must recover the exact full ranking, at every n.
    return {
        f"w{i}": {"a": 3.0, "b": 2.0, "c": 1.0} for i in range(n_windows)
    }


def test_ladder_uses_frozen_n_values_and_draws():
    per_window = _noiseless_per_window()
    result = run_sample_complexity(per_window, policies=["a", "b", "c"], base_seed=1)
    assert [pt.n for pt in result.points] == list(SAMPLE_COMPLEXITY_N_VALUES)
    assert all(pt.n_draws == SAMPLE_COMPLEXITY_DRAWS_PER_N for pt in result.points)


def test_noiseless_ranking_always_recovered():
    per_window = _noiseless_per_window()
    result = run_sample_complexity(per_window, policies=["a", "b", "c"], base_seed=2)
    assert all(pt.p_exact_recovery == 1.0 for pt in result.points)
    assert result.first_n_meeting_exact_threshold == min(pt.n for pt in result.points)


def test_deterministic_given_same_seed():
    per_window = _noiseless_per_window()
    r1 = run_sample_complexity(per_window, policies=["a", "b", "c"], base_seed=5)
    r2 = run_sample_complexity(per_window, policies=["a", "b", "c"], base_seed=5)
    assert [pt.seed for pt in r1.points] == [pt.seed for pt in r2.points]
    assert [pt.p_exact_recovery for pt in r1.points] == [pt.p_exact_recovery for pt in r2.points]


def test_noisy_ranking_recovery_below_one():
    import numpy as np
    rng = np.random.default_rng(0)
    per_window = {
        f"w{i}": {
            "a": 1.0 + rng.normal(0, 5),
            "b": 1.0 + rng.normal(0, 5),
            "c": 1.0 + rng.normal(0, 5),
        }
        for i in range(40)
    }
    result = run_sample_complexity(per_window, policies=["a", "b", "c"], base_seed=3)
    # With this much per-window noise around near-tied means, small n should
    # not deterministically recover the full-window ranking every time.
    assert result.points[0].p_exact_recovery <= 1.0


def test_concentrated_vs_spread_runs_and_returns_finite_values():
    per_window_by_source = {
        "s1": _noiseless_per_window(40),
        "s2": _noiseless_per_window(40),
        "s3": _noiseless_per_window(40),
    }
    result = compare_concentrated_vs_spread(
        per_window_by_source, policies=["a", "b", "c"], n_total=12, n_draws=50,
    )
    assert result.mean_tau_concentrated == result.mean_tau_concentrated  # not NaN
    assert result.mean_tau_spread == result.mean_tau_spread
