#!/usr/bin/env python3
"""POST_PHASE12_SLO_DEFINITION_SENSITIVITY_EXTENSION: builds the
deterministic cell manifest for the SLO-sensitivity campaign, per
docs/SLO_DEFINITION_SENSITIVITY_PROTOCOL_20260903.md and
configs/analysis/slo_sensitivity_20260903.json.

One cell = (slo_variant, source_family, window_id, load_region, policy_id).
No repetition column: the simulator is deterministic given identical
Requests, and each window's frozen synthesis_seed is reused unchanged
across variants (only the SLO rule differs).

Writes a manifest JSON with a stable, hashed cell list. Never executes a
cell, never synthesizes a Request, never constructs a Simulator -- pure
enumeration, exactly mirroring
scripts/ranking_portability/build_phase12_campaign_freeze.py's posture at
the manifest-build stage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.analysis.slo_variant import SLO_VARIANT_MULTIPLIERS  # noqa: E402
from robustbench.ranking_portability.analysis.contract import PRIMARY_POLICIES  # noqa: E402

DEFAULT_CAMPAIGN_FREEZE = REPO_ROOT / "artifacts/manifests/ranking_portability_phase12_campaign_freeze.json"
DEFAULT_CONTRACT = REPO_ROOT / "configs/analysis/slo_sensitivity_20260903.json"
DEFAULT_OUTPUT = REPO_ROOT / "artifacts/manifests/slo_sensitivity_campaign_manifest_20260903.json"

REGIONS = ("PRE_KNEE", "KNEE", "POST_KNEE", "OVERLOAD", "HIGH_PRESSURE")


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).decode().strip()


def _sha256_obj(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def build_manifest(campaign_freeze_path: Path, contract_path: Path) -> dict:
    with open(campaign_freeze_path) as f:
        campaign = json.load(f)
    with open(contract_path) as f:
        contract = json.load(f)

    if set(PRIMARY_POLICIES) != set(contract["scope"]["policies"]):
        raise ValueError("frozen contract policy panel does not match PRIMARY_POLICIES -- STOPPING")

    # Recover the per-source list of 40 window_ids and each window's frozen
    # synthesis_seed from the sealed campaign's own cell list (LOW/rep0 is
    # sufficient since every region/repetition for a given window shares
    # the same synthesis_seed in the sealed design).
    windows_by_source: dict[str, dict[str, int]] = {}
    for c in campaign["cells"]:
        if c["repetition"] != 0:
            continue
        windows_by_source.setdefault(c["source_family"], {})[c["window_id"]] = c["synthesis_seed"]

    for source in contract["scope"]["sources"]:
        n = len(windows_by_source.get(source, {}))
        if n != contract["scope"]["windows_per_source"]:
            raise ValueError(f"expected {contract['scope']['windows_per_source']} windows for {source}, found {n}")

    region_assignment_index = campaign["region_assignment_index"]

    cells = []
    for variant_key in sorted(SLO_VARIANT_MULTIPLIERS):
        variant_multiplier = SLO_VARIANT_MULTIPLIERS[variant_key]
        for source in contract["scope"]["sources"]:
            for window_id in sorted(windows_by_source[source]):
                seed = windows_by_source[source][window_id]
                for region in REGIONS:
                    key = f"{source}::{window_id}::{region}"
                    if key not in region_assignment_index:
                        raise ValueError(f"missing region_assignment_index entry for {key}")
                    absolute_load_factor = float(region_assignment_index[key]["absolute_load_factor"])
                    for policy_id in PRIMARY_POLICIES:
                        cell_id = f"slo_sensitivity::{variant_key}::{key}::{policy_id}"
                        cells.append({
                            "cell_id": cell_id,
                            "slo_variant": variant_key,
                            "slo_multiplier": variant_multiplier,
                            "source_family": source,
                            "window_id": window_id,
                            "load_region": region,
                            "region_assignment_key": key,
                            "absolute_load_factor": absolute_load_factor,
                            "policy_id": policy_id,
                            "synthesis_seed": seed,
                        })

    expected = contract["expected_cells"]
    if len(cells) != expected:
        raise ValueError(f"expected {expected} cells, built {len(cells)} -- STOPPING")

    manifest = {
        "manifest_kind": "POST_PHASE12_SLO_DEFINITION_SENSITIVITY_EXTENSION_CAMPAIGN_MANIFEST",
        "label": "POST_PHASE12_SLO_DEFINITION_SENSITIVITY_EXTENSION",
        "protocol_doc": "docs/SLO_DEFINITION_SENSITIVITY_PROTOCOL_20260903.md",
        "contract_path": str(contract_path.relative_to(REPO_ROOT)),
        "contract_sha256": _sha256_obj(contract),
        "campaign_freeze_sha256": campaign["campaign_freeze_sha256"],
        "repo_sha": _git_sha(),
        "n_cells": len(cells),
        "cells": cells,
    }
    manifest["manifest_sha256"] = _sha256_obj({"cells": cells, "contract_sha256": manifest["contract_sha256"],
                                                "campaign_freeze_sha256": manifest["campaign_freeze_sha256"]})
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign-freeze", type=Path, default=DEFAULT_CAMPAIGN_FREEZE)
    ap.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    args = ap.parse_args()

    manifest = build_manifest(args.campaign_freeze, args.contract)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    print(f"Wrote {args.out}: n_cells={manifest['n_cells']} manifest_sha256={manifest['manifest_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
