#!/usr/bin/env python3
"""Read-only post-Stage0 diagnostic: why did BurstGPT contribute less
scheduler differentiation than Azure-2024/Bailian-Qwen (Criterion 5)?

Reads the completed, frozen 1,080-cell Stage-0 matrix and the frozen
windows/calibration manifests. Writes CSV/JSON diagnostic artifacts only.
Does NOT modify any Stage-0 result cell, does NOT change any threshold or
tie epsilon, does NOT relabel tied/non-tied status, does NOT launch
anything.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, "src")
from robustbench.descriptors.window_descriptors import compute_window_descriptor  # noqa: E402
from robustbench.workloads.external.schema import ExternalWorkloadRecord  # noqa: E402
from robustbench.stage0.analyzer import TIE_TOLERANCE  # noqa: E402
from robustbench.stage0.cell import STAGE0_POLICIES  # noqa: E402

OUT_DIR = Path("results/stage0_burstgpt_diagnostic")

METRIC_FIELDS = [
    "arrival_normalized_weighted_goodput", "completion_fraction",
    "slo_violation_rate", "mean_latency", "p95_latency", "mean_ttft",
    "p95_ttft", "request_throughput", "token_throughput", "weighted_goodput",
]


def _is_nan(v):
    return isinstance(v, float) and v != v


def _finite_vals(rows, field):
    out = []
    for r in rows:
        v = r.get(field)
        if v is not None and not _is_nan(v):
            out.append(v)
    return out


def load_cells(results_dir: Path) -> list[dict]:
    plan = json.load(open(results_dir / "stage0_plan.json"))
    cells = []
    for c in plan["cells"]:
        p = results_dir / "cells" / (c["cell_id"].replace("::", "__") + ".json")
        cells.append(json.load(open(p)))
    return cells


def group_conditions(cells: list[dict]) -> dict[tuple, dict[str, dict]]:
    """key = (source, window, region) -> {policy_id: rep0_row}"""
    by_group: dict[tuple, dict[str, dict]] = defaultdict(dict)
    for r in cells:
        if r["repetition"] != 0:
            continue  # rep0==rep1 verified identical; use rep0 as the representative
        key = (r["source_family"], r["window_id"], r["load_region"])
        by_group[key][r["policy_id"]] = r
    return by_group


def condition_row(key, by_policy: dict[str, dict]) -> dict:
    source, window, region = key
    rows = list(by_policy.values())
    anwg = {p: r["arrival_normalized_weighted_goodput"] for p, r in by_policy.items()}
    vals = list(anwg.values())
    lo, hi = min(vals), max(vals)
    rng = hi - lo
    tied = rng <= TIE_TOLERANCE
    rel_range = (rng / lo) if lo != 0 else (float("inf") if rng > 0 else 0.0)
    winner = max(anwg, key=lambda p: anwg[p])
    cf_vals = [r["completion_fraction"] for r in rows]

    out = {
        "source_family": source, "window_id": window, "load_region": region,
        "tied": tied,
        "anwg_min": lo, "anwg_max": hi, "anwg_range": rng,
        "anwg_relative_range": rel_range,
        "winning_policy": winner,
        "completion_fraction_min": min(cf_vals), "completion_fraction_max": max(cf_vals),
        "completion_fraction_range": max(cf_vals) - min(cf_vals),
    }
    for field in ("p95_latency", "mean_latency", "slo_violation_rate",
                  "request_throughput", "token_throughput", "mean_ttft"):
        fv = _finite_vals(rows, field)
        out[f"{field}_n_finite"] = len(fv)
        out[f"{field}_min"] = min(fv) if fv else None
        out[f"{field}_max"] = max(fv) if fv else None
        out[f"{field}_range"] = (max(fv) - min(fv)) if fv else None
    return out


def main() -> None:
    results_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "results/stage0_v1")
    windows_path = Path(sys.argv[2] if len(sys.argv) > 2 else "artifacts/manifests/stage0_windows.json")
    calibration_path = Path(sys.argv[3] if len(sys.argv) > 3 else "artifacts/manifests/stage0_load_calibration.json")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    cells = load_cells(results_dir)
    by_group = group_conditions(cells)
    assert len(by_group) == 90, f"expected 90 (source,window,region) groups, got {len(by_group)}"

    all_rows = [condition_row(key, by_policy) for key, by_policy in by_group.items()]
    all_rows.sort(key=lambda r: (r["source_family"], r["window_id"], r["load_region"]))

    # ---- 1. source_differentiation.csv ----
    by_source = defaultdict(list)
    for r in all_rows:
        by_source[r["source_family"]].append(r)
    src_summary = []
    for source, rows in sorted(by_source.items()):
        non_tied = [r for r in rows if not r["tied"]]
        windows_non_tied = len({r["window_id"] for r in non_tied})
        n_windows = len({r["window_id"] for r in rows})
        src_summary.append({
            "source_family": source,
            "non_tied_conditions": len(non_tied),
            "total_conditions": len(rows),
            "pct_non_tied": len(non_tied) / len(rows),
            "windows_non_tied_in_ge1_region": windows_non_tied,
            "n_windows": n_windows,
        })
    with open(OUT_DIR / "source_differentiation.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(src_summary[0].keys()))
        w.writeheader(); w.writerows(src_summary)

    # ---- 2. all 90 conditions (superset used for burstgpt matrix + tie magnitude) ----
    with open(OUT_DIR / "all_conditions.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        w.writeheader(); w.writerows(all_rows)

    burst_rows = [r for r in all_rows if r["source_family"] == "burstgpt"]
    with open(OUT_DIR / "burstgpt_window_region_matrix.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(burst_rows[0].keys()))
        w.writeheader(); w.writerows(burst_rows)

    # ---- 3. tied_condition_ranges.csv (per-source tied vs non-tied dist) ----
    tie_stats = []
    for source, rows in sorted(by_source.items()):
        for tied_flag in (True, False):
            subset = [r for r in rows if r["tied"] == tied_flag]
            if not subset:
                continue
            anwg_ranges = [r["anwg_range"] for r in subset]
            cf_ranges = [r["completion_fraction_range"] for r in subset]
            p95_ranges = [r["p95_latency_range"] for r in subset if r["p95_latency_range"] is not None]
            tie_stats.append({
                "source_family": source, "tied": tied_flag, "n": len(subset),
                "anwg_range_max": max(anwg_ranges), "anwg_range_mean": sum(anwg_ranges) / len(anwg_ranges),
                "completion_fraction_range_max": max(cf_ranges),
                "completion_fraction_range_mean": sum(cf_ranges) / len(cf_ranges),
                "p95_latency_range_mean": (sum(p95_ranges) / len(p95_ranges)) if p95_ranges else None,
                "p95_latency_range_n": len(p95_ranges),
            })
    with open(OUT_DIR / "tied_condition_ranges.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(tie_stats[0].keys()))
        w.writeheader(); w.writerows(tie_stats)

    # ---- 4. calibration_comparison.csv ----
    calib = json.load(open(calibration_path))
    calib_by_window = {c["window_id"]: c for c in calib["calibrations"]}
    calib_rows = []
    for window_id, c in sorted(calib_by_window.items()):
        source = None
        for r in all_rows:
            if r["window_id"] == window_id:
                source = r["source_family"]
                break
        sanity = c.get("sanity", {})
        regions = c.get("load_regions", {})
        calib_rows.append({
            "source_family": source, "window_id": window_id,
            "lambda_ref": c.get("lambda_ref"),
            "pre_knee_load_value": regions.get("PRE_KNEE"),
            "knee_load_value": regions.get("KNEE"),
            "overload_load_value": regions.get("OVERLOAD"),
            "pre_knee_slo_violation_rate": sanity.get("pre_knee_slo_violation_rate"),
            "pre_knee_completion_fraction": sanity.get("pre_knee_completion_fraction"),
            "knee_slo_violation_rate": sanity.get("knee_slo_violation_rate"),
            "knee_completion_fraction": sanity.get("knee_completion_fraction"),
            "overload_slo_violation_rate": sanity.get("overload_slo_violation_rate"),
            "overload_completion_fraction": sanity.get("overload_completion_fraction"),
            "plausible": sanity.get("plausible"),
            "notes": "; ".join(sanity.get("notes", [])),
        })
    with open(OUT_DIR / "calibration_comparison.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(calib_rows[0].keys()))
        w.writeheader(); w.writerows(calib_rows)

    # ---- 5. descriptor_comparison.csv ----
    windows_manifest = json.load(open(windows_path))
    records_by_window = {w["window_id"]: w["records"] for w in windows_manifest["windows"]}
    desc_rows = []
    for window_id, records in sorted(records_by_window.items()):
        source = None
        for r in all_rows:
            if r["window_id"] == window_id:
                source = r["source_family"]
                break
        if source is None:
            continue
        recs = [ExternalWorkloadRecord(**rec) for rec in records]
        d = compute_window_descriptor(recs, source_family=source, window_id=window_id)
        desc_rows.append({
            "source_family": source, "window_id": window_id,
            "request_count": d.request_count, "arrival_rate_rps": d.arrival_rate_rps,
            "interarrival_cv": d.interarrival_cv, "burstiness_b": d.burstiness_b,
            "prompt_tokens_mean": d.prompt_tokens_mean, "prompt_tokens_p90": d.prompt_tokens_p90,
            "prompt_tokens_cv": d.prompt_tokens_cv,
            "output_tokens_mean": d.output_tokens_mean, "output_tokens_p90": d.output_tokens_p90,
            "output_tokens_cv": d.output_tokens_cv,
            "prompt_output_correlation": d.prompt_output_correlation,
            "long_context_fraction": d.long_context_fraction,
            "concurrency_proxy": d.concurrency_proxy, "kv_pressure_proxy": d.kv_pressure_proxy,
            "has_native_priority": d.has_native_priority, "has_native_slo": d.has_native_slo,
        })
    with open(OUT_DIR / "descriptor_comparison.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(desc_rows[0].keys()))
        w.writeheader(); w.writerows(desc_rows)

    # ---- 6. policy_pair_similarity.csv ----
    pair_rows = []
    policies = list(STAGE0_POLICIES)
    for source, rows in sorted(by_source.items()):
        by_group_local = {(r["window_id"], r["load_region"]): r for r in rows}
        for i in range(len(policies)):
            for j in range(i + 1, len(policies)):
                p1, p2 = policies[i], policies[j]
                diffs = []
                identical = 0
                n = 0
                for key, by_policy in by_group.items():
                    if key[0] != source:
                        continue
                    if p1 not in by_policy or p2 not in by_policy:
                        continue
                    a = by_policy[p1]["arrival_normalized_weighted_goodput"]
                    b = by_policy[p2]["arrival_normalized_weighted_goodput"]
                    n += 1
                    d = abs(a - b)
                    diffs.append(d)
                    if d <= TIE_TOLERANCE:
                        identical += 1
                if n == 0:
                    continue
                pair_rows.append({
                    "source_family": source, "policy_a": p1, "policy_b": p2, "n_conditions": n,
                    "frac_identical_within_tie_tol": identical / n,
                    "mean_abs_diff": sum(diffs) / len(diffs),
                    "max_abs_diff": max(diffs),
                })
    with open(OUT_DIR / "policy_pair_similarity.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(pair_rows[0].keys()))
        w.writeheader(); w.writerows(pair_rows)

    # ---- 7. metric_dependence.csv (ANWG-tied conditions: does another metric differ?) ----
    metric_dep_rows = []
    for r in all_rows:
        if not r["tied"]:
            continue
        other_differs = False
        details = []
        for field in ("completion_fraction", "p95_latency", "slo_violation_rate",
                      "request_throughput", "mean_ttft"):
            rng = r.get(f"{field}_range") if field != "completion_fraction" else r["completion_fraction_range"]
            n_finite = r.get(f"{field}_n_finite") if field != "completion_fraction" else 6
            if rng is None or (n_finite or 0) < 2:
                continue
            # "differs" heuristic: range exceeds the same relative-range rule as Criterion 4
            base = r.get(f"{field}_min") if field != "completion_fraction" else r["completion_fraction_min"]
            differs = (rng > 0) if (base in (0, None)) else ((rng / base) > 0.10)
            if differs:
                other_differs = True
                details.append(field)
        metric_dep_rows.append({
            "source_family": r["source_family"], "window_id": r["window_id"],
            "load_region": r["load_region"],
            "classification": "ANWG_TIED_OTHER_METRIC_DIFFERS" if other_differs else "TIED_ACROSS_METRICS",
            "differing_metrics": ";".join(details),
        })
    with open(OUT_DIR / "metric_dependence.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(metric_dep_rows[0].keys()) if metric_dep_rows else
                            ["source_family", "window_id", "load_region", "classification", "differing_metrics"])
        w.writeheader(); w.writerows(metric_dep_rows)

    # ---- 8. diagnostic_summary.json ----
    def wilson_ci(k, n, z=1.96):
        if n == 0:
            return (None, None)
        p = k / n
        denom = 1 + z ** 2 / n
        center = (p + z ** 2 / (2 * n)) / denom
        half = (z * math.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2))) / denom
        return (max(0.0, center - half), min(1.0, center + half))

    summary = {"per_source": {}, "criterion5_threshold_sensitivity": {}}
    total_non_tied = sum(1 for r in all_rows if not r["tied"])
    counts = {s: sum(1 for r in rows if not r["tied"]) for s, rows in by_source.items()}
    for source, rows in sorted(by_source.items()):
        non_tied = counts[source]
        lo30, hi30 = wilson_ci(non_tied, 30)
        n_windows_source = len({r["window_id"] for r in rows})
        win_non_tied = len({r["window_id"] for r in rows if not r["tied"]})
        lo10, hi10 = wilson_ci(win_non_tied, n_windows_source)
        summary["per_source"][source] = {
            "non_tied_conditions": non_tied, "of_30": non_tied / 30,
            "wilson_95ci_condition_level": [lo30, hi30],
            "windows_non_tied_ge1_region": win_non_tied, "of_10_windows": win_non_tied / n_windows_source,
            "wilson_95ci_window_level": [lo10, hi10],
            "share_of_total_non_tied": non_tied / total_non_tied if total_non_tied else None,
        }
    # arithmetic sensitivity for criterion 5 (14.3% -> 15% floor), purely mechanical
    burst = counts.get("burstgpt", 0)
    others_total = total_non_tied - burst
    x = 0
    while (burst + x) / (total_non_tied + x) < 0.15 and x < 100:
        x += 1
    summary["criterion5_threshold_sensitivity"] = {
        "current_counts": counts, "current_total_non_tied": total_non_tied,
        "current_shares": {s: counts[s] / total_non_tied for s in counts},
        "additional_burstgpt_non_tied_conditions_needed_to_reach_15pct_share": x,
        "note": "purely arithmetic; NOT a recommendation to select more non-tied "
                "BurstGPT conditions post-hoc -- see docs/STAGE0_BURSTGPT_DIAGNOSTIC.md section K",
    }
    with open(OUT_DIR / "diagnostic_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
