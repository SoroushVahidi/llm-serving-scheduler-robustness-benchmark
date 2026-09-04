<!--
This file mirrors the published Hugging Face dataset card for
SoroushVahidi/llm-serving-scheduler-portability (v1.0.0). It is a
source-controlled copy for GitHub readers; the live card at
https://huggingface.co/datasets/SoroushVahidi/llm-serving-scheduler-portability
is authoritative if the two ever diverge. Update both together.
-->

---
license: mit
tags:
  - llm-serving
  - scheduling
  - benchmark
  - ranking-portability
  - systems
pretty_name: LLM-Serving Scheduler Portability (LSSP)
---

# LLM-Serving Scheduler Portability (LSSP) — v1.0.0

LSSP measures how *portable* comparative LLM-serving scheduler rankings
are across workload sources, load regions, evaluation metrics, and SLO
definitions: does the best-performing scheduling policy stay best when
you change the traffic source or the load level, or do rankings reverse?
This dataset is the derived analysis behind that question, paired with a
selected-case physical validation (RQ6).

**This is an initial (v1.0.0), intentionally partial release** — see
"What's in this release" below for exactly what is and is not included,
and why. Everything included is either byte-identical to its source
(noted per file) or an explicitly-labeled, content-complete-on-the-claims-
that-matter reduction.

## Relation to the paper

Companion dataset to *"How Portable Are LLM-Serving Scheduler Rankings
Across Workloads, Operating Regions, and Metrics?"* (Soroush Vahidi;
GitHub: [`SoroushVahidi/llm-serving-scheduler-robustness-benchmark`](https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark)).
This dataset revision corresponds to GitHub release
[`v1.0.0`](https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark/releases/tag/v1.0.0)
(commit `18128a8cf4d449c333c6db4d31788dd5eae180bd`).

## What's in this release

| Path | Contents | Fidelity |
|---|---|---|
| `rq6/RQ6_ANALYSIS_RESULT.json` | The complete **reduced RQ6 result**: per-source point estimates, 95% bootstrap CIs, bootstrap settings, and all upstream provenance hashes (execution SHA, three manifest hashes, simulator-source hashes) for Slurm job `1222413`'s 240/240-cell campaign. Sufficient to fully and independently verify every RQ6 claim in the manuscript. | Complete on all reported numbers |
| `table_data/rq1_rq2_portability.json` | RQ1/RQ2 cross-source ranking-portability table (all 18 source-pair×region rows, all per-metric summaries). | Complete content, minified (whitespace-only change) |
| `table_data/rq4_sample_complexity.json` | RQ4/RQ5 sample-complexity recovery curves (all 3 sources × 5 sample sizes, concentrated-vs-spread comparison). | Complete on headline numbers; omits the exhaustive per-metric `secondary_metric_thresholds` breakdown, minified |
| `LSSP_THIRD_PARTY_SOURCE_LICENSES.md` | Per-source license/redistribution/attribution detail for BurstGPT, Azure-2024, Bailian/Qwen. | Byte-identical to GitHub source |
| `checksums.json` | SHA-256 for every byte-identical file above. | — |
| `README.md` | This dataset card. | — |

**Not included in this v1.0.0 revision, and why**:
- **`table_data/rq3_reversals.json`, `table_data/rq5_temporal_robustness.json`** and the **six intermediate canonical `analysis_canonical/*.json` outputs** (pairwise reversals, ranking correlations, sample complexity, telemetry explanation, temporal robustness, top-k overlap): deferred to a follow-up dataset revision. The manuscript's headline RQ1/RQ2/RQ4/RQ5 numbers are already fully present above; the deferred files back RQ3's pilot-scale result and finer per-metric/per-condition detail beyond the headline tables. Because these six files are absent, `paper/scripts/generate_phase12_tables_figures.py` (which consumes them as input) cannot currently be run against this dataset download — the released `table_data/*.json` files are that script's *output*, already provided directly.
- **`manifests/`** (frozen campaign manifests, including the 18,720-execution campaign freeze): not duplicated here — every one of these files is already publicly tracked in the GitHub repository under `artifacts/manifests/` in the tagged `v1.0.0` release.
- **The full 240 raw per-cell RQ6 execution records** and the exploded per-cell raw/enriched shards for RQ1–RQ5 (tens of megabytes, not yet packaged for release): the included reduced/canonical files are sufficient to verify every reported claim; the raw per-cell shards exist only for independent verification of the analysis step itself and are candidates for a follow-up revision.

## RQ6 status

RQ6 (Slurm job `1222413`, execution SHA `703a752762348bd911c9d93f17731fa5244b38f9`)
is complete: 240/240 cells `COMPLETED`, independently validated, and
analyzed with the frozen `robustbench.real_llm.rq6_validation_analysis`
implementation (2,000-resample window-level paired bootstrap, 95% CI).
Result: all three real-system `slai_faithful`-vs-`vllm_faithful` ANWG
effects are statistically supported and favor `vllm_faithful`; the
simulator-predicted Azure/BurstGPT reversal did **not** reproduce on
physical hardware, while the Azure/Bailian-Qwen stable control **did**
retain its ordering. This is a selected-case validation (2 of 13 panel
policies, 3 sources, one operating region) — see the manuscript's
Limitations section for exact scope.

## License / redistribution

Code (GitHub repository) is MIT-licensed. This dataset — all
LSSP-derived files above — is released under the same MIT terms. **No
raw third-party workload trace files are included.** BurstGPT
(CC-BY-4.0), Azure LLM Inference Trace 2024 (CC-BY), and Bailian/Qwen
(Apache-2.0) are referenced by canonical source, release tag/commit, and
independently-verified SHA-256 only; this project has consistently
treated all three as read-only-referenced rather than duplicated. See
`LSSP_THIRD_PARTY_SOURCE_LICENSES.md` in this dataset for full
per-source detail, redistribution status, and acquisition instructions.

## Citation

See `CITATION.cff` in the [GitHub repository](https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark).
The archived-artifact citation is available now via the Zenodo DOI,
[10.5281/zenodo.22306798](https://doi.org/10.5281/zenodo.22306798); the
manuscript's own journal citation will be added once one exists.

## Limitations

- RQ6 evaluated 2 of 13 panel policies, 3 sources, one operating region,
  one hardware/software environment, one physical execution per
  (policy, source, window) cell.
- See "Not included in this revision" above for the specific deferred
  files and the reason for each.
- `METRIC_DEFINITION_SENSITIVITY` and `SLO_DEFINITION_SENSITIVITY`
  robustness families have no implementing artifact; disclosed as a gap,
  not populated with an invented result.
- Bailian/Qwen license confidence is MEDIUM (single-source confirmation).
