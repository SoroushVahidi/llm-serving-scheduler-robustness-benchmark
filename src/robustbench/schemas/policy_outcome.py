"""Canonical policy_outcomes row schema (see docs/DATASET_V2_SCHEMA.md, table 3).

Every simulation cell (one policy x one workload_window x one load level x one
seed) must serialize to exactly this shape before it is written to results/ or
considered for the eventual Dataset v2 release. `validate_policy_outcome_row`
is intentionally strict about presence, not about the *value* being
scientifically meaningful -- that is the statistical analysis plan's job.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional

REQUIRED_IDENTITY_FIELDS = (
    "workload_window_id",
    "source_family",
    "load_level",
    "policy_id",
    "seed",
    "experiment_version",
    "code_sha",
    "config_hash",
)

REQUIRED_METRIC_FIELDS = (
    "num_completed",
    "num_dropped",
    "request_throughput",
    "token_throughput",
    "mean_latency",
    "p95_latency",
    "slo_violation_rate",
)


@dataclass
class PolicyOutcomeRow:
    workload_window_id: str
    source_family: str
    load_level: str
    policy_id: str
    seed: int
    experiment_version: str
    code_sha: str
    config_hash: str

    num_completed: int
    num_dropped: int
    request_throughput: float
    token_throughput: float
    mean_latency: float
    p95_latency: float
    slo_violation_rate: float

    mean_ttft: Optional[float] = None
    p95_ttft: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)


def validate_policy_outcome_row(row: dict) -> list[str]:
    """Returns a list of problems (empty if the row is well-formed). Never
    raises -- callers decide what is fatal for their use case."""
    problems: list[str] = []
    for f in REQUIRED_IDENTITY_FIELDS + REQUIRED_METRIC_FIELDS:
        if f not in row:
            problems.append(f"missing required field '{f}'")
    if "num_completed" in row and "num_dropped" in row:
        if not isinstance(row["num_completed"], int) or not isinstance(row["num_dropped"], int):
            problems.append("num_completed/num_dropped must be int")
        elif row["num_completed"] < 0 or row["num_dropped"] < 0:
            problems.append("num_completed/num_dropped must be non-negative")
    if "seed" in row and not isinstance(row["seed"], int):
        problems.append("seed must be int")
    return problems
