---
DRAFT ONLY -- NOT PUBLISHED. This is the intended content for
SoroushVahidi/llm-serving-scheduler-portability's README.md dataset card.
Publishing is Query-3 scope, gated on RQ6 status review.
---

# LLM-Serving Scheduler Portability (LSSP)

## Summary

LSSP measures how *portable* LLM-serving scheduler rankings are across
workload sources, load regions, and evaluation windows: does the
best-performing scheduling policy stay the best when you change the
traffic source or the load level, or do rankings reverse? This dataset is
the full campaign matrix and derived analysis behind that question:
**120 workload windows × 6 load regions × 13 scheduling policies ×
2 repetitions = 18,720 simulated scheduler-outcome cells**, plus the
frozen statistical analysis run over them.

## Relation to the paper

Companion dataset to "How Portable Are LLM-Serving Scheduler Rankings
Across Workloads, Operating Regions, and Metrics?" (Soroush Vahidi,
submitted to the *Journal of Supercomputing*; GitHub:
`SoroushVahidi/llm-serving-scheduler-robustness-benchmark`). The
authoritative reference for "which manuscript state does this dataset
match" is the **exact commit SHA and, once cut, the GitHub release
tag** the dataset card is republished alongside at actual publication
time — not a mutable branch name, which can move. As of this draft, the
paper's active manuscript branch is `manuscript/lssp-jsc-final-post-rq6-polish-20260904`.
RQ1–RQ5, the cross-metric extension, and the SLO-definition-sensitivity
extension in the paper are computed directly from `analysis/canonical/`
and `analysis/extensions/` in this dataset (see "Cross-metric and
SLO-definition sensitivity extensions" below). **RQ6 (real-vLLM
validation) is now complete** — see "RQ6 status" below and
`docs/RQ6_PUBLIC_RESULT_PROVENANCE.md` in the code repository for the
full result and computational provenance.

## Dataset structure

See `docs/LSSP_DATASET_RELEASE_SCHEMA.md` in the code repository for the
full design rationale. Top level:

- `manifests/` — frozen identity manifests for phases 10 (windows), 11
  (load calibration/region assignment), 12 (campaign freeze, shard plan,
  shard checksums).
- `campaign/raw/`, `campaign/enriched/` — per-shard scheduler-outcome rows
  before and after the provenance-repair pass; `campaign/enriched/.../
  consolidated.json` is the single admitted input to the frozen analysis.
- `analysis/canonical/` — the six frozen Phase-12 analysis-contract
  outputs (ranking correlations, top-k overlap, pairwise reversals,
  sample-complexity, temporal robustness, telemetry-conditioned
  explanation).
- `analysis/table_data/` — the exact JSON the paper's tables/figures are
  generated from.
- `analysis/extensions/cross_metric/` — the cross-metric ranking-portability
  extension (990 correlation records, 54,450 pairwise disagreement
  records; content-hash directory `33729102c2f8867cb521f8557cd51b42d8830811de8dea16cc7ab68d53b61fd9`).
- `analysis/extensions/slo_sensitivity/` — the SLO-definition-sensitivity
  extension, pilot and full-scale (19,800 raw cells; content-hash
  directory `424b332ff860870ae062db3360c18170476c19b462eb895dff69cd0d88b22c6d`).
- `real_vllm/provenance/` — engineering-only environment/fidelity records
  for the real-vLLM SLAI scheduler plugin; **no scheduler-outcome data**.
- `schemas/`, `checksums/`, `LICENSES/` — machine-readable row schema,
  full-release checksum ledger, third-party source license/acquisition
  documentation.

Both extension directories are labeled
`POST_PHASE12_RESULT_INDEPENDENT_ANALYSIS_EXTENSION` in their own status
manifests: computed by reusing the sealed Phase-12 analysis package's
statistical primitives as a library, without modifying, re-running, or
re-deriving any of the six canonical `analysis/canonical/` artifacts.

## Workload sources

Three real-world traffic sources, 40 windows each (120 total):
**BurstGPT** (CC-BY-4.0), **Azure LLM Inference Trace 2024** (CC-BY,
AzurePublicDataset), **Bailian/Qwen** anonymized traces (Apache-2.0). Raw
source files are **not** included in this release (see License section);
this dataset ships only LSSP-derived window samples and descriptors.

## Load regions

Six calibrated regions per (source, window) pair, 720 total assignments,
derived from a preregistered FIFO calibration (`lambda_ref`) with fixed
multipliers: `LOW`, `PRE_KNEE`, `KNEE`, `POST_KNEE`, `OVERLOAD`,
`HIGH_PRESSURE`.

## Policy panel: 11 primary / 13 total

