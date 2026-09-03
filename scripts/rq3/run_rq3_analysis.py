#!/usr/bin/env python3
"""Consume one RQ3 campaign's raw cell outputs plus the frozen real-side
reference extract and produce the synthetic-to-real transfer records.

Never reads/writes anything under the sealed Phase-12 analysis output
namespace; never modifies the real reference extract; never regenerates
campaign cells.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.rq3.transfer_stats import CI_LEVEL, N_BOOTSTRAP, compute_transfer  # noqa: E402
from robustbench.rq3.synthetic_families import MIN_COMMON_POLICIES  # noqa: E402

DEFAULT_REAL_REFERENCE = REPO_ROOT / "artifacts/manifests/rq3/real_reference_conditions_20260903.json"
DEFAULT_CONTRACT = REPO_ROOT / "configs/rq3/rq3_synthetic_to_real_20260903.json"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).decode().strip()


def _load_synthetic_cells(campaign_out_dir: Path) -> List[Dict[str, Any]]:
    cells = []
    for family_dir in sorted(campaign_out_dir.iterdir()):
        if not family_dir.is_dir():
            continue
        for cell_path in sorted(family_dir.glob("*.json")):
            with open(cell_path) as f:
                cells.append(json.load(f))
    return cells


def _synthetic_per_policy_per_window(cells: List[Dict[str, Any]], family_id: str, region: str,
                                      metric: str) -> Dict[str, List[float]]:
    by_policy: Dict[str, Dict[str, float]] = defaultdict(dict)
    for c in cells:
        if c["source_family"] != f"synthetic_{family_id}" or c["load_region"] != region:
            continue
        if not c.get("success"):
            continue
        v = c.get(metric)
        if v is None:
            continue
        by_policy[c["policy_id"]][c["window_id"]] = v
    windows = sorted({w for wm in by_policy.values() for w in wm})
    return {p: [wm.get(w) for w in windows] for p, wm in by_policy.items()}, windows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--campaign-out-dir", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--real-reference", type=Path, default=DEFAULT_REAL_REFERENCE)
    ap.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()

    with open(args.manifest) as f:
        manifest = json.load(f)
    with open(args.real_reference) as f:
        real_ref = json.load(f)
    with open(args.contract) as f:
        contract = json.load(f)

    metric = contract["primary_metric"]
    families = contract["synthetic_families"]
    real_sources = contract["real_reference"]["real_sources"]
    regions = contract["load_regions"]

    cells = _load_synthetic_cells(args.campaign_out_dir)
    input_hash = hashlib.sha256(
        json.dumps({"manifest_sha256": manifest["campaign_manifest_sha256"],
                    "real_reference_sha256": _sha256_file(args.real_reference)},
                   sort_keys=True).encode()
    ).hexdigest()
    contract_hash = hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest()
    code_sha = _git_sha()

    rng = np.random.default_rng(20260903)

    records = []
    for fam in families:
        family_id = fam["family_id"]
        for region in regions:
            synth_ppw, synth_windows = _synthetic_per_policy_per_window(cells, family_id, region, metric)
            for real_source in real_sources:
                real_cond = real_ref["source_condition_policy_window_values"][real_source][region]
                real_ppw = real_cond["per_policy_per_window"]
                result = compute_transfer(
                    synth_ppw, real_ppw, min_common_policies=MIN_COMMON_POLICIES,
                    n_bootstrap=N_BOOTSTRAP, ci_level=CI_LEVEL, rng=rng,
                )
                records.append({
                    "synthetic_family": family_id,
                    "real_source": real_source,
                    "region": region,
                    "metric": metric,
                    "effective_policy_count": result.effective_policy_count,
                    "policy_panel": result.policy_panel,
                    "n_synthetic_windows": len(synth_windows),
                    "n_real_windows": len(real_cond["windows"]),
                    "kendall_tau_b": result.kendall_tau_b,
                    "kendall_ci": result.kendall_ci,
                    "spearman_rho": result.spearman_rho,
                    "spearman_ci": result.spearman_ci,
                    "top1_agreement": result.top1_agreement,
                    "top3_overlap": result.top3_overlap,
                    "bootstrap_count": result.bootstrap_count,
                    "sign_agreement_rate": result.sign_agreement_rate,
                    "n_sign_pairs": result.n_sign_pairs,
                    "analysis_contract_hash": contract_hash,
                    "input_hash": input_hash,
                    "code_sha": code_sha,
                    "status": result.status,
                })

    records.sort(key=lambda r: (r["synthetic_family"], r["real_source"], r["region"]))

    keys = [(r["synthetic_family"], r["real_source"], r["region"]) for r in records]
    n_duplicates = len(keys) - len(set(keys))
    n_undefined = sum(1 for r in records if r["status"] != "OK")
    expected_records = len(families) * len(real_sources) * len(regions)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    with open(args.out_dir / "rq3_transfer_correlations.json", "w") as f:
        json.dump(records, f, indent=2, sort_keys=True)

    status_doc = {
        "scientific_status": "POST_PHASE12_RESULT_INDEPENDENT_ANALYSIS_EXTENSION",
        "is_pilot": manifest.get("is_pilot", False),
        "expected_records": expected_records,
        "observed_records": len(records),
        "undefined_records": n_undefined,
        "n_duplicates": n_duplicates,
        "analysis_contract_hash": contract_hash,
        "input_hash": input_hash,
        "code_sha": code_sha,
        "campaign_manifest_sha256": manifest["campaign_manifest_sha256"],
    }
    with open(args.out_dir / "rq3_status.json", "w") as f:
        json.dump(status_doc, f, indent=2, sort_keys=True)

    print(json.dumps(status_doc, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
