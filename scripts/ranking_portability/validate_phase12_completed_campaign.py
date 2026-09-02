#!/usr/bin/env python3
"""Independent completed-Phase-12-campaign validator (post-campaign;
frozen ahead of any real result). Deliberately does not import
`consolidate_phase12_campaign.py`'s report -- reads the consolidated
artifact's `cells` dict directly and independently re-derives the
expected 18,720-cell Cartesian product from the frozen contract module,
exactly like `validate_phase12_campaign_freeze.py` does for the
pre-launch matrix.

Requires an explicit `--consolidated` path (no default); checked against
the result-blindness guard unless `--allow-live` is passed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.ranking_portability.analysis.matrix_validator import (  # noqa: E402
    IMMUTABLE_HASH_MANIFEST_KEYS,
    validate_completed_campaign,
)
from robustbench.ranking_portability.analysis.result_blindness import (  # noqa: E402
    assert_not_live_campaign_path,
)
from robustbench.ranking_portability.phase12_campaign import (  # noqa: E402
    CAMPAIGN_SOURCES,
    load_campaign_window_ids,
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--compact-window-index", type=Path, required=True)
    ap.add_argument("--consolidated", type=Path, required=True)
    ap.add_argument("--allow-live", action="store_true", default=False)
    args = ap.parse_args()

    assert_not_live_campaign_path(args.consolidated, allow_live=args.allow_live)

    with open(args.manifest) as f:
        manifest = json.load(f)
    with open(args.compact_window_index) as f:
        compact_index = json.load(f)
    with open(args.consolidated) as f:
        consolidated = json.load(f)

    window_ids_by_source = load_campaign_window_ids(compact_index)
    expected_hashes = {k: manifest.get(k) for k in IMMUTABLE_HASH_MANIFEST_KEYS}

    report = validate_completed_campaign(
        manifest=manifest,
        consolidated_rows=consolidated["cells"],
        window_ids_by_source=window_ids_by_source,
        expected_immutable_hashes=expected_hashes,
    )

    print(f"n_expected_cells={report.n_expected_cells}")
    print(f"n_actual_valid_cells={report.n_actual_valid_cells}")
    print(f"n_windows={report.n_windows}")
    print(f"n_windows_per_source={report.n_windows_per_source}")
    print(f"n_regions={report.n_regions}")
    print(f"n_policies={report.n_policies}")
    print(f"n_reps={report.n_reps}")
    print(f"n_assignment_keys_represented={report.n_assignment_keys_represented}")
    print(f"n_rep_input_mismatches={report.n_rep_input_mismatches}")
    print(f"n_rep_output_metric_diagnostic_mismatches={report.n_rep_output_metric_diagnostic_mismatches}")
    print(f"secondary_stratum_leakage={report.secondary_stratum_leakage}")
    print(f"n_problems={len(report.problems)}")
    for p in report.problems[:20]:
        print(f"PROBLEM: {p}")

    if report.valid:
        print("PHASE12_COMPLETED_CAMPAIGN_INDEPENDENTLY_VALID = YES")
        return 0
    print("PHASE12_COMPLETED_CAMPAIGN_INDEPENDENTLY_VALID = NO")
    return 1


if __name__ == "__main__":
    sys.exit(main())
