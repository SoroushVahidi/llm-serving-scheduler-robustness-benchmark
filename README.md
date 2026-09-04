# LLM-Serving Scheduler Portability Benchmark (LSSP)

**How portable are LLM-serving scheduler rankings across workloads,
operating regions, and metrics?** LSSP measures whether the best-ranked
LLM-serving scheduling policy stays best when you change the traffic
source, the load level, or the ranking metric — or whether comparative
conclusions from one paper's benchmark setup silently fail to generalize
to another's.

Companion artifact for the manuscript *"How Portable Are LLM-Serving
Scheduler Rankings Across Workloads, Operating Regions, and Metrics?"*
(Soroush Vahidi), prepared for submission to *The Journal of
Supercomputing*.

## Paper and archival resources

| | |
|---|---|
| Manuscript (PDF, in this repository) | [`How_Portable_Are_LLM-Serving_Scheduler_Rankings_Across_Workloads_Operating_Regions_and_Metrics.pdf`](./How_Portable_Are_LLM-Serving_Scheduler_Rankings_Across_Workloads_Operating_Regions_and_Metrics.pdf) |
| GitHub release | [`v1.0.0`](https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark/releases/tag/v1.0.0) |
| Archived snapshot (Zenodo) | [10.5281/zenodo.22306798](https://doi.org/10.5281/zenodo.22306798) |
| Derived dataset (Hugging Face) | [`SoroushVahidi/llm-serving-scheduler-portability`](https://huggingface.co/datasets/SoroushVahidi/llm-serving-scheduler-portability) |

## Study at a glance

| | |
|---|---|
| Independently released workload sources | 3 (BurstGPT, Azure LLM Inference Trace 2024, Bailian/Qwen) — BurstGPT and Azure are distinct releases, not independent underlying providers |
| Workload windows | 120 (40 per source), 200 requests each |
| Scheduling policies executed | 13 (11 `PRIMARY` + 2 `STYLE_APPROXIMATION` robustness-only) |
| Calibrated operating regions | 6 |
| Unique policy–window–region configurations | 9,360 |
| Deterministic verification passes per configuration | 2 (a determinism check, not an independent statistical sample) |
| Total simulator executions | 18,720 |
| RQ6 physical (real-vLLM) executions | 240 (2 policies × 3 sources × 40 windows, one execution per cell) |

## Main findings

Evidence status is labeled explicitly below — see the manuscript for full detail.

- **Primary.** Cross-source ranking portability is real but uneven: Kendall's
  τ<sub>b</sub> ranges 0.55–1.00 across source pairs and regions. 3.6%
  (36/990) of pairwise comparisons are statistically supported reversals,
  all involving the same policy pair, with one workload source (BurstGPT)
  on one side of every case.
- **Post-campaign sensitivity.** Ranking portability across *evaluation
  metrics* is more limited than across sources (median τ<sub>b</sub> =
  0.419, top-ranked policy agrees in only 31.9% of conditions). Portability
  under alternative SLO-synthesis conventions is comparatively high but
  not perfect.
- **Pilot only.** RQ3 (synthetic-to-real ranking transfer) has an
  engineering-validation pilot but draws no transfer conclusion — the
  transfer statistic is undefined in most pilot conditions by design.
- **Selected-case physical validation.** RQ6 ran 2 of the 13 panel
  policies on 3 sources at one operating region on a real vLLM/GPU
  deployment. The simulator's largest-effect-size predicted reversal did
  **not** reproduce on physical hardware; a paired stable-ordering control
  **did** retain its qualitative ordering. This is evidence of a
  selected-case simulator-fidelity boundary, not a general estimate of
  hardware reversal prevalence.

## Artifact map

| Surface | Contains | Does not contain |
|---|---|---|
| **GitHub** (this repository) | Simulator, policy implementations, analysis pipeline, frozen manifests, manuscript source and PDF, reproduction tooling | The exploded raw per-cell campaign matrix (too large for git); raw third-party traces |
| **Hugging Face** | A small, explicitly-scoped set of derived, analysis-ready outputs (currently: two headline result tables and the reduced RQ6 result) — see the dataset card for the exact file list and what's deferred | The six intermediate canonical analysis artifacts; the exploded 18,720-execution matrix; the 240 raw RQ6 per-cell records; raw third-party traces |
| **Zenodo** | Immutable archive of the GitHub `v1.0.0` release | — |
| **Third-party sources** | Referenced by canonical location, license, and checksum (BurstGPT, Azure-2024, Bailian/Qwen) | Not redistributed raw under this project's license — acquire from the original publishers |

## Quick start

```bash
git clone https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark
cd llm-serving-scheduler-robustness-benchmark
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Reproduce the reported analyses

**Tier 1 — smoke verification (seconds, no GPU, no trace acquisition):**

```bash
./scripts/artifact/run_toy_reproduction.sh
```

Runs the full simulator/analysis pipeline end-to-end on a synthetic
fixture to confirm the installation works. Not scientific evidence on its
own. See `docs/ARTIFACT_EVALUATION_GUIDE.md` for the full reviewer-facing
evaluation path.

**Tier 2 — check the released headline numbers:**

The Hugging Face dataset currently ships two headline result tables
(`table_data/rq1_rq2_portability.json`, `table_data/rq4_sample_complexity.json`)
and the reduced RQ6 result (`rq6/RQ6_ANALYSIS_RESULT.json`), each with a
documented fidelity note on the dataset card. These let you independently
check the numbers reported in the manuscript by direct inspection against
the released JSON. The six intermediate canonical analysis artifacts that
`paper/scripts/generate_phase12_tables_figures.py` consumes as *input*
are not (yet) part of the public dataset release, so that script cannot
currently be run against the Hugging Face download — see the dataset
card's "What's in this release" table for exactly what is and isn't
included, and why.

**Tier 3 — full campaign regeneration (expensive, optional):**

Rerunning all 18,720 executions is not required to verify the paper —
only to independently regenerate the campaign matrix itself. See
`docs/ARTIFACT_EVALUATION_GUIDE.md` and `scripts/artifact/run_frozen_campaign.sh`.
This takes substantially longer than the Tier 1 smoke test and needs the
raw source traces acquired separately (see
`docs/LSSP_THIRD_PARTY_SOURCE_LICENSES.md`).

## Scope and limitations

- RQ3 is a pilot/engineering-validation result only; no synthetic-to-real
  transfer conclusion is drawn.
- RQ6 is a selected-case physical validation (2 of 13 policies, 3
  sources, one operating region, one hardware/software environment, one
  physical execution per cell) — not a comprehensive real-hardware
  re-execution of the full campaign.
- The study does not isolate a causal provider effect from ordinary
  cross-source variation (BurstGPT and Azure share underlying cloud
  infrastructure).
- One preregistered robustness family (`METRIC_DEFINITION_SENSITIVITY`)
  has no implementing artifact — disclosed as a gap, not filled with an
  invented result.
- Raw third-party workload traces are not redistributed; see the license
  audit below.

Full detail: `paper/sections/limitations.tex` (Threats to Validity).

## Citation

See [`CITATION.cff`](./CITATION.cff). The manuscript's own citation will
be added once a journal DOI exists; the archived-artifact citation
(Zenodo DOI above) is available now.

## License

Project code and released project content are MIT-licensed (see
[`LICENSE`](./LICENSE)). Third-party raw workload traces (BurstGPT,
Azure LLM Inference Trace 2024, Bailian/Qwen) remain under their original
publishers' licenses and are not redistributed here — see
`docs/LSSP_THIRD_PARTY_SOURCE_LICENSES.md` for per-source terms and
acquisition instructions.

## Documentation

`docs/README.md` is the documentation index: current reviewer-facing
guides vs. scientific provenance/freeze records vs. historical/internal
development notes, organized so you don't have to guess which `docs/*.md`
file is authoritative.
