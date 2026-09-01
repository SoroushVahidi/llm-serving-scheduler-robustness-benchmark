#!/usr/bin/env python3
"""Paper-facing, leakage-resistant workload-source-separability result.

Runs read-only against the FROZEN window_descriptors.parquet from the
2026-09-01 overnight characterization run. Does not regenerate windows or
descriptors. Builds on docs/SOURCE_SEPARABILITY_AUDIT_20260901.md's
findings: excludes the 3 deterministic pressure-proxy features from the
primary classifier matrix, and uses a structurally leakage-safe
per-fold sklearn Pipeline (see separability_pipeline.py) instead of the
original pooled-before-split preprocessing.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier

from robustbench.characterization.descriptors import COMMON_NUMERIC_FEATURES
from robustbench.characterization.separability_pipeline import (
    DETERMINISTIC_PROXY_FEATURES,
    PAPER_FACING_FEATURES,
    evaluate_grouped,
)

SEED = 20260901
PRIMARY_WINDOW_SIZE = 200
N_PERMUTATION_REPEATS = 30

RESULTS_DIR = REPO_ROOT / "results" / "workload_distribution_characterization_v1"
OUT_DIR = RESULTS_DIR / "paper_facing_separability"
OUT_DIR.mkdir(parents=True, exist_ok=True)
(OUT_DIR / "grouped_confusion_matrices").mkdir(exist_ok=True)


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).decode().strip()


parquet_path = RESULTS_DIR / "window_descriptors.parquet"
df_all = pd.read_parquet(parquet_path)
df = df_all[df_all.window_size_requested == PRIMARY_WINDOW_SIZE].reset_index(drop=True)
sources = sorted(df.source_family.unique().tolist())
log(f"loaded {len(df_all)} rows total, {len(df)} at window_size={PRIMARY_WINDOW_SIZE}, sources={sources}")

X = df[list(PAPER_FACING_FEATURES)].astype(float).to_numpy()
y = df["source_family"].to_numpy()
time_bucket = df["time_bucket"].to_numpy()

# ---------------------------------------------------------------------------
# A1/A2: feature manifest
# ---------------------------------------------------------------------------
feature_manifest = {
    "primary_classifier_features": list(PAPER_FACING_FEATURES),
    "n_primary_features": len(PAPER_FACING_FEATURES),
    "excluded_deterministic_proxies": list(DETERMINISTIC_PROXY_FEATURES),
    "exclusion_reason": (
        "Exact deterministic products of other features already in the primary "
        "matrix (R^2=1.0 vs. the product of their components; "
        "docs/SOURCE_SEPARABILITY_AUDIT_20260901.md section 5). Retained in the "
        "underlying descriptor dataset (window_descriptors.parquet) as documented "
        "derived pressure-proxy descriptors -- excluded only from THIS classifier's "
        "primary input matrix."
    ),
    "preprocessing": (
        "sklearn.pipeline.Pipeline(SimpleImputer(median), StandardScaler(), estimator), "
        "refit fresh on each grouped fold's TRAIN rows only -- structurally leakage-safe "
        "(see src/robustbench/characterization/separability_pipeline.py and "
        "tests/test_separability_pipeline_no_leakage.py)."
    ),
    "evaluation_scheme": "leave-one-time_bucket-out (EARLY/MIDDLE/LATE), 3 folds",
}
with open(OUT_DIR / "feature_manifest.json", "w") as f:
    json.dump(feature_manifest, f, indent=2)

# ---------------------------------------------------------------------------
# A3: primary evaluation -- RF / LogReg / shallow tree, grouped
# ---------------------------------------------------------------------------
model_specs = [
    ("random_forest", lambda: RandomForestClassifier(
        n_estimators=300, max_depth=None, random_state=SEED, class_weight="balanced_subsample"
    ), True),
    ("logistic_regression", lambda: LogisticRegression(
        max_iter=5000, class_weight="balanced", random_state=SEED
    ), False),
    ("decision_tree_depth3", lambda: DecisionTreeClassifier(
        max_depth=3, random_state=SEED, class_weight="balanced"
    ), False),
]

grouped_rows = []
model_summary_rows = []
results_by_model = {}

for name, factory, want_perm in model_specs:
    result = evaluate_grouped(
        X, y, time_bucket, factory, PAPER_FACING_FEATURES, model_name=name, seed=SEED,
        compute_permutation_importance=want_perm, n_repeats=N_PERMUTATION_REPEATS,
    )
    results_by_model[name] = result
    for fr in result.folds:
        grouped_rows.append({
            "model": name, "held_out_bucket": fr.held_out_group,
            "n_train": fr.n_train, "n_test": fr.n_test,
            "balanced_accuracy": fr.balanced_accuracy, "macro_f1": fr.macro_f1,
        })
    model_summary_rows.append({
        "model": name,
        "balanced_accuracy_pooled": result.balanced_accuracy_pooled,
        "macro_f1_pooled": result.macro_f1_pooled,
        "balanced_accuracy_mean": result.balanced_accuracy_mean,
        "balanced_accuracy_std": result.balanced_accuracy_std,
        "macro_f1_mean": result.macro_f1_mean,
        "macro_f1_std": result.macro_f1_std,
        "n_folds": len(result.folds),
    })
    if result.confusion_matrix is not None:
        pd.DataFrame(result.confusion_matrix, index=result.class_labels, columns=result.class_labels).to_csv(
            OUT_DIR / "grouped_confusion_matrices" / f"{name}.csv"
        )
    log(f"{name}: balanced_accuracy(pooled)={result.balanced_accuracy_pooled:.4f} "
        f"mean_across_folds={result.balanced_accuracy_mean:.4f}+-{result.balanced_accuracy_std:.4f}")

pd.DataFrame(grouped_rows).to_csv(OUT_DIR / "grouped_model_metrics_per_fold.csv", index=False)
pd.DataFrame(model_summary_rows).to_csv(OUT_DIR / "grouped_model_metrics.csv", index=False)

# ---------------------------------------------------------------------------
# A4: clean permutation importance (RF, n_repeats=30, grouped, aggregated)
# ---------------------------------------------------------------------------
rf_result = results_by_model["random_forest"]
perm_rows = []
for feat in PAPER_FACING_FEATURES:
    perm_rows.append({
        "feature": feat,
        "permutation_importance_mean": rf_result.permutation_importance_mean[feat],
        "permutation_importance_std": rf_result.permutation_importance_std[feat],
        "n_folds_positive": rf_result.permutation_importance_n_folds_positive[feat],
        "n_folds_total": len(rf_result.folds),
    })
perm_df = pd.DataFrame(perm_rows).sort_values("permutation_importance_mean", ascending=False)
perm_df["rank"] = range(1, len(perm_df) + 1)
perm_df.to_csv(OUT_DIR / "permutation_importance.csv", index=False)
log(f"permutation importance: top feature = {perm_df.iloc[0]['feature']} "
    f"({perm_df.iloc[0]['permutation_importance_mean']:.5f})")

# ---------------------------------------------------------------------------
# A5: attribution triangulation (single-feature RF, LOFO, group ablation)
# ---------------------------------------------------------------------------
def rf_factory():
    return RandomForestClassifier(n_estimators=300, max_depth=None, random_state=SEED,
                                   class_weight="balanced_subsample")


baseline_bal_acc = rf_result.balanced_accuracy_mean

single_rows = []
for i, feat in enumerate(PAPER_FACING_FEATURES):
    Xf = X[:, [i]]
    r = evaluate_grouped(Xf, y, time_bucket, rf_factory, [feat], model_name="single_feature", seed=SEED)
    single_rows.append({"feature": feat, "single_feature_balanced_accuracy": r.balanced_accuracy_mean})
single_df = pd.DataFrame(single_rows).set_index("feature")

lofo_rows = []
for i, feat in enumerate(PAPER_FACING_FEATURES):
    remaining_idx = [j for j in range(len(PAPER_FACING_FEATURES)) if j != i]
    Xf = X[:, remaining_idx]
    r = evaluate_grouped(Xf, y, time_bucket, rf_factory,
                          [PAPER_FACING_FEATURES[j] for j in remaining_idx], model_name="lofo", seed=SEED)
    lofo_rows.append({"feature": feat, "lofo_balanced_accuracy_without": r.balanced_accuracy_mean,
                       "lofo_delta": r.balanced_accuracy_mean - baseline_bal_acc})
lofo_df = pd.DataFrame(lofo_rows).set_index("feature")

FEATURE_GROUPS = {
    "arrival_burstiness": [
        "mean_arrival_rate_rps", "interarrival_cv", "interarrival_p50_s",
        "interarrival_p90_s", "interarrival_p99_s", "burstiness_b",
        "peak_short_window_arrival_rate_rps", "idle_gap_fraction",
    ],
    "prompt_length": [
        "prompt_tokens_mean", "prompt_tokens_cv", "prompt_tokens_p90", "prompt_tokens_p99",
        "long_prompt_fraction_512", "long_prompt_fraction_2048", "long_prompt_fraction_8192",
    ],
    "output_length": ["output_tokens_mean", "output_tokens_cv", "output_tokens_p90", "output_tokens_p99"],
    "joint_token_stats": [
        "prompt_output_pearson_r", "prompt_output_spearman_r", "total_tokens_mean",
        "total_tokens_p90", "total_tokens_p99", "prompt_output_ratio_mean",
        "total_tokens_tail_ratio_p99_p50", "total_tokens_excess_kurtosis", "total_tokens_gini",
    ],
}
feat_to_group = {f: g for g, feats in FEATURE_GROUPS.items() for f in feats}

group_ablation_rows = []
for gname, gfeats in FEATURE_GROUPS.items():
    remaining = [f for f in PAPER_FACING_FEATURES if f not in gfeats]
    idxs = [PAPER_FACING_FEATURES.index(f) for f in remaining]
    Xf = X[:, idxs]
    r = evaluate_grouped(Xf, y, time_bucket, rf_factory, remaining, model_name="group_ablation", seed=SEED)
    group_ablation_rows.append({"group": gname, "balanced_accuracy_without_group": r.balanced_accuracy_mean,
                                 "delta": r.balanced_accuracy_mean - baseline_bal_acc})
group_df = pd.DataFrame(group_ablation_rows).set_index("group")

attribution_rows = []
for feat in PAPER_FACING_FEATURES:
    attribution_rows.append({
        "feature": feat,
        "feature_group": feat_to_group.get(feat, "pressure_proxies_excluded"),
        "permutation_importance_mean": rf_result.permutation_importance_mean[feat],
        "permutation_importance_rank": int(perm_df.set_index("feature").loc[feat, "rank"]),
        "single_feature_balanced_accuracy": single_df.loc[feat, "single_feature_balanced_accuracy"],
        "lofo_delta": lofo_df.loc[feat, "lofo_delta"],
        "group_ablation_delta": group_df.loc[feat_to_group[feat], "delta"] if feat in feat_to_group else None,
    })
attribution_df = pd.DataFrame(attribution_rows).sort_values("permutation_importance_rank")
attribution_df.to_csv(OUT_DIR / "attribution_summary.csv", index=False)

# top-8 by a simple combined signal: rank by permutation importance primarily,
# tie-broken by single-feature accuracy (both computed under the SAME grouped
# holdout, so directly comparable)
top8 = attribution_df.sort_values(
    ["permutation_importance_mean", "single_feature_balanced_accuracy"], ascending=[False, False]
).head(8)
log("Top 8 attribution candidates:\n" + top8[["feature", "permutation_importance_mean",
                                                "single_feature_balanced_accuracy", "lofo_delta"]].to_string())

# ---------------------------------------------------------------------------
# A: critical ablation summary (mirrors audit's critical_feature_ablation.csv,
# recomputed on the cleaned 28-feature matrix)
# ---------------------------------------------------------------------------
critical_rows = [{"config": "all_paper_facing_features", "n_features": len(PAPER_FACING_FEATURES),
                   "balanced_accuracy": baseline_bal_acc}]
for name, excl in [
    ("minus_total_tokens_mean", ["total_tokens_mean"]),
    ("minus_long_prompt_fraction_8192", ["long_prompt_fraction_8192"]),
    ("minus_top2_permutation_features", list(top8["feature"].iloc[:2])),
]:
    remaining = [f for f in PAPER_FACING_FEATURES if f not in excl]
    idxs = [PAPER_FACING_FEATURES.index(f) for f in remaining]
    r = evaluate_grouped(X[:, idxs], y, time_bucket, rf_factory, remaining, model_name=name, seed=SEED)
    critical_rows.append({"config": name, "n_features": len(remaining), "balanced_accuracy": r.balanced_accuracy_mean})
pd.DataFrame(critical_rows).to_csv(OUT_DIR / "critical_ablation_summary.csv", index=False)

# ---------------------------------------------------------------------------
# provenance + integrity
# ---------------------------------------------------------------------------
provenance = {
    "generated_at_utc": pd.Timestamp.utcnow().isoformat(),
    "repo_sha": git_sha(),
    "audited_repo_sha": "8709151",
    "characterization_repo_sha": "862e8f5f789cce329f84d535c54cfc4b747e8d7e",
    "window_descriptors_parquet_sha256": sha256_file(parquet_path),
    "primary_window_size": PRIMARY_WINDOW_SIZE,
    "n_windows": int(len(df)),
    "n_primary_features": len(PAPER_FACING_FEATURES),
    "excluded_features": list(DETERMINISTIC_PROXY_FEATURES),
    "permutation_importance_n_repeats": N_PERMUTATION_REPEATS,
    "seed": SEED,
}
with open(OUT_DIR / "provenance.json", "w") as f:
    json.dump(provenance, f, indent=2)

integrity_report = {
    "n_rows_total": int(len(df_all)),
    "n_rows_primary_window_size": int(len(df)),
    "sources": sources,
    "n_missing_cells_in_primary_matrix": int(np.isnan(X).sum()),
    "files_written": sorted(p.name for p in OUT_DIR.glob("*") if p.is_file()),
}
with open(OUT_DIR / "integrity_report.json", "w") as f:
    json.dump(integrity_report, f, indent=2)

log("DONE.")
print(json.dumps({m["model"]: {"balanced_accuracy_mean": m["balanced_accuracy_mean"],
                                "balanced_accuracy_pooled": m["balanced_accuracy_pooled"]}
                   for m in model_summary_rows}, indent=2))
