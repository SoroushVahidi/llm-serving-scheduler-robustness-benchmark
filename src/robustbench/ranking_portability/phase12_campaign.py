"""Phase-12B Pilot-V2 scientific-campaign matrix contract: frozen,
deterministic Cartesian-product construction over the canonical 120-window
Phase-10 freeze. No scientific-outcome logic lives here -- this module only
defines the frozen dimensions and generates the cell-identity matrix. The
matrix is NOT executed by anything in this module; execution is Phase-12C's
job, gated on this freeze (`docs/RANKING_PORTABILITY_PHASE12_CAMPAIGN_PRELAUNCH_FREEZE.md`).

`SCIENTIFIC_STATUS_PILOT_V2_SCIENTIFIC` is the status every real campaign
cell must carry -- never `ENGINEERING_SMOKE`
(`robustbench.ranking_portability.phase12_smoke`) and never left unset, so
downstream analysis can never accidentally mix smoke and scientific
evidence.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .calibration import REGION_SEQUENCE
from .phase12_smoke import SMOKE_POLICIES, synthesis_seed_for_window

SCIENTIFIC_STATUS_PILOT_V2_SCIENTIFIC = "PILOT_V2_SCIENTIFIC"

CAMPAIGN_SOURCES: Tuple[str, ...] = ("burstgpt", "azure_llm_2024", "bailian_qwen")
CAMPAIGN_REGIONS: Tuple[str, ...] = REGION_SEQUENCE
# Identical 13-policy panel and order as the Phase-12A smoke -- imported,
# never redefined, so the campaign panel cannot silently drift from what
# the smoke already exercised.
CAMPAIGN_POLICIES: Tuple[str, ...] = SMOKE_POLICIES
CAMPAIGN_REPETITIONS: Tuple[int, ...] = (0, 1)
WINDOWS_PER_SOURCE = 40

EXPECTED_CAMPAIGN_CELL_COUNT = (
    len(CAMPAIGN_SOURCES) * WINDOWS_PER_SOURCE * len(CAMPAIGN_REGIONS)
    * len(CAMPAIGN_POLICIES) * len(CAMPAIGN_REPETITIONS)
)
EXPECTED_ASSIGNMENT_KEY_COUNT = len(CAMPAIGN_SOURCES) * WINDOWS_PER_SOURCE * len(CAMPAIGN_REGIONS)
CELLS_PER_ASSIGNMENT_KEY = len(CAMPAIGN_POLICIES) * len(CAMPAIGN_REPETITIONS)


@dataclass(frozen=True)
class CampaignCellSpec:
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


def load_campaign_window_ids(compact_index: dict) -> Dict[str, List[str]]:
    """Extracts the exact, canonical-order, per-source window-ID lists from
    the frozen compact index (`ranking_portability_pilot_v2_windows_index.json`,
    already loaded as `compact_index`). Never resamples, filters, or
    reorders -- this IS the frozen Phase-10 window identity, verbatim.
    Raises if any source does not have exactly 40 windows (a structural
    precondition of the preregistered Design-B matrix, not something this
    function silently tolerates a mismatch on)."""
    by_source: Dict[str, List[str]] = {s: [] for s in CAMPAIGN_SOURCES}
    for w in compact_index["windows"]:
        source = w["source_family"]
        if source in by_source:
            by_source[source].append(w["window_id"])
    for source in CAMPAIGN_SOURCES:
        n = len(by_source[source])
        if n != WINDOWS_PER_SOURCE:
            raise ValueError(
                f"Source {source!r} has {n} frozen windows in the compact index, "
                f"expected exactly {WINDOWS_PER_SOURCE}."
            )
    return by_source


def generate_campaign_cell_specs(window_ids_by_source: Dict[str, List[str]]) -> List[CampaignCellSpec]:
    """Deterministic Cartesian product, fixed iteration order (source ->
    window [canonical order] -> region -> policy -> repetition). Never
    inspects any outcome, descriptor, or content beyond the window ID
    itself."""
    specs: List[CampaignCellSpec] = []
    for source in CAMPAIGN_SOURCES:
        for window_id in window_ids_by_source[source]:
            for region in CAMPAIGN_REGIONS:
                for policy_id in CAMPAIGN_POLICIES:
                    for rep in CAMPAIGN_REPETITIONS:
                        specs.append(
                            CampaignCellSpec(
                                source_family=source, window_id=window_id,
                                load_region=region, policy_id=policy_id, repetition=rep,
                            )
                        )
    return specs


def compute_campaign_freeze_identity(
    *,
    parent_smoke_branch_sha: str,
    telemetry_amendment_sha256: str,
    phase10_window_hash: str,
    phase11_prelaunch_hash: str,
    phase11_raw_fifo_hash: str,
    phase11_region_assignment_hash: str,
    window_ids_by_source: Dict[str, List[str]],
    execution_file_hashes: dict,
    full_matrix_hash: str,
) -> dict:
    """Aggregate SHA-256 identity for the campaign freeze contract itself,
    computed BEFORE any campaign cell is executed. Mirrors
    `phase12_smoke.compute_smoke_freeze_identity`'s pattern, extended with
    the telemetry-amendment identity and the full-matrix content hash."""
    payload = {
        "parent_smoke_branch_sha": parent_smoke_branch_sha,
        "telemetry_amendment_sha256": telemetry_amendment_sha256,
        "phase10_window_hash": phase10_window_hash,
        "phase11_prelaunch_hash": phase11_prelaunch_hash,
        "phase11_raw_fifo_hash": phase11_raw_fifo_hash,
        "phase11_region_assignment_hash": phase11_region_assignment_hash,
        "campaign_sources": list(CAMPAIGN_SOURCES),
        "campaign_window_ids_by_source": {s: list(ws) for s, ws in sorted(window_ids_by_source.items())},
        "campaign_regions": list(CAMPAIGN_REGIONS),
        "campaign_policies": list(CAMPAIGN_POLICIES),
        "campaign_repetitions": list(CAMPAIGN_REPETITIONS),
        "expected_campaign_cell_count": EXPECTED_CAMPAIGN_CELL_COUNT,
        "execution_file_hashes": execution_file_hashes,
        "full_matrix_hash": full_matrix_hash,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    return {"campaign_freeze_sha256": digest, **payload}


__all__ = [
    "SCIENTIFIC_STATUS_PILOT_V2_SCIENTIFIC",
    "CAMPAIGN_SOURCES",
    "CAMPAIGN_REGIONS",
    "CAMPAIGN_POLICIES",
    "CAMPAIGN_REPETITIONS",
    "WINDOWS_PER_SOURCE",
    "EXPECTED_CAMPAIGN_CELL_COUNT",
    "EXPECTED_ASSIGNMENT_KEY_COUNT",
    "CELLS_PER_ASSIGNMENT_KEY",
    "CampaignCellSpec",
    "load_campaign_window_ids",
    "generate_campaign_cell_specs",
    "compute_campaign_freeze_identity",
    "synthesis_seed_for_window",
]
