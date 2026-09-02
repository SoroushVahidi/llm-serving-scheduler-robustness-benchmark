#!/usr/bin/env python3
"""Phase-12 real statistical-analysis launcher (post-prefreeze,
post-admission). Prepared by the analysis-prefreeze task
(docs/RANKING_PORTABILITY_PHASE12_ANALYSIS_PREFREEZE.md) but NOT executed
by it -- this script is the exact entry point for the subsequent real
analysis run.

FAIL-CLOSED GATES (all must pass, in order, before a single row of the
admitted consolidated artifact is interpreted):

1. Path blindness: every input path is checked against the
   result-blindness guard; reading the live campaign-results tree
   requires the explicit `--allow-live` override (the deliberate
   production run is its sole intended use). The OUTPUT directory is
   never allowed under the live campaign-results tree, no override.
2. Admission: the Phase-12D analysis-admission manifest must say
   `PHASE12_COMPLETED_CAMPAIGN_VALID = true` and
   `PHASE12_ANALYSIS_INPUT_ADMITTED = true`.
3. Frozen campaign identity: the admission manifest's
   `campaign_freeze_sha256` and `full_matrix_hash` must equal the pinned
   frozen values below, byte for byte.
4. Admitted-artifact identity: the SHA-256 of the consolidated artifact
   file's bytes must equal the admission-manifest-bound (and pinned)
   `consolidated_artifact_sha256`.
5. Analysis-code identity: `git rev-parse HEAD` at this repository must
   equal the caller-supplied `--expected-analysis-git-sha` (the exact
   analysis-prefreeze branch HEAD recorded at freeze time). The verified
   SHA is stamped into every output artifact.
6. Output namespace: `--output-dir` must resolve to a path ending in
   `artifacts/analysis/phase12`, must not already exist with content,
   and must not be the admitted input's directory or one of its
   ancestors -- the admitted input is opened read-only and never
   modified.

After the gates, the admitted matrix is RE-VALIDATED independently
(`matrix_validator.validate_completed_campaign`, which never trusts the
consolidator) and the analysis-input manifest is rebuilt through
`input_manifest.build_analysis_input_manifest`, which refuses on any
validation problem. Only then do the frozen analyses run, writing the
six canonical artifacts of `output_writer.CANONICAL_ARTIFACT_RELATIVE_PATHS`.

All analytic choices (metrics, top-k, reversal thresholds, bootstrap
unit/count, Friedman scope, FDR families, sample-complexity ladder,
temporal splits, robustness strata, descriptor set, seeds) come from the
frozen contract module and are not selectable here. The only numeric
parameters the CLI accepts that affect output CONTENT are
`--azure-boundary-epoch-seconds` (an explicit, caller-supplied temporal
boundary the frozen design requires as a parameter, never invented) and
the identity arguments above.

The telemetry explanatory model's reversal-site indicator is frozen
result-blind as follows (no real outcome was consulted to choose it):
for the primary metric, for each load region, each unordered source
pair (X, Y), and each unordered PRIMARY policy pair (a, b), a window w
of source X is a reversal site iff sign(a_w - b_w) is defined, nonzero,
and opposite to the sign of the aggregate (a - b) difference in source
Y at that region (and symmetrically for windows of Y against X's
aggregate). ALL pairs are enumerated and reported; none is selected
based on results.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.ranking_portability.analysis import (  # noqa: E402
    consolidation,  # noqa: F401  (imported so the frozen pipeline graph is complete)
)
from robustbench.ranking_portability.analysis.contract import (  # noqa: E402
    ALL_RANKING_METRICS,
    ANALYSIS_CONTRACT_VERSION,
    BOOTSTRAP_RESAMPLES,
    CAMPAIGN_SOURCES,
    PRIMARY_METRIC,
    PRIMARY_POLICIES,
    SAMPLE_COMPLEXITY_DRAWS_PER_N,
    SIX_REGION_GRID,
)
from robustbench.ranking_portability.analysis.input_manifest import (  # noqa: E402
    build_analysis_input_manifest,
)
from robustbench.ranking_portability.analysis.matrix_validator import (  # noqa: E402
    IMMUTABLE_HASH_MANIFEST_KEYS,
    validate_completed_campaign,
)
from robustbench.ranking_portability.analysis.omnibus import (  # noqa: E402
    apply_fdr_family,
    friedman_for_condition,
)
from robustbench.ranking_portability.analysis.output_writer import (  # noqa: E402
    CANONICAL_ARTIFACT_RELATIVE_PATHS,
    write_analysis_artifact,
)
from robustbench.ranking_portability.analysis.ranking_analysis import (  # noqa: E402
    compare_conditions,
    per_window_policy_values,
)
from robustbench.ranking_portability.analysis.result_blindness import (  # noqa: E402
    assert_not_live_campaign_path,
)
from robustbench.ranking_portability.analysis.reversal_analysis import (  # noqa: E402
    classify_pairwise_reversal,
)
from robustbench.ranking_portability.analysis.robustness import (  # noqa: E402
    ROBUSTNESS_COMPONENT_STATUS,
    all_policy_families,
    filter_four_region_subset,
    filter_leave_one_policy_family_out,
    filter_leave_one_source_out,
    filter_primary_only,
    seed_sensitivity_applicable,
)
from robustbench.ranking_portability.analysis.sample_complexity import (  # noqa: E402
    compare_concentrated_vs_spread,
    run_sample_complexity,
)
from robustbench.ranking_portability.analysis.telemetry_explanation import (  # noqa: E402
    fit_reversal_association,
)
from robustbench.ranking_portability.analysis.temporal_analysis import (  # noqa: E402
    filter_rows_to_windows,
    split_azure_calendar,
    split_bailian_relative,
    split_burstgpt_bisect,
    split_burstgpt_tercile,
)
from robustbench.ranking_portability.phase12_campaign import (  # noqa: E402
    load_campaign_window_ids,
)

# --- Pinned frozen identities (fail-closed gates; identity binding only,
# never outcome content). These are the exact values recorded by the
# Phase-12B prelaunch freeze and the Phase-12D admission manifest. ---
EXPECTED_CAMPAIGN_FREEZE_SHA256 = (
    "81fa3d9b48a2241001e6820942d4542dcc5b5e30973ad9d2786e72972494f57a"
)
EXPECTED_FULL_MATRIX_HASH = (
    "832d96d7ff4d5e8843c233a6a4708bbbbc578ef6b65307c37f5ac127c62c1ccf"
)
EXPECTED_CONSOLIDATED_ARTIFACT_SHA256 = (
    "73adf7d97f06985ec8f8e1c2f794fd43178433eb198e1c00705e817f4bde9c26"
)

ANALYSIS_OUTPUT_NAMESPACE_SUFFIX = ("artifacts", "analysis", "phase12")


class GateRefusal(RuntimeError):
    """A fail-closed launch gate rejected the run. Nothing was analyzed."""


def _refuse(msg: str) -> None:
    raise GateRefusal(f"REFUSING TO RUN: {msg}")


def _sha256_file_bytes(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_head_sha(repo_root: Path) -> str:
    return (
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root)
        .decode()
        .strip()
    )


def verify_launch_gates(
    *,
    admission_manifest_path: Path,
    consolidated_artifact_path: Path,
    campaign_manifest_path: Path,
    compact_window_index_path: Path,
    output_dir: Path,
    expected_analysis_git_sha: str,
    allow_live: bool,
    repo_root: Path = REPO_ROOT,
) -> dict:
    """Runs every fail-closed gate. Returns the parsed admission manifest
    only if ALL gates pass; raises GateRefusal otherwise. Reads file
    bytes solely for identity hashing -- never interprets comparative
    content."""
    for p in (
        admission_manifest_path,
        consolidated_artifact_path,
        campaign_manifest_path,
        compact_window_index_path,
    ):
        assert_not_live_campaign_path(p, allow_live=allow_live)
    # The output namespace is NEVER allowed under the live results tree.
    assert_not_live_campaign_path(output_dir, allow_live=False)

    if not admission_manifest_path.exists():
        _refuse(f"admission manifest not found: {admission_manifest_path}")
    if not consolidated_artifact_path.exists():
        _refuse(f"consolidated artifact not found: {consolidated_artifact_path}")

    with open(admission_manifest_path) as f:
        admission = json.load(f)

    if admission.get("PHASE12_COMPLETED_CAMPAIGN_VALID") is not True:
        _refuse("admission manifest does not declare PHASE12_COMPLETED_CAMPAIGN_VALID = true")
    if admission.get("PHASE12_ANALYSIS_INPUT_ADMITTED") is not True:
        _refuse("admission manifest does not declare PHASE12_ANALYSIS_INPUT_ADMITTED = true")

    if admission.get("campaign_freeze_sha256") != EXPECTED_CAMPAIGN_FREEZE_SHA256:
        _refuse(
            f"campaign_freeze_sha256 mismatch: admission={admission.get('campaign_freeze_sha256')!r} "
            f"expected={EXPECTED_CAMPAIGN_FREEZE_SHA256!r}"
        )
    if admission.get("full_matrix_hash") != EXPECTED_FULL_MATRIX_HASH:
        _refuse(
            f"full_matrix_hash mismatch: admission={admission.get('full_matrix_hash')!r} "
            f"expected={EXPECTED_FULL_MATRIX_HASH!r}"
        )
    if admission.get("consolidated_artifact_sha256") != EXPECTED_CONSOLIDATED_ARTIFACT_SHA256:
        _refuse(
            "consolidated_artifact_sha256 mismatch: "
            f"admission={admission.get('consolidated_artifact_sha256')!r} "
            f"expected={EXPECTED_CONSOLIDATED_ARTIFACT_SHA256!r}"
        )

    actual_artifact_sha = _sha256_file_bytes(consolidated_artifact_path)
    if actual_artifact_sha != EXPECTED_CONSOLIDATED_ARTIFACT_SHA256:
        _refuse(
            f"consolidated artifact file bytes SHA-256 mismatch: file={actual_artifact_sha!r} "
            f"expected={EXPECTED_CONSOLIDATED_ARTIFACT_SHA256!r} -- the admitted input is not "
            "the exact artifact the admission manifest binds."
        )

    actual_git_sha = _git_head_sha(repo_root)
    if actual_git_sha != expected_analysis_git_sha:
        _refuse(
            f"analysis-code git SHA mismatch: HEAD={actual_git_sha!r} "
            f"expected={expected_analysis_git_sha!r} -- run only from the exact frozen "
            "analysis-prefreeze code identity."
        )

    resolved_out = output_dir.resolve()
    parts = tuple(p.lower() for p in resolved_out.parts)
    suffix = ANALYSIS_OUTPUT_NAMESPACE_SUFFIX
    if len(parts) < len(suffix) or parts[-len(suffix):] != suffix:
        _refuse(
            f"output dir {resolved_out} does not end with the canonical analysis namespace "
            f"{'/'.join(suffix)} -- refusing to write analysis artifacts anywhere else."
        )
    resolved_input = consolidated_artifact_path.resolve()
    if resolved_out == resolved_input or resolved_out in resolved_input.parents or resolved_input in resolved_out.parents:
        _refuse("output dir overlaps the admitted input path -- the admitted input is immutable.")
    if resolved_out.exists() and any(resolved_out.iterdir()):
        _refuse(f"output dir {resolved_out} already exists and is non-empty -- refusing to overwrite.")

    return admission


def _unordered_pairs(items):
    return list(itertools.combinations(sorted(items), 2))


def _rows_for(rows, *, source=None, region=None):
    out = rows
    if source is not None:
        out = [r for r in out if r["source_family"] == source]
    if region is not None:
        out = [r for r in out if r["load_region"] == region]
    return out


def _comparison_payload(res) -> dict:
    return {
        "metric": res.metric,
        "condition_x": res.condition_x_label,
        "condition_y": res.condition_y_label,
        "n_policies_compared": res.point.n_policies_compared,
        "kendall_tau": res.point.kendall_tau,
        "kendall_p": res.point.kendall_p,
        "spearman_rho": res.point.spearman_rho,
        "spearman_p": res.point.spearman_p,
        "kendall_tau_ci": list(res.kendall_tau_ci) if res.kendall_tau_ci else None,
        "spearman_rho_ci": list(res.spearman_rho_ci) if res.spearman_rho_ci else None,
        "topk_overlap": {str(k): v for k, v in res.point.topk_overlap.items()},
        "topk_k_reduced": {str(k): v for k, v in res.point.topk_k_reduced.items()},
        "n_conditions_excluded_for_undefined_metric": res.n_conditions_excluded_for_undefined_metric,
    }


def run_analysis(
    *,
    rows,
    window_meta,
    analysis_input_manifest,
    output_dir: Path,
    azure_boundary_epoch_seconds: float,
    n_resamples: int = BOOTSTRAP_RESAMPLES,
    draws_per_n: int = SAMPLE_COMPLEXITY_DRAWS_PER_N,
    metrics=ALL_RANKING_METRICS,
) -> dict:
    """Executes the frozen analysis contract over an admitted, re-validated
    row set and writes the six canonical artifacts. `window_meta` maps
    window_id -> {"source_family", "arrival_time_s_min", "relative_order",
    "descriptor"}. The `n_resamples`/`draws_per_n`/`metrics` parameters
    exist ONLY so synthetic tests can run the same code at toy scale; the
    CLI never overrides the frozen contract defaults."""
    import numpy as np

    output_dir = Path(output_dir)
    primary_rows = filter_primary_only(rows)
    policies = list(PRIMARY_POLICIES)
    rng = np.random.default_rng(0)
    written = {}

    # --- 0. Friedman omnibus FIRST (per metric x load region), before any
    # pairwise decomposition, per the frozen contract. ---
    omnibus_records = []
    friedman_p_by_metric = {m: [] for m in metrics}
    for metric in metrics:
        for region in SIX_REGION_GRID:
            res = friedman_for_condition(
                _rows_for(primary_rows, region=region), metric=metric
            )
            friedman_p_by_metric[metric].append(
                res.p_value if res.p_value is not None else float("nan")
            )
            omnibus_records.append({
                "metric": metric, "load_region": region,
                "statistic": res.statistic, "p_value": res.p_value,
                "n_blocks": res.n_blocks, "n_treatments": res.n_treatments,
                "excluded_policies": res.excluded_policies,
            })
    friedman_fdr = {
        m: apply_fdr_family(f"friedman::{m}", friedman_p_by_metric[m]).rejected
        for m in metrics
    }

    # --- 1. Cross-source ranking comparisons (Kendall tau-b, Spearman rho,
    # top-{1,3}) per metric x region x source pair; BH FDR per
    # (metric, region) family over the Kendall p-values. ---
    ranking_records = {m: [] for m in metrics}
    kendall_p_family = {}
    for metric in metrics:
        for region in SIX_REGION_GRID:
            family_key = f"{metric}::{region}"
            kendall_p_family[family_key] = []
            for sx, sy in _unordered_pairs(CAMPAIGN_SOURCES):
                res = compare_conditions(
                    _rows_for(primary_rows, source=sx, region=region),
                    _rows_for(primary_rows, source=sy, region=region),
                    metric=metric, all_policies=policies,
                    condition_x_label=f"{sx}::{region}",
                    condition_y_label=f"{sy}::{region}",
                    n_resamples=n_resamples, rng=rng,
                )
                kendall_p_family[family_key].append(
                    res.point.kendall_p if res.point.kendall_p is not None else float("nan")
                )
                ranking_records[metric].append(_comparison_payload(res))
    ranking_fdr = {
        k: apply_fdr_family(k, ps).rejected for k, ps in kendall_p_family.items()
    }
    for metric in metrics:
        fam = [f"{metric}::{r}" for r in SIX_REGION_GRID]
        for rec, fdr_flags in zip(
            ranking_records[metric],
            itertools.chain.from_iterable(ranking_fdr[k] for k in fam),
        ):
            rec["bh_fdr_rejected_within_metric_region_family"] = bool(fdr_flags)

    topk_records = {
        m: [
            {
                "condition_x": r["condition_x"], "condition_y": r["condition_y"],
                "topk_overlap": r["topk_overlap"], "topk_k_reduced": r["topk_k_reduced"],
            }
            for r in ranking_records[m]
        ]
        for m in metrics
    }

    # --- 2. Pairwise reversals per metric x region x source pair x primary
    # policy pair, classified by the frozen five-class contract (CI-based;
    # never pooled across the microscopic/unsupported classes). ---
    reversal_records = {m: [] for m in metrics}
    for metric in metrics:
        for region in SIX_REGION_GRID:
            for sx, sy in _unordered_pairs(CAMPAIGN_SOURCES):
                rows_x = _rows_for(primary_rows, source=sx, region=region)
                rows_y = _rows_for(primary_rows, source=sy, region=region)
                for pa, pb in _unordered_pairs(policies):
                    res = classify_pairwise_reversal(
                        rows_x, rows_y, policy_a=pa, policy_b=pb,
                        metric=metric, n_resamples=n_resamples, rng=rng,
                    )
                    reversal_records[metric].append({
                        "metric": metric, "load_region": region,
                        "condition_x": f"{sx}::{region}", "condition_y": f"{sy}::{region}",
                        "policy_a": pa, "policy_b": pb,
                        "classification": res.classification.value,
                        "diff_x": res.diff_x, "diff_y": res.diff_y,
                        "margin_x": res.margin_x, "margin_y": res.margin_y,
                        "ci_x": list(res.ci_x) if res.ci_x else None,
                        "ci_y": list(res.ci_y) if res.ci_y else None,
                        "fdr_family": f"{metric}::{region}",
                    })

    # --- 3. Sample complexity per source x metric (frozen ladder), plus the
    # purely descriptive concentrated-vs-spread budget comparison. ---
    sample_records = []
    for source in CAMPAIGN_SOURCES:
        source_rows = _rows_for(primary_rows, source=source)
        for metric in metrics:
            per_window = per_window_policy_values(source_rows, metric)
            res = run_sample_complexity(
                per_window, policies=policies, draws_per_n=draws_per_n,
            )
            sample_records.append({
                "source": source, "metric": metric,
                "reference_ranking": list(res.reference_ranking),
                "points": [
                    {
                        "n": p.n, "n_draws": p.n_draws, "seed": p.seed,
                        "p_exact_recovery": p.p_exact_recovery,
                        "p_topk_recovery": {str(k): v for k, v in p.p_topk_recovery.items()},
                    }
                    for p in res.points
                ],
                "first_n_meeting_exact_threshold": res.first_n_meeting_exact_threshold,
                "first_n_meeting_topk_threshold": {
                    str(k): v for k, v in res.first_n_meeting_topk_threshold.items()
                },
            })
    concentrated_records = []
    for metric in metrics:
        per_window_by_source = {
            s: per_window_policy_values(_rows_for(primary_rows, source=s), metric)
            for s in CAMPAIGN_SOURCES
        }
        res = compare_concentrated_vs_spread(
            per_window_by_source, policies=policies, n_draws=draws_per_n,
        )
        concentrated_records.append({
            "metric": metric, "n_total": res.n_total, "n_draws": res.n_draws,
            "mean_tau_concentrated": res.mean_tau_concentrated,
            "mean_tau_spread": res.mean_tau_spread,
        })

    # --- 4. Temporal robustness (source held fixed; cross-source toolkit
    # reused unchanged; primary metric). ---
    timestamps = {w: m["arrival_time_s_min"] for w, m in window_meta.items()}
    relative_order = {w: m["relative_order"] for w, m in window_meta.items()}
    temporal_records = []
    split_specs = {
        "burstgpt": [
            ("TERCILE", split_burstgpt_tercile(timestamps), False),
            ("BISECT", split_burstgpt_bisect(timestamps), True),
        ],
        "azure_llm_2024": [
            ("CALENDAR_BOUNDARY", split_azure_calendar(
                timestamps, boundary_epoch_seconds=azure_boundary_epoch_seconds,
            ), False),
        ],
        "bailian_qwen": [],
    }
    bailian_split = split_bailian_relative(relative_order)
    split_specs["bailian_qwen"].append(
        (bailian_split.chronology_type, bailian_split.groups, False)
    )
    for source, splits in split_specs.items():
        source_rows = _rows_for(primary_rows, source=source)
        source_windows = {w for w, m in window_meta.items() if m["source_family"] == source}
        for split_name, groups, is_sensitivity in splits:
            groups = {g: [w for w in ws if w in source_windows] for g, ws in groups.items()}
            for region in SIX_REGION_GRID:
                for gx, gy in _unordered_pairs(groups):
                    res = compare_conditions(
                        _rows_for(filter_rows_to_windows(source_rows, groups[gx]), region=region),
                        _rows_for(filter_rows_to_windows(source_rows, groups[gy]), region=region),
                        metric=PRIMARY_METRIC, all_policies=policies,
                        condition_x_label=f"{source}::{region}::{split_name}::{gx}",
                        condition_y_label=f"{source}::{region}::{split_name}::{gy}",
                        n_resamples=n_resamples, rng=rng,
                    )
                    payload = _comparison_payload(res)
                    payload["source"] = source
                    payload["split"] = split_name
                    payload["is_sensitivity_split"] = is_sensitivity
                    if source == "bailian_qwen":
                        payload["chronology_label"] = bailian_split.chronology_type
                    temporal_records.append(payload)

    # --- 5. Robustness strata: registry + headline (primary metric)
    # cross-source tau recomputed under each row-filter stratum. ---
    def _headline_taus(stratum_rows):
        taus = []
        for region in SIX_REGION_GRID:
            for sx, sy in _unordered_pairs(CAMPAIGN_SOURCES):
                rx = _rows_for(stratum_rows, source=sx, region=region)
                ry = _rows_for(stratum_rows, source=sy, region=region)
                if not rx or not ry:
                    continue
                res = compare_conditions(
                    rx, ry, metric=PRIMARY_METRIC, all_policies=policies,
                    condition_x_label=f"{sx}::{region}",
                    condition_y_label=f"{sy}::{region}",
                    n_resamples=n_resamples, rng=rng,
                )
                taus.append({
                    "load_region": region, "source_x": sx, "source_y": sy,
                    "kendall_tau": res.point.kendall_tau,
                })
        return taus

    robustness_payload = {
        "component_status": {
            k: {
                "implemented_as_postprocessing": v.implemented_as_postprocessing,
                "new_execution_required_for_this_sensitivity": v.new_execution_required_for_this_sensitivity,
                "note": v.note,
            }
            for k, v in ROBUSTNESS_COMPONENT_STATUS.items()
        },
        "seed_sensitivity_applicable": seed_sensitivity_applicable(),
        "headline_metric": PRIMARY_METRIC,
        "strata": {"PRIMARY_ONLY": _headline_taus(primary_rows)},
    }
    for excluded in CAMPAIGN_SOURCES:
        robustness_payload["strata"][f"LEAVE_ONE_SOURCE_OUT::{excluded}"] = _headline_taus(
            filter_leave_one_source_out(primary_rows, excluded)
        )
    robustness_payload["strata"]["LOAD_CALIBRATION_SENSITIVITY::FOUR_REGION_SUBSET"] = _headline_taus(
        filter_four_region_subset(primary_rows)
    )
    for family in all_policy_families():
        robustness_payload["strata"][f"LEAVE_ONE_POLICY_FAMILY_OUT::{family}"] = _headline_taus(
            filter_leave_one_policy_family_out(primary_rows, family)
        )

    # --- 6. Telemetry/descriptor explanatory model (never predictive):
    # ALL primary policy pairs x source pairs x regions enumerated, fixed
    # descriptor set, fixed result-blind reversal-site rule (module docstring). ---
    descriptors = {w: m["descriptor"] for w, m in window_meta.items()}
    telemetry_records = []
    for region in SIX_REGION_GRID:
        for sx, sy in _unordered_pairs(CAMPAIGN_SOURCES):
            for pa, pb in _unordered_pairs(policies):
                agg_sign = {}
                for s in (sx, sy):
                    pw = per_window_policy_values(
                        _rows_for(primary_rows, source=s, region=region), PRIMARY_METRIC
                    )
                    diffs = [d[pa] - d[pb] for d in pw.values() if pa in d and pb in d]
                    mean_diff = float(np.mean(diffs)) if diffs else 0.0
                    agg_sign[s] = (1 if mean_diff > 0 else (-1 if mean_diff < 0 else 0))
                indicator = {}
                for s, other in ((sx, sy), (sy, sx)):
                    pw = per_window_policy_values(
                        _rows_for(primary_rows, source=s, region=region), PRIMARY_METRIC
                    )
                    for w, d in pw.items():
                        if pa not in d or pb not in d:
                            continue
                        w_sign = 1 if d[pa] - d[pb] > 0 else (-1 if d[pa] - d[pb] < 0 else 0)
                        if w_sign == 0 or agg_sign[other] == 0:
                            continue
                        indicator[w] = w_sign != agg_sign[other]
                fit = fit_reversal_association(descriptors, indicator)
                telemetry_records.append({
                    "metric": PRIMARY_METRIC, "load_region": region,
                    "source_x": sx, "source_y": sy, "policy_a": pa, "policy_b": pb,
                    "features": fit.features,
                    "coefficients": fit.coefficients,
                    "intercept": fit.intercept,
                    "n_observations": fit.n_observations,
                    "n_reversal_sites": fit.n_reversal_sites,
                    "n_excluded_missing_descriptor": fit.n_excluded_missing_descriptor,
                    "converged": fit.converged,
                    "explanatory_only_never_a_selector": True,
                })

    # --- Write the six canonical artifacts, each stamped with the full
    # four-field identity of the admitted input + analysis code. ---
    artifacts = {
        "ranking_correlations": {
            "analysis_contract_version": ANALYSIS_CONTRACT_VERSION,
            "policies": policies, "metrics": list(metrics),
            "bootstrap_resamples": n_resamples,
            "omnibus_friedman": omnibus_records,
            "omnibus_friedman_bh_fdr_by_metric": {
                m: [bool(b) for b in flags] for m, flags in friedman_fdr.items()
            },
            "comparisons": ranking_records,
        },
        "topk_overlap": {"top_k_values": [1, 3], "comparisons": topk_records},
        "pairwise_reversals": {
            "reversal_contract": "five-class frozen contract (reversal_analysis.ReversalClass)",
            "fdr_family_note": "families are per (metric, load_region); reversal decisions use "
                               "the frozen CI-exclusion rule, never pooled across classes",
            "records": reversal_records,
        },
        "sample_complexity": {
            "ladder_n_values": sorted({p["n"] for r in sample_records for p in r["points"]}),
            "draws_per_n": draws_per_n,
            "per_source_metric": sample_records,
            "concentrated_vs_spread": concentrated_records,
        },
        "temporal_robustness": {"records": temporal_records},
        "telemetry_explanation": {
            "model": "single pre-specified logistic regression, fixed descriptor set",
            "records": telemetry_records,
            "robustness": robustness_payload,
        },
    }
    for key, payload in artifacts.items():
        rel = CANONICAL_ARTIFACT_RELATIVE_PATHS[key]
        out_path = output_dir / Path(rel).name
        write_analysis_artifact(out_path, payload, analysis_input_manifest=analysis_input_manifest)
        written[key] = str(out_path)
    return written


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--admission-manifest", type=Path, required=True,
                    help="Phase-12D analysis-admission manifest "
                         "(ranking_portability_phase12_analysis_input.json)")
    ap.add_argument("--consolidated-artifact", type=Path, required=True,
                    help="Admitted consolidated campaign artifact (JSON with a 'cells' dict)")
    ap.add_argument("--campaign-manifest", type=Path, required=True,
                    help="Frozen Phase-12B campaign freeze manifest "
                         "(ranking_portability_phase12_campaign_freeze.json)")
    ap.add_argument("--compact-window-index", type=Path, required=True,
                    help="Frozen Phase-10 compact window index "
                         "(ranking_portability_pilot_v2_windows_index.json)")
    ap.add_argument("--output-dir", type=Path, required=True,
                    help="Must resolve to a path ending artifacts/analysis/phase12; "
                         "must not already contain files")
    ap.add_argument("--expected-analysis-git-sha", type=str, required=True,
                    help="Exact analysis-prefreeze branch HEAD SHA this run is pinned to; "
                         "the launcher refuses if the checkout differs")
    ap.add_argument("--azure-boundary-epoch-seconds", type=float, required=True,
                    help="Explicit calendar boundary for the Azure-2024 temporal split "
                         "(frozen collection-window boundary; never invented by the code)")
    ap.add_argument("--allow-live", action="store_true", default=False,
                    help="Lift the result-blindness path guard for the deliberate "
                         "production run (never used by prefreeze tests)")
    args = ap.parse_args(argv)

    try:
        verify_launch_gates(
            admission_manifest_path=args.admission_manifest,
            consolidated_artifact_path=args.consolidated_artifact,
            campaign_manifest_path=args.campaign_manifest,
            compact_window_index_path=args.compact_window_index,
            output_dir=args.output_dir,
            expected_analysis_git_sha=args.expected_analysis_git_sha,
            allow_live=args.allow_live,
        )
    except GateRefusal as e:
        print(e)
        return 2

    with open(args.consolidated_artifact) as f:
        consolidated = json.load(f)
    with open(args.campaign_manifest) as f:
        campaign_manifest = json.load(f)
    with open(args.compact_window_index) as f:
        compact_index = json.load(f)

    rows = consolidated["cells"]
    window_ids_by_source = load_campaign_window_ids(compact_index)

    # Independent re-validation of the admitted matrix -- the launcher
    # never trusts the consolidator's or the admission manifest's say-so.
    expected_hashes = {k: campaign_manifest.get(k) for k in IMMUTABLE_HASH_MANIFEST_KEYS}
    report = validate_completed_campaign(
        manifest=campaign_manifest,
        consolidated_rows=rows,
        window_ids_by_source=window_ids_by_source,
        expected_immutable_hashes=expected_hashes,
    )
    if not report.valid:
        print("REFUSING TO RUN: independent matrix re-validation failed:")
        for p in report.problems[:20]:
            print(f"PROBLEM: {p}")
        return 2

    analysis_input_manifest = build_analysis_input_manifest(
        campaign_freeze_sha256=EXPECTED_CAMPAIGN_FREEZE_SHA256,
        consolidated_rows=rows,
        matrix_validation_problems=report.problems,
        repo_root=REPO_ROOT,
    )

    window_meta = {}
    for w in compact_index["windows"]:
        window_meta[w["window_id"]] = {
            "source_family": w["source_family"],
            "arrival_time_s_min": w["arrival_time_s_min"],
            "descriptor": w.get("descriptor", {}),
        }
    for source, window_ids in window_ids_by_source.items():
        for i, wid in enumerate(window_ids):
            window_meta[wid]["relative_order"] = i

    written = run_analysis(
        rows=list(rows.values()),
        window_meta=window_meta,
        analysis_input_manifest=analysis_input_manifest,
        output_dir=args.output_dir,
        azure_boundary_epoch_seconds=args.azure_boundary_epoch_seconds,
    )
    print(f"PHASE12_ANALYSIS_INPUT_ADMITTED = YES (re-verified)")
    print(f"analysis_contract_version = {ANALYSIS_CONTRACT_VERSION}")
    for key, path in written.items():
        print(f"wrote {key}: {path}")
    print("PHASE12_REAL_ANALYSIS_STATUS = COMPLETE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
