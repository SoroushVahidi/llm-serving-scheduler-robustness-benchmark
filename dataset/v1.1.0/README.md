---
license: cc-by-4.0
pretty_name: LLM-Serving Scheduler Portability (LSSP) — complete Phase-12 evidence
tags:
  - llm-serving
  - scheduling
  - systems
  - benchmark
  - reproducibility
  - ranking-portability
  - simulation
  - performance-evaluation
configs:
  - config_name: scheduler_outcomes
    default: true
    data_files:
      - split: train
        path: data/tables/scheduler_outcomes.parquet
  - config_name: unique_configurations
    data_files:
      - split: train
        path: data/tables/unique_configurations.parquet
  - config_name: workload_windows
    data_files:
      - split: train
        path: data/tables/workload_windows.parquet
  - config_name: load_region_assignments
    data_files:
      - split: train
        path: data/tables/load_region_assignments.parquet
  - config_name: policy_registry
    data_files:
      - split: train
        path: data/tables/policy_registry.parquet
  - config_name: pairwise_reversals
    data_files:
      - split: train
        path: data/tables/pairwise_reversals.parquet
  - config_name: ranking_correlations
    data_files:
      - split: train
        path: data/tables/ranking_correlations.parquet
  - config_name: sample_complexity
    data_files:
      - split: train
        path: data/tables/sample_complexity.parquet
  - config_name: telemetry_explanation
    data_files:
      - split: train
        path: data/tables/telemetry_explanation.parquet
  - config_name: temporal_robustness
    data_files:
      - split: train
        path: data/tables/temporal_robustness.parquet
  - config_name: topk_overlap
    data_files:
      - split: train
        path: data/tables/topk_overlap.parquet
---

# LLM-Serving Scheduler Portability (LSSP) — v1.1.0

This is an **expanded, reproducibility-oriented release of previously completed LSSP experiments**. It makes the frozen Phase-12 simulation matrix and six canonical analysis artifacts available in the existing LSSP dataset lineage. It is **not a new experimental campaign** or a claim of new independent scientific results.

