# RQ6 Public Result Provenance

This file is the publication-facing record of the completed RQ6 real-vLLM
physical-validation result reported in `paper/sections/real_system.tex`.
It exists so the manuscript's RQ6 claims can be independently checked from
this repository alone, without access to the private Wulver cluster
filesystem the campaign was executed on.

## Execution identity

- Slurm array job: `1222413` (240 tasks, indices 0-239, concurrency 4) —
  240/240 `COMPLETED`, `ExitCode 0:0`, 0 failed/cancelled/timeout/OOM.
- Execution worktree HEAD (frozen scientific-prefreeze branch
  `research/lssp-rq6-real-vllm-scientific-prefreeze-20260902`):
  `703a752762348bd911c9d93f17731fa5244b38f9`.
- Validation manifest sha256: `172efb13b30efea440a18644ef852fa2d0b8cc6fee93ea730981b2ac868bd670`
  (`configs/real_vllm/rq6_validation_manifest_v1_20260903.json` in the
  scientific-prefreeze repository).
- Case-selection manifest sha256: `f34e1c6a9f8d4c695720d14f7929741594ac8f7818a427db832933554e909e5a`.
- Calibration manifest sha256: `839f1ea99982cbfd198aa12c801a5e2e90ee47699b2b75e7b1c67da3878a8d00`
  (120/120 terminal: 43 converged, 77 lower-bound-already-violating).
- Input cell count: **240** (2 policies x 3 sources x 40 windows/source,
  200 requests/window), independently validated for identity,
  completeness, schema, and provenance against the frozen task-matrix
  enumeration before analysis (no missing/duplicate/corrupt cells).

## Analysis method

`robustbench.real_llm.rq6_validation_analysis` (unmodified) --
`condition_effect` / `reversal_analysis` / `stable_control_analysis` /
`apply_family_fdr`, reusing `robustbench.ranking_portability.analysis.stats
.block_bootstrap_ci`: paired, window-level bootstrap over the 40
independent windows/source, 2,000 resamples, 95% CI, RNG seed 0. BH-FDR
q=0.05 over the frozen 4-test family. Effect = ANWG(`slai_faithful`) -
ANWG(`vllm_faithful`).

## Result summary

| Source | Effect (SLAI-vLLM) | 95% CI | Winner |
|---|---|---|---|
| Azure-2024 HIGH_PRESSURE | -0.0235 | [-0.02663, -0.02038] | vLLM |
| BurstGPT HIGH_PRESSURE | -0.2003 | [-0.26375, -0.14437] | vLLM |
| Bailian/Qwen HIGH_PRESSURE | -0.0256 | [-0.02987, -0.02188] | vLLM |

Simulator-predicted Azure/BurstGPT reversal (`+0.520375` Azure/SLAI,
`-0.347625` BurstGPT/vLLM, per the hash-verified upstream Phase-12
`pairwise_reversals.json`, sha256 `c90619e822925146ad4395deebbf0cc8ccd0fd66cc13a8aa84202fc39a5cfdde`):
**NOT reproduced** (real system favors vLLM on both conditions). Azure/Bailian-Qwen
stable control (simulator Kendall tau-b `1.0`, from `ranking_correlations.json`,
sha256 `d77d5e973f70f8dfe443ebdf35b9c01e94adb84cc62cecef3a2c9afbb88773ff`):
qualitatively **reproduced** (consistent vLLM-favoring ordering on both
real-system conditions).

## Full analysis-result artifact

Generated 2026-09-04T13:06:16Z by a read-only driver invoking the frozen
analysis functions above against the 240 validated raw outputs. The
`provenance.worktree` field below is redacted to a repository-relative
description (the original recorded an absolute private-cluster path,
not meaningful outside that environment).

