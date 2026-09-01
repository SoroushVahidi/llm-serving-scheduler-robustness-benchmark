"""Ranking-portability-pilot per-cell execution + telemetry collection path.

Deliberately minimal: this implements ONLY what
`docs/RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md` section 8's telemetry
contract requires to be testable end-to-end -- constructing a `Simulator`,
running one policy on one trace, and packaging `RunMetrics` +
`TelemetrySummary` into a `RankingPortabilityCellResult`. It does NOT
sample workload windows, calibrate load, or implement a SLURM/harness
layer (`docs/RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md`'s window/load/
policy execution machinery is explicitly out of scope for this change).

Never raises: any exception is caught and returned as an explicit
`success=False` `RankingPortabilityCellResult`, matching
`stage0.runner.execute_cell`'s convention.
"""
from __future__ import annotations

import traceback
from typing import List, Optional, Sequence

from ..core.types import GPUConfig, Request
from ..policies.base import BasePolicy
from ..simulator.service_model import ServiceModel
from ..simulator.simulator import Simulator, SimulatorConfig
from .schema import RankingPortabilityCellResult, validate_cell_result


def execute_cell(
    *,
    cell_id: str,
    source_family: str,
    window_id: str,
    load_region: str,
    load_factor: float,
    policy_id: str,
    repetition: int,
    synthesis_seed: int,
    repo_sha: str,
    policy: BasePolicy,
    requests: Sequence[Request],
    gpu_configs: List[GPUConfig],
    service_model: Optional[ServiceModel] = None,
    drain_steps: int = 50_000,
    scientific_status: Optional[str] = None,
) -> RankingPortabilityCellResult:
    """Run `policy` on `requests` and return a schema-validated
    `RankingPortabilityCellResult`, telemetry included. `scientific_status`
    should be `"FIXTURE_ONLY_DO_NOT_ANALYZE"` for capability/coverage tests
    (see `docs/RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md`'s tests) --
    never left `None` for anything but real, frozen pilot evidence."""
    base_kwargs = dict(
        cell_id=cell_id, source_family=source_family, window_id=window_id,
        load_region=load_region, load_factor=load_factor, policy_id=policy_id,
        repetition=repetition, synthesis_seed=synthesis_seed, repo_sha=repo_sha,
    )
    try:
        if service_model is None:
            service_model = ServiceModel()
        sim_cfg = SimulatorConfig(
            gpu_configs=gpu_configs, service_model=service_model, drain_steps=drain_steps,
        )
        sim = Simulator(sim_cfg)
        sim.load_trace(list(requests))
        policy.reset()
        m = sim.run(policy, workload_tag=cell_id, seed=synthesis_seed)
        telemetry = sim.telemetry_summary()

        result = RankingPortabilityCellResult.from_run(
            **base_kwargs, telemetry=telemetry, m=m, scientific_status=scientific_status,
        )
    except Exception as e:  # noqa: BLE001 -- never let one cell crash a caller
        result = RankingPortabilityCellResult(
            **base_kwargs, success=False,
            error_category=type(e).__name__,
            error_detail="".join(traceback.format_exception_only(type(e), e)).strip()
            + " | " + traceback.format_exc(limit=3).replace("\n", " "),
            scientific_status=scientific_status,
        )
        return result

    problems = validate_cell_result(result.to_dict())
    if problems:
        result.success = False
        result.error_category = "schema_validation_failed"
        result.error_detail = "; ".join(problems)
    return result
