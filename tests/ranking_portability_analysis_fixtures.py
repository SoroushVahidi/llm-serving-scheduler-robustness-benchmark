"""Shared fabricated-fixture builders for the Phase-12 analysis-prefreeze
test suite. Every value here is synthetic and has ZERO connection to any
real scheduler execution -- this module must never read a real campaign
artifact (docs/RANKING_PORTABILITY_PHASE12_ANALYSIS_PREFREEZE.md,
PHASE12_ANALYSIS_PREFREEZE_RESULT_BLIND = YES).
"""
from __future__ import annotations

from typing import Optional


def make_telemetry(*, schema_version: str = "telemetry_v1", n_steps: int = 100) -> dict:
    return {
        "schema_version": schema_version,
        "queue_depth_mean": 1.0,
        "queue_depth_max": 3,
        "batch_saturation_mean": 0.5,
        "batch_saturation_max": 0.9,
        "prefill_decode_contention_fraction": 0.1,
        "kv_occupancy_mean": 0.4,
        "kv_occupancy_max": 0.8,
        "admission_control_activations": 0,
        "preemption_or_reorder_events": 0,
        "token_budget_saturation_fraction": 0.2,
        "n_steps": n_steps,
    }


def make_cell_row(
    *,
    source_family: str = "burstgpt",
    window_id: str,
    load_region: str = "KNEE",
    policy_id: str,
    repetition: int = 0,
    synthesis_seed: int = 42,
    load_factor: float = 1.0,
    success: bool = True,
    scientific_status: str = "PILOT_V2_SCIENTIFIC",
    anwg: float = 0.5,
    completion_fraction: float = 1.0,
    weighted_completion_fraction: float = 1.0,
    slo_violation_rate: Optional[float] = 0.1,
    weighted_goodput: Optional[float] = 0.4,
    mean_latency: Optional[float] = 1.0,
    p95_latency: Optional[float] = 2.0,
    mean_ttft: Optional[float] = 0.2,
    p95_ttft: Optional[float] = 0.5,
    request_throughput: Optional[float] = 10.0,
    token_throughput: Optional[float] = 100.0,
    error_category: Optional[str] = None,
    error_detail: Optional[str] = None,
) -> dict:
    """Builds a schema-valid (or, if success=False, error-shaped)
    `RankingPortabilityCellResult`-equivalent dict, purely from
    caller-supplied fabricated numbers."""
    cell_id = f"{source_family}::{window_id}::{load_region}::{policy_id}::rep{repetition}"
    if not success:
        return {
            "schema_version": "ranking_portability_cell_result_v1",
            "cell_id": cell_id, "source_family": source_family, "window_id": window_id,
            "load_region": load_region, "load_factor": load_factor, "policy_id": policy_id,
            "repetition": repetition, "synthesis_seed": synthesis_seed,
            "arrival_normalized_weighted_goodput": None, "completion_fraction": None,
            "weighted_completion_fraction": None, "slo_violation_rate": None,
            "weighted_goodput": None, "mean_latency": None, "p95_latency": None,
            "mean_ttft": None, "p95_ttft": None, "request_throughput": None,
            "token_throughput": None,
            "telemetry_schema_version": "", "telemetry": {},
            "repo_sha": "fixture", "window_manifest_sha256": "", "calibration_manifest_sha256": "",
            "policy_registry_hash": "", "simulator_config_hash": "", "synthesis_version": "",
            "environment": {},
            "success": False,
            "error_category": error_category or "FabricatedFixtureError",
            "error_detail": error_detail or "fabricated failure for testing",
            "scientific_status": scientific_status,
        }
    return {
        "schema_version": "ranking_portability_cell_result_v1",
        "cell_id": cell_id, "source_family": source_family, "window_id": window_id,
        "load_region": load_region, "load_factor": load_factor, "policy_id": policy_id,
        "repetition": repetition, "synthesis_seed": synthesis_seed,
        "arrival_normalized_weighted_goodput": anwg,
        "completion_fraction": completion_fraction,
        "weighted_completion_fraction": weighted_completion_fraction,
        "slo_violation_rate": slo_violation_rate,
        "weighted_goodput": weighted_goodput,
        "mean_latency": mean_latency,
        "p95_latency": p95_latency,
        "mean_ttft": mean_ttft,
        "p95_ttft": p95_ttft,
        "request_throughput": request_throughput,
        "token_throughput": token_throughput,
        "telemetry_schema_version": "telemetry_v1",
        "telemetry": make_telemetry(),
        "repo_sha": "fixture", "window_manifest_sha256": "fixture", "calibration_manifest_sha256": "fixture",
        "policy_registry_hash": "fixture", "simulator_config_hash": "fixture", "synthesis_version": "fixture",
        "environment": {},
        "success": True,
        "error_category": None, "error_detail": None,
        "scientific_status": scientific_status,
    }


