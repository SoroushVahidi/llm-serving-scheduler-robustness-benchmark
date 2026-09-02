# WORKLOAD_DATASET_LEDGER.md

This ledger records the authoritative workload-related provenance and dataset semantics that matter for LSSP.

| source | authoritative record | provider | period/version | semantics | LSSP role | caveats |
|---|---|---|---|---|---|---|
| BurstGPT | `BurstGPT: A Real-world Workload Dataset to Optimize LLM Serving Systems` (arXiv:2401.17644; GitHub dataset release) | HPMLL | release-versioned trace family | bursty request traces from LLM serving workloads | primary independent source | not a scheduler result; used as real-workload source |
| Azure LLM Inference Trace 2023 | official Azure public trace release | Microsoft Azure | 2023 public release | production-style inference trace over time | independent provider-domain source | distinct from 2024; treat as separate source |
| Azure LLM Inference Trace 2024 | official Azure public trace release | Microsoft Azure | 2024 public release | production-style inference trace over time | independent provider-domain source | distinct from 2023; use exact release/version |
| Bailian / Qwen | project release or dataset registry as used by the repo | Alibaba / Qwen ecosystem | exact project snapshot | trace family with provider-specific semantics | independent source candidate | exact provenance must remain version-specific; do not imply identity with Azure or BurstGPT |
| TraceLab | `TraceLab: Characterizing Coding Agent Workloads for LLM Serving` (arXiv:2606.30560) | UW-SyFi + coding-agent trace collection | exact trace snapshot | coding-agent usage patterns and bursty agent sessions | OOD / workload-family context | provenance requires exact version control before manuscript use |
| ServeGen | `ServeGen: Workload Characterization and Generation of Large Language Model Serving in Production` (NSDI 2026; arXiv:2505.09999) | Alibaba / project team | generator version | synthetic workload generator for realism and drift | workload-generation context | not a source-equivalent dataset for scheduler ranking portability |
| LLM-2026 overlap / prior project artifact | repo-local historical artifact | historical project lineage | exact historical reproduction artifact | not a new public dataset | historical reference only | must not be repackaged as new evidence |

## Safe terminology

- Use `workload source` rather than `dataset family` when the exact public trace is part of a broader benchmark family.
- Distinguish provider-domain sources (Azure, Qwen/Bailian, BurstGPT) from generator-based artifacts (ServeGen).
- Treat trace provenance as exact-version-sensitive; a source with a publication record is not automatically identical to the exact artifact used in LSSP.

## Forbidden terminology

Do not use a blanket phrase such as `the LLM serving literature uses one common public trace family` when the project actually uses multiple independent provider sources and workload families.
