"""
Statistical distributions used in synthetic workload generation.
"""
from __future__ import annotations

import math

import numpy as np


def poisson_arrivals(
    rng: np.random.Generator,
    rate: float,
    duration: float,
) -> np.ndarray:
    """Generate Poisson arrival times in [0, duration]."""
    expected = rate * duration
    n = rng.poisson(expected)
    times = np.sort(rng.uniform(0, duration, size=n))
    return times


def bursty_arrivals(
    rng: np.random.Generator,
    mean_rate: float,
    duration: float,
    burst_factor: float = 5.0,
    burst_fraction: float = 0.2,
) -> np.ndarray:
    """Arrivals that alternate between burst and quiet periods.

    burst_fraction of the time runs at mean_rate * burst_factor;
    the rest runs at a lower rate to keep the mean equal to mean_rate.
    """
    quiet_rate = mean_rate * (1 - burst_fraction * burst_factor) / (1 - burst_fraction)
    quiet_rate = max(quiet_rate, 0.0)
    burst_rate = mean_rate * burst_factor

    times: list[float] = []
    t = 0.0
    while t < duration:
        if rng.random() < burst_fraction:
            segment_duration = rng.exponential(1.0 / mean_rate) * 5
            seg_times = t + poisson_arrivals(rng, burst_rate, segment_duration)
        else:
            segment_duration = rng.exponential(1.0 / mean_rate) * 5
            seg_times = t + poisson_arrivals(rng, quiet_rate, segment_duration)
        times.extend(seg_times[seg_times <= duration].tolist())
        t += segment_duration

    return np.sort(np.array(times))


def lognormal_tokens(
    rng: np.random.Generator,
    n: int,
    mean: float,
    sigma: float,
    low: int = 1,
    high: int = 4096,
) -> np.ndarray:
    """Log-normal integer token counts clipped to [low, high]."""
    mu = math.log(mean) - 0.5 * sigma ** 2
    samples = rng.lognormal(mean=mu, sigma=sigma, size=n)
    return np.clip(np.round(samples).astype(int), low, high)


def pareto_tokens(
    rng: np.random.Generator,
    n: int,
    scale: float,
    shape: float = 1.5,
    low: int = 1,
    high: int = 4096,
) -> np.ndarray:
    """Pareto-distributed token counts (heavy-tailed)."""
    u = rng.uniform(size=n)
    samples = scale / (u ** (1.0 / shape))
    return np.clip(np.round(samples).astype(int), low, high)


def uniform_tokens(
    rng: np.random.Generator,
    n: int,
    low: int,
    high: int,
) -> np.ndarray:
    return rng.integers(low, high + 1, size=n)


def prediction_noise(
    rng: np.random.Generator,
    actual: np.ndarray,
    relative_error: float = 0.2,
) -> np.ndarray:
    """Add multiplicative log-normal noise to simulate imperfect output prediction."""
    sigma = math.sqrt(math.log(1 + relative_error ** 2))
    noise = rng.lognormal(mean=0.0, sigma=sigma, size=len(actual))
    predicted = np.clip(np.round(actual * noise).astype(int), 1, 4096)
    return predicted
