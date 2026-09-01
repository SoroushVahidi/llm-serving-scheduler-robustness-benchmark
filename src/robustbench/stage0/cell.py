"""Canonical Stage-0 cell identity and grid expansion.

A "cell" is one (source, window, load_region, policy, repetition)
combination in the frozen 1,080-cell Stage-0 pilot
(docs/STAGE0_DISCRIMINABILITY_PROTOCOL.md). This module defines the
canonical, deterministic identity for a cell and expands the full grid
from the frozen windows/calibration/policy manifests -- it does not run
anything.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import List

#: Frozen per docs/STAGE0_DISCRIMINABILITY_PROTOCOL.md -- six representative
#: policies spanning the fidelity taxonomy. Order is significant only for
#: display; cell identity does not depend on order.
STAGE0_POLICIES: tuple[str, ...] = (
    "fifo",
    "edf",
    "kv_constrained_online",
    "vllm_faithful",
    "sarathi_faithful",
    "vllm_style_token_budget",
)

#: Policy fidelity taxonomy, per docs/POLICY_COMPARABILITY_AUDIT.md as cited
#: in the frozen protocol -- used by Part B10's high-fidelity subset (STYLE_APPROXIMATION excluded).
STAGE0_POLICY_FIDELITY: dict[str, str] = {
    "fifo": "REPOSITORY_NATIVE_CLASSICAL",
    "edf": "REPOSITORY_NATIVE_CLASSICAL",
    "kv_constrained_online": "SIMULATOR_PROXY",
    "vllm_faithful": "FAITHFUL_EXTERNAL",
    "sarathi_faithful": "FAITHFUL_EXTERNAL",
    "vllm_style_token_budget": "STYLE_APPROXIMATION",
}

STAGE0_LOAD_REGIONS: tuple[str, ...] = ("PRE_KNEE", "KNEE", "OVERLOAD")

#: Verification repetitions only (not statistically independent samples) --
#: docs/STAGE0_DISCRIMINABILITY_PROTOCOL.md: "solely to verify deterministic
#: rerun behavior... mirroring test_deterministic_rerun". Both repetitions
#: use IDENTICAL inputs/seed; the harness asserts their outputs match.
STAGE0_N_REPETITIONS = 2

STAGE0_PRIMARY_METRIC = "arrival_normalized_weighted_goodput"


@dataclass(frozen=True)
class CellSpec:
    source_family: str
    window_id: str
    load_region: str
    load_factor: float
    policy_id: str
    repetition: int
    synthesis_seed: int
    scenario_config_hash: str

    @property
    def cell_id(self) -> str:
        return f"{self.source_family}::{self.window_id}::{self.load_region}::{self.policy_id}::rep{self.repetition}"

    def canonical_hash(self) -> str:
        """Deterministic hash of every field that determines this cell's
        expected output -- used to detect duplicate/conflicting cell specs."""
        payload = json.dumps(asdict(self), sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()

    def to_dict(self) -> dict:
        d = asdict(self)
        d["cell_id"] = self.cell_id
        d["canonical_hash"] = self.canonical_hash()
        return d


def expand_cell_grid(
    windows_manifest: dict,
    calibration_manifest: dict,
    *,
    policies: tuple[str, ...] = STAGE0_POLICIES,
    load_regions: tuple[str, ...] = STAGE0_LOAD_REGIONS,
    n_repetitions: int = STAGE0_N_REPETITIONS,
    synthesis_seed_base: int = 900_000,
) -> List[CellSpec]:
    """Expands the full canonical Stage-0 cell grid from the frozen windows
    manifest (artifacts/manifests/stage0_windows.json) and load-calibration
    manifest (artifacts/manifests/stage0_load_calibration.json). Raises if
    any window is missing a calibration entry, or if the resulting grid
    does not contain exactly
    n_windows * len(load_regions) * len(policies) * n_repetitions cells."""
    cal_by_window = {c["window_id"]: c for c in calibration_manifest["calibrations"]}
    windows = windows_manifest["windows"]

    cells: List[CellSpec] = []
    seen_hashes: set[str] = set()
    for window_index, w in enumerate(windows):
        window_id = w["window_id"]
        if window_id not in cal_by_window:
            raise ValueError(f"window {window_id!r} has no load-calibration entry -- cannot expand grid")
        cal = cal_by_window[window_id]
        synthesis_seed = synthesis_seed_base + window_index
        for load_region in load_regions:
            load_factor = cal["load_regions"][load_region]
            for policy_id in policies:
                for rep in range(n_repetitions):
                    spec = CellSpec(
                        source_family=w["source_family"],
                        window_id=window_id,
                        load_region=load_region,
                        load_factor=load_factor,
                        policy_id=policy_id,
                        repetition=rep,
                        synthesis_seed=synthesis_seed,
                        scenario_config_hash=hashlib.sha256(
                            json.dumps({"window_id": window_id, "load_region": load_region,
                                        "load_factor": load_factor}, sort_keys=True).encode()
                        ).hexdigest()[:16],
                    )
                    h = spec.canonical_hash()
                    if h in seen_hashes:
                        raise ValueError(f"duplicate canonical cell hash for {spec.cell_id}")
                    seen_hashes.add(h)
                    cells.append(spec)

    expected = len(windows) * len(load_regions) * len(policies) * n_repetitions
    if len(cells) != expected:
        raise ValueError(f"expanded {len(cells)} cells, expected {expected}")
    return cells
