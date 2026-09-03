"""Deterministic RQ3 campaign manifest: (family, seed) -> calibrated window,
(family, seed, region, policy) -> cell.

Calibration (FIFO-only, policy-independent, per `calibrate_window`) is
computed once per (family, seed) at manifest-build time and frozen into the
manifest, exactly like the real-source Phase-11/RQ6 calibration freezes --
so no policy-under-study result can influence load_factor selection.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List

from ..calibration.stage0_load_calibration import calibrate_window
from .synthetic_families import (
    FAMILY_IDS,
    LOAD_REGIONS,
    PRIMARY_POLICIES,
    REGION_MULTIPLIERS,
    SEEDS,
    generate_family_window,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _sha256_obj(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def _requests_content_sha256(requests) -> str:
    payload = [
        {
            "request_id": r.request_id, "arrival_time": r.arrival_time,
            "prompt_tokens": r.prompt_tokens, "predicted_output_tokens": r.predicted_output_tokens,
            "actual_output_tokens": r.actual_output_tokens, "slo_deadline": r.slo_deadline,
            "priority": r.priority, "class_id": r.class_id,
        }
        for r in requests
    ]
    return _sha256_obj(payload)


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).decode().strip()


@dataclass
class WindowUnit:
    family_id: str
    seed: int
    window_id: str
    n_requests: int
    requests_content_sha256: str
    lambda_ref: float
    load_factors: Dict[str, float]  # region -> absolute compression factor


@dataclass
class CampaignCell:
    cell_id: str
    family_id: str
    seed: int
    window_id: str
    load_region: str
    load_factor: float
    policy_id: str
    repetition: int


def build_windows(*, family_ids=FAMILY_IDS, seeds=SEEDS) -> List[WindowUnit]:
    units: List[WindowUnit] = []
    for family_id in sorted(family_ids):
        for seed in sorted(seeds):
            window_id = f"rq3_{family_id}_s{seed:02d}"
            requests = generate_family_window(family_id, seed)
            calib = calibrate_window(requests, window_id=window_id, source_family=f"synthetic_{family_id}")
            load_factors = {
                region: calib.lambda_ref * REGION_MULTIPLIERS[region] for region in LOAD_REGIONS
            }
            units.append(WindowUnit(
                family_id=family_id, seed=seed, window_id=window_id,
                n_requests=len(requests),
                requests_content_sha256=_requests_content_sha256(requests),
                lambda_ref=calib.lambda_ref, load_factors=load_factors,
            ))
    return units


def build_cells(windows: List[WindowUnit], *, policies=PRIMARY_POLICIES) -> List[CampaignCell]:
    cells: List[CampaignCell] = []
    for w in windows:
        for region in LOAD_REGIONS:
            for policy_id in sorted(policies):
                cell_id = f"{w.window_id}__{region}__{policy_id}"
                cells.append(CampaignCell(
                    cell_id=cell_id, family_id=w.family_id, seed=w.seed, window_id=w.window_id,
                    load_region=region, load_factor=w.load_factors[region],
                    policy_id=policy_id, repetition=0,
                ))
    return cells


def build_manifest(*, family_ids=FAMILY_IDS, seeds=SEEDS, policies=PRIMARY_POLICIES) -> Dict[str, Any]:
    windows = build_windows(family_ids=family_ids, seeds=seeds)
    cells = build_cells(windows, policies=policies)
    manifest = {
        "manifest_kind": "rq3_synthetic_to_real_campaign_manifest_v1",
        "code_sha": _git_sha(),
        "n_families": len(family_ids),
        "n_seeds_per_family": len(seeds),
        "n_regions": len(LOAD_REGIONS),
        "n_policies": len(policies),
        "n_windows": len(windows),
        "n_cells": len(cells),
        "family_ids": sorted(family_ids),
        "seeds": sorted(seeds),
        "load_regions": list(LOAD_REGIONS),
        "policies": sorted(policies),
        "windows": [asdict(w) for w in sorted(windows, key=lambda w: (w.family_id, w.seed))],
        "cells": [asdict(c) for c in sorted(cells, key=lambda c: c.cell_id)],
    }
    manifest["campaign_manifest_sha256"] = _sha256_obj({
        k: v for k, v in manifest.items() if k != "campaign_manifest_sha256"
    })
    return manifest
