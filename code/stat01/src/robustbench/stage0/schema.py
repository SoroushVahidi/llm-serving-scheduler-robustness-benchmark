"""Canonical Stage-0 cell result schema (section B5)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional

CELL_RESULT_SCHEMA_VERSION = "stage0_cell_result_v1"

REQUIRED_FIELDS = (
    "cell_id", "canonical_hash", "source_family", "window_id", "load_region",
    "load_factor", "policy_id", "repetition", "synthesis_seed",
    "arrival_normalized_weighted_goodput", "completion_fraction",
    "slo_violation_rate", "success", "repo_sha", "window_manifest_sha256",
    "calibration_manifest_sha256", "policy_registry_hash",
)


@dataclass
class CellResult:
    schema_version: str = CELL_RESULT_SCHEMA_VERSION

    # Identification
    cell_id: str = ""
    canonical_hash: str = ""
    source_family: str = ""
    window_id: str = ""
    load_region: str = ""
    load_factor: float = float("nan")
    policy_id: str = ""
    repetition: int = -1
    synthesis_seed: int = -1

    # Metrics (None when success=False)
    arrival_normalized_weighted_goodput: Optional[float] = None
    completion_fraction: Optional[float] = None
    slo_violation_rate: Optional[float] = None
    weighted_goodput: Optional[float] = None
    mean_latency: Optional[float] = None
    p95_latency: Optional[float] = None
    mean_ttft: Optional[float] = None
    p95_ttft: Optional[float] = None
    request_throughput: Optional[float] = None
    token_throughput: Optional[float] = None

    # Provenance
    repo_sha: str = ""
    window_manifest_sha256: str = ""
    calibration_manifest_sha256: str = ""
    policy_registry_hash: str = ""
    simulator_config_hash: str = ""
    synthesis_version: str = ""
    environment: dict = field(default_factory=dict)

    # Failure
    success: bool = False
    error_category: Optional[str] = None
    error_detail: Optional[str] = None

    # Set to "SMOKE_ONLY_DO_NOT_ANALYZE" by harness.py's `run --scientific-status`
    # for infrastructure-exercise runs (section E) -- None for a real Stage-0
    # evidence run. Never analyzed by analyzer.py as scientific evidence;
    # callers/analysts must check this field before treating any row as data.
    scientific_status: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


def validate_cell_result(d: dict) -> list[str]:
    """Returns a list of validation problems (empty = valid). Never raises."""
    problems = []
    for f in REQUIRED_FIELDS:
        if f not in d:
            problems.append(f"missing required field: {f}")
    if d.get("success") is True:
        # ALWAYS_DEFINED metrics (see docs/STAGE0_METRIC_DEFINITIONS.md's
        # "Conditional metric audit"): never NaN for a real Stage-0 window.
        for metric_field in ("arrival_normalized_weighted_goodput", "completion_fraction"):
            v = d.get(metric_field)
            if v is None:
                problems.append(f"success=True but {metric_field} is None")
            elif isinstance(v, float) and (v != v):  # NaN check without importing math
                problems.append(f"success=True but {metric_field} is NaN")

        # slo_violation_rate is CONDITIONAL_ON_COMPLETION (population =
        # completed requests only). NaN is the documented, valid
        # representation of "undefined" exactly when completion_fraction
        # == 0.0 (docs/STAGE0_ZERO_COMPLETION_METRIC_AMENDMENT_20260901.md)
        # -- it must still be finite whenever its population is non-empty.
        svr = d.get("slo_violation_rate")
        if svr is None:
            problems.append("success=True but slo_violation_rate is None")
        elif isinstance(svr, float) and (svr != svr):
            if d.get("completion_fraction") != 0.0:
                problems.append(
                    "success=True but slo_violation_rate is NaN despite "
                    "completion_fraction != 0.0"
                )
    if d.get("success") is False:
        if not d.get("error_category"):
            problems.append("success=False but error_category is empty")
    if d.get("repetition") not in (0, 1):
        problems.append(f"repetition must be 0 or 1, got {d.get('repetition')}")
    return problems
