from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, rel_path: str):
    path = REPO_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run_calibration_mod = _load_module("run_rq6_calibration", "scripts/real_vllm/run_rq6_calibration.py")

from robustbench.real_llm.rq6_calibration import (
    BISECTION_ITERATIONS,
    BISECTION_LOG_HI,
    BISECTION_LOG_LO,
    REFERENCE_POLICY,
    SLO_VIOLATION_THRESHOLD,
    WindowRequestReplayResult,
    _parse_prometheus_gauge,
    bisect_lambda_ref_real,
    check_reset_barrier,
    replay_window_once,
)
from robustbench.real_llm.rq6_slo_metrics import RequestOutcome


class _FakeTokenizer:
    def encode(self, text, add_special_tokens=False):
        return text.split()

    def decode(self, ids):
        return " ".join(ids)


def _fake_window(n=4, arrival=0.0, deadline=1.0, output_tokens=8):
    return [
        {
            "request_id": f"r{i}", "window_id": "w0", "request_index": i,
            "base_relative_arrival_s": arrival, "base_slo_deadline_s": deadline,
            "input_tokens": 10, "output_tokens_target": output_tokens,
            "predicted_output_tokens": output_tokens, "priority": 1.0, "weight": 1.0,
            "class_id": "stage0_uniform", "prompt_generation_seed": i, "source_record_id": f"src:{i}",
        }
        for i in range(n)
    ]


ALWAYS_OK_METRICS = "vllm:num_requests_running{model_name=\"m\"} 0.0\nvllm:num_requests_waiting{model_name=\"m\"} 0.0\n"


# ---------------------------------------------------------------------------
# Prometheus gauge parsing
# ---------------------------------------------------------------------------

def test_parse_prometheus_gauge_present():
    text = 'vllm:num_requests_running{model_name="m"} 3.0\nother_metric 5\n'
    assert _parse_prometheus_gauge(text, "vllm:num_requests_running") == 3.0


def test_parse_prometheus_gauge_absent():
    assert _parse_prometheus_gauge("other_metric 1\n", "vllm:num_requests_running") is None


# ---------------------------------------------------------------------------
# 13. Episode reset barrier
# ---------------------------------------------------------------------------

def test_reset_barrier_passes_immediately_when_queues_empty():
    report = check_reset_barrier(lambda: ALWAYS_OK_METRICS, timeout_s=5.0)
    assert report.passed is True
    assert report.num_requests_running == 0
    assert report.num_requests_waiting == 0


def test_reset_barrier_times_out_when_queue_never_drains():
    busy_metrics = 'vllm:num_requests_running{model_name="m"} 1.0\nvllm:num_requests_waiting{model_name="m"} 0.0\n'
    report = check_reset_barrier(lambda: busy_metrics, timeout_s=0.3, poll_interval_s=0.05)
    assert report.passed is False
    assert report.num_requests_running == 1.0


def test_reset_barrier_passes_when_metrics_unavailable():
    """Older vLLM without /metrics: absent gauges must not block forever --
    the sequential wait-for-all-responses design is the primary isolation
    mechanism, this barrier is defense-in-depth."""
    report = check_reset_barrier(lambda: "no relevant metrics here\n", timeout_s=1.0)
    assert report.passed is True
    assert report.metrics_available is False


# ---------------------------------------------------------------------------
# 2/3. Timing scaling + exact 200-request (here: N-request) replay
# ---------------------------------------------------------------------------

def test_replay_window_once_dispatches_every_request_exactly_once():
    window = _fake_window(n=6)
    calls = []

    def call_fn(prompt, max_tokens, ignore_eos):
        calls.append((prompt, max_tokens, ignore_eos))
        return {"output_tokens": max_tokens, "prompt_tokens": 10}

    result = replay_window_once(
        window, candidate_scale=1.0, tokenizer=_FakeTokenizer(), model="m", call_fn=call_fn,
    )
    assert result.n_total == 6
    assert len(calls) == 6
    assert all(mt == 8 for _, mt, _ in calls)
    assert all(ignore_eos is True for _, _, ignore_eos in calls)


def test_replay_window_once_all_met_gives_zero_violation():
    window = _fake_window(n=5, arrival=0.0, deadline=10.0)  # huge slack
    result = replay_window_once(
        window, candidate_scale=1.0, tokenizer=_FakeTokenizer(), model="m",
        call_fn=lambda p, mt, ie: {"output_tokens": mt, "prompt_tokens": 10},
    )
    assert result.slo_violation_rate == pytest.approx(0.0)
    assert result.n_completed == 5


# ---------------------------------------------------------------------------
# 10. Timeout/failure handling (fail-closed)
# ---------------------------------------------------------------------------

def test_replay_window_once_failed_call_fail_closed():
    def failing_call_fn(prompt, max_tokens, ignore_eos):
        raise RuntimeError("simulated server crash")

    window = _fake_window(n=3)
    result = replay_window_once(
        window, candidate_scale=1.0, tokenizer=_FakeTokenizer(), model="m", call_fn=failing_call_fn,
    )
    assert result.n_completed == 0
    assert result.slo_violation_rate == pytest.approx(1.0)  # fail-closed


