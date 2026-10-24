"""
Compare multiple policies on the same set of traces across multiple seeds.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from ..core.metrics import RunMetrics
from ..core.types import GPUConfig, Request
from ..policies.base import BasePolicy
from ..simulator.service_model import ServiceModel
from ..workloads.synthetic import WorkloadConfig, generate_workload
from .run_policy import run_policy


def compare_policies(
    policies: List[BasePolicy],
    requests_per_seed: Dict[int, List[Request]],
    gpu_configs: List[GPUConfig],
    service_model: Optional[ServiceModel] = None,
    workload_tag: str = "comparison",
    drain_steps: int = 50_000,
    verbose: bool = False,
) -> List[RunMetrics]:
    """Run all policies on all seeds and collect metrics.

    Parameters
    ----------
    policies : list of BasePolicy
    requests_per_seed : dict mapping seed -> trace
    gpu_configs : GPU configuration (shared across all runs)
    service_model : optional
    workload_tag : str
    drain_steps : int
    verbose : bool

    Returns
    -------
    List of RunMetrics, one per (policy, seed) pair.
    """
    results: List[RunMetrics] = []

    for seed, requests in requests_per_seed.items():
        for policy in policies:
            if verbose:
                print(f"  Running {policy.name} | seed={seed} | n_req={len(requests)}")
            m = run_policy(
                policy=policy,
                requests=requests,
                gpu_configs=gpu_configs,
                service_model=service_model,
                workload_tag=workload_tag,
                seed=seed,
                drain_steps=drain_steps,
            )
            results.append(m)

    return results


def generate_traces_for_seeds(
    config: WorkloadConfig,
    seeds: List[int],
) -> Dict[int, List[Request]]:
    """Generate one trace per seed using the same config."""
    return {
        seed: generate_workload(config, seed=seed)
        for seed in seeds
    }
