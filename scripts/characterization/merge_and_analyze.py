#!/usr/bin/env python3
"""Merge per-source window/descriptor fragments and run every section-6
distribution-shift analysis from
docs/WORKLOAD_DISTRIBUTION_CHARACTERIZATION_PROTOCOL.md. Outcome-blind:
never imports robustbench.policies / robustbench.simulator /
robustbench.evaluation, never touches a scheduler outcome.

Expects `--fragments-dir` to already contain, for every source built by
`build_and_describe_windows.py`:
    windows_{source}.json
    descriptors_{source}.parquet
    integrity_{source}.json

Writes every file listed in docs/WORKLOAD_DISTRIBUTION_CHARACTERIZATION_PROTOCOL.md
section 11 into `--results-dir`, plus the final combined manifest into
`--manifest-out`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from robustbench.characterization.descriptors import (  # noqa: E402
    COMMON_NUMERIC_FEATURES,
    DESCRIPTOR_SCHEMA_VERSION,
)
from robustbench.characterization.distances import (  # noqa: E402
    benjamini_hochberg,
    bootstrap_mean_ci,
    centroid_euclidean_distance,
    mahalanobis_centroid_distance,
    mann_whitney_with_effect_size,
    mmd_rbf_unbiased,
    pairwise_row_distances,
    univariate_pair_distance,
)
from robustbench.characterization.separability import (  # noqa: E402
    SEPARABILITY_MODEL_VERSION,
    evaluate_source_separability,
)

PRIMARY_WINDOW_SIZE = 200
ALL_WINDOW_SIZES = (100, 200, 500)
STATISTICAL_PROTOCOL_VERSION = "workload_characterization_statistical_protocol_v1"


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).decode().strip()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_json(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def load_fragments(fragments_dir: Path, sources: list[str]) -> tuple[dict, pd.DataFrame, dict]:
    manifests = {}
    frames = []
    integrity = {}
    for source in sources:
        manifest_path = fragments_dir / f"windows_{source}.json"
        parquet_path = fragments_dir / f"descriptors_{source}.parquet"
        integrity_path = fragments_dir / f"integrity_{source}.json"
        if not manifest_path.exists():
            print(f"WARNING: missing fragment for source={source} ({manifest_path}); skipping", file=sys.stderr)
            continue
        with open(manifest_path) as f:
            manifests[source] = json.load(f)
        frames.append(pd.read_parquet(parquet_path))
        with open(integrity_path) as f:
            integrity[source] = json.load(f)
    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return manifests, combined, integrity


def build_feature_matrix(df: pd.DataFrame, features: list[str]) -> tuple[np.ndarray, dict]:
    """Column-median imputation (pooled across all rows passed in), with a
    transparent count of how many cells were imputed per feature -- never
    silently hidden. Rows where ALL features are NaN are dropped (would
    contribute nothing but noise to a centroid/classifier)."""
    sub = df[features].astype(float)
    all_nan_rows = sub.isna().all(axis=1)
    sub = sub.loc[~all_nan_rows]
    imputed_counts = {}
    for col in features:
        n_missing = int(sub[col].isna().sum())
        imputed_counts[col] = n_missing
        if n_missing > 0:
            median = sub[col].median()
            sub[col] = sub[col].fillna(median if not np.isnan(median) else 0.0)
    return sub.to_numpy(dtype=float), {"imputed_counts": imputed_counts, "n_rows_dropped_all_nan": int(all_nan_rows.sum())}


def standardize_matrix(X: np.ndarray) -> np.ndarray:
    mean = X.mean(axis=0)
    std = X.std(axis=0)
    std_safe = np.where(std > 0, std, 1.0)
    return (X - mean) / std_safe


def univariate_cross_source(df_ws: pd.DataFrame, sources: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Section 6A. Returns (source_summary, pairwise_distances)."""
    summary_rows = []
    for source in sources:
        sub = df_ws[df_ws.source_family == source]
        for feat in COMMON_NUMERIC_FEATURES:
            vals = sub[feat].dropna().to_numpy(dtype=float)
            lo, hi = bootstrap_mean_ci(vals) if vals.size >= 2 else (None, None)
            summary_rows.append({
                "source_family": source,
                "feature": feat,
                "n_windows": int(vals.size),
                "mean": float(np.mean(vals)) if vals.size else None,
                "std": float(np.std(vals)) if vals.size else None,
                "ci95_lo": lo,
                "ci95_hi": hi,
            })
    summary_df = pd.DataFrame(summary_rows)

    pair_rows = []
    for feat in COMMON_NUMERIC_FEATURES:
        raw_pvals = []
        pair_indices = []
        for s_a, s_b in combinations(sources, 2):
            a = df_ws[df_ws.source_family == s_a][feat].dropna().to_numpy(dtype=float)
            b = df_ws[df_ws.source_family == s_b][feat].dropna().to_numpy(dtype=float)
            res = univariate_pair_distance(a, b)
            pair_rows.append({
                "feature": feat, "source_a": s_a, "source_b": s_b,
                "n_a": int(a.size), "n_b": int(b.size),
                "cohens_d": res.cohens_d, "ks_statistic": res.ks_statistic,
                "ks_pvalue": res.ks_pvalue, "wasserstein": res.wasserstein,
            })
            raw_pvals.append(res.ks_pvalue)
            pair_indices.append(len(pair_rows) - 1)
        adjusted = benjamini_hochberg(raw_pvals)
        for idx, p_adj in zip(pair_indices, adjusted):
            pair_rows[idx]["ks_pvalue_bh_adjusted"] = p_adj
    pair_df = pd.DataFrame(pair_rows)
    return summary_df, pair_df


