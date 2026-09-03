#!/usr/bin/env python3
"""POST_PHASE12_SLO_DEFINITION_SENSITIVITY_EXTENSION analysis.

Reuses the sealed, unmodified ranking-portability analysis machinery
(`ranking_portability/analysis/ranking_analysis.py::compare_conditions`,
`ranking_portability/analysis/reversal_analysis.py::classify_pairwise_reversal`)
to compare each alternative SLO-variant's cell results against the primary
variant's, per docs/SLO_DEFINITION_SENSITIVITY_PROTOCOL_20260903.md sections
9. Never modifies the sealed analysis code, never recomputes primary
Phase-12 results -- reads only this extension's own campaign output plus
the frozen read-only reversal reference
(configs/analysis/phase12_primary_reversals_reference.json).

Outputs (into the same run's output directory as the campaign results):
  cross_metric-style siblings for THIS extension:
    ranking_robustness.json         -- per (source, region, variant) vs primary
    reversal_persistence.json       -- per reference reversal, per variant
    slo_sensitivity_status.json     -- structural summary
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.ranking_portability.analysis.contract import (  # noqa: E402
    BOOTSTRAP_CI_LEVEL,
    BOOTSTRAP_RESAMPLES,
    PRIMARY_METRIC,
    PRIMARY_POLICIES,
)
from robustbench.ranking_portability.analysis.ranking_analysis import compare_conditions  # noqa: E402
from robustbench.ranking_portability.analysis.reversal_analysis import (  # noqa: E402
    ReversalClass,
    classify_pairwise_reversal,
    per_window_policy_values,
)

DEFAULT_REFERENCE = REPO_ROOT / "configs/analysis/phase12_primary_reversals_reference.json"
PRIMARY_VARIANT = "primary_20x"


def _rows_for(all_rows: List[dict], *, source: str, region: str, variant: str) -> List[dict]:
    return [
        r for r in all_rows
        if r.get("source_family") == source and r.get("load_region") == region
        and r.get("slo_variant") == variant and r.get("success")
    ]


def ranking_robustness(all_rows: List[dict], sources: List[str], regions: List[str],
                        variants: List[str]) -> List[dict]:
    out = []
    for source in sources:
        for region in regions:
            primary_rows = _rows_for(all_rows, source=source, region=region, variant=PRIMARY_VARIANT)
            for variant in variants:
                if variant == PRIMARY_VARIANT:
                    continue
                variant_rows = _rows_for(all_rows, source=source, region=region, variant=variant)
                if not primary_rows or not variant_rows:
                    out.append({
                        "source": source, "region": region, "variant": variant,
                        "metric": PRIMARY_METRIC, "status": "UNDEFINED_INSUFFICIENT_DATA",
                    })
                    continue
                cmp = compare_conditions(
                    primary_rows, variant_rows, metric=PRIMARY_METRIC,
                    all_policies=list(PRIMARY_POLICIES),
                    condition_x_label=f"{source}::{region}::{PRIMARY_VARIANT}",
                    condition_y_label=f"{source}::{region}::{variant}",
                    n_resamples=BOOTSTRAP_RESAMPLES, ci_level=BOOTSTRAP_CI_LEVEL,
                )
                out.append({
                    "source": source, "region": region, "variant": variant,
                    "metric": PRIMARY_METRIC,
                    "kendall_tau_b": cmp.point.kendall_tau,
                    "kendall_ci": cmp.kendall_tau_ci,
                    "spearman_rho": cmp.point.spearman_rho,
                    "spearman_ci": cmp.spearman_rho_ci,
                    "top1_agreement": cmp.point.topk_overlap.get(1) if cmp.point.topk_overlap else None,
                    "top3_overlap": cmp.point.topk_overlap.get(3) if cmp.point.topk_overlap else None,
                    "n_policies_compared": cmp.point.n_policies_compared,
                    "bootstrap_count": BOOTSTRAP_RESAMPLES,
                    "status": "OK",
                })
    return out


def reversal_persistence(all_rows: List[dict], reference_path: Path, variants: List[str]) -> List[dict]:
    with open(reference_path) as f:
        reference = json.load(f)
    out = []
    for rec in reference["supported_practical_reversals_primary_metric"]:
        cond_x, region = rec["condition_x"].split("::")
        cond_y, region_y = rec["condition_y"].split("::")
        assert region == region_y == rec["load_region"]
        policy_a, policy_b = rec["policy_a"], rec["policy_b"]
        for variant in variants:
            rows_x = _rows_for(all_rows, source=cond_x, region=region, variant=variant)
            rows_y = _rows_for(all_rows, source=cond_y, region=region, variant=variant)
            if not rows_x or not rows_y:
                out.append({
                    "reference_condition_x": rec["condition_x"], "reference_condition_y": rec["condition_y"],
                    "load_region": region, "policy_a": policy_a, "policy_b": policy_b,
                    "variant": variant, "persistence": "UNDEFINED_INSUFFICIENT_DATA",
                })
                continue
            pw_x = per_window_policy_values(rows_x, PRIMARY_METRIC)
            pw_y = per_window_policy_values(rows_y, PRIMARY_METRIC)
            result = classify_pairwise_reversal(
                pw_x, pw_y, policy_a, policy_b,
                n_resamples=BOOTSTRAP_RESAMPLES, ci_level=BOOTSTRAP_CI_LEVEL,
            )
            if result.classification == ReversalClass.SUPPORTED_PRACTICAL_REVERSAL:
                persistence = "PERSISTS"
            elif result.classification in (ReversalClass.STABLE_NO_SIGN_CHANGE,):
                persistence = "DISAPPEARS"
            elif result.classification == ReversalClass.MICROSCOPIC_SIGN_CHANGE:
                persistence = "BECOMES_UNSUPPORTED"
            elif result.classification == ReversalClass.UNSUPPORTED_SIGN_CHANGE_WIDE_CI:
                persistence = "BECOMES_UNSUPPORTED"
            else:
                persistence = "UNDEFINED"
            direction_changed = (
                result.diff_x is not None and rec.get("diff_x") is not None
                and (result.diff_x > 0) != (rec["diff_x"] > 0)
            )
            if direction_changed and persistence != "UNDEFINED_INSUFFICIENT_DATA":
                persistence = "DIRECTION_CHANGE"
            out.append({
                "reference_condition_x": rec["condition_x"], "reference_condition_y": rec["condition_y"],
                "load_region": region, "policy_a": policy_a, "policy_b": policy_b,
                "variant": variant, "classification": result.classification.value,
                "persistence": persistence, "diff_x": result.diff_x, "diff_y": result.diff_y,
                "margin_x": result.margin_x, "margin_y": result.margin_y,
            })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=Path, required=True, help="campaign run's results.json")
    ap.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE)
    ap.add_argument("--sources", nargs="*", default=["burstgpt", "azure_llm_2024", "bailian_qwen"])
    ap.add_argument("--regions", nargs="*", default=["PRE_KNEE", "KNEE", "POST_KNEE", "OVERLOAD", "HIGH_PRESSURE"])
    ap.add_argument("--variants", nargs="*", default=["tight_10x", "primary_20x", "loose_40x"])
    args = ap.parse_args()

    with open(args.results) as f:
        results: Dict[str, dict] = json.load(f)
    all_rows = list(results.values())

    ranking = ranking_robustness(all_rows, args.sources, args.regions, args.variants)
    reversals = reversal_persistence(all_rows, args.reference, args.variants) if args.reference.exists() else []

    out_dir = args.results.parent
    with open(out_dir / "ranking_robustness.json", "w") as f:
        json.dump(ranking, f, indent=2, sort_keys=True)
    with open(out_dir / "reversal_persistence.json", "w") as f:
        json.dump(reversals, f, indent=2, sort_keys=True)

    status = {
        "manifest_kind": "POST_PHASE12_SLO_DEFINITION_SENSITIVITY_EXTENSION_ANALYSIS_STATUS",
        "n_input_rows": len(all_rows),
        "n_ranking_robustness_records": len(ranking),
        "n_reversal_persistence_records": len(reversals),
        "n_reversals_persisting": sum(1 for r in reversals if r.get("persistence") == "PERSISTS"),
        "n_reversals_disappearing": sum(1 for r in reversals if r.get("persistence") == "DISAPPEARS"),
    }
    with open(out_dir / "slo_sensitivity_status.json", "w") as f:
        json.dump(status, f, indent=2, sort_keys=True)
    print(json.dumps(status, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
