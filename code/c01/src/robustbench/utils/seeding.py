"""Global seeding utilities for reproducibility."""
from __future__ import annotations

import random

import numpy as np


def set_global_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)


def seed_sequence(base_seed: int, n: int) -> list[int]:
    """Derive n distinct child seeds from a base seed."""
    rng = np.random.default_rng(base_seed)
    return rng.integers(0, 2**31 - 1, size=n).tolist()