# ---------------------------------------------------------------------------
# 5/6/7/8/9/11/15. Bisection: SLO calc, update rule, convergence,
# lower/upper-bound early exit, deterministic candidate history,
# derived HIGH_PRESSURE = 1.5x real lambda_ref
# ---------------------------------------------------------------------------

def _slow_call_fn(delay_s):
    def call_fn(prompt, max_tokens, ignore_eos):
        time.sleep(delay_s)
        return {"output_tokens": max_tokens, "prompt_tokens": 10}
    return call_fn


def test_bisect_converges_near_known_crossover_factor():
    # 4 identical requests, arrival=0, slack=1.0 (deadline=1.0). Real
    # deadline at candidate scale s is 1.0/s. Each call takes ~20ms, so the
    # crossover (violation flips 0 -> 1) is at s* = 1.0 / 0.02 = 50. Real
    # wall-clock sleep/thread-pool jitter means this is a coarse check of
    # the right order of magnitude, not exact precision -- exactness of the
    # bisection *algorithm itself* is separately verified by the
    # lower/upper-bound early-exit tests below, which have no timing
    # dependency at all.
    call_duration = 0.02
    crossover = 1.0 / call_duration
    window = _fake_window(n=4, arrival=0.0, deadline=1.0)

    result = bisect_lambda_ref_real(
        window, tokenizer=_FakeTokenizer(), model="m",
        call_fn=_slow_call_fn(call_duration), fetch_metrics=lambda: ALWAYS_OK_METRICS,
        source="fake_source", window_id="w0",
    )
    assert result.convergence_status == "CONVERGED"
    assert result.real_lambda_ref == pytest.approx(crossover, rel=0.5)
    assert result.derived_high_pressure == pytest.approx(1.5 * result.real_lambda_ref)
    assert result.reference_policy == REFERENCE_POLICY == "vllm_faithful"
    assert len(result.candidate_history) == 2 + BISECTION_ITERATIONS
    # Deterministic candidate history: iteration indices are sequential and
    # every recorded factor lies within the frozen search bounds.
    assert [c.iteration for c in result.candidate_history] == list(range(2 + BISECTION_ITERATIONS))
    assert all(10 ** BISECTION_LOG_LO <= c.factor <= 10 ** BISECTION_LOG_HI for c in result.candidate_history)


def test_bisect_lower_bound_already_violating():
    # Deadline so tight that even the slowest (lowest-factor) candidate violates.
    window = _fake_window(n=2, arrival=0.0, deadline=0.0001)
    result = bisect_lambda_ref_real(
        window, tokenizer=_FakeTokenizer(), model="m",
        call_fn=_slow_call_fn(0.05), fetch_metrics=lambda: ALWAYS_OK_METRICS,
        source="s", window_id="w",
    )
    assert result.convergence_status == "LOWER_BOUND_ALREADY_VIOLATING"
    assert result.real_lambda_ref == pytest.approx(10 ** BISECTION_LOG_LO)
    assert len(result.candidate_history) == 2  # early exit: only f_lo, f_hi measured


def test_bisect_upper_bound_never_violating():
    # Deadline so generous that even the highest-factor (most compressed) candidate meets it.
    window = _fake_window(n=2, arrival=0.0, deadline=1e9)
    result = bisect_lambda_ref_real(
        window, tokenizer=_FakeTokenizer(), model="m",
        call_fn=lambda p, mt, ie: {"output_tokens": mt, "prompt_tokens": 10},
        fetch_metrics=lambda: ALWAYS_OK_METRICS,
        source="s", window_id="w",
    )
    assert result.convergence_status == "UPPER_BOUND_NEVER_VIOLATING"
    assert result.real_lambda_ref == pytest.approx(10 ** BISECTION_LOG_HI)
    assert len(result.candidate_history) == 2


# ---------------------------------------------------------------------------
# 12. Source/window isolation: identical requests under different
#     (source, window_id) labels produce identical numeric results but
#     carry their own distinct identity in the result.
# ---------------------------------------------------------------------------

def test_source_window_isolation_labels_carried_through_not_mixed():
    window = _fake_window(n=2, arrival=0.0, deadline=10.0)
    call_fn = lambda p, mt, ie: {"output_tokens": mt, "prompt_tokens": 10}
    r1 = bisect_lambda_ref_real(
        window, tokenizer=_FakeTokenizer(), model="m", call_fn=call_fn,
        fetch_metrics=lambda: ALWAYS_OK_METRICS, source="azure_llm_2024", window_id="azure_llm_2024_stage0_w00",
    )
    r2 = bisect_lambda_ref_real(
        window, tokenizer=_FakeTokenizer(), model="m", call_fn=call_fn,
        fetch_metrics=lambda: ALWAYS_OK_METRICS, source="burstgpt", window_id="burstgpt_stage0_w00",
    )
    assert r1.source == "azure_llm_2024" and r1.window_id == "azure_llm_2024_stage0_w00"
    assert r2.source == "burstgpt" and r2.window_id == "burstgpt_stage0_w00"
    assert r1.real_lambda_ref == pytest.approx(r2.real_lambda_ref)  # same inputs -> same numeric result


