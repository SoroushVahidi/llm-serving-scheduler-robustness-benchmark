# WORKLOAD_DISTRIBUTION_CHARACTERIZATION_PROTOCOL.md

Frozen protocol for the outcome-blind workload-distribution-characterization
experiment (branch `research/bootstrap-cross-workload-benchmark-20260831`).
This is a SECOND, independent experiment from the frozen Stage-0
scheduler-discriminability pilot (`docs/STAGE0_DISCRIMINABILITY_PROTOCOL.md`)
-- it shares no code path with `robustbench.policies`, `robustbench.simulator`,
or `robustbench.evaluation`, and computes no scheduler outcome, SBS/VBS, or
exploitability quantity. Frozen before the full characterization campaign
was launched, per the pre-registration discipline in
`docs/STATISTICAL_ANALYSIS_PLAN.md`.

## 0. Scientific purpose

Q1. How different are BurstGPT, Azure 2024, Bailian/Qwen, and TraceLab in
    source-native observable workload characteristics?
Q2. How much temporal distribution shift exists WITHIN each source?
Q3. Are source-to-source differences larger than ordinary within-source
    temporal variation?
Q4. Which workload dimensions account for the largest differences?
Q5. Are the conclusions robust to reasonable choices of window size?

Explicitly out of scope: any scheduler-policy comparison, SBS/VBS,
exploitability, or scheduler ranking. See `docs/CLAIM_BOUNDARIES.md`.

## 1. Sources

| Source | Real data | Checksum (source_registry.yaml) | Rows (data, excl. header) |
|---|---|---|---|
| BurstGPT | `BurstGPT_without_fails_2.csv` | sha256:56193aa9... | 3,784,213 |
| Azure LLM Inference 2024 (conversation split) | `AzureLLMInferenceTrace_conv_2024.csv` | sha256:a0cc9b96... | 27,303,999 |
| Bailian/Qwen | `qwen_traceB_blksz_16.jsonl` | sha256:68e3f98e... | 172,800 |
| TraceLab | `syfi_coding_trace.jsonl.gz` (GitHub release `v0.0.1`) | sha256:9d265eae... | 357,161 |

All four are read read-only from Wulver project storage (paths in
`configs/workloads/source_registry.yaml`); none are copied into this repo.

**Excluded from this run:** Azure 2023 (optional per task charter; omitted
to keep the primary cross-source comparison to four sources sharing a
comparable acquisition/adapter maturity level -- may be added in a follow-up
run, clearly labeled `PRIOR_REFERENCE`, not `NEW_CONFIRMATORY`, per
`docs/EVIDENCE_INDEPENDENCE_PLAN.md`). ServeGen (a generator, not a fixed
trace -- see `docs/SERVEGEN_ADOPTION_AUDIT.md`). Mooncake (`INTERNAL_ONLY`,
excluded from any distributable output per `docs/DATA_LICENSE_AUDIT.md`).

TraceLab is re-derived directly from the raw, official release asset with a
NEW adapter (`src/robustbench/workloads/external/adapters/tracelab.py`) --
it does **not** reuse the existing HF `tracelab_scheduler_ood_policy_sweep`
512-window config, per the explicit recommendation in
`docs/TRACELAB_PROVENANCE_RESOLUTION.md`.

## 2. Feature-provenance rule

Every `ExternalWorkloadRecord` field carries `field_provenance` in
`{SOURCE_OBSERVED, DETERMINISTIC_DERIVED, SYNTHESIZED_IMPUTED, UNAVAILABLE}`
(`src/robustbench/workloads/external/schema.py`). This experiment's
descriptors (`src/robustbench/characterization/descriptors.py`) are computed
only from fields with `SOURCE_OBSERVED` or `DETERMINISTIC_DERIVED`
provenance (arrival time, prompt/output tokens, and their trivial sums).
No synthetic SLO, priority, tenant label, or scheduler annotation is ever
injected, read, or referenced anywhere in this pipeline.

## 3. Window sampling (frozen 2026-09-01)

