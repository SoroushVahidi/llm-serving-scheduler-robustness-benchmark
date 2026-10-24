"""Executes one Stage-0 cell end-to-end (section B3).

1. load the exact frozen workload window (records embedded in
   stage0_windows.json, addressed by window_id)
2. apply the exact frozen load transformation (`_rebase_and_scale` at the
   cell's frozen `load_factor`, reusing the SAME function the calibration
   module itself uses -- single source of truth for the load transform)
3. instantiate the requested frozen policy (`make_policy_any`)
4. execute the simulator (`run_policy`)
5. compute metrics (returned by `run_policy` as `RunMetrics`)
6. validate output schema (`validate_cell_result`)
7-9. caller (harness.py) writes atomically / writes provenance / writes
   explicit failure state -- this module never writes files itself, so it
   stays independently unit-testable.
"""
from __future__ import annotations

import traceback
from typing import Optional

from ..calibration.stage0_load_calibration import (
    REFERENCE_POLICY as _CALIBRATION_REFERENCE_POLICY,  # noqa: F401  (re-exported for clarity in provenance)
    STAGE0_REFERENCE_GPU_CONFIG,
    _rebase_and_scale,
)
from ..evaluation.run_policy import run_policy
from ..policies.registry import make_policy_any
from ..workloads.external.benchmark_synthesis import (
    SYNTHESIS_VERSION,
    synthesize_requests_from_window,
)
from ..workloads.external.schema import ExternalWorkloadRecord
from .cell import CellSpec
from .schema import CellResult, validate_cell_result


def execute_cell(
    spec: CellSpec,
    *,
    window_records: list[dict],
    repo_sha: str,
    window_manifest_sha256: str,
    calibration_manifest_sha256: str,
    policy_registry_hash: str,
    scientific_status: Optional[str] = None,
) -> CellResult:
    """Never raises -- any exception is caught and returned as an explicit
    `success=False` CellResult with `error_category`/`error_detail`, so a
    single bad cell can never silently drop out of the matrix or crash a
    SLURM array task processing many cells.

    `scientific_status`: pass "SMOKE_ONLY_DO_NOT_ANALYZE" for
    infrastructure-exercise runs (section E) -- stamped onto the result and
    enforced by analyzer.py, which refuses to treat any labeled cell as
    Stage-0 evidence."""
    base = CellResult(
        scientific_status=scientific_status,
        cell_id=spec.cell_id,
        canonical_hash=spec.canonical_hash(),
        source_family=spec.source_family,
        window_id=spec.window_id,
        load_region=spec.load_region,
        load_factor=spec.load_factor,
        policy_id=spec.policy_id,
        repetition=spec.repetition,
        synthesis_seed=spec.synthesis_seed,
        repo_sha=repo_sha,
        window_manifest_sha256=window_manifest_sha256,
        calibration_manifest_sha256=calibration_manifest_sha256,
        policy_registry_hash=policy_registry_hash,
        synthesis_version=SYNTHESIS_VERSION,
    )
    try:
        records = [ExternalWorkloadRecord(**r) for r in window_records]
        requests, _synth_manifest = synthesize_requests_from_window(
            records, window_id=spec.window_id, seed=spec.synthesis_seed
        )
        if len(requests) < 2:
            base.success = False
            base.error_category = "insufficient_requests"
            base.error_detail = f"only {len(requests)} usable requests synthesized"
            return base

        scaled = _rebase_and_scale(requests, spec.load_factor)
        policy = make_policy_any(spec.policy_id)
        # repetition is a VERIFICATION rep, not an independent statistical
        # sample -- both repetitions use the identical seed/inputs
        # deliberately (docs/STAGE0_DISCRIMINABILITY_PROTOCOL.md); the
        # harness checks rep0==rep1 as a data-integrity property, not a
        # source of statistical power.
        m = run_policy(
            policy, scaled, [STAGE0_REFERENCE_GPU_CONFIG],
            workload_tag=f"stage0::{spec.cell_id}", seed=spec.synthesis_seed,
        )

        base.arrival_normalized_weighted_goodput = m.arrival_normalized_weighted_goodput
        base.completion_fraction = m.completion_fraction
        base.slo_violation_rate = m.slo_violation_rate
        base.weighted_goodput = m.weighted_goodput
        base.mean_latency = m.mean_latency
        base.p95_latency = m.p95_latency
        base.mean_ttft = m.mean_ttft
        base.p95_ttft = m.p95_ttft
        base.request_throughput = m.request_throughput
        base.token_throughput = m.token_throughput
        base.success = True
    except Exception as e:  # noqa: BLE001 -- deliberate: never let one cell crash the harness
        base.success = False
        base.error_category = type(e).__name__
        base.error_detail = "".join(traceback.format_exception_only(type(e), e)).strip() + \
            " | " + traceback.format_exc(limit=3).replace("\n", " ")
        return base

    problems = validate_cell_result(base.to_dict())
    if problems:
        base.success = False
        base.error_category = "schema_validation_failed"
        base.error_detail = "; ".join(problems)
    return base
