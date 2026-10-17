# Scientific schema and field meanings

The seven files under `scientific/` are **unchanged authoritative JSON**. [The observed field inventory](schemas/scientific_field_inventory.json) enumerates every field path and observed type in those seven files and the six included scientific manifests, including optional/nested paths. This document defines the scientific meanings and the transformations in the separate `data/tables/*.parquet` convenience views. JSON object key order and Parquet column order have no scientific meaning.

## Matrix container: `scientific/campaign/consolidated.json`

| Field | Meaning |
|---|---|
| `manifest_kind` | Type of consolidated scientific artifact. |
| `campaign_freeze_sha256` | Frozen Phase-12 campaign identity; shared with every canonical analysis. |
| `execution_repo_sha` | Source commit used for final simulation execution. |
| `full_matrix_hash` | Scientific identity of the frozen 18,720-cell design; distinct from file SHA-256. |
| `n_cells` | Stated execution-row count. |
| `cells_content_sha256` | Internal content digest of cell data; distinct from the source-file SHA-256 and the analysis-input digest. |
| `provenance_amendment_sha256`, `provenance_contract_version`, `repair_code_git_sha` | Identity/version of the post-campaign provenance repair; performance results were not rerun. |
| `raw_shard_ledger_sha256`, `repaired_shard_ledger_sha256` | Hash identities of archived per-shard provenance ledgers. Shard payloads and ledgers containing internal paths are not redistributed here. |
| `cells[]` | Exactly 18,720 final, successful execution records. |

### `cells[]` identifiers and scientific inputs

| Field | Meaning |
|---|---|
| `cell_id` | Unique `source::window::region::policy::repN` execution key. |
| `source_family` | One of `burstgpt`, `azure_llm_2024`, `bailian_qwen`; distinct releases, while BurstGPT and Azure are not independent underlying providers. |
| `window_id` | One of 120 frozen 200-request workload windows; **the inferential sampling unit**. |
| `load_region` | One of six calibrated operating regions; see `EXPERIMENT_DESIGN.md`. |
| `load_factor` | Actual arrival-load rate used by the simulator for this window and region; not the nominal multiplier label. |
| `policy_id` | One of 13 frozen scheduler implementations. The policy-registry view identifies the 11 primary policies and two robustness-only approximations. |
| `repetition` | 0 or 1; two deterministic verification executions of the same configuration, not independent draws. |
| `synthesis_seed`, `synthesis_version` | Frozen input-field synthesis seed and rule version; seeds recur across source windows and do not make repetitions independent. |

### `cells[]` measurements

All eleven fields below are per-cell simulator outcomes. For exact formulas and ranking treatment, see the [frozen metric definitions](https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark/blob/main/docs/RANKING_PORTABILITY_METRIC_DEFINITIONS.md). The three `ALWAYS_DEFINED` values are finite for every successful cell. Conditional metrics retain `NaN` when their precondition is absent; 422 rows have at least one undefined metric. No released view imputes a value.

| Field | Class | Meaning |
|---|---|---|
| `arrival_normalized_weighted_goodput` | Always defined | **ANWG**, priority weight of SLO-met completed arrivals divided by total priority weight of all arrivals; the manuscript's primary ranking metric. |
| `completion_fraction` | Always defined | Completed requests divided by arriving requests. |
| `weighted_completion_fraction` | Always defined | Priority-weighted share of arrivals completed. |
| `slo_violation_rate` | Completion conditional | Share of completed requests missing their latency SLO. |
| `weighted_goodput` | Completion conditional | Priority-weighted SLO-met performance conditioned on completed requests; unlike ANWG, its denominator is not all arrivals. |
| `mean_latency`, `p95_latency` | Completion conditional | Mean and 95th-percentile completion latency of completed requests, in seconds. |
| `request_throughput`, `token_throughput` | Completion conditional | Completed requests or generated tokens per simulated second. |
| `mean_ttft`, `p95_ttft` | First-token conditional | Mean and 95th-percentile time to first token in seconds among completed requests with recorded first-token time; can be undefined even when completion is positive. |

The paper discusses `p99_latency` in a broader metric contract, but **no `p99_latency` column exists in this frozen 11-metric matrix**. The release does not invent it.

### `cells[]` telemetry and status

