# LLM-Serving Scheduler Portability Benchmark (LSSP)

**How portable are LLM-serving scheduler rankings across workloads,
operating regions, and metrics?** LSSP measures whether the best-ranked
LLM-serving scheduling policy stays best when you change the traffic
source, the load level, or the ranking metric — or whether comparative
conclusions from one paper's benchmark setup silently fail to generalize
to another's.

Companion repository to the manuscript *"How Portable Are LLM-Serving
Scheduler Rankings Across Workloads, Operating Regions, and Metrics?"*
(Soroush Vahidi, submitted to the *Journal of Supercomputing*).

## What's here

- **Simulator + policy library** (`src/robustbench/`): 13 scheduling
  policies (FIFO, EDF, least-laxity-first, weighted-fair-share,
  admission-control, KV-constrained-online, plus faithful reimplementations
  of vLLM, vLLM-chunked-prefill, Sarathi, and SLAI/RAD scheduling).
- **Workload ingestion** for three real traffic sources: BurstGPT,
  Azure LLM Inference Trace 2024, and Bailian/Qwen anonymized traces.
- **The Phase-12 campaign**: 120 workload windows (40 per source) × 6
  calibrated load regions × 13 policies × 2 deterministic repetitions =
  **18,720 simulated scheduler-outcome cells**, plus the frozen statistical
  analysis run over them (ranking correlation, top-k overlap, pairwise
  reversal detection, sample-complexity, temporal and 7-family robustness
  checks).
- **Real-vLLM engineering infrastructure** (`src/robustbench/real_llm/`):
  a `--scheduler-cls` plugin reproducing the SLAI/RAD policy inside actual
  vLLM 0.27.1, algorithm-fidelity-tested against the simulator, plus
  server/orchestration/provenance tooling for RQ6, now used to execute the
  240-cell RQ6 scientific campaign itself (Slurm job `1222413`,
  240/240 completed, validated 240/240).
- **The manuscript source** (`paper/`), built from the same hash-pinned
  analysis artifacts this repo ships.

## Research questions

| | |
|---|---|
| RQ1 | How stable are scheduler rankings across independent workload sources? |
| RQ2 | How stable are scheduler rankings under temporal, provider, and domain shifts? |
| RQ3 | To what extent do rankings obtained on synthetic stress workloads transfer to rankings on independent real-trace-derived workloads? |
| RQ4 | Which source-native observable workload characteristics are associated with cross-distribution scheduler rank reversals? |
| RQ5 | How many independent workload windows are required before a comparative scheduler ranking becomes statistically stable? |
| RQ6 | Do representative simulated scheduler rankings and cross-workload rank reversals reproduce on a real serving engine? |

In addition to RQ1-RQ6, the benchmark extends its core portability question to evaluate **cross-metric disagreement** and **SLO-definition sensitivity** as critical, standalone sensitivity axes.

## Status

| | |
|---|---|
| Phase 10 (workload windows) | Complete, frozen |
| Phase 11 (load calibration) | Complete, frozen |
| Phase 12 (18,720-cell campaign) | Complete, frozen |
| Phase 12 statistical analysis | Complete, validated |
| RQ1–RQ5 & sensitivity axes | Complete, interpreted, populated in the manuscript |
| RQ6 case selection | Complete, frozen |
| RQ6 real-vLLM scientific execution | **Complete** — 240/240 cells (Slurm job `1222413`), all validated, exit `0:0` |
| RQ6 statistical analysis | **Complete** — reversal not reproduced, stable control reproduced (see manuscript §Real-System Validation and `docs/RQ6_PUBLIC_RESULT_PROVENANCE.md`) |
| Manuscript | RQ6 integrated; build verified (38 pages, 0 undefined refs/citations); publication/release gate in progress |

Nothing above is provisional language left over from an earlier draft —
every "complete" here is backed by a hash-identified, independently
re-verified artifact (see `docs/LSSP_DATASET_RELEASE_SCHEMA.md` for the
identity chain). RQ6 is no longer an open item: the real-vLLM scheduler
plugin was used to execute all 240 frozen (policy, source, window) cells,
every output was independently validated against the frozen task-matrix
enumeration (identity, completeness, schema, provenance, no duplicates/
overwrites), and the frozen, unmodified analysis implementation
(`robustbench.real_llm.rq6_validation_analysis`) was run against that
validated dataset. Result: all three real-system SLAI-vs-vLLM effects are
statistically supported and favor `vllm_faithful`; the simulator-predicted
Azure/BurstGPT reversal did not reproduce, while the Azure/Bailian-Qwen
stable control did. The manuscript's RQ6 section reports this result, not
a pending contract.

## Install

```bash
git clone https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark
cd llm-serving-scheduler-robustness-benchmark
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Run a small smoke

```bash
./scripts/artifact/run_toy_reproduction.sh
```

Runs a handful of cells end-to-end on synthetic data — no real trace
acquisition, no GPU, seconds not hours. See `docs/ARTIFACT_EVALUATION_GUIDE.md`
for the full reviewer-facing evaluation path.

## Reproduce the paper's analysis from the released dataset

The 18,720-cell campaign matrix and its six canonical analysis outputs are
**not** in this git repository (too large; see `docs/
LSSP_DATASET_RELEASE_SCHEMA.md`). They will be released as
`SoroushVahidi/llm-serving-scheduler-portability` on Hugging Face
(**not yet published** — see that doc's status note).

```bash
python scripts/dataset/validate_lssp_release.py --release-dir <downloaded>
python paper/scripts/generate_phase12_tables_figures.py --analysis-dir <downloaded>/analysis/canonical
python paper/scripts/generate_phase12_figures.py
```

Both generation scripts hash-gate their inputs against the exact frozen
hashes and refuse to run on any mismatch — you cannot silently regenerate
the paper's tables from different data.

## Full campaign reproduction (expensive, optional)

Rerunning all 18,720 cells is not required to verify the paper — only to
independently regenerate the campaign matrix itself. See
`docs/ARTIFACT_EVALUATION_GUIDE.md` and `scripts/artifact/
run_frozen_campaign.sh`. This takes substantially longer than the toy
smoke above and needs the raw source traces acquired separately (see
`docs/LSSP_THIRD_PARTY_SOURCE_LICENSES.md`).

## Limitations

- RQ6 is a selected-case physical validation (2 of 13 policies, 3 sources,
  one operating region, one hardware/software environment, one physical
  execution per policy/window) — not a comprehensive real-hardware
  re-execution of the full Pilot-V2 matrix (see Status above and
  `paper/sections/limitations.tex`).
- One preregistered robustness-family gap (`METRIC_DEFINITION_SENSITIVITY`) has no implementing artifact — reported as a disclosed gap in the manuscript, not filled with an invented result.
- Full details: `paper/sections/limitations.tex`.

## Citation

BibTeX placeholder — DOI not yet assigned; will be added at publication.
See `CITATION.cff`.

## Documentation index

`docs/README.md` — current guides vs. scientific freeze records vs.
internal engineering notes, organized so you don't have to guess which
`docs/*.md` file is still authoritative. `docs/RQ6_PUBLIC_RESULT_PROVENANCE.md`
carries the full completed-RQ6 result and computational provenance
independently of the private cluster it was executed on.
