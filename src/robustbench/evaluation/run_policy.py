"""
Run a single policy on a single trace and return metrics.
"""
from __future__ import annotations

from typing import List, Optional, Sequence

from ..core.metrics import RunMetrics
from ..core.types import GPUConfig, Request
from ..policies.base import BasePolicy
from ..simulator.service_model import ServiceModel
from ..simulator.simulator import Simulator, SimulatorConfig


def run_policy(
    policy: BasePolicy,
    requests: Sequence[Request],
    gpu_configs: List[GPUConfig],
    service_model: Optional[ServiceModel] = None,
    workload_tag: str = "unknown",
    seed: int = 0,
    drain_steps: int = 50_000,
) -> RunMetrics:
    """Run one policy on one trace and return metrics.

    Parameters
    ----------
    policy : BasePolicy
    requests : list of Request
        Trace sorted by arrival_time (or will be sorted internally).
    gpu_configs : list of GPUConfig
    service_model : optional ServiceModel
    workload_tag : str
        Label for this workload in output tables.
    seed : int
        Seed used to generate the trace (recorded in metrics, not re-applied here).
    drain_steps : int
        Steps to continue after last arrival to drain active batches.
    """
    if service_model is None:
        service_model = ServiceModel()

    sim_cfg = SimulatorConfig(
        gpu_configs=gpu_configs,
        service_model=service_model,
        drain_steps=drain_steps,
    )
    sim = Simulator(sim_cfg)
    sim.load_trace(list(requests))
    policy.reset()
    return sim.run(policy, workload_tag=workload_tag, seed=seed)
