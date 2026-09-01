"""Canonical ranking-portability-pilot cell result schema.

Standalone from `robustbench.stage0.schema` (Stage-0's schema is completely
unchanged by this module -- historical Stage-0 cells have no `telemetry`
block and remain valid under `stage0.schema.validate_cell_result`, which
this module never touches). This is a NEW schema for a NEW, not-yet-
launched pilot (docs/RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md); telemetry
is REQUIRED here, unlike anything in Stage-0's cell format.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Optional

from ..simulator.telemetry import TelemetrySummary, validate_telemetry

CELL_SCHEMA_VERSION = "ranking_portability_cell_result_v1"

# ALWAYS_DEFINED per docs/RANKING_PORTABILITY_METRIC_DEFINITIONS.md --
# required non-NaN whenever success=True.
ALWAYS_DEFINED_METRIC_FIELDS = (
    "arrival_normalized_weighted_goodput",
    "completion_fraction",
    "weighted_completion_fraction",
)

# CONDITIONAL_ON_COMPLETION / CONDITIONAL_ON_OTHER_PRECONDITION per the same
# doc -- NaN is schema-valid only when its documented precondition fails,
# and the caller must record which precondition applies per field (there is
# no single shared "completion_fraction == 0.0" rule the way Stage-0 had
# only one such field; see `docs/RANKING_PORTABILITY_METRIC_DEFINITIONS.md`).
CONDITIONAL_ON_COMPLETION_FIELDS = (
    "slo_violation_rate",
    "weighted_goodput",
    "mean_latency",
    "p95_latency",
    "request_throughput",
    "token_throughput",
)
CONDITIONAL_ON_OTHER_PRECONDITION_FIELDS = ("mean_ttft", "p95_ttft")

REQUIRED_TOP_LEVEL_FIELDS = (
    "cell_id", "source_family", "window_id", "load_region", "load_factor",
    "policy_id", "repetition", "synthesis_seed", "success", "repo_sha",
    "telemetry_schema_version", "telemetry",
) + ALWAYS_DEFINED_METRIC_FIELDS


@dataclass
class RankingPortabilityCellResult:
    schema_version: str = CELL_SCHEMA_VERSION

    cell_id: str = ""
    source_family: str = ""
    window_id: str = ""
    load_region: str = ""
    load_factor: float = float("nan")
    policy_id: str = ""
    repetition: int = -1
    synthesis_seed: int = -1

    arrival_normalized_weighted_goodput: Optional[float] = None
    completion_fraction: Optional[float] = None
    weighted_completion_fraction: Optional[float] = None
    slo_violation_rate: Optional[float] = None
    weighted_goodput: Optional[float] = None
    mean_latency: Optional[float] = None
    p95_latency: Optional[float] = None
    mean_ttft: Optional[float] = None
    p95_ttft: Optional[float] = None
    request_throughput: Optional[float] = None
    token_throughput: Optional[float] = None

    # REQUIRED for every Pilot-V2 cell (unlike Stage-0, which has no such
    # field at all) -- docs/RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md section 8.
    telemetry_schema_version: str = ""
    telemetry: dict = field(default_factory=dict)

    # Provenance
    repo_sha: str = ""
    window_manifest_sha256: str = ""
    calibration_manifest_sha256: str = ""
    policy_registry_hash: str = ""
    simulator_config_hash: str = ""
    synthesis_version: str = ""
    environment: dict = field(default_factory=dict)

    success: bool = False
    error_category: Optional[str] = None
    error_detail: Optional[str] = None

    # Distinguishes capability/fixture runs from real pilot evidence -- same
    # convention and same enforcement discipline as Stage-0's field.
    scientific_status: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_run(
        *,
        cell_id: str, source_family: str, window_id: str, load_region: str,
        load_factor: float, policy_id: str, repetition: int, synthesis_seed: int,
        repo_sha: str, telemetry: TelemetrySummary, m,
        scientific_status: Optional[str] = None,
    ) -> "RankingPortabilityCellResult":
        """Build from a completed `RunMetrics` (`m`) plus a `TelemetrySummary`
        -- never computes anything itself, purely a field-mapping
        constructor (mirrors `stage0.runner.execute_cell`'s field-copy
        pattern)."""
        return RankingPortabilityCellResult(
            cell_id=cell_id, source_family=source_family, window_id=window_id,
            load_region=load_region, load_factor=load_factor, policy_id=policy_id,
            repetition=repetition, synthesis_seed=synthesis_seed,
            arrival_normalized_weighted_goodput=m.arrival_normalized_weighted_goodput,
            completion_fraction=m.completion_fraction,
            weighted_completion_fraction=m.weighted_completion_fraction,
            slo_violation_rate=m.slo_violation_rate,
            weighted_goodput=m.weighted_goodput,
            mean_latency=m.mean_latency, p95_latency=m.p95_latency,
            mean_ttft=m.mean_ttft, p95_ttft=m.p95_ttft,
            request_throughput=m.request_throughput, token_throughput=m.token_throughput,
            telemetry_schema_version=telemetry.schema_version,
            telemetry=telemetry.to_dict(),
            repo_sha=repo_sha,
            success=True,
            scientific_status=scientific_status,
        )


def _is_nan(v) -> bool:
    return isinstance(v, float) and v != v


def validate_cell_result(d: dict) -> list[str]:
    """Returns a list of validation problems (empty = valid). Never raises.
    Mirrors `robustbench.stage0.schema.validate_cell_result`'s structure
    but is an independent function -- Stage-0's validator is untouched."""
    problems: list[str] = []
    for f in REQUIRED_TOP_LEVEL_FIELDS:
        if f not in d:
            problems.append(f"missing required field: {f}")

    if d.get("repetition") not in (0, 1):
        problems.append(f"repetition must be 0 or 1, got {d.get('repetition')}")

    if d.get("success") is True:
        for f in ALWAYS_DEFINED_METRIC_FIELDS:
            v = d.get(f)
            if v is None:
                problems.append(f"success=True but {f} is None")
            elif _is_nan(v):
                problems.append(f"success=True but {f} is NaN (ALWAYS_DEFINED)")

        completion_fraction = d.get("completion_fraction")
        for f in CONDITIONAL_ON_COMPLETION_FIELDS:
            v = d.get(f)
            if v is None:
                problems.append(f"success=True but {f} is None")
            elif _is_nan(v) and completion_fraction != 0.0:
                problems.append(
                    f"success=True but {f} is NaN despite completion_fraction != 0.0"
                )
        # mean_ttft/p95_ttft: CONDITIONAL_ON_OTHER_PRECONDITION (no completed
        # request recorded a first-token time) -- unchecked here, same
        # precedent as Stage-0's schema, which never validated latency/TTFT
        # fields either (docs/RANKING_PORTABILITY_METRIC_DEFINITIONS.md:
        # NaN/None is always valid for these, independent of
        # completion_fraction).

        # Telemetry is REQUIRED for every successful Pilot-V2 cell -- this
        # is the one hard requirement Stage-0 never had.
        telemetry = d.get("telemetry")
        if not isinstance(telemetry, dict) or not telemetry:
            problems.append("success=True but telemetry block is missing/empty")
        else:
            t_version = d.get("telemetry_schema_version")
            if not t_version:
                problems.append("success=True but telemetry_schema_version is empty")
            try:
                t = TelemetrySummary(**telemetry)
            except TypeError as e:
                problems.append(f"telemetry block does not match TelemetrySummary: {e}")
            else:
                problems.extend(f"telemetry.{p}" for p in validate_telemetry(t))

    if d.get("success") is False:
        if not d.get("error_category"):
            problems.append("success=False but error_category is empty")

    return problems