# ---------------------------------------------------------------------------
# 16. No SLAI invocation during calibration
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 14. Slurm array index -> exact window mapping (deterministic, no
#     duplicates, covers all 120 (source, window) units)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not run_calibration_mod.DEFAULT_MANIFEST_DIR.exists(), reason="RQ6 workload manifests not yet built",
)
def test_array_index_to_window_mapping_deterministic_and_complete():
    units_a = run_calibration_mod.enumerate_calibration_units(run_calibration_mod.DEFAULT_MANIFEST_DIR)
    units_b = run_calibration_mod.enumerate_calibration_units(run_calibration_mod.DEFAULT_MANIFEST_DIR)
    assert units_a == units_b  # deterministic across separate calls
    assert len(units_a) == 120
    keys = [(s, w) for s, w, _ in units_a]
    assert len(keys) == len(set(keys))  # no duplicates
    sources = {s for s, _, _ in units_a}
    assert sources == {"azure_llm_2024", "burstgpt", "bailian_qwen"}
    for source in sources:
        assert sum(1 for s, _, _ in units_a if s == source) == 40


def test_reference_policy_is_always_vllm_faithful_never_slai():
    assert REFERENCE_POLICY == "vllm_faithful"
    # Structural guarantee, not just a naming check: neither the per-window
    # replay nor the bisection driver accepts a policy/scheduler parameter
    # at all -- there is no code path by which a caller could substitute a
    # different (e.g. slai_faithful) policy into calibration.
    import inspect
    assert "policy" not in inspect.signature(replay_window_once).parameters
    assert "policy" not in inspect.signature(bisect_lambda_ref_real).parameters


# ---------------------------------------------------------------------------
# 17. CLI-level end-to-end: run_rq6_calibration.py main() invoked exactly as
#     run_rq6_calibration.sbatch invokes it -- from the repo root, with a
#     relative --calibration-manifest path -- must not raise and must write
#     the output file. Regression test for the relative_to(REPO_ROOT) crash
#     that made every array task in job 1220428 fail after a full bisection
#     run, right before writing output.
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not run_calibration_mod.DEFAULT_MANIFEST_DIR.exists(), reason="RQ6 workload manifests not yet built",
)
def test_main_cli_with_relative_calibration_manifest_path(tmp_path, monkeypatch):
    # Reproduces exactly how run_rq6_calibration.sbatch invokes this script:
    # `cd "$REPO"`, the real (default) --manifest-dir, and a *relative*
    # --calibration-manifest path. Uses the real frozen workload manifests
    # and calibration manifest so both relative_to(REPO_ROOT) call sites in
    # main() run against real absolute paths, not a synthetic stand-in repo.
    units = run_calibration_mod.enumerate_calibration_units(run_calibration_mod.DEFAULT_MANIFEST_DIR)
    source, window_id, _ = units[0]

    calibration_manifest_rel = Path("configs/real_vllm/rq6_calibration_manifest_v2_20260903.json")
    assert (REPO_ROOT / calibration_manifest_rel).exists()

    out_dir = tmp_path / "artifacts" / "real_vllm" / "calibration" / "rq6" / "fake_hash"

    class _FakeHandle:
        base_url = "http://127.0.0.1:1"
        def stop(self, timeout_s: float = 20.0) -> int:
            return 0

    def _fake_bisect(*args, **kwargs):
        from robustbench.real_llm.rq6_calibration import BisectionCandidateRecord, WindowCalibrationResult
        return WindowCalibrationResult(
            source=source, window_id=window_id, reference_policy=REFERENCE_POLICY,
            real_lambda_ref=1.0, derived_high_pressure=1.5,
            convergence_status="converged",
            candidate_history=[BisectionCandidateRecord(
                iteration=0, factor=1.0, slo_violation_rate=0.0, n_completed=2, n_total=2,
                reset_barrier_passed=True,
            )],
        )

    monkeypatch.setattr(run_calibration_mod, "start_vllm_server", lambda **kwargs: _FakeHandle())
    monkeypatch.setattr(run_calibration_mod, "wait_for_server_ready", lambda handle, timeout_s=600.0: True)
    monkeypatch.setattr(run_calibration_mod, "bisect_lambda_ref_real", _fake_bisect)
    monkeypatch.setattr(run_calibration_mod, "_load_tokenizer", lambda model: _FakeTokenizer())
    monkeypatch.chdir(REPO_ROOT)  # matches the sbatch script's `cd "$REPO"`

    argv = [
        "run_rq6_calibration.py",
        "--array-index", "0",
        "--model", "fake-model",
        "--out-dir", str(out_dir),
        "--calibration-manifest", str(calibration_manifest_rel),  # relative, like the sbatch script
    ]
    monkeypatch.setattr("sys.argv", argv)

    run_calibration_mod.main()  # must not raise ValueError from Path.relative_to

    out_path = out_dir / source / f"{window_id}.json"
    assert out_path.exists()
    written = json.loads(out_path.read_text())
    assert written["calibration_manifest_path"] == str(calibration_manifest_rel)
    assert written["real_lambda_ref"] == 1.0