13 scheduling policies total. 11 are `PRIMARY` (used for every RQ1-RQ5
ranking/reversal computation): 6 `REPOSITORY_NATIVE_CLASSICAL`
(fifo, edf, least_laxity_first, estimated_service_time_first,
weighted_fair_share, admission_control), 1 `SIMULATOR_PROXY`
(kv_constrained_online), 4 `FAITHFUL_EXTERNAL` (vllm_faithful,
vllm_chunked_prefill_faithful, sarathi_faithful, slai_faithful). 2 are
`STYLE_APPROXIMATION`, `ROBUSTNESS_ONLY` (vllm_style_token_budget,
scorpio_style_slo_guard) — included in robustness-family checks but never
in the core PRIMARY ranking.

## Scale

18,720 cells = 120 windows × 6 regions × 13 policies × 2 repetitions
(deterministic rep0/rep1). `campaign/raw/` (33MB) is the un-repaired
per-shard output; `campaign/enriched/` (76MB, includes the consolidated
18,720-row matrix) is the provenance-repaired, analysis-admitted version.

## Deterministic rep0/rep1 verification

Each cell is run twice under a fixed, cell-derived seed pair (not
independently randomized) so rep0/rep1 agreement is a determinism check,
not a variance estimate. Divergence between rep0 and rep1 for the same
cell indicates a non-determinism defect, not scientific variability, and
was checked as part of provenance repair.

## RQ mapping

| RQ | Question | Evidence in this dataset |
|---|---|---|
| RQ1 | Cross-source ranking stability | `analysis/canonical/` (990 conditions) |
| RQ2 | Temporal/provider/domain-shift stability | `analysis/canonical/` (temporal robustness) |
| RQ3 | Synthetic-stress → real-trace ranking transfer | **Pilot only** — see "RQ3 pilot boundary" below |
| RQ4 | Workload descriptors associated with reversals | `analysis/canonical/` (telemetry-conditioned explanation) |
| RQ5 | Sample complexity (how many windows needed) | `analysis/canonical/` (sample-complexity) |
| RQ6 | Simulated rankings/reversals vs. a real serving engine | **Complete** (result: `docs/RQ6_PUBLIC_RESULT_PROVENANCE.md`); raw per-cell rows not yet bundled in a tagged dataset revision — see "RQ6 status" below |
| — | Cross-metric ranking portability (post-campaign extension, not a numbered RQ) | `analysis/extensions/cross_metric/` |
| — | SLO-definition sensitivity (post-campaign extension, not a numbered RQ) | `analysis/extensions/slo_sensitivity/` |

## RQ3 pilot boundary

