#!/usr/bin/env python3
"""Deterministic generation of manuscript table-data and figures from the
six frozen, validated Phase-12 canonical analysis artifacts.

Every output file is stamped with the source artifact's SHA-256, this
script's own git identity (best-effort), and a generation timestamp.
No numeric value in the generated table-data/figures is manually edited;
everything is computed here from the frozen JSON artifacts.

Usage:
    python3 generate_phase12_tables_figures.py --data-dir <dir containing the six *.json files>

Refuses (raises) if any input file's SHA-256 does not match the frozen
validated hash ledger below.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_HASHES = {
    "ranking_correlations.json": "d77d5e973f70f8dfe443ebdf35b9c01e94adb84cc62cecef3a2c9afbb88773ff",
    "topk_overlap.json": "585e916acfb32cb02a8f99cdce65a882c5dee7acc6cbdfbad2e86716d0001b37",
    "pairwise_reversals.json": "c90619e822925146ad4395deebbf0cc8ccd0fd66cc13a8aa84202fc39a5cfdde",
    "sample_complexity.json": "cb54afc0e1bb868580b6a8c929d94f4718dbc1eaa01d527b0a2c265c07578dcf",
    "temporal_robustness.json": "c19a3c6400336525beda132386585e9d709782f5e0b05dec36867ee1850675d0",
    "telemetry_explanation.json": "b073fa0bbe91efe670151e7250d603f020ed7c0f1a60b90397fa7c18c5d591f6",
}

ANALYSIS_GIT_SHA = "eb574a8ce5c34a80fddbcfd4417f6626fbdddfd1"
PRIMARY_METRIC = "arrival_normalized_weighted_goodput"
SOURCES = ["azure_llm_2024", "bailian_qwen", "burstgpt"]
REGIONS = ["LOW", "PRE_KNEE", "KNEE", "POST_KNEE", "OVERLOAD", "HIGH_PRESSURE"]
FOUR_REGION_SUBSET = ["LOW", "PRE_KNEE", "KNEE", "OVERLOAD"]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _git_sha(repo_root: Path) -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root).decode().strip()
    except Exception:
        return "UNKNOWN"


def load_verified(data_dir: Path) -> dict:
    out = {}
    for fname, expected in EXPECTED_HASHES.items():
        p = data_dir / fname
        actual = _sha256(p)
        if actual != expected:
            raise SystemExit(
                f"STOP: hash mismatch for {fname}: expected {expected}, got {actual}"
            )
        with open(p) as f:
            out[fname] = json.load(f)
    return out


def stamp(repo_root: Path) -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "analysis_code_git_sha": ANALYSIS_GIT_SHA,
        "generation_script_git_sha": _git_sha(repo_root),
        "source_artifact_hashes": EXPECTED_HASHES,
    }


def cond(source: str, region: str) -> str:
    return f"{source}::{region}"


# ---------------------------------------------------------------------------
# RQ1: cross-workload / cross-region ranking portability (primary metric)
# ---------------------------------------------------------------------------

def build_rq1(rc: dict, tk: dict, repo_root: Path) -> dict:
    rows = []
    for entry in rc["comparisons"][PRIMARY_METRIC]:
        rows.append({
            "condition_x": entry["condition_x"],
            "condition_y": entry["condition_y"],
            "kendall_tau": entry["kendall_tau"],
            "kendall_tau_ci": entry["kendall_tau_ci"],
            "spearman_rho": entry["spearman_rho"],
            "spearman_rho_ci": entry["spearman_rho_ci"],
            "topk_overlap": entry["topk_overlap"],
            "n_policies_compared": entry["n_policies_compared"],
            "n_conditions_excluded_for_undefined_metric": entry["n_conditions_excluded_for_undefined_metric"],
        })

    # Secondary-metric compact summary: mean/min/max Kendall tau-b across the
    # 18 conditions, per metric.
    secondary = {}
    for metric, entries in rc["comparisons"].items():
        taus = [e["kendall_tau"] for e in entries if e["kendall_tau"] == e["kendall_tau"]]  # drop NaN
        if not taus:
            secondary[metric] = {"n_defined": 0}
            continue
        secondary[metric] = {
            "n_defined": len(taus),
            "n_total": len(entries),
            "mean_kendall_tau": sum(taus) / len(taus),
            "min_kendall_tau": min(taus),
            "max_kendall_tau": max(taus),
        }

    # Region-level aggregate for the primary metric (mean tau across the 3
    # source-pairs at each region) -- used for RQ2.
    by_region = {r: [] for r in REGIONS}
    for e in rc["comparisons"][PRIMARY_METRIC]:
        region = e["condition_x"].split("::")[1]
        assert region == e["condition_y"].split("::")[1]
        if e["kendall_tau"] == e["kendall_tau"]:
            by_region[region].append(e["kendall_tau"])
    region_summary = {
        r: {
            "n_defined": len(vals),
            "mean_kendall_tau": (sum(vals) / len(vals)) if vals else None,
            "min_kendall_tau": min(vals) if vals else None,
            "max_kendall_tau": max(vals) if vals else None,
        }
        for r, vals in by_region.items()
    }

    return {
        "manifest_kind": "rq1_rq2_portability_table",
        **stamp(repo_root),
        "primary_metric": PRIMARY_METRIC,
        "primary_metric_source_pair_x_region_table": rows,
        "secondary_metric_summary": secondary,
        "primary_metric_by_region_summary": region_summary,
    }


# ---------------------------------------------------------------------------
# RQ3: pairwise reversal classification (primary metric headline; secondary
# summary across all metrics)
# ---------------------------------------------------------------------------

def build_rq3(pr: dict, repo_root: Path) -> dict:
    CLASSES = [
        "UNDEFINED_UNESTIMABLE", "STABLE_NO_SIGN_CHANGE", "MICROSCOPIC_SIGN_CHANGE",
        "UNSUPPORTED_SIGN_CHANGE_WIDE_CI", "SUPPORTED_PRACTICAL_REVERSAL",
    ]

    primary_recs = pr["records"][PRIMARY_METRIC]
    primary_counts = {c: 0 for c in CLASSES}
    for r in primary_recs:
        primary_counts[r["classification"]] += 1
    n_primary = len(primary_recs)
    primary_rates = {c: primary_counts[c] / n_primary for c in CLASSES}

    supported = [r for r in primary_recs if r["classification"] == "SUPPORTED_PRACTICAL_REVERSAL"]

    def effect_size(r) -> float:
        # Operationalized effect size: the smaller-magnitude of the two
        # condition margins (the binding constraint for "largest effect
        # size" under the AND-both-conditions practical-margin rule).
        return min(abs(r["margin_x"]), abs(r["margin_y"]))

    supported_sorted = sorted(supported, key=effect_size, reverse=True)
    supported_detail = []
    for r in supported_sorted:
        supported_detail.append({
            "policy_a": r["policy_a"], "policy_b": r["policy_b"],
            "condition_x": r["condition_x"], "condition_y": r["condition_y"],
            "load_region": r["load_region"],
            "margin_x": r["margin_x"], "margin_y": r["margin_y"],
            "diff_x": r["diff_x"], "diff_y": r["diff_y"],
            "ci_x": r["ci_x"], "ci_y": r["ci_y"],
            "bh_fdr_p_pair_iut": r["bh_fdr_p_pair_iut"],
            "supported_after_fdr": r["supported_after_fdr"],
            "operationalized_effect_size_min_abs_margin": effect_size(r),
        })

    stable_examples = [r for r in primary_recs if r["classification"] == "STABLE_NO_SIGN_CHANGE"][:5]

    # Secondary-metric aggregate: class counts per metric.
    secondary = {}
    for metric, recs in pr["records"].items():
        counts = {c: 0 for c in CLASSES}
        for r in recs:
            counts[r["classification"]] += 1
        secondary[metric] = counts

    # Per-region breakdown for the primary metric.
    by_region = {r: {c: 0 for c in CLASSES} for r in REGIONS}
    for r in primary_recs:
        by_region[r["load_region"]][r["classification"]] += 1

    return {
        "manifest_kind": "rq3_reversal_table",
        **stamp(repo_root),
        "primary_metric": PRIMARY_METRIC,
        "primary_metric_class_counts": primary_counts,
        "primary_metric_class_rates": primary_rates,
        "primary_metric_n_total_pairwise_records": n_primary,
        "primary_metric_by_region_class_counts": by_region,
        "supported_practical_reversals_primary_metric_sorted_by_effect_size": supported_detail,
        "n_supported_practical_reversals_primary_metric": len(supported_detail),
        "stable_examples_primary_metric_sample": [
            {"policy_a": r["policy_a"], "policy_b": r["policy_b"],
             "condition_x": r["condition_x"], "condition_y": r["condition_y"],
             "load_region": r["load_region"]}
            for r in stable_examples
        ],
        "secondary_metric_class_counts": secondary,
        "effect_size_definition": "min(abs(margin_x), abs(margin_y)) -- the binding (smaller) of the two per-condition practical margins required to both exceed 10% under the frozen SUPPORTED_PRACTICAL_REVERSAL definition",
    }


# ---------------------------------------------------------------------------
# RQ4: sample complexity
# ---------------------------------------------------------------------------

def build_rq4(sc: dict, repo_root: Path) -> dict:
    threshold = 0.9
    rows = []
    for entry in sc["per_source_metric"]:
        if entry["metric"] != PRIMARY_METRIC:
            continue
        points = sorted(entry["points"], key=lambda p: p["n"])
        rows.append({
            "source": entry["source"],
            "points": [
                {"n": p["n"], "p_exact_recovery": p["p_exact_recovery"], "p_topk_recovery": p["p_topk_recovery"]}
                for p in points
            ],
            "first_n_meeting_exact_threshold": entry["first_n_meeting_exact_threshold"],
            "first_n_meeting_topk_threshold": entry["first_n_meeting_topk_threshold"],
            "reaches_0.9_exact_by_n40": (
                entry["first_n_meeting_exact_threshold"] is not None
            ),
        })

    # Secondary-metric compact summary: first_n_meeting_exact_threshold per (source, metric).
    secondary = []
    for entry in sc["per_source_metric"]:
        secondary.append({
            "source": entry["source"], "metric": entry["metric"],
            "first_n_meeting_exact_threshold": entry["first_n_meeting_exact_threshold"],
            "first_n_meeting_topk_threshold": entry["first_n_meeting_topk_threshold"],
        })

    return {
        "manifest_kind": "rq4_sample_complexity_table",
        **stamp(repo_root),
        "primary_metric": PRIMARY_METRIC,
        "ladder_n_values": sc["ladder_n_values"],
        "draws_per_n": sc["draws_per_n"],
        "recovery_threshold": threshold,
        "primary_metric_rows": rows,
        "concentrated_vs_spread": sc["concentrated_vs_spread"],
        "secondary_metric_thresholds": secondary,
    }


# ---------------------------------------------------------------------------
# RQ5: temporal + computable robustness families
# ---------------------------------------------------------------------------

def build_rq5(tr: dict, rc: dict, repo_root: Path) -> dict:
    temporal_rows = [r for r in tr["records"]]

    # LEAVE_ONE_SOURCE_OUT: for the primary metric, recompute the mean tau
    # across the remaining 2 source-pairs when each source is excluded in
    # turn (pure filter over the already-computed comparisons list).
    primary_entries = rc["comparisons"][PRIMARY_METRIC]

    def pair_sources(e):
        sx = e["condition_x"].split("::")[0]
        sy = e["condition_y"].split("::")[0]
        return sx, sy

    leave_one_out = {}
    for held_out in SOURCES:
        kept = [e for e in primary_entries if held_out not in pair_sources(e)]
        taus = [e["kendall_tau"] for e in kept if e["kendall_tau"] == e["kendall_tau"]]
        leave_one_out[held_out] = {
            "n_conditions_remaining": len(kept),
            "mean_kendall_tau_excluding_this_source": (sum(taus) / len(taus)) if taus else None,
        }
    full_taus = [e["kendall_tau"] for e in primary_entries if e["kendall_tau"] == e["kendall_tau"]]
    full_mean_tau = sum(full_taus) / len(full_taus) if full_taus else None

    # LOAD_CALIBRATION_SENSITIVITY: 4-region subset vs full 6-region grid.
    four_region_entries = [
        e for e in primary_entries
        if e["condition_x"].split("::")[1] in FOUR_REGION_SUBSET
    ]
    four_taus = [e["kendall_tau"] for e in four_region_entries if e["kendall_tau"] == e["kendall_tau"]]
    load_calibration_sensitivity = {
        "four_region_subset": FOUR_REGION_SUBSET,
        "n_conditions_four_region": len(four_region_entries),
        "mean_kendall_tau_four_region": (sum(four_taus) / len(four_taus)) if four_taus else None,
        "mean_kendall_tau_full_six_region": full_mean_tau,
    }

    return {
        "manifest_kind": "rq5_temporal_robustness_table",
        **stamp(repo_root),
        "primary_metric": PRIMARY_METRIC,
        "temporal_records": temporal_rows,
        "robustness_primary_only": {
            "note": "Headline ranking_correlations.json already restricts to the 11-policy PRIMARY panel (verified in the structural audit); PRIMARY_ONLY is therefore identical to the headline result by construction, not a separate recomputation.",
        },
        "robustness_leave_one_source_out": {
            "full_panel_mean_kendall_tau": full_mean_tau,
            "per_excluded_source": leave_one_out,
        },
        "robustness_load_calibration_sensitivity": load_calibration_sensitivity,
        "robustness_window_size_sensitivity_note": "Identical to the RQ4 sample-complexity ladder (per the frozen robustness contract); not separately recomputed here.",
        "robustness_metric_definition_sensitivity_note": "NOT computable from the six aggregate canonical artifacts alone -- requires per-cell metric values from the full consolidated matrix, which are out of scope for this manuscript-generation pass.",
        "robustness_leave_one_policy_family_out_note": "NOT computable from the six aggregate canonical artifacts alone for the tau-b/rho ranking statistics (which depend on the joint 11-policy ranking) -- requires per-cell metric values.",
        "slo_definition_sensitivity": "UNAVAILABLE -- no preregistered alternative SLO-synthesis rule ever existed; not fabricated.",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    data = load_verified(args.data_dir)

    rc = data["ranking_correlations.json"]
    tk = data["topk_overlap.json"]
    pr = data["pairwise_reversals.json"]
    sc = data["sample_complexity.json"]
    tr = data["temporal_robustness.json"]

    args.out_dir.mkdir(parents=True, exist_ok=True)

    rq1 = build_rq1(rc, tk, repo_root)
    rq3 = build_rq3(pr, repo_root)
    rq4 = build_rq4(sc, repo_root)
    rq5 = build_rq5(tr, rc, repo_root)

    for name, payload in [("rq1_rq2_portability", rq1), ("rq3_reversals", rq3),
                           ("rq4_sample_complexity", rq4), ("rq5_temporal_robustness", rq5)]:
        outp = args.out_dir / f"{name}.json"
        with open(outp, "w") as f:
            json.dump(payload, f, indent=2, sort_keys=False, default=str)
        print(f"wrote {outp}")

    # ---- printed summary for interpretation (stdout only, not a table file) ----
    print("\n=== RQ1 primary-metric source-pair x region tau (first 5) ===")
    for row in rq1["primary_metric_source_pair_x_region_table"][:5]:
        print(row["condition_x"], "vs", row["condition_y"], "tau=", round(row["kendall_tau"], 3) if row["kendall_tau"] == row["kendall_tau"] else "NaN")

    print("\n=== RQ1 by-region mean tau ===")
    for r, s in rq1["primary_metric_by_region_summary"].items():
        print(r, s)

    print("\n=== RQ3 primary-metric class counts ===")
    print(rq3["primary_metric_class_counts"])
    print("n supported reversals:", rq3["n_supported_practical_reversals_primary_metric"])

    print("\n=== RQ4 primary metric per-source recovery (n=40 point) ===")
    for row in rq4["primary_metric_rows"]:
        p40 = [p for p in row["points"] if p["n"] == 40][0]
        print(row["source"], "n=40 exact=", p40["p_exact_recovery"], "topk=", p40["p_topk_recovery"], "first_n_exact=", row["first_n_meeting_exact_threshold"])

    print("\n=== RQ5 leave-one-source-out ===")
    print(rq5["robustness_leave_one_source_out"])
    print("\n=== RQ5 load-calibration sensitivity ===")
    print(rq5["robustness_load_calibration_sensitivity"])


if __name__ == "__main__":
    main()
