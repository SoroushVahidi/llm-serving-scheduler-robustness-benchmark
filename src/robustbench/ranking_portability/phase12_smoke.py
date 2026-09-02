"""Phase-12A Pilot-V2 engineering smoke: frozen selection contract + pure
cell-matrix construction, importable without touching real workload data.

This module intentionally contains NO scientific-outcome logic (no
statistics, no ranking, no result interpretation) -- it only defines the
frozen, outcome-blind smoke-selection contract
(docs/RANKING_PORTABILITY_PHASE12_SMOKE_FREEZE.md) and generates the
deterministic Cartesian product of cells to execute. The real execution
path lives in `scripts/ranking_portability/build_phase12_smoke.py`, which
must be run "where the real source files (or a verified extract) live"
(same convention as `build_pilot_v2_windows.py`).

`SCIENTIFIC_STATUS_ENGINEERING_SMOKE` is written into every cell's
`RankingPortabilityCellResult.scientific_status` field
(`docs/RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md` section 6's schema,
`scientific_status` field) so smoke output can never be mistaken for real
confirmatory Pilot-V2 evidence downstream.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import List, Tuple

from .calibration import REGION_SEQUENCE

SCIENTIFIC_STATUS_ENGINEERING_SMOKE = "ENGINEERING_SMOKE"

# Selection rule (frozen, outcome-blind): all 3 primary Pilot-V2 sources,
# the FIRST window per source by canonical manifest ordering (identical
# rule applied to every source -- never chosen by inspecting content or
# outcomes). All 3 selected windows happen to be STAGE0_WINDOW-class
# windows (evidence_class), which is a consequence of canonical manifest
# ordering (Stage-0-reused windows are placed first in the freeze), not a
# separate choice.
SMOKE_SOURCES: Tuple[str, ...] = ("burstgpt", "azure_llm_2024", "bailian_qwen")
SMOKE_WINDOW_IDS: dict = {
    "burstgpt": "burstgpt_stage0_w00",
    "azure_llm_2024": "azure_llm_2024_stage0_w00",
    "bailian_qwen": "bailian_qwen_stage0_w00",
}

# All 6 frozen operating regions (docs/RANKING_PORTABILITY_PHASE11_CALIBRATION_FREEZE.md).
SMOKE_REGIONS: Tuple[str, ...] = REGION_SEQUENCE

# The 13 Pilot-V2 executed policies (11 PRIMARY + 2 STYLE_APPROXIMATION
# robustness-only), per docs/RANKING_PORTABILITY_POLICY_PANEL.md.
# distserve_faithful / llumnix_faithful (secondary stratum) are explicitly
# excluded, per the smoke task's own instruction.
SMOKE_POLICIES: Tuple[str, ...] = (
    "fifo",
    "edf",
    "least_laxity_first",
    "estimated_service_time_first",
    "weighted_fair_share",
    "kv_constrained_online",
    "vllm_faithful",
    "vllm_chunked_prefill_faithful",
    "sarathi_faithful",
    "slai_faithful",
    "admission_control",
    "vllm_style_token_budget",
    "scorpio_style_slo_guard",
)

# Simulator is deterministic given identical inputs; both reps use the
# SAME synthesis seed and SAME scaled requests -- rep0/rep1 verify
# determinism, they are not an independent stochastic draw
# (docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md section F: "Seed sensitivity:
# not applicable").
SMOKE_REPETITIONS: Tuple[int, ...] = (0, 1)

EXPECTED_SMOKE_CELL_COUNT = (
    len(SMOKE_SOURCES) * len(SMOKE_REGIONS) * len(SMOKE_POLICIES) * len(SMOKE_REPETITIONS)
)


@dataclass(frozen=True)
class SmokeCellSpec:
    source_family: str
    window_id: str
    load_region: str
    policy_id: str
    repetition: int

    @property
    def cell_id(self) -> str:
        return (
            f"{self.source_family}::{self.window_id}::{self.load_region}::"
            f"{self.policy_id}::rep{self.repetition}"
        )


def generate_smoke_cell_specs() -> List[SmokeCellSpec]:
    """Deterministic Cartesian product over the frozen smoke dimensions, in
    a fixed, reproducible iteration order (source -> region -> policy ->
    repetition). Never inspects any outcome."""
    specs: List[SmokeCellSpec] = []
    for source in SMOKE_SOURCES:
        window_id = SMOKE_WINDOW_IDS[source]
        for region in SMOKE_REGIONS:
            for policy_id in SMOKE_POLICIES:
                for rep in SMOKE_REPETITIONS:
                    specs.append(
                        SmokeCellSpec(
                            source_family=source,
                            window_id=window_id,
                            load_region=region,
                            policy_id=policy_id,
                            repetition=rep,
                        )
                    )
    return specs


def synthesis_seed_for_window(window_id: str) -> int:
    """Identical rule to `scripts/ranking_portability/build_phase11_calibration.py`
    (`900000 + int(window_id.rsplit("w", 1)[1])`) -- reused verbatim so this
    smoke's synthesized requests are byte-identical to what Phase-11 already
    calibrated against for the same window, letting the smoke validation
    gate cross-check its own recomputed `lambda_ref` against the frozen
    Phase-11 region-assignment artifact as an independent integrity check."""
    return 900000 + int(window_id.rsplit("w", 1)[1])


def compute_smoke_freeze_identity(
    *,
    parent_branch_sha: str,
    phase10_window_hash: str,
    phase11_prelaunch_hash: str,
    phase11_raw_fifo_hash: str,
    phase11_region_assignment_hash: str,
    execution_file_hashes: dict,
) -> dict:
    """Aggregate SHA-256 identity for the smoke freeze contract itself,
    computed BEFORE any cell is executed. Mirrors
    `build_phase11_calibration.py::_prelaunch_freeze_record`'s pattern."""
    payload = {
        "parent_branch_sha": parent_branch_sha,
        "phase10_window_hash": phase10_window_hash,
        "phase11_prelaunch_hash": phase11_prelaunch_hash,
        "phase11_raw_fifo_hash": phase11_raw_fifo_hash,
        "phase11_region_assignment_hash": phase11_region_assignment_hash,
        "smoke_sources": list(SMOKE_SOURCES),
        "smoke_window_ids": SMOKE_WINDOW_IDS,
        "smoke_regions": list(SMOKE_REGIONS),
        "smoke_policies": list(SMOKE_POLICIES),
        "smoke_repetitions": list(SMOKE_REPETITIONS),
        "expected_smoke_cell_count": EXPECTED_SMOKE_CELL_COUNT,
        "execution_file_hashes": execution_file_hashes,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    return {"smoke_freeze_sha256": digest, **payload}


__all__ = [
    "SCIENTIFIC_STATUS_ENGINEERING_SMOKE",
    "SMOKE_SOURCES",
    "SMOKE_WINDOW_IDS",
    "SMOKE_REGIONS",
    "SMOKE_POLICIES",
    "SMOKE_REPETITIONS",
    "EXPECTED_SMOKE_CELL_COUNT",
    "SmokeCellSpec",
    "generate_smoke_cell_specs",
    "synthesis_seed_for_window",
    "compute_smoke_freeze_identity",
]