Implemented in `scripts/characterization/build_and_describe_windows.py`,
reusing the generic, already-tested `select_stride_windows` stride sampler
(`src/robustbench/workloads/external/stage0_window_selection.py`) -- NOT
Stage-0's frozen per-source parameters
(`burstgpt_independent_sampling.py`, `scripts/build_stage0_windows.py`),
which use offset/seed values chosen for a different purpose (avoiding a
third party's likely window placement). This experiment needs the full
chronological range per source to build meaningful EARLY/MIDDLE/LATE strata,
so:

- **seed = 20260910** for every source (distinct from every Stage-0 seed:
  20260901 BurstGPT / 20260902 Azure-2024 / 20260903 Bailian).
- **offset_valid_rows = 0** for every source (no rows skipped at the front).
- **window sizes:** 100, 200, 500 requests/window. Primary/headline
  analyses use **200**; 100 and 500 are the frozen sensitivity set
  (section 6F below).
- **target windows/source/window-size: 100.** If a source has too few valid
  rows for 100 non-overlapping windows at a given window size, the maximum
  scientifically defensible count is used instead (`n_available // window_size`,
  floor of 10 windows -- below that the (source, window_size) combination is
  excluded and recorded in the manifest, never padded/duplicated).
- **chronological EARLY/MIDDLE/LATE tagging**
  (`src/robustbench/characterization/chronology.py`): a window's stratum is
  the third (by valid-row position, not by wall-clock date, since not every
  source has an absolute calendar timestamp) of the available range its
  start index falls into.

Manifest: `artifacts/manifests/workload_characterization_windows.json`
(per-source fragments merged by `scripts/characterization/merge_and_analyze.py`).
Validity rule for a row entering the windowing pool (same predicate as
Stage-0, `_is_valid_for_windowing`): `arrival_time_s` present, `input_tokens
> 0`, `output_tokens > 0`. Rows failing this (e.g. TraceLab tool-call-only
rounds with `output_tokens == 0`, or rounds with empty `timing_events`) are
dropped from the windowing pool and counted in the fragment's integrity
report -- never imputed.

## 4. Descriptors (`src/robustbench/characterization/descriptors.py`)

One `WorkloadCharacterizationDescriptor` per window, ~55 fields covering:
arrival structure (rate, interarrival mean/std/CV/percentiles, Goh-Barabasi
burstiness B, peak short-window rate over 20 equal-width sub-bins, idle-gap
fraction using a 3x-mean-interarrival gap threshold), prompt/output token
structure (mean/median/std/CV/p90/p95/p99/max), joint length structure
(Pearson/Spearman prompt-output correlation, total-token distribution,
prompt/output ratio distribution with +1 smoothing), long-prompt fractions
at four predeclared thresholds (512/2048/8192/32768 tokens), three
documented pressure proxies (`approx_token_arrival_rate_tps`,
`approx_concurrent_request_proxy`, `approx_kv_demand_proxy_tokens` --
Little's-law-style approximations, never measured backend quantities), and
heavy-tail/inequality statistics (p99/p50 tail ratio, excess kurtosis, Gini
coefficient) on total tokens. `COMMON_NUMERIC_FEATURES` (30 fields) is the
frozen subset used for every multivariate/classifier analysis below.

## 5. Distribution-shift analyses (section 6, frozen before results inspected)

Implemented in `scripts/characterization/merge_and_analyze.py` and
`src/robustbench/characterization/distances.py` /
`src/robustbench/characterization/separability.py`. **Window is the unit
throughout** -- no analysis treats individual requests as independent
samples.

- **A. Univariate cross-source** (`source_summary.csv`,
  `source_pair_distances.csv` / `_univariate.csv`): per source per common
  feature, mean + percentile-bootstrap 95% CI (2000 resamples); per source
  pair per feature, Cohen's d, two-sample KS statistic/p-value, Wasserstein
  distance; KS p-values are Benjamini-Hochberg FDR-adjusted within each
  feature's family of pairwise tests.
- **B. Multivariate source distance** (`source_pair_distances_multivariate.csv`):
  per source pair, on the `COMMON_NUMERIC_FEATURES` matrix standardized
  (z-scored) on the pooled pair's own rows: centroid Euclidean distance,
  ridge-regularized Mahalanobis centroid distance (pooled covariance,
  `pinv` for numerical stability), and unbiased RBF-kernel MMD^2
  (median-heuristic bandwidth).
- **C. Within-source temporal drift** (`temporal_drift_distances.csv`):
  the same B-style multivariate distances plus a compact max-|Cohen's d|
  summary, computed EARLY-vs-MIDDLE, MIDDLE-vs-LATE, EARLY-vs-LATE within
  each source.
- **D. Cross-source vs within-source** (`cross_vs_within_summary.json`):
  window-level pairwise Euclidean distances (standardized common features)
  pooled across all cross-source window pairs vs all within-source
  EARLY/MIDDLE/LATE window pairs; two-sided Mann-Whitney U test with a
  rank-biserial effect size (positive => cross-source pairs are more
  distant than within-source temporal pairs).
- **E. Source separability** (`source_classifier_metrics.json`,
  `source_classifier_confusion.csv`, `feature_importance.csv`): a
  `RandomForestClassifier` (300 trees, `class_weight="balanced_subsample"`)
  evaluated with `StratifiedKFold` cross-validation (5-fold, or the largest
  feasible fold count if a class has fewer than 5 windows);
  `cross_val_predict` for balanced accuracy / macro-F1 / confusion matrix
  (every prediction made by a model that never saw that row in training);
  permutation importance (20 repeats, `balanced_accuracy` scoring) computed
  per held-out fold and averaged, not on training data. **Framing: this
  measures workload separability, never a scheduler selector** -- see
  `docs/CLAIM_BOUNDARIES.md`.
- **F. Window-size sensitivity** (`window_size_sensitivity.csv`): sections
  B/D/E repeated independently at window sizes 100, 200, and 500.

## 6. Outputs

`results/workload_distribution_characterization_v1/`: `window_descriptors.parquet`,
`source_summary.csv`, `source_pair_distances.csv` (+ `_univariate.csv` /
`_multivariate.csv` companions), `temporal_drift_distances.csv`,
`cross_vs_within_summary.json`, `source_classifier_metrics.json`,
`source_classifier_confusion.csv`, `feature_importance.csv`,
`window_size_sensitivity.csv`, `integrity_report.json`, `provenance.json`.

## 7. What this experiment does not do

Per the task charter and `docs/CLAIM_BOUNDARIES.md`: no Stage-0 six-policy
panel, no scheduler winner/ranking, no SBS/VBS, no exploitability, no
window selection informed by scheduler behavior. `robustbench.characterization`
imports nothing from `robustbench.policies`, `robustbench.simulator`, or
`robustbench.evaluation`, and nothing in those packages imports
`robustbench.characterization` -- this is enforced by construction (see
`src/robustbench/characterization/__init__.py`), not just by convention.
