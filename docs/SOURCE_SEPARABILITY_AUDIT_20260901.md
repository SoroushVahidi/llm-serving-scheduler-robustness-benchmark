# SOURCE_SEPARABILITY_AUDIT_20260901.md

Audit of the source-separability classifier result (section 6E of
`docs/WORKLOAD_DISTRIBUTION_CHARACTERIZATION_PROTOCOL.md`) published in the
2026-09-01 overnight workload-distribution-characterization run
(`results/workload_distribution_characterization_v1/source_classifier_metrics.json`,
`feature_importance.csv`). Triggered by a suspicious pattern in the
original result: `balanced_accuracy = macro_f1 = 1.0` at window_size=200
alongside `feature_importances` that were almost all exactly `0.0`.

This audit runs entirely against the FROZEN `window_descriptors.parquet`
from that run. It does **not** regenerate windows or descriptors, does not
touch Stage-0, and does not run in the dirty original working tree (see
"Repository safety" below).

## 1. Pipeline reconstruction (section 2)

Code: `src/robustbench/characterization/separability.py`
(`evaluate_source_separability`, `_fit_predict_permutation_importance`),
invoked from `scripts/characterization/merge_and_analyze.py:source_separability()`.

| Item | Value |
|---|---|
| Estimator | `sklearn.ensemble.RandomForestClassifier(n_estimators=300, max_depth=None, random_state=20260901, class_weight="balanced_subsample")` |
| Library versions | sklearn 1.9.0, pandas 3.0.5, numpy 2.5.2, Python 3.12.13 (`.venv312`) |
| Seed | `20260901` (separability-specific; distinct from the window-sampling seed `20260910`) |
| Input features (X) | the 31-column `COMMON_NUMERIC_FEATURES` tuple from `robustbench.characterization.descriptors` — see feature manifest below |
| Target (y) | `source_family` (4 classes: azure_llm_2024, bailian_qwen, burstgpt, tracelab) |
| Preprocessing: imputation | column-median, computed over the **full** primary-window-size DataFrame (train+test pooled) before any split; 20 cells imputed out of 400×31=12,400 at window_size=200 |
| Preprocessing: scaling | z-score standardization, mean/std computed over the **full** pooled matrix before `StratifiedKFold` — see "preprocessing leakage" finding below |
| Split procedure | `sklearn.model_selection.StratifiedKFold(n_splits=5, shuffle=True, random_state=20260901)` + `cross_val_predict` — i.e. random, class-stratified, **not** chronological/grouped |
| Test fraction | 1/5 per fold; every row's reported prediction comes from a model that never saw that row in training (via `cross_val_predict`) |
| Window sizes modeled | separately — `df[df.window_size_requested == ws]` for each of 100/200/500, never mixed |
| Window overlap | none by construction (see section 3) |
| Feature importance | **fold-held-out permutation importance** (`sklearn.inspection.permutation_importance`, `scoring="balanced_accuracy"`, `n_repeats=20`), computed on each fold's held-out test rows using that fold's freshly-fit RF, then averaged across the 5 folds — **not** RF's native impurity `.feature_importances_` |
| Serialization | `dict[str, float]` → sorted descending → `pandas.to_csv`; no rounding in code |

## 2. Target / metadata leakage (section 3)

`classifier_feature_manifest.json` (in the audit results dir) lists the
exact 31-feature `X` and confirms by set-difference against every column in
`window_descriptors.parquet` that **no** source-identifying metadata
(`source_family`, `window_id`, `source_file`, `sampling_seed`,
`window_start_index`, provenance counters, etc.) is present in `X`. **No
target/metadata leakage.**

## 3. Train/test window overlap (section 4)

Reconstructed row ranges from `artifacts/manifests/characterization_fragments/windows_{source}.json`
(`start_index_in_valid_rows`, `request_count`) for every (source,
window_size). `select_stride_windows` places windows in disjoint,
equal-width stride buckets by construction (one window per bucket, bucket
width = `n_available // n_windows` ≥ `window_size`).

Empirically verified (`overlap_audit.csv`): **0 exact overlaps, 0 partial
overlaps, 0 nested windows, 0 duplicate descriptor vectors** across all
(source, window_size) combinations. Window sizes are evaluated
independently, so no cross-window-size contamination either. **No overlap
leakage.**

## 4. Feature-importance implementation audit (section 5)

