#!/usr/bin/env python3
"""Phase-12 campaign-shard consolidator (post-campaign; frozen ahead of
any real result, see docs/RANKING_PORTABILITY_PHASE12_ANALYSIS_PREFREEZE.md).

Reads the 64 shard-output files a completed campaign run would produce
under a campaign-freeze-namespaced directory
(`<shard-output-dir>/shard_{000..063}.json`, matching
`run_phase12_campaign_shard.py`'s `_output_path` convention), validates
every row's identity/schema/telemetry against the frozen manifest, and
writes one canonical consolidated JSON only if the matrix is complete
and every row is valid. Never imputes an undefined metric; never accepts
a stale/invalid checkpoint row.

THIS SCRIPT TAKES NO DEFAULT INPUT DIRECTORY. `--shard-output-dir` is
required, and by default the path is checked against the result-blindness
guard (pass `--allow-live` to lift that check for a genuine, deliberate
production consolidation run after the campaign is real and complete --
never used by this prefreeze task or its tests).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.ranking_portability.analysis.consolidation import consolidate  # noqa: E402
from robustbench.ranking_portability.analysis.result_blindness import (  # noqa: E402
    assert_not_live_campaign_path,
)


def _load_shard_outputs(shard_output_dir: Path, shard_count: int):
    shard_outputs = {}
    for shard_id in range(shard_count):
        path = shard_output_dir / f"shard_{shard_id:03d}.json"
        if not path.exists():
            shard_outputs[shard_id] = (shard_output_dir.name, {})
            continue
        with open(path) as f:
            rows = json.load(f)
        shard_outputs[shard_id] = (shard_output_dir.name, rows)
    return shard_outputs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--shard-plan", type=Path, required=True)
    ap.add_argument("--shard-output-dir", type=Path, required=True)
    ap.add_argument("--campaign-freeze-sha256", type=str, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--allow-live", action="store_true", default=False)
    args = ap.parse_args()

    assert_not_live_campaign_path(args.shard_output_dir, allow_live=args.allow_live)

    with open(args.manifest) as f:
        manifest = json.load(f)
    with open(args.shard_plan) as f:
        shard_plan = json.load(f)

    shard_outputs = _load_shard_outputs(args.shard_output_dir, shard_plan["shard_count"])
    report = consolidate(
        manifest=manifest,
        shard_outputs=shard_outputs,
        expected_campaign_freeze_sha256=args.campaign_freeze_sha256,
    )

    print(f"n_expected_cells={report.n_expected_cells}")
    print(f"n_consolidated_valid={report.n_consolidated_valid}")
    print(f"n_missing={report.n_missing}")
    print(f"n_failed={report.n_failed}")
    print(f"n_invalid={report.n_invalid}")
    print(f"n_duplicate_cross_shard={report.n_duplicate_cross_shard}")
    print(f"n_unknown_cell_ids={report.n_unknown_cell_ids}")
    print(f"n_wrong_provenance_shards={report.n_wrong_provenance_shards}")
    print(f"n_rep_mismatch_pairs={len(report.rep_mismatch_pairs)}")
    print(f"is_complete_and_valid={report.is_complete_and_valid}")

    if not report.is_complete_and_valid:
        print("CONSOLIDATION_INCOMPLETE_OR_INVALID -- no canonical artifact written.")
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(
            {"campaign_freeze_sha256": report.campaign_freeze_sha256, "cells": report.consolidated_rows},
            f, sort_keys=True,
        )
    print(f"wrote canonical consolidated artifact: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
