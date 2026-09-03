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
  server/orchestration/provenance tooling for RQ6.
- **The manuscript source** (`paper/`), built from the same hash-pinned
  analysis artifacts this repo ships.

## Research questions

| | |
|---|---|
| RQ1–RQ2 | Do scheduler rankings stay stable across workload sources and load regions? |
| RQ3 | Do rankings stay stable across ranking metrics (top-1 vs. top-3, different correlation measures)? |
| RQ4 | How much data (how many windows) does a reliable ranking require? |
| RQ5 | How robust are the conclusions to 7 methodological perturbations (temporal split, policy-family leave-one-out, etc.)? |
| RQ6 | Do the simulator's conclusions hold when the same scheduling logic runs inside real vLLM under contention? |

## Status

| | |
|---|---|
| Phase 10 (workload windows) | Complete, frozen |
| Phase 11 (load calibration) | Complete, frozen |
| Phase 12 (18,720-cell campaign) | Complete, frozen |
| Phase 12 statistical analysis | Complete, validated |
| RQ1–RQ5 | Complete, interpreted, populated in the manuscript |
| RQ6 case selection (which cells to validate on real vLLM) | Complete, frozen |
| RQ6 real-vLLM scheduler plugin | Engineering-validated (algorithm-fidelity + local forced-contention); **not yet run as scientific evidence** |
| Manuscript | Ready pending RQ6 |

Nothing above is provisional language left over from an earlier draft —
every "complete" here is backed by a hash-identified, independently
re-verified artifact (see `docs/LSSP_DATASET_RELEASE_SCHEMA.md` for the
identity chain). RQ6 is explicitly the one open item: the plugin is
validated as *engineering*, but no real-vLLM run has yet produced
scientific evidence, and the manuscript's RQ6 section says so rather than
reporting one.

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

- RQ6 has no real-vLLM scientific data yet (see Status above).
- Two disclosed robustness-family gaps (`METRIC_DEFINITION_SENSITIVITY`,
  `SLO_DEFINITION_SENSITIVITY`) have no implementing artifact — reported
  as gaps in the manuscript, not filled with an invented result.
- Full details: `paper/sections/limitations.tex`.

## Citation

BibTeX placeholder — DOI not yet assigned; will be added at publication.
See `CITATION.cff`.

## Documentation index

`docs/README.md` — current guides vs. scientific freeze records vs.
internal engineering notes, organized so you don't have to guess which
`docs/*.md` file is still authoritative.