Refit one representative fold directly (not from the saved JSON) and pulled
the raw, full-precision `permutation_importance` vector plus, for contrast,
sklearn's native impurity `.feature_importances_` from the same fitted
estimator (`feature_importance_root_cause.json`):

- `permutation_importance_sum` (one fold): **0.000000**
- `rf_impurity_importance_sum` (same fitted model, same fold): **1.000000** (sums to 1 by construction, as expected)
- Values are full float64 precision (e.g. `0.0003749999999999987`), not
  rounded/truncated — **rules out a rounding/serialization bug.**
- The pattern reproduces from a fresh, correctly-indexed fit — **rules out
  a wrong-estimator/wrong-index bug.**

**Not a bug.** Root cause: a **ceiling effect + multicollinearity**. With
`balanced_accuracy` already at 1.0 and heavy feature redundancy (below),
permuting any single feature while its correlated/deterministic partners
stay intact cannot meaningfully drop a near-perfect score — a well-known
limitation of permutation importance under correlated features, not a
pipeline defect.

## 5. Multicollinearity audit

`multicollinearity_audit.json`: **27 of the 435 feature pairs have
|Pearson r| > 0.9.** Three "pressure proxy" descriptors are **exact
deterministic products of other features already in X**:

| Proxy feature | = product of | R² vs. product |
|---|---|---|
| `approx_token_arrival_rate_tps` | `mean_arrival_rate_rps × total_tokens_mean` | 1.0000 |
| `approx_concurrent_request_proxy` | `mean_arrival_rate_rps × output_tokens_mean` | 1.0000 |
| `approx_kv_demand_proxy_tokens` | `mean_arrival_rate_rps × output_tokens_mean × prompt_tokens_mean` | 1.0000 |

These are legitimate, documented "pressure proxy" descriptors (not a
mistake to have computed them), but including them **and** their raw
components in the same separability feature matrix inflates redundancy and
is a direct contributor to the permutation-importance ceiling effect above.

## 6. Leakage-resistant grouped evaluation (sections 6-8)

Two chronological schemes, both using the pre-existing, independently
computed `time_bucket` (EARLY/MIDDLE/LATE, assigned from window start
position — see `chronology.py`, unrelated to the descriptor values
themselves, so using it as a grouping variable is not circular):

- **Scheme 1 (blocked holdout)** and **Scheme 2 (repeated grouped split)**
  are the same construction here: leave-one-bucket-out, rotated over all
  three buckets (train on 2 buckets, test on the third), which is both a
  blocked holdout *and* a 3-fold repeated grouped CV. Scaler **fit on the
  train fold only** (fixes the global-standardization leakage noted in
  section 1).

| Model | Balanced accuracy (pooled) | Macro-F1 (pooled) | Mean across 3 folds | Std across folds |
|---|---|---|---|---|
| Random Forest (original config) | **1.000** | 1.000 | 1.000 | 0.000 |
| Logistic regression (multinomial) | 0.988 | 0.987 | 0.987 | 0.0072 |
| Decision tree, depth ≤ 3 | 0.975 | 0.975 | 0.975 | 0.0305 |

Per-fold breakdown (`grouped_split_metrics.csv`): every fold, every model,
scores ≥ 0.93; the worst single fold (depth-3 tree, LATE held out) is
still 0.932. **Separability survives proper leakage-resistant, chronologically-blocked evaluation — the original random-split result was not an artifact of overlap or shuffling.**

### Depth-3 tree structure (full-data refit, for interpretability only)

```
|--- prompt_tokens_mean <= -0.42
|   |--- approx_token_arrival_rate_tps <= -0.05
|   |   |--- class: burstgpt
|   |--- approx_token_arrival_rate_tps >  -0.05
|   |   |--- class: bailian_qwen
|--- prompt_tokens_mean >  -0.42
|   |--- long_prompt_fraction_8192 <= -0.19
|   |   |--- class: azure_llm_2024
|   |--- long_prompt_fraction_8192 >  -0.19
|   |   |--- class: tracelab
```

Four sources are separated almost perfectly with **3 splits on 2
underlying signals** (prompt length, then arrival-rate×token-size or
long-prompt fraction) — this is a **low-dimensional, interpretable
phenomenon**, not one that requires model complexity.

## 7. Feature attribution (sections 5-6, redone under grouped holdout)