def multivariate_source_distances(
    df_ws: pd.DataFrame, sources: list[str], features: list[str]
) -> pd.DataFrame:
    """Section 6B, computed per source pair using a shared standardizer fit
    on the pooled (both sources') rows for that pair -- keeps each pairwise
    comparison self-contained rather than depending on the full N-source
    pool's scale."""
    rows = []
    for s_a, s_b in combinations(sources, 2):
        sub = df_ws[df_ws.source_family.isin([s_a, s_b])]
        X, impute_report = build_feature_matrix(sub, features)
        labels = sub.loc[~sub[features].astype(float).isna().all(axis=1), "source_family"].to_numpy()
        Xz = standardize_matrix(X)
        X_a = Xz[labels == s_a]
        X_b = Xz[labels == s_b]
        rows.append({
            "source_a": s_a, "source_b": s_b,
            "n_a": int(X_a.shape[0]), "n_b": int(X_b.shape[0]),
            "centroid_euclidean_distance": centroid_euclidean_distance(X_a, X_b),
            "mahalanobis_centroid_distance": mahalanobis_centroid_distance(X_a, X_b),
            "mmd_rbf_squared": mmd_rbf_unbiased(X_a, X_b),
            "n_cells_imputed_total": sum(impute_report["imputed_counts"].values()),
        })
    return pd.DataFrame(rows)


def temporal_drift(df_ws: pd.DataFrame, sources: list[str], features: list[str]) -> pd.DataFrame:
    """Section 6C: EARLY vs MIDDLE, MIDDLE vs LATE, EARLY vs LATE, per
    source, using the same distance framework as 6A/6B (univariate summary
    via Cohen's d/KS/Wasserstein pooled to one row per feature-pair would be
    verbose; this table reports the multivariate summary plus a compact
    univariate max-effect-size column for a quick per-source read)."""
    rows = []
    bucket_pairs = [("EARLY", "MIDDLE"), ("MIDDLE", "LATE"), ("EARLY", "LATE")]
    for source in sources:
        sub_source = df_ws[df_ws.source_family == source]
        for b_a, b_b in bucket_pairs:
            sub = sub_source[sub_source.time_bucket.isin([b_a, b_b])]
            if sub.empty:
                continue
            X, impute_report = build_feature_matrix(sub, features)
            labels = sub.loc[~sub[features].astype(float).isna().all(axis=1), "time_bucket"].to_numpy()
            Xz = standardize_matrix(X)
            X_a = Xz[labels == b_a]
            X_b = Xz[labels == b_b]
            max_abs_d = 0.0
            any_d = False
            for feat in features:
                a = sub_source[sub_source.time_bucket == b_a][feat].dropna().to_numpy(dtype=float)
                b = sub_source[sub_source.time_bucket == b_b][feat].dropna().to_numpy(dtype=float)
                res = univariate_pair_distance(a, b)
                if res.cohens_d is not None:
                    max_abs_d = max(max_abs_d, abs(res.cohens_d))
                    any_d = True
            rows.append({
                "source_family": source, "bucket_a": b_a, "bucket_b": b_b,
                "n_a": int(X_a.shape[0]), "n_b": int(X_b.shape[0]),
                "centroid_euclidean_distance": centroid_euclidean_distance(X_a, X_b),
                "mahalanobis_centroid_distance": mahalanobis_centroid_distance(X_a, X_b),
                "mmd_rbf_squared": mmd_rbf_unbiased(X_a, X_b),
                "max_abs_cohens_d_any_feature": max_abs_d if any_d else None,
            })
    return pd.DataFrame(rows)


