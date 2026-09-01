"""
Synthetic workload generators for the LLM serving simulator.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import numpy as np

from ..core.types import Request
from .distributions import (
    bursty_arrivals,
    lognormal_tokens,
    pareto_tokens,
    poisson_arrivals,
    prediction_noise,
    uniform_tokens,
)


@dataclass
class SLOClass:
    class_id: str
    slo_slack: float    # seconds added to arrival_time to get deadline
    priority: float     # higher = more important
    weight: float       # fraction of requests in this class


DEFAULT_SLO_CLASSES = [
    SLOClass("tight",  slo_slack=0.5,  priority=3.0, weight=0.2),
    SLOClass("medium", slo_slack=2.0,  priority=2.0, weight=0.5),
    SLOClass("loose",  slo_slack=10.0, priority=1.0, weight=0.3),
]


@dataclass
class WorkloadConfig:
    # Arrival process: "poisson" or "bursty"
    arrival_process: str = "poisson"
    # Mean arrival rate (requests per second)
    arrival_rate: float = 20.0
    # Simulation trace duration in seconds
    duration: float = 10.0
    # Prompt token distribution: "lognormal" or "uniform" or "pareto"
    prompt_dist: str = "lognormal"
    prompt_mean: float = 128.0
    prompt_sigma: float = 0.8
    prompt_low: int = 16
    prompt_high: int = 1024
    # Output token distribution
    output_dist: str = "lognormal"
    output_mean: float = 64.0
    output_sigma: float = 0.8
    output_low: int = 1
    output_high: int = 512
    # Prediction noise
    prediction_noise_rel: float = 0.15
    # SLO classes
    slo_classes: List[SLOClass] = field(default_factory=lambda: list(DEFAULT_SLO_CLASSES))
    # Bursty arrival params
    burst_factor: float = 5.0
    burst_fraction: float = 0.2
    # Tag for identification
    tag: str = "synthetic"


def generate_workload(
    config: WorkloadConfig,
    seed: int = 0,
) -> List[Request]:
    """Generate a list of Request objects from the given workload configuration."""
    rng = np.random.default_rng(seed)

    # --- Arrival times ---
    if config.arrival_process == "poisson":
        arrival_times = poisson_arrivals(rng, config.arrival_rate, config.duration)
    elif config.arrival_process == "bursty":
        arrival_times = bursty_arrivals(
            rng,
            config.arrival_rate,
            config.duration,
            burst_factor=config.burst_factor,
            burst_fraction=config.burst_fraction,
        )
    else:
        raise ValueError(f"Unknown arrival_process: {config.arrival_process}")

    n = len(arrival_times)
    if n == 0:
        return []

    # --- Prompt tokens ---
    if config.prompt_dist == "lognormal":
        prompt_tokens = lognormal_tokens(
            rng, n, config.prompt_mean, config.prompt_sigma,
            config.prompt_low, config.prompt_high,
        )
    elif config.prompt_dist == "uniform":
        prompt_tokens = uniform_tokens(rng, n, config.prompt_low, config.prompt_high)
    elif config.prompt_dist == "pareto":
        prompt_tokens = pareto_tokens(rng, n, config.prompt_mean, low=config.prompt_low, high=config.prompt_high)
    else:
        raise ValueError(f"Unknown prompt_dist: {config.prompt_dist}")

    # --- Output tokens ---
    if config.output_dist == "lognormal":
        output_tokens = lognormal_tokens(
            rng, n, config.output_mean, config.output_sigma,
            config.output_low, config.output_high,
        )
    elif config.output_dist == "uniform":
        output_tokens = uniform_tokens(rng, n, config.output_low, config.output_high)
    elif config.output_dist == "pareto":
        output_tokens = pareto_tokens(rng, n, config.output_mean, low=config.output_low, high=config.output_high)
    else:
        raise ValueError(f"Unknown output_dist: {config.output_dist}")

    # --- Predicted output (with noise) ---
    predicted_output = prediction_noise(rng, output_tokens, config.prediction_noise_rel)

    # --- SLO classes ---
    class_weights = np.array([c.weight for c in config.slo_classes], dtype=float)
    class_weights /= class_weights.sum()
    class_indices = rng.choice(len(config.slo_classes), size=n, p=class_weights)

    requests: List[Request] = []
    for i in range(n):
        cls = config.slo_classes[class_indices[i]]
        req = Request(
            request_id=i,
            arrival_time=float(arrival_times[i]),
            prompt_tokens=int(prompt_tokens[i]),
            predicted_output_tokens=int(predicted_output[i]),
            actual_output_tokens=int(output_tokens[i]),
            slo_deadline=float(arrival_times[i]) + cls.slo_slack,
            priority=cls.priority,
            class_id=cls.class_id,
        )
        requests.append(req)

    return requests


# ---------------------------------------------------------------------------
# Named preset generators
# ---------------------------------------------------------------------------

def make_small_debug_trace(seed: int = 42) -> List[Request]:
    """A tiny deterministic trace for unit tests and debugging.

    10 requests with known properties and predictable behavior.
    """
    cfg = WorkloadConfig(
        arrival_process="poisson",
        arrival_rate=2.0,
        duration=5.0,
        prompt_mean=20.0,
        prompt_sigma=0.3,
        output_mean=10.0,
        output_sigma=0.3,
        prediction_noise_rel=0.0,
        tag="small_debug",
    )
    return generate_workload(cfg, seed=seed)


def make_medium_trace(seed: int = 0) -> List[Request]:
    cfg = WorkloadConfig(
        arrival_process="poisson",
        arrival_rate=30.0,
        duration=30.0,
        prompt_mean=128.0,
        prompt_sigma=0.8,
        output_mean=64.0,
        output_sigma=0.8,
        prediction_noise_rel=0.15,
        tag="medium",
    )
    return generate_workload(cfg, seed=seed)


def make_heavy_tail_trace(seed: int = 0) -> List[Request]:
    cfg = WorkloadConfig(
        arrival_process="poisson",
        arrival_rate=20.0,
        duration=20.0,
        prompt_dist="pareto",
        prompt_mean=128.0,
        output_dist="pareto",
        output_mean=64.0,
        prediction_noise_rel=0.2,
        tag="heavy_tail",
    )
    return generate_workload(cfg, seed=seed)


def make_bursty_trace(seed: int = 0) -> List[Request]:
    cfg = WorkloadConfig(
        arrival_process="bursty",
        arrival_rate=20.0,
        duration=20.0,
        burst_factor=8.0,
        burst_fraction=0.15,
        tag="bursty",
    )
    return generate_workload(cfg, seed=seed)


# ---------------------------------------------------------------------------
# Phase 1.5 preset generators
# ---------------------------------------------------------------------------

def make_prefill_heavy_trace(seed: int = 0) -> List[Request]:
    """Long prompts, short outputs — stresses prefill throughput."""
    cfg = WorkloadConfig(
        arrival_process="poisson",
        arrival_rate=20.0,
        duration=20.0,
        prompt_mean=512.0,
        prompt_sigma=0.5,
        prompt_low=256,
        prompt_high=2048,
        output_mean=32.0,
        output_sigma=0.5,
        output_low=4,
        output_high=128,
        prediction_noise_rel=0.1,
        tag="prefill_heavy",
    )
    return generate_workload(cfg, seed=seed)


def make_decode_heavy_trace(seed: int = 0) -> List[Request]:
    """Short prompts, long outputs — stresses decode throughput / KV memory."""
    cfg = WorkloadConfig(
        arrival_process="poisson",
        arrival_rate=20.0,
        duration=20.0,
        prompt_mean=32.0,
        prompt_sigma=0.4,
        prompt_low=8,
        prompt_high=128,
        output_mean=512.0,
        output_sigma=0.6,
        output_low=64,
        output_high=2048,
        prediction_noise_rel=0.2,
        tag="decode_heavy",
    )
    return generate_workload(cfg, seed=seed)


def make_mixed_slo_trace(seed: int = 0) -> List[Request]:
    """Mix of tight / medium / loose SLO classes at moderate load."""
    tight   = SLOClass("tight",  slo_slack=0.3,  priority=3.0, weight=0.4)
    medium  = SLOClass("medium", slo_slack=2.0,  priority=2.0, weight=0.4)
    loose   = SLOClass("loose",  slo_slack=10.0, priority=1.0, weight=0.2)
    cfg = WorkloadConfig(
        arrival_process="poisson",
        arrival_rate=25.0,
        duration=20.0,
        prompt_mean=128.0,
        prompt_sigma=0.7,
        output_mean=96.0,
        output_sigma=0.7,
        prediction_noise_rel=0.15,
        slo_classes=[tight, medium, loose],
        tag="mixed_slo",
    )
    return generate_workload(cfg, seed=seed)


def make_burst_heavy_tail_trace(seed: int = 0) -> List[Request]:
    """Bursty arrivals with Pareto (heavy-tail) output lengths."""
    cfg = WorkloadConfig(
        arrival_process="bursty",
        arrival_rate=15.0,
        duration=30.0,
        burst_factor=10.0,
        burst_fraction=0.2,
        prompt_mean=128.0,
        prompt_sigma=0.6,
        output_dist="pareto",
        output_mean=128.0,
        output_low=8,
        output_high=2048,
        prediction_noise_rel=0.25,
        tag="burst_heavy_tail",
    )
    return generate_workload(cfg, seed=seed)


def make_overloaded_prefill_trace(seed: int = 0) -> List[Request]:
    """High arrival rate with large prompts — saturates prefill capacity."""
    cfg = WorkloadConfig(
        arrival_process="poisson",
        arrival_rate=80.0,
        duration=10.0,
        prompt_mean=256.0,
        prompt_sigma=0.8,
        prompt_low=64,
        prompt_high=1024,
        output_mean=64.0,
        output_sigma=0.8,
        output_low=8,
        output_high=256,
        prediction_noise_rel=0.1,
        tag="overloaded_prefill",
    )
    return generate_workload(cfg, seed=seed)