`telemetry` is an observational, per-execution object. Zeros can indicate genuine absence of a mechanism or a simulator mode without that mechanism; they are not missing-data markers. KV occupancy is normalized demand relative to nominal KV capacity and may exceed 1 for policies that do not enforce that capacity at admission.

| Field under `telemetry` | Meaning |
|---|---|
| `schema_version` | Telemetry schema version. |
| `n_steps` | Number of simulator time steps observed; must be positive. |
| `queue_depth_mean`, `queue_depth_max` | Mean and maximum waiting-queue depth across steps. |
| `batch_saturation_mean`, `batch_saturation_max` | Mean and maximum active-sequence count relative to configured maximum. |
| `kv_occupancy_mean`, `kv_occupancy_max` | Mean and maximum KV demand relative to nominal capacity; may exceed 1. |
| `prefill_decode_contention_fraction` | Fraction of sampled GPU-step diagnostics with both prefill and decode work. |
| `admission_control_activations` | Count of admission-control activations. |
| `preemption_or_reorder_events` | Count of preemption/reordering events. |
| `token_budget_saturation_fraction` | Fraction of sampled diagnostics in which the token budget was saturated. |

| Other cell field | Meaning |
|---|---|
| `telemetry_schema_version` | Expected outer telemetry version; must agree with nested schema. |
| `success`, `error_category`, `error_detail` | Execution status and error category/detail. All final cells are successful and their error fields are null. |
| `scientific_status` | Final cells are `PILOT_V2_SCIENTIFIC`; public engineering smoke uses a different status. |
| `schema_version` | Cell-result schema version. |
| `repo_sha`, `window_manifest_sha256`, `calibration_manifest_sha256`, `phase11_raw_fifo_calibration_sha256`, `phase11_region_assignments_sha256`, `policy_registry_hash`, `simulator_config_hash` | Frozen code, window, calibration, policy and simulator identities used to prevent mixing incompatible results. |
| `environment` | Execution environment metadata object; empty in these final rows. |

## Six canonical analysis files

Every analysis file includes `analysis_code_git_sha`, `analysis_contract_version`, `campaign_freeze_sha256`, and `consolidated_result_sha256`. The last field is an **internal analysis-input identity**, not the SHA-256 of `consolidated.json`; use the checksums ledger for byte-level file verification. These files are already-computed analyses, not new simulations.

### `pairwise_reversals.json`

`records` maps each of 11 metric names to 990 policy-pair × source-pair × region rows (10,890 total). Each row has `metric`, `policy_a`, `policy_b`, `condition_x`, `condition_y`, `load_region`, `fdr_family`; `diff_x`/`diff_y` (estimated policy-A minus policy-B effects), `margin_x`/`margin_y` (absolute winning difference divided by the losing value); `ci_x`/`ci_y` (bootstrap intervals); `p_x`/`p_y` and `bh_fdr_p_pair_iut` (condition-level and intersection-union p-values entering the FDR family); `bh_fdr_rejected_within_metric_loadregion_family` and `supported_after_fdr` (multiplicity/support flags); and `classification` (stable/reversal/unsupported or undefined outcome). Null inference fields are meaningful when a comparison is not testable. Top-level `reversal_contract` and `fdr_note` record the frozen classification/multiplicity convention. Never count every row as a supported reversal.

### `ranking_correlations.json`

`comparisons` maps each metric to 18 source-pair × region records (198 total). Row fields: `metric`, `condition_x`, `condition_y`, `n_policies_compared`, `n_conditions_excluded_for_undefined_metric`; `kendall_tau`, `kendall_p`, `kendall_tau_ci`; `spearman_rho`, `spearman_p`, `spearman_rho_ci`; `topk_overlap` and `topk_k_reduced` maps keyed by k=1/3; and `bh_fdr_rejected_within_metric_region_family`. Top-level `metrics`, `policies`, and `bootstrap_resamples` specify the analysis panel and resampling count. `omnibus_friedman[]` adds 66 rows with `metric`, `load_region`, `n_blocks`, `n_treatments`, `statistic`, `p_value`, `excluded_policies`; `omnibus_friedman_bh_fdr_by_metric` maps metrics to six corresponding adjusted rejection flags.

### `sample_complexity.json`

