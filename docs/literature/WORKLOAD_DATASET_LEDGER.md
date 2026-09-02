# WORKLOAD_DATASET_LEDGER.md

This ledger records the authoritative workload-related provenance and dataset semantics that matter for LSSP.

| source | authoritative record | provider / underlying infrastructure | period/version | semantics | LSSP role | caveats |
|---|---|---|---|---|---|---|
| BurstGPT | `BurstGPT: A Real-World Workload Dataset to Optimize LLM Serving Systems` (KDD 2025; DOI 10.1145/3711896.3737413; arXiv:2401.17644; GitHub `HPMLL/BurstGPT` v2.0) | Dataset released by HPMLL (academic group); **underlying traffic logged from a regional customer of Microsoft's Azure OpenAI GPT service** (per the paper's own abstract) | 213-day collection window; 10.31M traces (dataset-release figure; not independently row-counted by this project) | bursty request traces from LLM serving workloads | primary independent workload source | not a scheduler result; used as real-workload source. **Do not describe as an "independent provider" relative to this project's Azure trace sources** — see the provider-relationship caveat below. |
| Azure LLM Inference Trace 2023 (conversation / code) | official Azure/AzurePublicDataset GitHub release; analysis paper: Splitwise (Patel et al., ISCA 2024, arXiv:2311.18677) | Microsoft (own internal Azure LLM inference services) | collected 2023-11-11 | production-style inference trace over time | independent, Microsoft-released source | distinct from 2024; treat as a separate release. Same underlying cloud infrastructure family as BurstGPT (Azure) — see provider-relationship caveat. |
| Azure LLM Inference Trace 2024 | official Azure/AzurePublicDataset GitHub release; analysis paper: DynamoLLM (Stojkovic et al., HPCA 2025, arXiv:2408.00741) | Microsoft (own internal Azure LLM inference services) | collected 2024-05-10 to 2024-05-19 | production-style inference trace over time | independent, Microsoft-released source | distinct from 2023; use exact release/version. Same underlying cloud infrastructure family as BurstGPT (Azure) — see provider-relationship caveat. |
| Bailian / Qwen | project release or dataset registry as used by the repo | Alibaba / Qwen ecosystem | exact project snapshot | trace family with provider-specific semantics | independent source candidate | exact provenance must remain version-specific; do not imply identity with Azure or BurstGPT |
| TraceLab | `TraceLab: Characterizing Coding Agent Workloads for LLM Serving` (arXiv:2606.30560) | UW-SyFi + coding-agent trace collection | exact trace snapshot | coding-agent usage patterns and bursty agent sessions | OOD / workload-family context | provenance requires exact version control before manuscript use |
| ServeGen | `ServeGen: Workload Characterization and Generation of Large Language Model Serving in Production` (NSDI 2026; arXiv:2505.09999) | Alibaba / project team | generator version | synthetic workload generator for realism and drift | workload-generation context | not a source-equivalent dataset for scheduler ranking portability |
| LLM-2026 overlap / prior project artifact | repo-local historical artifact | historical project lineage | exact historical reproduction artifact | not a new public dataset | historical reference only | must not be repackaged as new evidence |

## Provider-relationship caveat (added Query 3, 2026-09-01/02)

BurstGPT's own paper states its traces come from a regional customer's use of **Microsoft's Azure OpenAI GPT service**. This project's own Azure 2023/2024 traces are also Microsoft's own official releases of internal Azure LLM inference service traffic. Both trace families therefore sit on Microsoft Azure's underlying LLM-serving infrastructure, collected through different mechanisms (third-party academic logging of one regional Azure OpenAI customer for BurstGPT; Microsoft's own internal release for the Azure 2023/2024 traces). **Primary-source evidence does not support calling BurstGPT and this project's Azure traces "independent providers."** They remain legitimately distinct, independently released *workload artifacts* — different collection methodology, different customer population, different release/version history, different research teams — and should be described that way. Bailian/Qwen (Alibaba Cloud) and TraceLab (UW-SyFi coding-agent sessions) are unaffected by this caveat; those remain genuinely different underlying platforms from Azure/BurstGPT.

## Safe terminology

- Use `workload source` rather than `dataset family` when the exact public trace is part of a broader benchmark family.
- Distinguish `distinct workload sources` / `independently released workload artifacts` (BurstGPT vs. this project's Azure traces) from genuinely different underlying platforms (Azure/BurstGPT vs. Bailian/Qwen vs. TraceLab).
- Do **not** use the phrase `independent providers` for the BurstGPT-vs-Azure pair; the underlying infrastructure is the same (Microsoft Azure), even though the release mechanisms, collection methodology, and datasets themselves are independent artifacts.
- Treat trace provenance as exact-version-sensitive; a source with a publication record is not automatically identical to the exact artifact used in LSSP.

## Forbidden terminology

- Do not use a blanket phrase such as `the LLM serving literature uses one common public trace family` when the project actually uses multiple independently released workload artifacts.
- Do not describe BurstGPT and this project's Azure traces as `independent providers`; use `distinct workload sources` / `independently released workload artifacts` instead.
