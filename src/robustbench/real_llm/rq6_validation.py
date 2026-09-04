"""RQ6 real-vLLM scientific validation: task-matrix enumeration, calibrated
load lookup, and the arrival-normalized-weighted-goodput (ANWG) metric for
the real-system collection layer.

`RQ6_REAL_VLLM_SCIENTIFIC_VALIDATION = NOT_STARTED` as of this module's
authorship -- this is prefreeze infrastructure, not evidence.

Reuses, rather than duplicates:
- `rq6_calibration.replay_window_once` for the actual dispatch/timing/outcome
  collection (identical sequential wait-for-all-responses replay design,
  identical episode-reset contract) -- this module adds only what calibration
  did not need: a second metric computed from the same outcomes
  (arrival-normalized-weighted-goodput, not calibration's completion-
  normalized slo_violation_rate), and policy/scheduler selection (calibration
  is always `vllm_faithful`; validation is `slai_faithful` XOR
  `vllm_faithful`).
- `rq6_slo_metrics.RequestOutcome`/`scale_request_timing`/
  `real_slo_violation_rate` unchanged.
- `calibration_common.build_exact_length_prompt` unchanged.

Task matrix (frozen, docs/RQ6_REAL_VLLM_SCIENTIFIC_PROTOCOL_20260902.md
"Calibration population" + "Statistics" sections, and
artifacts/manifests/phase12_rq6_case_selection_20260902.json): 2 policies x
3 sources x 40 windows/source = 240 cells, region fixed at HIGH_PRESSURE
(the only region named by the frozen case selection), one real execution per
cell -- uncertainty quantification is the window-level block-bootstrap over
the 40 windows/source (mirroring Phase-12's own methodology), not repeated
stochastic replicates of one cell. See
docs/RQ6_REAL_VLLM_VALIDATION_PREFREEZE_20260903.md's protocol reconciliation
for the final RQ6-specific replicate decision: one real execution per cell,
uncertainty via window-level bootstrap over the 40-window population. This
decision is RQ6-specific and was frozen before any RQ6 real-system outcomes
exist.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

from .rq6_calibration import WindowRequestReplayResult
from .rq6_slo_metrics import RequestOutcome

# Sorted so "slai_faithful" < "vllm_faithful" -- fixes enumeration order.
POLICIES: Tuple[str, str] = ("slai_faithful", "vllm_faithful")

SLAI_SCHEDULER_CLS = "robustbench.real_llm.slai_plugin.slai_vllm_scheduler.LSSPSlaiVLLMScheduler"

#: Frozen operating region for RQ6 (the only region named by the frozen case
#: selection manifest). Not a free parameter of this module.
RQ6_REGION = "HIGH_PRESSURE"

#: Frozen sources, matching the case-selection manifest's reversal_case
#: (azure_llm_2024 vs burstgpt) and stable_control (azure_llm_2024 vs
#: bailian_qwen) -- azure_llm_2024 appears in both, so all three sources are
#: required to run every frozen comparison.
RQ6_SOURCES: Tuple[str, str, str] = ("azure_llm_2024", "bailian_qwen", "burstgpt")


@dataclass(frozen=True)
class ValidationCell:
    """One (policy, source, window_id) unit of the frozen 240-cell task
    matrix. `array_index` is this cell's position in the deterministic
    enumeration (`enumerate_validation_cells`), i.e. the Slurm array task id
    that must produce this exact cell."""

    array_index: int
    policy: str
    source: str
    window_id: str
    workload_manifest_path: Path


def enumerate_validation_cells(manifest_dir: Path) -> List[ValidationCell]:
    """Deterministic (source, window_id, policy) enumeration across the three
    workload manifests, crossed with `POLICIES`. Mirrors
    `rq6_calibration.enumerate_calibration_units`'s sort-based determinism
    guarantee: re-running this against unchanged manifests always reproduces
    the same array_index -> cell mapping. 3 sources x 40 windows x 2 policies
    = 240 cells."""
    window_units: List[Tuple[str, str, Path]] = []
    for path in sorted(manifest_dir.glob("rq6_workload_*.json")):
        with open(path) as f:
            manifest = json.load(f)
        for w in manifest["windows"]:
            window_units.append((manifest["source"], w["window_id"], path))
    window_units.sort(key=lambda u: (u[0], u[1]))

    cells: List[ValidationCell] = []
    index = 0
    for source, window_id, path in window_units:
        for policy in sorted(POLICIES):
            cells.append(ValidationCell(
                array_index=index, policy=policy, source=source,
                window_id=window_id, workload_manifest_path=path,
            ))
            index += 1
    return cells


def load_window_requests(manifest_path: Path, window_id: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
    with open(manifest_path) as f:
        manifest = json.load(f)
    for w in manifest["windows"]:
        if w["window_id"] == window_id:
            return w["requests"], manifest, w
    raise KeyError(f"window_id {window_id!r} not found in {manifest_path}")


class CalibrationLookupError(RuntimeError):
    """Raised when a validation cell's required calibration output is
    missing, unreadable, or fails a provenance check. A scientific
    validation run must never silently substitute an assumed or default
    load factor for a real calibration measurement."""


#: Every terminal status the frozen calibration bisection
#: (`rq6_calibration.bisect_lambda_ref_real`) can produce is a valid,
#: scientifically usable outcome -- see
#: docs/RQ6_REAL_VLLM_VALIDATION_PREFREEZE_20260903.md
#: "CALIBRATION_TERMINAL_STATUS_CONTRACT" for the full derivation from the
#: bisection code itself. All three set `derived_high_pressure` to a
#: well-defined finite value; none requires special-case handling by callers.
VALID_CALIBRATION_TERMINAL_STATUSES = frozenset({
    "CONVERGED",
    "LOWER_BOUND_ALREADY_VIOLATING",
    "UPPER_BOUND_NEVER_VIOLATING",
})

REQUIRED_CALIBRATION_OUTPUT_KEYS = frozenset({
    "source", "window_id", "reference_policy", "real_lambda_ref",
    "derived_high_pressure", "convergence_status", "window_content_sha256",
    "calibration_manifest_sha256", "repo_sha",
})


def load_calibrated_scale(
    calibration_dir: Path, source: str, window_id: str, *,
    expected_calibration_manifest_sha256: str,
    expected_window_content_sha256: str,
) -> Dict[str, Any]:
    """Loads the one calibration output this validation cell depends on
    (`<calibration_dir>/<source>/<window_id>.json`), verifies it is schema-
    complete, matches the frozen calibration manifest hash and this window's
    own frozen content hash, and has a valid terminal status. Returns the
    parsed calibration record on success. Raises `CalibrationLookupError`
    on any failure -- there is no fallback numeric value."""
    path = calibration_dir / source / f"{window_id}.json"
    if not path.exists():
        raise CalibrationLookupError(f"missing calibration output: {path}")
    with open(path) as f:
        record = json.load(f)

    missing_keys = REQUIRED_CALIBRATION_OUTPUT_KEYS - record.keys()
    if missing_keys:
        raise CalibrationLookupError(f"{path}: missing required keys {sorted(missing_keys)}")

    if record["calibration_manifest_sha256"] != expected_calibration_manifest_sha256:
        raise CalibrationLookupError(
            f"{path}: calibration_manifest_sha256 mismatch "
            f"(expected {expected_calibration_manifest_sha256}, got {record['calibration_manifest_sha256']})"
        )
    if record["window_content_sha256"] != expected_window_content_sha256:
        raise CalibrationLookupError(
            f"{path}: window_content_sha256 mismatch "
            f"(expected {expected_window_content_sha256}, got {record['window_content_sha256']})"
        )
    if record["source"] != source or record["window_id"] != window_id:
        raise CalibrationLookupError(f"{path}: source/window_id label mismatch with lookup key")
    if record["reference_policy"] != "vllm_faithful":
        raise CalibrationLookupError(f"{path}: reference_policy must be vllm_faithful, got {record['reference_policy']!r}")
    if record["convergence_status"] not in VALID_CALIBRATION_TERMINAL_STATUSES:
        raise CalibrationLookupError(
            f"{path}: unrecognized convergence_status {record['convergence_status']!r} "
            f"(valid: {sorted(VALID_CALIBRATION_TERMINAL_STATUSES)})"
        )
    scale = record["derived_high_pressure"]
    if not (isinstance(scale, (int, float)) and scale > 0):
        raise CalibrationLookupError(f"{path}: derived_high_pressure must be a positive number, got {scale!r}")
    return record


def real_arrival_normalized_weighted_goodput(outcomes: Sequence[RequestOutcome]) -> float:
    """Real-system analogue of `robustbench.core.metrics`'s frozen
    `arrival_normalized_weighted_goodput` definition
    (`success_weight / arrival_weight`, docs/STAGE0_METRIC_DEFINITIONS.md):

        sum(weight_i for i in COMPLETED if t_done_i <= slo_deadline_i)
        / sum(weight_i for i in ALL requests dispatched this window)

    `outcomes` must be exactly `WindowRequestReplayResult.outcomes` (or
    equivalent): one entry per dispatched request regardless of completion,
    by construction of `rq6_calibration.replay_window_once` -- so the
    arrival-weight denominator is simply the sum over `outcomes`, never a
    separately-supplied population. Unlike `rq6_slo_metrics.
    real_slo_violation_rate` (completion-normalized: denominator =
    completed-only), this is arrival-normalized (denominator = all arrivals),
    matching the frozen `arrival_normalized_weighted_goodput` name exactly --
    the two metrics are intentionally different normalizations, not
    duplicates of each other.
    """
    arrival_weight = sum(o.weight for o in outcomes)
    if arrival_weight <= 0:
        return float("nan")
    success_weight = sum(
        o.weight for o in outcomes if o.t_done_s is not None and o.t_done_s <= o.slo_deadline_s
    )
    return success_weight / arrival_weight


@dataclass
class WindowValidationResult:
    policy: str
    source: str
    window_id: str
    candidate_scale: float
    arrival_normalized_weighted_goodput: float
    slo_violation_rate: float
    n_completed: int
    n_total: int


def summarize_replay(
    policy: str, source: str, window_id: str, candidate_scale: float,
    replay: WindowRequestReplayResult,
) -> WindowValidationResult:
    return WindowValidationResult(
        policy=policy, source=source, window_id=window_id, candidate_scale=candidate_scale,
        arrival_normalized_weighted_goodput=real_arrival_normalized_weighted_goodput(replay.outcomes),
        slo_violation_rate=replay.slo_violation_rate,
        n_completed=replay.n_completed, n_total=replay.n_total,
    )