RQ3 is preregistered as a **SECONDARY** research question, never part of
this study's headline result contract. Only an engineering-validation
pilot of the synthetic-to-real transfer pipeline exists: 176/176 pilot
cells and 24/24 analysis records materialized, 0 schema-validation
failures, but the transfer statistic (Kendall's τ_b) is undefined in
21/24 (88%) pilot conditions by design (only 2 synthesis seeds per
family — too few for the frozen block-bootstrap statistic to resolve).
**No synthetic-to-real transfer conclusion, positive or negative, is
drawn from this pilot**, in this dataset or in the paper. A full-scale
(440-cell) extension has not been run and is deferred to future work; if
it is ever added to a future dataset release, it will appear as a
clearly separate `rq3_full_extension/` directory, never merged into or
retroactively relabeling the pilot data.

## RQ6 status

The 120-task real-vLLM calibration campaign (a *prerequisite* for RQ6,
not the RQ6 result itself) is complete (120/120 terminal states: 43
converged, 77 lower-bound already violating). The RQ6 scientific
ranking-agreement validation itself is now also complete: Slurm array job
`1222413` (240/240 cells, 2 policies x 3 sources x 40 windows/source)
completed, was independently validated (identity, completeness, schema,
provenance; 0 missing/duplicate/corrupt), and was analyzed with the
frozen `robustbench.real_llm.rq6_validation_analysis` implementation. The
result — the Azure/BurstGPT simulator-predicted reversal did not
reproduce; the Azure/Bailian-Qwen stable control did — is reported in the
manuscript's Real-System Validation section and in
`docs/RQ6_PUBLIC_RESULT_PROVENANCE.md` in the code repository (full
provenance: execution SHA, manifest hashes, analysis settings, complete
result JSON), independent of this dataset. **The 240 raw per-cell RQ6
outputs are not yet bundled into a tagged dataset revision here** — as
originally planned, they are a candidate for a separately tagged revision
(e.g. `v1.1`) rather than a silent addition to an existing release's
files (see "Versioning" below); that inclusion decision is made at actual
publication time, not by this draft.

## Fields / schema

`scheduler_outcomes` rows follow `robustbench.ranking_portability.schema.
RankingPortabilityCellResult` (schema `docs/schemas/
ranking_portability_cell_result_v1.md`) plus two release-level fields
(`dataset_release_version`, `campaign_freeze_sha256`). Field categories
(identifier / scientific input / outcome / provenance metadata) are
enumerated in `robustbench.dataset.lssp_release_contract.
SCHEDULER_OUTCOMES_FIELD_CATEGORY`.

### Observed vs. synthesized fields

All `campaign/` rows are **simulator-observed**, not synthesized —
produced by actually running each of the 13 policy implementations against
each window/region cell in `robustbench.simulator`. No field in this
release is imputed, interpolated, or estimated from a subset of cells.
`telemetry` fields are computed post-hoc from the simulator's own recorded
per-step state (never influence the scheduling decision that produced
them). Undefined-metric semantics (e.g. `mean_latency` is `NaN` when
`completion_fraction == 0.0`) are schema-valid, not missing data.

## Provenance

Every table traces to a frozen, hash-identified manifest:
`campaign_freeze_sha256` (`81fa3d9b...494f57a`), full-matrix hash
(`832d96d7...c62c1ccf`), admitted consolidated-input hash
(`73adf7d9...bde9c26`), analysis-code git SHA (`eb574a8c...6dfbddfd1`,
distinct from the documentation-only `bd641d4`). See `checksums/
release_checksums.json` for every released file's SHA-256.

## License / redistribution

See `LICENSES/THIRD_PARTY_SOURCES.md`. Third-party raw source data is
**not** included (referenced by canonical location + verified checksum
only). LSSP-derived artifacts (window samples, descriptors, campaign
matrix, analysis outputs) are released under [dataset license — to be
finalized at publication, consistent with the code repository's LICENSE].

## Limitations

- RQ6 (real-vLLM scheduler validation) is complete and its result/provenance
  is documented (`docs/RQ6_PUBLIC_RESULT_PROVENANCE.md`), but its 240 raw
  per-cell outputs are **not yet bundled as rows in this dataset release** —
  see "RQ6 status" above.
- `METRIC_DEFINITION_SENSITIVITY` and `SLO_DEFINITION_SENSITIVITY`
  robustness families have no implementing artifact; disclosed as a gap,
  not populated with an invented result.
- Bailian/Qwen license confidence is MEDIUM (single-source confirmation);
  see `LICENSES/THIRD_PARTY_SOURCES.md`.

## Intended research use

This dataset is intended for: (1) independently reproducing the paper's
RQ1–RQ5, cross-metric, and SLO-sensitivity results from the frozen,
hash-verified analysis outputs; (2) methodological research on
comparative-ranking-portability evaluation for systems benchmarks more
generally; (3) meta-research on benchmark sample complexity and
reversal-detection methodology. It is a simulator-derived comparative
benchmark, not a source of absolute latency/throughput numbers for any
real deployment.

## Out-of-scope uses

- **Not** validated evidence that any single scheduling policy is
  universally best — every ranking here is scoped to a specific
  (source, region, metric, SLO-definition) condition (see "RQ mapping").
- **Not** a substitute for real-hardware benchmarking; simulator outcomes
  are not claimed to match real-engine absolute performance anywhere in
  this release (see `real_vllm/provenance/`'s own scope note and the
  paper's Threats to Validity section).
- **Not** a general-purpose LLM-serving traces dataset — the three
  workload sources are referenced, not redistributed raw (see
  "License / redistribution"), and this release ships only LSSP-derived
  windows, descriptors, and outcomes for the specific policy panel and
  protocol described here.
- **Not** confirmatory synthetic-to-real transfer evidence for RQ3 (pilot
  only — see above). RQ6 real-vLLM validation evidence exists (see "RQ6
  status" above) but its raw rows are not part of this dataset release.

## Versioning

This draft has no assigned dataset revision yet. At actual publication,
this release will be tagged with an explicit revision identifier (e.g.
`v1.0`) on Hugging Face, paired with a specific GitHub release tag and
commit SHA for the code repository, so that "which paper result does
this dataset version support" is always answerable from the tag alone,
not from a mutable branch pointer. A future RQ6 addition will be a new,
separately tagged revision (e.g. `v1.1`), not an in-place rewrite of
`v1.0`'s files. See "Versioning and archival strategy" in
`docs/LSSP_DATASET_RELEASE_SCHEMA.md` for the full plan, including the
recommended persistent-identifier (Zenodo/DOI) sequencing.

## Contact / issues

For questions about this dataset or to report a data/documentation
issue, open an issue on the companion GitHub repository
(`github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark`)
rather than through Hugging Face discussions, so that dataset and code
issues stay in one tracker.

## How to load

```python
from huggingface_hub import snapshot_download
path = snapshot_download("SoroushVahidi/llm-serving-scheduler-portability",
                          repo_type="dataset")
```

## How to reproduce manuscript figures/tables

```bash
git clone https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark
cd llm-serving-scheduler-robustness-benchmark
pip install -e ".[dev]"
python paper/scripts/generate_phase12_tables_figures.py \
  --analysis-dir <downloaded>/analysis/canonical \
  --out-dir paper/generated/table_data
python paper/scripts/generate_phase12_figures.py
```

Both scripts hash-gate their inputs against the exact hashes above and
refuse to run on a mismatch.

## GitHub relation

Code: `github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark`.
This dataset is the released form of that repository's `artifacts/`
directory contents plus the Wulver-only campaign shards never committed to
git for size reasons.

## Citation

```
[BibTeX placeholder -- DOI not yet assigned; update at publication]
```
