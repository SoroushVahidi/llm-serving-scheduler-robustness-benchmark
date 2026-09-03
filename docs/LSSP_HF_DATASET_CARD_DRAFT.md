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

Companion dataset to "[paper title, Journal of Supercomputing submission]"
(GitHub: `SoroushVahidi/llm-serving-scheduler-robustness-benchmark`,
branch lineage `manuscript/lssp-jsc-polish-20260902`). RQ1-RQ5 in the
paper are computed directly from `analysis/canonical/` in this dataset.
**RQ6 (real-vLLM validation) has no data in this release yet** — see
"RQ6 status" below.

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
- `real_vllm/provenance/` — engineering-only environment/fidelity records
  for the real-vLLM SLAI scheduler plugin; **no scheduler-outcome data**.
- `schemas/`, `checksums/`, `LICENSES/` — machine-readable row schema,
  full-release checksum ledger, third-party source license/acquisition
  documentation.

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

- RQ6 (real-vLLM scheduler validation) has **no scientific data** in this
  release — engineering/fidelity validation only, disclosed separately.
- `METRIC_DEFINITION_SENSITIVITY` and `SLO_DEFINITION_SENSITIVITY`
  robustness families have no implementing artifact; disclosed as a gap,
  not populated with an invented result.
- Bailian/Qwen license confidence is MEDIUM (single-source confirmation);
  see `LICENSES/THIRD_PARTY_SOURCES.md`.

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