def cross_vs_within(df_ws: pd.DataFrame, sources: list[str], features: list[str]) -> dict:
    """Section 6D. Window-level unit throughout (never per-request)."""
    all_sub = df_ws[df_ws.source_family.isin(sources)]
    X_all, impute_report = build_feature_matrix(all_sub, features)
    mask = ~all_sub[features].astype(float).isna().all(axis=1)
    labels_source = all_sub.loc[mask, "source_family"].to_numpy()
    labels_bucket = all_sub.loc[mask, "time_bucket"].to_numpy()
    Xz = standardize_matrix(X_all)

    cross_source_dists = []
    for s_a, s_b in combinations(sources, 2):
        X_a = Xz[labels_source == s_a]
        X_b = Xz[labels_source == s_b]
        cross_source_dists.append(pairwise_row_distances(X_a, X_b))
    cross_source_dists = np.concatenate(cross_source_dists) if cross_source_dists else np.array([])

    within_source_temporal_dists = []
    for source in sources:
        src_mask = labels_source == source
        Xs = Xz[src_mask]
        buckets_s = labels_bucket[src_mask]
        for b_a, b_b in combinations(sorted(set(buckets_s.tolist())), 2):
            within_source_temporal_dists.append(
                pairwise_row_distances(Xs[buckets_s == b_a], Xs[buckets_s == b_b])
            )
    within_source_temporal_dists = (
        np.concatenate(within_source_temporal_dists) if within_source_temporal_dists else np.array([])
    )

    mw = mann_whitney_with_effect_size(cross_source_dists, within_source_temporal_dists)
    return {
        "n_cross_source_window_pairs": int(cross_source_dists.size),
        "n_within_source_temporal_window_pairs": int(within_source_temporal_dists.size),
        "cross_source_pairwise_distance_mean": float(np.mean(cross_source_dists)) if cross_source_dists.size else None,
        "cross_source_pairwise_distance_median": float(np.median(cross_source_dists)) if cross_source_dists.size else None,
        "within_source_temporal_pairwise_distance_mean": float(np.mean(within_source_temporal_dists)) if within_source_temporal_dists.size else None,
        "within_source_temporal_pairwise_distance_median": float(np.median(within_source_temporal_dists)) if within_source_temporal_dists.size else None,
        "mann_whitney_statistic": mw.statistic,
        "mann_whitney_pvalue": mw.pvalue,
        "rank_biserial_effect_size": mw.rank_biserial,
        "interpretation": (
            "rank_biserial_effect_size > 0 means cross-source window pairs are "
            "systematically MORE distant (in standardized common-descriptor space) "
            "than within-source temporal window pairs -- i.e. source identity "
            "explains more distributional spread than ordinary within-source "
            "temporal drift."
        ),
        "n_cells_imputed_total": sum(impute_report["imputed_counts"].values()),
    }


