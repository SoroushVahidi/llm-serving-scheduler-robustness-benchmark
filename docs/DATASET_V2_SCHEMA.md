# DATASET_V2_SCHEMA.md

Design only — **not published in this task** (rule #10). A future Hugging
Face release built from this design must fix the provenance weakness of the
existing `llm-serving-scheduler-baselines` release: every row must carry
enough provenance to be reproduced without depending on an unresolvable
historical Git commit (`docs/REPRODUCIBILITY_CONTRACT.md`).

## Logical tables / configs

1. **`workload_windows`** — `workload_window_id` (stable, content-hashed),
   `source_family`, `window_construction_rule`, `request_count`,
   `start_arrival_time_s`, `end_arrival_time_s`, `source_version`,
   `source_license`, `source_url`.
2. **`workload_descriptors`** — one row per `workload_window_id`, the full
   `WindowDescriptor` (`src/robustbench/descriptors/window_descriptors.py`)
   serialized, including `field_provenance_summary`.
3. **`policy_outcomes`** — one row per (policy, window, load_level, seed);
   schema fixed by `src/robustbench/schemas/policy_outcome.py`
   (`PolicyOutcomeRow`).
4. **`policy_registry`** — a frozen snapshot of
   `configs/policies/canonical_policy_registry.yaml` at release time,
   including `policy_registry_version`.
5. **`workload_source_registry`** — a frozen snapshot of
   `configs/workloads/source_registry.yaml` at release time.
6. **`split_manifest`** — every row from every file in `configs/splits/`,
   with `manifest_sha256`.
7. **`rank_stability_pairs`** — one row per (source_or_split_pair, metric,
   load_level): `kendall_tau`, `spearman_rho`, `top_k_overlap`, CI bounds
   (`docs/STATISTICAL_ANALYSIS_PLAN.md` §A).
8. **`rank_reversal_pairs`** — one row per (policy_A, policy_B,
   source_or_split, load_level, metric): reversal frequency, effect size, CI
   (§B).
9. **`real_validation_subset`** — one row per (policy, workload_family,
   load_region, repetition) real-vLLM measurement
   (`docs/REAL_SYSTEM_VALIDATION_PLAN.md`).
10. **`provenance_manifest`** — one row per release artifact: `source`,
    `transformation`, `load_level`, `policy`, `experiment_version`,
    `code_sha`, `config_hash`, `random_seed`.

## Join key discipline

`workload_window_id` must be stable across tables 1–3 and 7–9 so that a
paired-policy analysis can join `policy_outcomes` to `workload_descriptors`
to `rank_reversal_pairs` without any fuzzy matching. `policy_id` must match
`configs/policies/canonical_policy_registry.yaml` verbatim.

## Provenance completeness requirement (per row)

Every row in every table must be traceable to: source, transformation
applied, load level (where applicable), policy (where applicable),
`experiment_version`, `code_sha` (this repo's commit, not the source repo's),
`config_hash`, and `random_seed` (where applicable) — see
`docs/REPRODUCIBILITY_CONTRACT.md`.
