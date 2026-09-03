#!/usr/bin/env python3
"""Build (but do not execute) the frozen RQ3 synthetic-to-real campaign
manifest. `--pilot` builds the reduced-seed engineering pilot manifest
instead of the full scientific campaign manifest -- see
docs/RQ3_SYNTHETIC_TO_REAL_PROTOCOL_20260903.md section 6/7.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.rq3.campaign import build_manifest  # noqa: E402
from robustbench.rq3.synthetic_families import FAMILY_IDS, PRIMARY_POLICIES  # noqa: E402

PILOT_SEEDS = [0, 1]
FULL_SEEDS = [0, 1, 2, 3, 4]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    seeds = PILOT_SEEDS if args.pilot else FULL_SEEDS
    manifest = build_manifest(family_ids=FAMILY_IDS, seeds=seeds, policies=PRIMARY_POLICIES)
    manifest["is_pilot"] = bool(args.pilot)

    default_name = (
        "rq3_campaign_manifest_pilot_20260903.json" if args.pilot
        else "rq3_campaign_manifest_full_20260903.json"
    )
    out_path = args.out or (REPO_ROOT / "artifacts/manifests/rq3" / default_name)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)

    print(f"Wrote {out_path}")
    print(f"n_cells={manifest['n_cells']} n_windows={manifest['n_windows']} "
          f"campaign_manifest_sha256={manifest['campaign_manifest_sha256']}")


if __name__ == "__main__":
    main()
