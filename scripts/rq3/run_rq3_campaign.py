#!/usr/bin/env python3
"""Execute every cell in a frozen RQ3 campaign manifest, writing one JSON
result file per cell under a namespace keyed by the manifest's own hash so
pilot and scientific outputs never collide.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.rq3.runner import run_manifest  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--out-root", type=Path, default=REPO_ROOT / "artifacts/rq3/synthetic_to_real")
    args = ap.parse_args()

    with open(args.manifest) as f:
        manifest = json.load(f)

    out_dir = args.out_root / manifest["campaign_manifest_sha256"]
    summary = run_manifest(manifest, out_dir)
    summary["campaign_manifest_sha256"] = manifest["campaign_manifest_sha256"]
    summary["is_pilot"] = manifest.get("is_pilot", False)
    summary["out_dir"] = str(out_dir)

    with open(out_dir / "_run_summary.json", "w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