`per_source_metric[]` has 33 source × metric records: `source`, `metric`, `reference_ranking` (ordered policy IDs), `first_n_meeting_exact_threshold`, `first_n_meeting_topk_threshold` (k=1/3 map), and five `points[]` each with `n` sampled windows, `n_draws`, `seed`, `p_exact_recovery`, and `p_topk_recovery` (k=1/3 map). Top-level `draws_per_n`, `ladder_n_values`, and `concentrated_vs_spread[]` define/resummarize the design. Each concentration record has `metric`, `n_draws`, `n_total`, `mean_tau_concentrated`, and `mean_tau_spread`. Sample-size points reuse the already-executed windows; they are not new scheduler runs.

### `telemetry_explanation.json`

`records[]` has 990 explanatory model rows with `metric`, `load_region`, `source_x`, `source_y`, `policy_a`, `policy_b`, `n_observations`, `n_reversal_sites`, `n_excluded_missing_descriptor`, `features[]`, `coefficients` (five named features: `burstiness_b`, `prompt_tokens_cv`, `output_tokens_cv`, `long_context_fraction`, `concurrency_proxy`), `intercept`, `converged`, and `explanatory_only_never_a_selector`. Nonconverged/no-data models can have `NaN` coefficients; never treat these as estimated effects. Top-level `model` names the prespecified logistic approach. `robustness.headline_metric`, `seed_sensitivity_applicable`, `component_status.<component>.{implemented_as_postprocessing,new_execution_required_for_this_sensitivity,note}`, and `strata.<stratum>[].{source_x,source_y,load_region,kendall_tau}` describe planned/checkable sensitivity families. The exact component/stratum names and all optional paths are in the machine field inventory; `SLO_DEFINITION_SENSITIVITY` is expressly not implemented from these frozen rows.

### `temporal_robustness.json`

`records[]` has 36 split-comparison rows: `source`, `split`, optional `chronology_label`, `is_sensitivity_split`, `metric`, `condition_x`, `condition_y`, `n_policies_compared`, `n_conditions_excluded_for_undefined_metric`, `kendall_tau`, `kendall_p`, `kendall_tau_ci`, `spearman_rho`, `spearman_p`, `spearman_rho_ci`, `topk_overlap`, and `topk_k_reduced`. The 36 numerical rows are already present in the public manuscript RQ5 table; this canonical file supplies exact hash-pinned provenance and a manuscript-generator input.

### `topk_overlap.json`

`comparisons` maps 11 metrics to 18 source-pair × region rows (198 total). Rows have `condition_x`, `condition_y`, `topk_overlap` (k=1/3 numeric map), and `topk_k_reduced` (whether fewer defined policies forced a reduced k). The parent metric key supplies each row's metric; `top_k_values` lists the configured k values. The Parquet view adds a `metric` column solely as a losslessly verified key alias.

## Manifest and Parquet-view conventions

Included Phase-10/11/12 manifests record 120 sampled-window identities and descriptors, 720 FIFO calibration/region assignments, and the frozen 18,720 planned cell keys. Their exact nested field paths and types are in [scientific_field_inventory.json](schemas/scientific_field_inventory.json). They contain descriptors, rates, hashes and source *filenames*, not third-party raw request rows. The amended validator report attests a passing final matrix. The original raw/repaired shard ledgers are cited by SHA in the admission manifest but omitted because their entries include internal HPC paths.

`scheduler_outcomes.parquet` retains every original cell field except that empty `environment` is encoded as `environment_json="{}"`, due to the Parquet prohibition on empty structs. `workload_windows.parquet` stores heterogeneous `descriptor` objects as lossless `descriptor_json` text. `load_region_assignments.parquet` adds `source_family` and `load_region` aliases to source `source` and `region`. Analysis views include `_source_keys`, a list of field names present in the original JSON row, to distinguish omitted fields from Parquet null columns; `topk_overlap.parquet` additionally adds the parent `metric` key. `unique_configurations.parquet` is derived from the two matching repetitions and contains the two cell IDs, shared inputs and an equality flag. The public validator reconstructs and compares **every** view row to its original scientific JSON or manifest row. IEEE `NaN` remains `NaN` in the Parquet views; pandas may display it as missing, but no value is imputed.
