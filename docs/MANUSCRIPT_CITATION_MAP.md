# MANUSCRIPT_CITATION_MAP.md

This map ties the central manuscript sections to the verified literature and LSSP project documents.

| manuscript section | required citation posture | citation keys | project documents |
|---|---|---|---|
| Introduction | motivation and background | `kwon2023vllm`, `yu2022orca`, `agrawal2024sarathi`, `zhong2024distserve`, `burstgpt2024`, `azure2024trace`, `servegen2026` | `docs/PROJECT_STATUS.md`, `docs/SCIENTIFIC_CAVEATS_AND_OPEN_ISSUES.md` |
| Related Work | narrow and conservative positioning | `kwon2023vllm`, `vidur2024`, `servegen2026`, `burstgpt2024`, `azure2024trace`, `tracelab2026`, `fastserve2024`, `jitserve2025`, `pars2025`, `libra2026` | `docs/literature/RELATED_WORK_POSITIONING.md`, `docs/literature/NOVELTY_THREAT_LEDGER.md` |
| Workload provenance | dataset semantics and exact trace families | `burstgpt2024`, `azure2024trace`, `tracelab2026`, `servegen2026` | `docs/literature/WORKLOAD_DATASET_LEDGER.md` |
| Scheduler methodology | mechanism context only | `yu2022orca`, `agrawal2024sarathi`, `zhong2024distserve`, `sun2024llumnix`, `fastserve2024`, `jitserve2025`, `pars2025`, `libra2026`, `efficientllmscheduling2024`, `slai2025`, `scorpio2025` | `docs/literature/SCHEDULER_BASELINE_LEDGER.md` |
| Benchmark design | benchmark object + protocol | project-local protocol docs; simulator precedent only | `docs/PROJECT_ROADMAP.md`, `docs/literature/BENCHMARK_SIMULATOR_LEDGER.md` |
| Statistical analysis | ranking-specific methods | project-defined analysis plan; standard methods | `docs/literature/STATISTICAL_METHODS_LEDGER.md` |
| Limitations | explicit boundary and unresolved provenance | `burstgpt2024`, `azure2024trace`, `tracelab2026` and project caveat docs | `docs/SCIENTIFIC_CAVEATS_AND_OPEN_ISSUES.md` |

## Rule

The manuscript should not claim any direct benchmark result from a cited system if that system was never used as a benchmark object for ranking portability in the exact sense the project defines.