def make_zero_completion_row(**kwargs) -> dict:
    """Case 8/9: zero-completion / undefined conditional metrics --
    CONDITIONAL_ON_COMPLETION fields are NaN iff completion_fraction==0.0."""
    kwargs.setdefault("completion_fraction", 0.0)
    kwargs.setdefault("weighted_completion_fraction", 0.0)
    kwargs.setdefault("slo_violation_rate", float("nan"))
    kwargs.setdefault("weighted_goodput", float("nan"))
    kwargs.setdefault("mean_latency", float("nan"))
    kwargs.setdefault("p95_latency", float("nan"))
    kwargs.setdefault("request_throughput", float("nan"))
    kwargs.setdefault("token_throughput", float("nan"))
    kwargs.setdefault("mean_ttft", float("nan"))
    kwargs.setdefault("p95_ttft", float("nan"))
    return make_cell_row(**kwargs)


def make_ttft_undefined_row(**kwargs) -> dict:
    """Case 10: TTFT-specific undefined case -- completion_fraction > 0
    but no completed request recorded a first-token time."""
    kwargs.setdefault("completion_fraction", 1.0)
    kwargs.setdefault("mean_ttft", float("nan"))
    kwargs.setdefault("p95_ttft", float("nan"))
    return make_cell_row(**kwargs)


def make_tiny_manifest(
    *,
    campaign_freeze_sha256: str,
    sources=("burstgpt",),
    windows_per_source=("w0", "w1"),
    regions=("KNEE",),
    policies=("fifo", "edf"),
    repetitions=(0, 1),
    synthesis_seed: int = 42,
) -> dict:
    """A tiny (source x window x region x policy x rep) manifest, shaped
    exactly like the real 18,720-cell manifest's `cells` /
    `region_assignment_index` fields but at fabricated toy scale."""
    cells = []
    region_assignment_index = {}
    for source in sources:
        for w in windows_per_source:
            for region in regions:
                key = f"{source}::{w}::{region}"
                region_assignment_index[key] = {
                    "lambda_ref": 1.0, "selected_load_factor": 1.0, "absolute_load_factor": 1.0,
                }
                for policy in policies:
                    for rep in repetitions:
                        cells.append({
                            "cell_id": f"{source}::{w}::{region}::{policy}::rep{rep}",
                            "source_family": source, "window_id": w, "load_region": region,
                            "policy_id": policy, "repetition": rep,
                            "synthesis_seed": synthesis_seed,
                            "region_assignment_key": key,
                            "scientific_status": "PILOT_V2_SCIENTIFIC",
                        })
    return {
        "campaign_freeze_sha256": campaign_freeze_sha256,
        "region_assignment_index": region_assignment_index,
        "cells": cells,
        "phase10_window_hash": "fixture-phase10-window",
        "phase10_compact_index_hash": "fixture-phase10-compact",
        "phase11_prelaunch_hash": "fixture-phase11-prelaunch",
        "phase11_raw_fifo_hash": "fixture-phase11-fifo",
        "phase11_region_assignment_hash": "fixture-phase11-assignment",
    }
