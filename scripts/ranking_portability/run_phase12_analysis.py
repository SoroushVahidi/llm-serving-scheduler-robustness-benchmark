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
7. Frozen temporal boundary: `--azure-boundary-epoch-seconds` must equal
   the canonical frozen value
   `contract.AZURE_2024_CALENDAR_BOUNDARY_EPOCH_SECONDS` (1715731200.0 =
   2024-05-15T00:00:00Z, the exact midpoint of the frozen 2024-05-10..
   2024-05-19 Azure-2024 collection window) -- the boundary is frozen,
   not operator-tunable.

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

The telemetry explanatory model's reversal-site indicator is the frozen
plan's window-indexed meaningful-reversal definition
(docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md S/A indexes a reversal "at a
given (source-pair, window, load-region, metric)"; S/G of
docs/STATISTICAL_ANALYSIS_PLAN.md asks whether "a given window is a
reversal site for a given pair (A, B)"): for the primary metric, for
each load region, each unordered source pair (X, Y), and each unordered
PRIMARY policy pair (a, b), a window w of source X is a reversal site
iff (i) the sign of (a_w - b_w) is defined, nonzero, and opposite to
the sign of the aggregate (a - b) difference in source Y at that
region, AND (ii) the frozen practical margin gate (winning margin > 10%
of the losing policy's value) holds in BOTH directions (window side and
other-source aggregate side). Windows where any quantity is undefined
or the margin is unestimable (zero loser) are excluded, never imputed
-- mirroring the frozen reversal contract. Symmetrically for windows of
Y against X's aggregate. ALL pairs are enumerated and reported; none is
selected based on results, and no real outcome was consulted to choose
this rule (it is the S/A definition applied at window level).

Multiplicity correction (frozen, docs/STATISTICAL_ANALYSIS_PLAN.md
"Multiple-testing correction"): Benjamini-Hochberg FDR q=0.05 per family
IS applied to (1) the Friedman omnibus p-values within each metric
family across load regions, (2) the Kendall-tau p-values within each
(metric, load-region) cross-source ranking-comparison family, and (3)
the pairwise reversal tests within each (metric, load-region) family --
the reversal per-pair p-value being the intersection-union combination
max(p_x, p_y) (BOTH conditions must be supported) of the frozen
block-bootstrap sign-test p-values read off the same resamples that
back the preregistered CI rule (reversal_analysis._bootstrap_diff_ci).
The frozen five-class classification itself is unchanged; the
multiplicity-corrected headline flag is `supported_after_fdr`.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.ranking_portability.analysis import (  # noqa: E402
    consolidation,  # noqa: F401  (imported so the frozen pipeline graph is complete)
)
from robustbench.ranking_portability.analysis.contract import (  # noqa: E402
    ALL_RANKING_METRICS,
    ANALYSIS_CONTRACT_VERSION,
    AZURE_2024_CALENDAR_BOUNDARY_EPOCH_SECONDS,
    BOOTSTRAP_RESAMPLES,
    CAMPAIGN_SOURCES,
    PRIMARY_METRIC,
    PRIMARY_POLICIES,
    REVERSAL_PRACTICAL_MARGIN_FRACTION,
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
    ReversalClass,
    _diff_and_margin,
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


def _normalize_cells_container(raw) -> dict:
    """Accepts the admitted artifact's `cells` in either the canonical
    dict form ({cell_id: row, ...}) or the list form ([{"cell_id": ...,
    ...}, ...]) and returns the canonical dict. Fail-closed: rejects
    duplicates in the list form, missing/empty/non-string `cell_id`
    values, non-dict list elements, type mismatches between the list's
    cell_ids and the rows' own `cell_id` fields, and any non-list/non-dict
    container."""
    if isinstance(raw, dict):
        for key, row in raw.items():
            if not isinstance(row, dict):
                _refuse(
                    f"cells dict value for key {key!r} is not a dict "
                    f"(got {type(row).__name__})"
                )
            cid = row.get("cell_id")
            if not isinstance(cid, str) or cid == "":
                _refuse(
                    f"cells dict row for key {key!r} has a missing/empty/"
                    f"non-string cell_id ({cid!r})"
                )
            if cid != key:
                _refuse(
                    f"cells dict key {key!r} does not match the row's "
                    f"own cell_id {cid!r}"
                )
        return raw
    if isinstance(raw, list):
        out: dict = {}
        for i, item in enumerate(raw):
            if not isinstance(item, dict):
                _refuse(
                    f"cells list element [{i}] is not a dict "
                    f"(got {type(item).__name__})"
                )
            cid = item.get("cell_id")
            if cid is None:
                _refuse(f"cells list element [{i}] has no 'cell_id' key")
            if not isinstance(cid, str):
                _refuse(
                    f"cells list element [{i}] cell_id is not a string "
                    f"(got {type(cid).__name__})"
                )
            if cid == "":
                _refuse(f"cells list element [{i}] has an empty cell_id")
            if cid in out:
                _refuse(f"cells list contains duplicate cell_id {cid!r}")
            out[cid] = item
        return out
    _refuse(
        f"cells container is neither a dict nor a list "
        f"(got {type(raw).__name__})"
    )


def verify_launch_gates(
    *,
    admission_manifest_path: Path,
    consolidated_artifact_path: Path,
    campaign_manifest_path: Path,
    compact_window_index_path: Path,
    output_dir: Path,
    expected_analysis_git_sha: str,
    azure_boundary_epoch_seconds: float,
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

    if azure_boundary_epoch_seconds != AZURE_2024_CALENDAR_BOUNDARY_EPOCH_SECONDS:
        _refuse(
            f"azure boundary epoch {azure_boundary_epoch_seconds!r} does not equal the frozen "
            f"canonical boundary {AZURE_2024_CALENDAR_BOUNDARY_EPOCH_SECONDS!r} "
            "(2024-05-15T00:00:00Z, exact midpoint of the frozen 2024-05-10..2024-05-19 "
            "Azure-2024 collection window, docs/EVIDENCE_INDEPENDENCE_PLAN.md) -- the "
            "calendar split boundary is frozen, not operator-tunable."
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


def _build_temporal_split_specs(window_meta, azure_boundary_epoch_seconds):
    """Builds the per-source temporal split specifications. SOURCE
    ISOLATION IS MANDATORY (docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md
    S/D, "source held fixed"): each source's temporal groups are computed
    from THAT SOURCE'S windows alone -- BurstGPT terciles/bisect over the
    40 BurstGPT timestamps only, Azure's calendar split over the 40 Azure
    timestamps only, Bailian's relative-order bisect over the 40 Bailian
    windows only. No other source's timestamps or order metadata may
    influence a source's split boundaries or group sizes."""
    def _source_map(key, source):
        return {
            w: m[key] for w, m in window_meta.items()
            if m["source_family"] == source
        }

    burstgpt_timestamps = _source_map("arrival_time_s_min", "burstgpt")
    azure_timestamps = _source_map("arrival_time_s_min", "azure_llm_2024")
    bailian_relative_order = _source_map("relative_order", "bailian_qwen")
    split_specs = {
        "burstgpt": [
            ("TERCILE", split_burstgpt_tercile(burstgpt_timestamps), False),
            ("BISECT", split_burstgpt_bisect(burstgpt_timestamps), True),
        ],
        "azure_llm_2024": [
            ("CALENDAR_BOUNDARY", split_azure_calendar(
                azure_timestamps, boundary_epoch_seconds=azure_boundary_epoch_seconds,
            ), False),
        ],
        "bailian_qwen": [],
    }
    bailian_split = split_bailian_relative(bailian_relative_order)
    split_specs["bailian_qwen"].append(
        (bailian_split.chronology_type, bailian_split.groups, False)
    )
    return split_specs


def _window_reversal_sites(rows, *, region, source_x, source_y, policy_a, policy_b):
    """The frozen window-level meaningful-reversal-site rule
    (docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md S/A applied at window level;
    docs/STATISTICAL_ANALYSIS_PLAN.md S/G). A window w of source X is a
    reversal site iff (i) the sign of (a_w - b_w) is defined, nonzero, and
    opposite to the sign of source Y's aggregate (a - b) difference at
    `region`, AND (ii) the frozen practical margin gate
    (REVERSAL_PRACTICAL_MARGIN_FRACTION) holds in BOTH directions. Windows
    with undefined values, zero-loser (unestimable) margins, exact ties,
    or microscopic margins are EXCLUDED from the indicator entirely
    (never imputed, never counted as non-sites) -- mirroring the frozen
    reversal contract's UNDEFINED_UNESTIMABLE / MICROSCOPIC classes."""
    agg = {}
    for s in (source_x, source_y):
        pw = per_window_policy_values(
            _rows_for(rows, source=s, region=region), PRIMARY_METRIC
        )
        pairs = [(d[policy_a], d[policy_b]) for d in pw.values()
                 if policy_a in d and policy_b in d]
        mean_a = float(np.mean([p[0] for p in pairs])) if pairs else None
        mean_b = float(np.mean([p[1] for p in pairs])) if pairs else None
        agg[s] = _diff_and_margin(mean_a, mean_b)
    indicator = {}
    for s, other in ((source_x, source_y), (source_y, source_x)):
        diff_o, margin_o = agg[other]
        if (
            diff_o is None or margin_o is None or diff_o == 0
            or margin_o <= REVERSAL_PRACTICAL_MARGIN_FRACTION
        ):
            continue  # other direction fails the frozen gate: no site estimable
        pw = per_window_policy_values(
            _rows_for(rows, source=s, region=region), PRIMARY_METRIC
        )
        for w, d in pw.items():
            if policy_a not in d or policy_b not in d:
                continue
            w_diff, w_margin = _diff_and_margin(d[policy_a], d[policy_b])
            if (
                w_diff is None or w_margin is None or w_diff == 0
                or w_margin <= REVERSAL_PRACTICAL_MARGIN_FRACTION
            ):
                continue  # unestimable or microscopic: excluded, never imputed
            indicator[w] = (w_diff > 0) != (diff_o > 0)
    return indicator


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
    output_dir = Path(output_dir)
    primary_rows = filter_primary_only(rows)
    policies = list(PRIMARY_POLICIES)
    rng = np.random.default_rng(0)
    written = {}

    # --- 0. Friedman omnibus FIRST (per metric x load region), before any
    # pairwise decomposition, per the frozen contract. Scope frozen by
    # docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md S/B: "Friedman rank-sum test
    # ACROSS SOURCES (block = window, treatment = policy) ... per metric and
    # load region" -- i.e. at a given (metric, load region) the blocks are
    # ALL 120 windows from all three sources pooled; source is not a
    # separate Friedman axis. The per-source temporal/heterogeneity
    # questions are answered by S/D's within-source splits, not by splitting
    # the omnibus. ---
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
    reversal_family_p = {}  # (metric, region) -> list of (record, p_pair)
    for metric in metrics:
        for region in SIX_REGION_GRID:
            family_members = []
            for sx, sy in _unordered_pairs(CAMPAIGN_SOURCES):
                rows_x = _rows_for(primary_rows, source=sx, region=region)
                rows_y = _rows_for(primary_rows, source=sy, region=region)
                for pa, pb in _unordered_pairs(policies):
                    res = classify_pairwise_reversal(
                        rows_x, rows_y, policy_a=pa, policy_b=pb,
                        metric=metric, n_resamples=n_resamples, rng=rng,
                    )
                    rec = {
                        "metric": metric, "load_region": region,
                        "condition_x": f"{sx}::{region}", "condition_y": f"{sy}::{region}",
                        "policy_a": pa, "policy_b": pb,
                        "classification": res.classification.value,
                        "diff_x": res.diff_x, "diff_y": res.diff_y,
                        "margin_x": res.margin_x, "margin_y": res.margin_y,
                        "ci_x": list(res.ci_x) if res.ci_x else None,
                        "ci_y": list(res.ci_y) if res.ci_y else None,
                        "p_x": res.p_x, "p_y": res.p_y,
                        "fdr_family": f"{metric}::{region}",
                    }
                    reversal_records[metric].append(rec)
                    # BH family membership (docs/STATISTICAL_ANALYSIS_PLAN.md
                    # "Multiple-testing correction": "all pairwise reversal
                    # tests within one load level"): exactly the tests that
                    # REACHED the pre-registered statistical-support stage
                    # (sign change + both practical margins pass). The
                    # per-pair p-value is the intersection-union combination
                    # max(p_x, p_y) -- BOTH conditions must show a
                    # statistically supported direction -- of the frozen
                    # block-bootstrap sign-test p-values. Tests that never
                    # reached the support stage (no sign change, microscopic
                    # margin, unestimable) are recorded separately by the
                    # frozen contract and are not reversal hypotheses.
                    if res.classification in (
                        ReversalClass.SUPPORTED_PRACTICAL_REVERSAL,
                        ReversalClass.UNSUPPORTED_SIGN_CHANGE_WIDE_CI,
                    ):
                        p_pair = (
                            max(res.p_x, res.p_y)
                            if res.p_x is not None and res.p_y is not None
                            else float("nan")
                        )
                        family_members.append((rec, p_pair))
            reversal_family_p[(metric, region)] = family_members
    # Apply the frozen per-family BH FDR (q = FDR_Q) to the reversal tests.
    for (metric, region), members in reversal_family_p.items():
        fdr = apply_fdr_family(
            f"{metric}::{region}", [p for _, p in members],
        )
        for (rec, p_pair), rejected in zip(members, fdr.rejected):
            rec["bh_fdr_p_pair_iut"] = p_pair
            rec["bh_fdr_rejected_within_metric_loadregion_family"] = bool(rejected)
            rec["supported_after_fdr"] = bool(
                rejected
                and rec["classification"] == ReversalClass.SUPPORTED_PRACTICAL_REVERSAL.value
            )
    # Tests that never reached the statistical-support stage carry no
    # reversal hypothesis: no p-value, never rejected, never supported.
    for metric in metrics:
        for rec in reversal_records[metric]:
            if "bh_fdr_p_pair_iut" not in rec:
                rec["bh_fdr_p_pair_iut"] = None
                rec["bh_fdr_rejected_within_metric_loadregion_family"] = None
                rec["supported_after_fdr"] = False

    # --- 3. Sample complexity per source x metric (frozen ladder), plus the
    # purely descriptive concentrated-vs-spread budget comparison. Scope is
    # frozen by docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md S/C ("reported per
    # source and per metric"; ladder top n=40 = "full window count";
    # concentrated-vs-spread reference = "the full 3x40 cross-source
    # reference") and docs/STATISTICAL_ANALYSIS_PLAN.md S/F ("per source
    # family and per metric"): the unit is the 40 frozen WINDOWS of one
    # source (load regions pooled within a window's per_window aggregate);
    # it is NOT indexed by load region -- the ladder maximum 40 equals the
    # per-source window count exactly. ---
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
    temporal_records = []
    split_specs = _build_temporal_split_specs(window_meta, azure_boundary_epoch_seconds)
    for source, splits in split_specs.items():
        source_rows = _rows_for(primary_rows, source=source)
        for split_name, groups, is_sensitivity in splits:
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
                        payload["chronology_label"] = split_name  # RELATIVE_CHRONOLOGY_ONLY
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
    # descriptor set, reversal-site rule = the frozen plan's window-indexed
    # meaningful-reversal definition (see module docstring): sign flip
    # against the other source's aggregate PLUS the frozen 10% margin gate
    # satisfied in BOTH directions; windows where the margin is unestimable
    # (undefined value or zero loser) are excluded, never imputed --
    # mirroring the frozen reversal contract exactly. ---
    descriptors = {w: m["descriptor"] for w, m in window_meta.items()}
    telemetry_records = []
    for region in SIX_REGION_GRID:
        for sx, sy in _unordered_pairs(CAMPAIGN_SOURCES):
            for pa, pb in _unordered_pairs(policies):
                indicator = _window_reversal_sites(
                    primary_rows, region=region,
                    source_x=sx, source_y=sy, policy_a=pa, policy_b=pb,
                )
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
            "fdr_note": "Benjamini-Hochberg FDR (q=0.05) IS applied to the reversal "
                        "family per (metric, load_region): family members are the tests "
                        "that reached the pre-registered statistical-support stage "
                        "(sign change + both margins pass); per-pair p = max(p_x, p_y) "
                        "(intersection-union over both conditions) of the frozen "
                        "block-bootstrap sign-test p-values. `supported_after_fdr` is "
                        "the multiplicity-corrected supported-reversal flag.",
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
                    help="Calendar boundary for the Azure-2024 temporal split; must equal "
                         "the frozen canonical value "
                         f"{AZURE_2024_CALENDAR_BOUNDARY_EPOCH_SECONDS} "
                         "(2024-05-15T00:00:00Z, contract.py) -- verified fail-closed")
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
            azure_boundary_epoch_seconds=args.azure_boundary_epoch_seconds,
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

    rows = _normalize_cells_container(consolidated["cells"])
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