def source_separability(df_ws: pd.DataFrame, sources: list[str], features: list[str]) -> dict:
    """Section 6E."""
    sub = df_ws[df_ws.source_family.isin(sources)]
    X, impute_report = build_feature_matrix(sub, features)
    mask = ~sub[features].astype(float).isna().all(axis=1)
    y = sub.loc[mask, "source_family"].tolist()
    Xz = standardize_matrix(X)
    result = evaluate_source_separability(Xz, y, list(features))
    return {
        "model_version": SEPARABILITY_MODEL_VERSION,
        "balanced_accuracy": result.balanced_accuracy,
        "macro_f1": result.macro_f1,
        "n_folds": result.n_folds,
        "n_windows": result.n_windows,
        "class_labels": result.class_labels,
        "confusion_matrix": result.confusion_matrix.tolist(),
        "feature_importances": result.feature_importances,
        "n_cells_imputed_total": sum(impute_report["imputed_counts"].values()),
        "framing": (
            "This measures whether workload sources are distinguishable from "
            "source-native workload descriptors -- it is NOT a scheduler "
            "selector and must never be interpreted or deployed as one "
            "(see docs/CLAIM_BOUNDARIES.md)."
        ),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fragments-dir", required=True, type=Path)
    ap.add_argument("--results-dir", required=True, type=Path)
    ap.add_argument("--manifest-out", required=True, type=Path)
    ap.add_argument("--sources", nargs="+", default=["burstgpt", "azure_llm_2024", "bailian_qwen", "tracelab"])
    args = ap.parse_args()

    args.results_dir.mkdir(parents=True, exist_ok=True)
    args.manifest_out.parent.mkdir(parents=True, exist_ok=True)

    print("Loading fragments...", file=sys.stderr)
    manifests, df, integrity = load_fragments(args.fragments_dir, args.sources)
    if df.empty:
        print("ERROR: no descriptor rows loaded from any fragment", file=sys.stderr)
        sys.exit(1)

    df.to_parquet(args.results_dir / "window_descriptors.parquet", index=False)
    print(f"window_descriptors.parquet: {len(df)} rows", file=sys.stderr)

    combined_manifest = {
        "manifest_kind": "workload_characterization_windows",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_sha": _git_sha(),
        "descriptor_schema_version": DESCRIPTOR_SCHEMA_VERSION,
        "sources": args.sources,
        "per_source_fragment_manifests": manifests,
    }
    with open(args.manifest_out, "w") as f:
        json.dump(combined_manifest, f, indent=2)
    manifest_hash = _sha256_file(args.manifest_out)
    print(f"combined window manifest sha256={manifest_hash}", file=sys.stderr)

    sources_present = sorted(df.source_family.unique().tolist())
    print(f"sources present: {sources_present}", file=sys.stderr)

    # ---- Primary window size (200) headline analyses ----
    df_primary = df[df.window_size_requested == PRIMARY_WINDOW_SIZE]
    print(f"Primary window size {PRIMARY_WINDOW_SIZE}: {len(df_primary)} rows", file=sys.stderr)

    summary_df, pair_df = univariate_cross_source(df_primary, sources_present)
    summary_df.to_csv(args.results_dir / "source_summary.csv", index=False)

    mv_df = multivariate_source_distances(df_primary, sources_present, list(COMMON_NUMERIC_FEATURES))
    pair_df.to_csv(args.results_dir / "source_pair_distances_univariate.csv", index=False)
    mv_df.to_csv(args.results_dir / "source_pair_distances_multivariate.csv", index=False)
    # Combined single file per section 11's naming (source_pair_distances.csv):
    # keep univariate as the row-per-feature-per-pair table (most detailed),
    # multivariate as a companion file, both documented in the protocol doc.
    pair_df.to_csv(args.results_dir / "source_pair_distances.csv", index=False)

    drift_df = temporal_drift(df_primary, sources_present, list(COMMON_NUMERIC_FEATURES))
    drift_df.to_csv(args.results_dir / "temporal_drift_distances.csv", index=False)

    cvw = cross_vs_within(df_primary, sources_present, list(COMMON_NUMERIC_FEATURES))
    with open(args.results_dir / "cross_vs_within_summary.json", "w") as f:
        json.dump(cvw, f, indent=2)

    sep = source_separability(df_primary, sources_present, list(COMMON_NUMERIC_FEATURES))
    with open(args.results_dir / "source_classifier_metrics.json", "w") as f:
        json.dump({k: v for k, v in sep.items() if k != "confusion_matrix"}, f, indent=2)
    cm_df = pd.DataFrame(sep["confusion_matrix"], index=sep["class_labels"], columns=sep["class_labels"])
    cm_df.to_csv(args.results_dir / "source_classifier_confusion.csv")
    fi_df = pd.DataFrame(
        sorted(sep["feature_importances"].items(), key=lambda kv: -kv[1]),
        columns=["feature", "permutation_importance_mean"],
    )
    fi_df.to_csv(args.results_dir / "feature_importance.csv", index=False)

    # ---- Window-size sensitivity (section 6F) ----
    sensitivity_rows = []
    for ws in ALL_WINDOW_SIZES:
        df_ws = df[df.window_size_requested == ws]
        if df_ws.empty or df_ws.source_family.nunique() < 2:
            continue
        ws_sources = sorted(df_ws.source_family.unique().tolist())
        mv_ws = multivariate_source_distances(df_ws, ws_sources, list(COMMON_NUMERIC_FEATURES))
        cvw_ws = cross_vs_within(df_ws, ws_sources, list(COMMON_NUMERIC_FEATURES))
        try:
            sep_ws = source_separability(df_ws, ws_sources, list(COMMON_NUMERIC_FEATURES))
            bal_acc = sep_ws["balanced_accuracy"]
            macro_f1 = sep_ws["macro_f1"]
        except ValueError as e:
            bal_acc, macro_f1 = None, None
            print(f"window_size={ws}: separability skipped ({e})", file=sys.stderr)
        sensitivity_rows.append({
            "window_size": ws,
            "n_sources": len(ws_sources),
            "n_windows_total": int(len(df_ws)),
            "mean_centroid_euclidean_distance": float(mv_ws["centroid_euclidean_distance"].mean()) if not mv_ws.empty else None,
            "mean_mahalanobis_centroid_distance": float(mv_ws["mahalanobis_centroid_distance"].dropna().mean()) if not mv_ws.empty else None,
            "mean_mmd_rbf_squared": float(mv_ws["mmd_rbf_squared"].dropna().mean()) if not mv_ws.empty else None,
            "cross_vs_within_rank_biserial": cvw_ws["rank_biserial_effect_size"],
            "cross_vs_within_pvalue": cvw_ws["mann_whitney_pvalue"],
            "classifier_balanced_accuracy": bal_acc,
            "classifier_macro_f1": macro_f1,
        })
    sensitivity_df = pd.DataFrame(sensitivity_rows)
    sensitivity_df.to_csv(args.results_dir / "window_size_sensitivity.csv", index=False)

    # ---- Integrity report ----
    integrity_report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "n_total_descriptor_rows": int(len(df)),
        "n_sources": len(sources_present),
        "sources": sources_present,
        "rows_per_source_per_window_size": (
            df.groupby(["source_family", "window_size_requested"]).size().reset_index(name="n_windows").to_dict(orient="records")
        ),
        "nan_fraction_per_common_feature": {
            feat: float(df[feat].isna().mean()) for feat in COMMON_NUMERIC_FEATURES
        },
        "per_source_fragment_integrity": integrity,
        "any_inf_values_detected": bool(
            np.isinf(df[list(COMMON_NUMERIC_FEATURES)].astype(float).to_numpy(na_value=0.0)).any()
        ),
    }
    with open(args.results_dir / "integrity_report.json", "w") as f:
        json.dump(integrity_report, f, indent=2)

    # ---- Provenance ----
    provenance = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_sha": _git_sha(),
        "descriptor_schema_version": DESCRIPTOR_SCHEMA_VERSION,
        "statistical_protocol_version": STATISTICAL_PROTOCOL_VERSION,
        "separability_model_version": SEPARABILITY_MODEL_VERSION,
        "window_manifest_sha256": manifest_hash,
        "primary_window_size": PRIMARY_WINDOW_SIZE,
        "window_sizes_evaluated": list(ALL_WINDOW_SIZES),
        "common_numeric_features": list(COMMON_NUMERIC_FEATURES),
        "n_common_numeric_features": len(COMMON_NUMERIC_FEATURES),
    }
    with open(args.results_dir / "provenance.json", "w") as f:
        json.dump(provenance, f, indent=2)

    print("DONE.", file=sys.stderr)
    print(f"manifest_sha256={manifest_hash}")


if __name__ == "__main__":
    main()
