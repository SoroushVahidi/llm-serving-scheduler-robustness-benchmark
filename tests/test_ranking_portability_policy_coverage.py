"""Capability-only coverage test: every policy in the Pilot-V2 PRIMARY
panel (docs/RANKING_PORTABILITY_POLICY_PANEL.md, 13 policies) can execute
on a tiny synthetic fixture and emit a schema-valid, complete telemetry
block. Every cell here is explicitly `scientific_status=
"FIXTURE_ONLY_DO_NOT_ANALYZE"` -- this test never uses a real Stage-0/
Pilot-V2 window and never compares policy quality/ranking (that is
explicitly out of scope for this change; see
docs/RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md).
"""
from __future__ import annotations

import pytest

from robustbench.core.types import GPUConfig, Request
from robustbench.policies.registry import make_policy_any
from robustbench.ranking_portability.execute_cell import execute_cell
from robustbench.ranking_portability.schema import validate_cell_result

PILOT_V2_PRIMARY_PANEL = (
    "fifo", "edf", "least_laxity_first", "estimated_service_time_first",
    "weighted_fair_share", "kv_constrained_online", "vllm_faithful",
    "vllm_chunked_prefill_faithful", "sarathi_faithful", "slai_faithful",
    "admission_control",
)
PILOT_V2_STYLE_APPROXIMATION_ROBUSTNESS_ONLY = (
    "vllm_style_token_budget", "scorpio_style_slo_guard",
)
ALL_13_EXECUTED_POLICIES = PILOT_V2_PRIMARY_PANEL + PILOT_V2_STYLE_APPROXIMATION_ROBUSTNESS_ONLY


def _fixture_requests() -> list[Request]:
    return [
        Request(request_id=i, arrival_time=float(i) * 0.5, prompt_tokens=50 + 10 * i,
                predicted_output_tokens=5, actual_output_tokens=5,
                slo_deadline=1000.0, priority=1.0 if i % 2 == 0 else 2.0,
                class_id="tight" if i % 2 == 0 else "loose")
        for i in range(6)
    ]


def _fixture_gpu_config() -> GPUConfig:
    return GPUConfig(gpu_id=0, max_active_sequences=4, max_batch_tokens=4096,
                      max_kv_tokens=131072)


@pytest.mark.parametrize("policy_id", ALL_13_EXECUTED_POLICIES)
def test_policy_executes_and_emits_valid_telemetry(policy_id):
    assert len(ALL_13_EXECUTED_POLICIES) == 13

    policy = make_policy_any(policy_id)
    result = execute_cell(
        cell_id=f"fixture::w00::KNEE::{policy_id}::rep0",
        source_family="fixture", window_id="w00", load_region="KNEE",
        load_factor=1.0, policy_id=policy_id, repetition=0, synthesis_seed=0,
        repo_sha="fixture_only", policy=policy, requests=_fixture_requests(),
        gpu_configs=[_fixture_gpu_config()],
        scientific_status="FIXTURE_ONLY_DO_NOT_ANALYZE",
    )

    assert result.success, (
        f"{policy_id} failed on fixture: {result.error_category}: {result.error_detail}"
    )
    assert result.scientific_status == "FIXTURE_ONLY_DO_NOT_ANALYZE"
    assert validate_cell_result(result.to_dict()) == []

    # Descriptive only -- report which mechanisms activated, never a
    # pass/fail comparison of policy quality.
    t = result.telemetry
    assert isinstance(t["admission_control_activations"], int) and t["admission_control_activations"] >= 0
    assert isinstance(t["preemption_or_reorder_events"], int) and t["preemption_or_reorder_events"] >= 0


def test_panel_size_matches_preregistration():
    assert len(PILOT_V2_PRIMARY_PANEL) == 11
    assert len(PILOT_V2_STYLE_APPROXIMATION_ROBUSTNESS_ONLY) == 2
    assert len(ALL_13_EXECUTED_POLICIES) == 13