```json
{
  "analysis_note": "Produced by an ad hoc read-only driver script (not committed to the repo) that calls the frozen, unmodified functions in robustbench.real_llm.rq6_validation_analysis. No repository-defined CLI for this module existed at time of run.",
  "bh_fdr": {
    "family_order": ["reversal_x_azure", "reversal_y_burstgpt", "stable_x_azure", "stable_y_bailian"],
    "p_values": [0.001, 0.001, 0.001, 0.001],
    "q": 0.05,
    "reject": [true, true, true, true]
  },
  "descriptive_aggregate_anwg": {
    "azure_llm_2024": {"slai_anwg_mean": 0.7465, "vllm_anwg_mean": 0.77},
    "bailian_qwen": {"slai_anwg_mean": 0.819625, "vllm_anwg_mean": 0.84525},
    "burstgpt": {"slai_anwg_mean": 0.116375, "vllm_anwg_mean": 0.316625}
  },
  "generated_at_utc": "2026-09-04T13:06:16.440350+00:00",
  "primary_effects": {
    "azure_internal_consistency_match": true,
    "azure_llm_2024": {
      "ci_hi": -0.020375, "ci_lo": -0.026625, "condition_label": "azure_llm_2024::HIGH_PRESSURE",
      "excludes_zero": true, "n_windows": 40, "p_value_two_sided": 0.001,
      "point_estimate": -0.0235, "winner": "vllm_faithful"
    },
    "bailian_qwen": {
      "ci_hi": -0.021875, "ci_lo": -0.029875, "condition_label": "bailian_qwen::HIGH_PRESSURE",
      "excludes_zero": true, "n_windows": 40, "p_value_two_sided": 0.001,
      "point_estimate": -0.025625, "winner": "vllm_faithful"
    },
    "burstgpt": {
      "ci_hi": -0.144372, "ci_lo": -0.263753, "condition_label": "burstgpt::HIGH_PRESSURE",
      "excludes_zero": true, "n_windows": 40, "p_value_two_sided": 0.001,
      "point_estimate": -0.20025, "winner": "vllm_faithful"
    }
  },
  "provenance": {
    "analysis_module": "robustbench.real_llm.rq6_validation_analysis",
    "bootstrap_resamples": 2000,
    "calibration_manifest_sha256": "839f1ea99982cbfd198aa12c801a5e2e90ee47699b2b75e7b1c67da3878a8d00",
    "case_selection_manifest_sha256": "f34e1c6a9f8d4c695720d14f7929741594ac8f7818a427db832933554e909e5a",
    "ci_level": 0.95,
    "head_sha": "703a752762348bd911c9d93f17731fa5244b38f9",
    "input_cell_count": 240,
    "rng_seed_reversal": 0,
    "rng_seed_stable_control": 0,
    "simulator_reversal_source": {
      "file": "llm-serving-scheduler-lssp-phase12-analysis/artifacts/analysis/phase12/pairwise_reversals.json",
      "matches_case_selection_manifest_reference": true,
      "sha256": "c90619e822925146ad4395deebbf0cc8ccd0fd66cc13a8aa84202fc39a5cfdde"
    },
    "simulator_stable_control_source": {
      "file": "llm-serving-scheduler-lssp-phase12-analysis/artifacts/analysis/phase12/ranking_correlations.json",
      "matches_case_selection_manifest_reference": true,
      "sha256": "d77d5e973f70f8dfe443ebdf35b9c01e94adb84cc62cecef3a2c9afbb88773ff"
    },
    "validation_manifest_sha256": "172efb13b30efea440a18644ef852fa2d0b8cc6fee93ea730981b2ac868bd670",
    "worktree": "[REDACTED: private-cluster absolute path; repo is research/lssp-rq6-real-vllm-scientific-prefreeze-20260902 @ 703a752762348bd911c9d93f17731fa5244b38f9]"
  },
  "reversal_analysis": {
    "agrees_with_simulator_selected_direction": false,
    "both_conditions_supported": true,
    "sign_flip_observed": false,
    "simulator_selected_x_winner": "slai_faithful",
    "simulator_selected_y_winner": "vllm_faithful"
  },
  "sanity_cross_check": {
    "azure_llm_2024": {"all_finite": true, "mean_effect": -0.0235, "n": 40, "sign": "vLLM"},
    "bailian_qwen": {"all_finite": true, "mean_effect": -0.025625, "n": 40, "sign": "vLLM"},
    "burstgpt": {"all_finite": true, "mean_effect": -0.20025, "n": 40, "sign": "vLLM"}
  },
  "stable_control_analysis": {"same_sign_both_conditions": true},
  "stamp": "RQ6_REAL_VLLM_ANALYSIS_RESULT"
}
```

## Raw per-cell outputs

The 240 raw per-cell JSON outputs (one per (policy, source, window) cell,
~1-2KB each) that this analysis was computed from are not included in
this repository (operational campaign data, not final published results;
consistent with this project's existing convention of not committing the
similarly-sized Phase-10/11/12 raw campaign outputs to git — see
`docs/LSSP_DATASET_RELEASE_SCHEMA.md`). They are candidates for inclusion
in the planned `SoroushVahidi/llm-serving-scheduler-portability` Hugging
Face dataset release alongside the existing Phase-12 outcome matrix, under
a `real_vllm/rq6/` prefix, hash-identified against the manifests above.