- **Single-feature classifiers** (`single_feature_metrics.csv`): the single
  best feature, `long_prompt_fraction_2048`, alone reaches **97.5% balanced
  accuracy** under leave-one-bucket-out. `prompt_tokens_mean` alone: 98.2%.
  `total_tokens_p90` alone: 98.0%. Even `mean_arrival_rate_rps` alone
  (an arrival-structure, non-length feature): 91.2%.
- **Leave-one-feature-out** (`leave_one_feature_out.csv`): removing any
  single feature from the full 31-feature RF changes balanced accuracy by
  at most **-0.0025** (removing `long_prompt_fraction_512`) — consistent
  with massive redundancy: no single feature is load-bearing once the
  others are present.
- **Feature-group ablation** (`feature_group_ablation.csv`): removing
  `arrival_burstiness` (8 feats), `output_length` (4 feats), or
  `pressure_proxies` (3 feats, the deterministic ones) changes accuracy by
  **0.000**. Removing `prompt_length` (7 feats) costs **-0.0076**; removing
  `joint_token_stats` (9 feats) costs **-0.0051**. **Prompt-length and
  joint-token-length statistics carry essentially all of the classifier's
  marginal, non-redundant separating signal.**
- **Grouped-holdout permutation importance** (`permutation_importance.csv`):
  now genuinely informative (nonzero, because grouped folds are harder than
  the original random split, e.g. LATE-held-out accuracy dips to 0.93-0.99).
  Top features: `prompt_tokens_mean` and `long_prompt_fraction_2048` (tied,
  0.00299), `long_prompt_fraction_512` (0.00286), `total_tokens_mean` and
  `prompt_output_ratio_mean` (0.00164 each); every arrival/burstiness,
  output-length, and pressure-proxy feature: exactly 0.0.

**RQ4 answer:** prompt-length distribution (mean, long-prompt fractions at
512/2048 tokens) and total-token-size statistics drive source separability;
arrival-timing structure and output-length alone carry almost no marginal
signal once prompt-length features are present.

## 8. Critical ablations (section 9)

`critical_feature_ablation.csv`, grouped holdout:

| Config | Balanced accuracy | n features |
|---|---|---|
| All features | 1.000 | 31 |
| − `total_tokens_mean` | 1.000 | 30 |
| − `long_prompt_fraction_8192` | 1.000 | 30 |
| − both | 1.000 | 29 |
| Common-core-only (− 3 deterministic pressure proxies) | 1.000 | 28 |

Removing the two flagged individual features, or the deterministic
multicollinear proxies entirely, **does not move balanced accuracy at
all**. This strongly supports genuine broad distributional separation, not
dependence on a narrow or artifactual set of features.

## 9. Scale / normalization audit (section 10)

`unit_transformation_audit.csv`. All 4 adapters use **raw, untransformed
token counts** — confirmed `tracelab.py` uses the newly-derived raw-asset
adapter (`input_tokens_total`/`output_tokens` fields), **not** the
pre-existing HF `tracelab_scheduler_ood_policy_sweep` config that
sqrt-compresses prompts (per `docs/TRACELAB_PROVENANCE_RESOLUTION.md`).
**No sqrt-compression or unit-scale artifact.**

One genuine **CAVEAT**, not a bug: `prompt_tokens_*` composes differently
across sources — TraceLab's `input_tokens_total` is an explicitly
cumulative, growing per-agent-session context size (includes reused
prefix across rounds), while BurstGPT's `Request tokens` is a single
per-request figure. Azure's `ContextTokens` is also potentially
multi-turn-cumulative per Azure's own schema. This is a genuine property
of how each source's underlying workload is architected (single API call
vs. growing agent session), not an artifact this project's adapters
introduced, and it is very likely part of *why* prompt-length features
separate sources so well — worth stating explicitly in the paper rather
than treated as a defect.

Arrival-time descriptors are computed only from within-source deltas, so
the real/relative/pseudonymized-timestamp differences across sources do not
bias them.

## 10. Missingness ablation (section 11)

`missingness_ablation.json`: a classifier trained **only** on
is-missing indicators (20 missing cells total out of 12,400,
i.e. 0.16%) achieves balanced accuracy **0.270** — barely above the
0.25 random-chance floor for 4 classes. **The headline separability result
is not a missingness artifact.**

## 11. Scientific verdict (section 13)

**`SEPARABILITY_RESULT_CONFIRMED_WITH_CAVEATS`**