The [companion manuscript](https://www.researchsquare.com/article/rs-10935389/v1), *How Portable Are LLM-Serving Scheduler Rankings Across Workloads, Operating Regions, and Metrics?* (Soroush Vahidi), studies whether comparative scheduler rankings survive changes in workload source, operating region, and metric. [Code and manuscript source](https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark) are separate from this data repository. The existing [Zenodo DOI 10.5281/zenodo.22306798](https://doi.org/10.5281/zenodo.22306798) archives the **v1.0.0 software repository**, not this data package. No dataset-specific DOI is claimed here until one is actually issued.

## What this revision adds

| Resource | v1.0.0 | v1.1.0 |
|---|---|---|
| Full Phase-12 execution matrix | Absent | **18,720 unchanged source rows** in `scientific/campaign/consolidated.json`; loadable `scheduler_outcomes` Parquet view |
| Unique policy–window–region configurations | Described, no table | **9,360** in `unique_configurations`, each with two deterministic verification passes |
| Six canonical Phase-12 analysis files | Absent | All six unchanged files in `scientific/analysis/`, plus six separate Parquet views |
| Frozen verification context | GitHub links | Selected exact manifests and passing amended matrix-validation report included |
| v1.0.0 reduced tables and RQ6 result | Present | Existing files remain byte-identical; RQ6 is a separate 240-execution physical study |

One [public GitHub engineering-smoke file](https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark/blob/main/artifacts/manifests/ranking_portability_phase12_smoke_raw.json) already contained **468 matching keyed numerical outcomes** (2.5% of the complete matrix). Source family, window, policy, region, repetition, seed, load factor, all 11 measurements, and telemetry match on these keys; the smoke status/code provenance differs from the final amended campaign. **18,252 keyed outcomes** had no matching row in the identified public LSSP releases. All 18,720 are retained for a coherent frozen matrix. The public manuscript tables already expose selected projections of the six analyses, including all 36 temporal-robustness numerical records. See [PUBLICATION_OVERLAP.md](PUBLICATION_OVERLAP.md) for the exact comparison and limits. The bounded third-party search found no demonstrably equivalent result dataset; it cannot prove that none exists anywhere.

## Experimental unit and scope

The complete matrix contains 120 workload windows (40 each from BurstGPT, Azure LLM Inference Trace 2024, and Bailian/Qwen), six FIFO-calibrated operating regions, and 13 executed policies (11 primary, two style-approximation robustness policies). Each policy–window–region configuration was simulated twice **deterministically** to verify repeatability. The workload window is the statistical unit; 18,720 executions are neither 18,720 independent samples nor 18,720 new experiments. Results are simulated under one frozen configuration, not general measurements of physical vLLM performance.

The matrix provides the primary arrival-normalized weighted goodput (ANWG) and ten other completion, latency, TTFT, throughput, weighted-goodput and SLO measures, plus mechanism telemetry. Conditional measurements can be undefined (`NaN` in the original JSON and the Parquet view); never replace them with zero. [SCHEMA.md](SCHEMA.md), [EXPERIMENT_DESIGN.md](EXPERIMENT_DESIGN.md) and [LIMITATIONS.md](LIMITATIONS.md) define fields, methods and interpretation.

## Load and verify

```python
from datasets import load_dataset

repo = "SoroushVahidi/llm-serving-scheduler-portability"
outcomes = load_dataset(repo, name="scheduler_outcomes", split="train", revision="v1.1.0")
configs = load_dataset(repo, name="unique_configurations", split="train", revision="v1.1.0")
print(len(outcomes), len(configs))  # 18720, 9360
```

The `revision` name shown above identifies the v1.1.0 dataset tag. To test a local copy, replace `repo` with its package-directory path. See [USAGE.md](USAGE.md) for tested Hugging Face and pandas examples, canonical-analysis access, and checksum commands. Every Parquet row was checked against its corresponding original JSON row; the original seven scientific files remain authoritative. Run `python scripts/validate_release.py` from a downloaded package to check hashes, keys, configurations, analysis identities, overlap and view equivalence. Add `--verify-public-smoke` to fetch and independently compare the pinned public 468-row file. See [VALIDATION.md](VALIDATION.md).

## Scientific interpretation

The manuscript reports uneven cross-source ranking portability and 36 statistically supported primary-metric policy-pair reversals among 990 comparisons, all involving one policy pair and BurstGPT on one side. The historical discriminability pilot had a genuine preregistered BurstGPT criterion failure; the RQ3 synthetic-to-real transfer pilot is **inconclusive** and does not support a transfer claim. The selected RQ6 physical experiment did **not** reproduce the simulator's largest predicted Azure/BurstGPT reversal, while its stable-order control retained qualitative ordering. These negative and limiting outcomes are part of the evidence, not exceptions to hide. See the [manuscript](https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark) and [LIMITATIONS.md](LIMITATIONS.md).

## Rights, citation, and versioning

The v1.1.0 release offers original LSSP scientific data, analyses, metadata and documentation under [CC BY 4.0](LICENSE-DATA), and release scripts under [MIT](LICENSE). See [LICENSE_SCOPE.md](LICENSE_SCOPE.md) for exact file groups. Previously public v1.0.0 files carried MIT terms; those historical permissions remain effective and are not revoked. Upstream trace rights are excluded. CC BY attribution when sharing licensed material is distinct from the separately recommended scholarly citation; the license does not require paper citation merely for using numerical facts. Original third-party request rows are not included. See [THIRD_PARTY_ATTRIBUTION.md](THIRD_PARTY_ATTRIBUTION.md) and [CITATION.md](CITATION.md). Existing HF v1.0.0 history, GitHub tags and the Zenodo Software DOI remain unchanged.

Documentation: [USAGE](USAGE.md) · [SCHEMA](SCHEMA.md) · [EXPERIMENT_DESIGN](EXPERIMENT_DESIGN.md) · [PROVENANCE](PROVENANCE.md) · [VALIDATION](VALIDATION.md) · [PUBLICATION_OVERLAP](PUBLICATION_OVERLAP.md) · [LIMITATIONS](LIMITATIONS.md) · [CHANGELOG](CHANGELOG.md).

## Acknowledgments

The computational experiments supporting this dataset used Wulver, the high-performance computing system provided by the New Jersey Institute of Technology (NJIT). The author gratefully acknowledges NJIT for providing these computational resources.

[CloudRift](https://cloudrift.ai) provided $1,000 in research credits supporting this research. These acknowledgments do not imply ownership, authorship, licensing, approval or endorsement.