- No metadata leakage, no window-overlap leakage, no missingness artifact,
  no unit/sqrt-compression artifact.
- Core separability is strong and **reproduces under proper
  leakage-resistant, chronologically-blocked evaluation** (RF 1.000,
  logistic regression 0.987, depth-3 tree 0.975) — this rules out
  `INVALID` and `WEAKENED` (the original random-split result was not
  optimistic due to leakage; grouped evaluation gives essentially the same
  answer).
- The caveats are about **interpretation, not validity**: (a) the original
  permutation-importance attribution was uninformative due to a genuine
  ceiling-effect + multicollinearity interaction (now corrected via grouped
  holdout + ablations, section 7); (b) 3 of 31 features are exact
  deterministic products of other included features and should be dropped
  or flagged if this feature set is reused elsewhere; (c) prompt-length
  comparability across sources has a documented semantic caveat (section 9)
  worth stating in the paper.

## 12. Paper implications (section 14)

1. **Yes** — the four workload sources occupy measurably different
   distributions (RQ1-3 of the characterization protocol; unaffected by
   this audit, see below).
2. **Yes** — a classifier distinguishes their windows from common
   source-native descriptors alone, and this now holds under a
   leakage-resistant, chronologically-blocked evaluation, not just a random
   split.
3. Audited balanced accuracy under the strongest (leave-one-bucket-out
   grouped) evaluation: **RF 1.000, logistic regression 0.987, depth-3 tree
   0.975** (window_size=200).
4. Descriptors driving the distinction: **`prompt_tokens_mean`,
   `long_prompt_fraction_512`, `long_prompt_fraction_2048`,
   `total_tokens_mean`, `total_tokens_p90`, `prompt_output_ratio_mean`** —
   i.e. prompt/total-length distribution, not arrival timing or output
   length.
5. Cross-source > within-source distance (`cross_vs_within_summary.json`,
   rank-biserial ≈ -0.59, p≈0) is **untouched by this audit** — that
   analysis uses standardized centroid/MMD distances over the full 31
   feature set as a distributional-distance question, not a classifier, and
   was not re-examined here; it was already window-level (not per-request)
   and used the same non-overlapping windows verified clean in section 3.
6. **No** — nothing here requires rerunning the 1200-row
   descriptor-generation job. The frozen descriptor table is
   uncorrupted, non-overlapping, and reproduces the exact original result.
7. **No** — nothing here undermines the scheduler-robustness paper's
   rationale; if anything it strengthens it (workload sources are provably,
   robustly distinguishable from source-native descriptors alone, under
   evaluation that rules out the obvious leakage explanations).

## 13. Recommended follow-up (not part of this audit's scope)

If `feature_importance.csv` / `source_classifier_metrics.json` are reused
downstream (e.g. cited directly in the paper), consider: (a) dropping the 3
deterministic pressure-proxy features from the *classifier's* input matrix
specifically (they add zero information per section 8, and their presence
makes any future impurity-based importance metric misleading) — the
multivariate-distance analyses (section 6B of the main protocol) are
unaffected since they don't rely on per-feature importance; (b) reporting
permutation importance computed on a held-out grouped split, not a random
split, if this analysis is rerun; (c) citing the depth-3 decision tree
split structure (section 6 above) as a compact, interpretable illustration
of what actually separates the sources.

## Repository safety

- Audit worktree: `/project/ikoutis/sv96/github/llm-serving-scheduler-robustness-separability-audit`
  (branch `research/workload-separability-audit-20260901`, created from
  committed SHA `b7090b8a073f49416cc9c575bc8710e28b983867`).
- The original dirty working tree
  (`/project/ikoutis/sv96/github/llm-serving-scheduler-robustness-benchmark`,
  and the local checkout at `/home/soroush/repos/llm-serving-scheduler-robustness-benchmark`)
  was **not modified**: the pre-existing uncommitted edit to
  `configs/workloads/source_registry.yaml` and the four untracked
  Stage-0-load-calibration files were left exactly as found.
- `main` unchanged throughout (`6a8277993e4ef19b10e3fa53baf476d0d0d490f0`).
- This audit never imports `robustbench.policies` / `robustbench.simulator`
  / `robustbench.evaluation`, never runs a scheduler policy, never touches
  Stage-0 code.
- `results/workload_distribution_characterization_v1/` (the original,
  non-audit files) was **not overwritten** — the audit writes only to a new
  `source_separability_audit/` subdirectory.
