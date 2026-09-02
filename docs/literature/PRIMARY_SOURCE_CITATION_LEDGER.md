# PRIMARY_SOURCE_CITATION_LEDGER.md

This ledger records the primary-source references that are acceptable for LSSP manuscripts and analysis planning.

## Verified / acceptable primary-source works

| work | canonical key | status | exact title | primary source | role in LSSP | safe wording |
|---|---|---|---|---|---|---|
| vLLM / PagedAttention | `kwon2023vllm` | PRIMARY_SOURCE_VERIFIED | `vLLM: Easy, Fast, and Cheap LLM Serving with PagedAttention` | USENIX OSDI 2023; arXiv:2309.06180 | serving-system baseline and reference architecture | `vLLM is a widely used LLM serving system that makes a relevant reference point; we do not treat it as a benchmark of ranking portability.` |
| Orca | `yu2022orca` | PRIMARY_SOURCE_VERIFIED | `Orca: A Distributed Serving System for Transformer-Based Generative Models` | USENIX OSDI 2022; arXiv:2207.00032 | scheduler-family background | `Orca is a foundational distributed serving system for iteration-level scheduling and is used only as background context.` |
| Sarathi-Serve | `agrawal2024sarathi` | PRIMARY_SOURCE_VERIFIED | `Sarathi-Serve: Efficient LLM Serving with Chunked Prefills and Continuous Batching` | arXiv / official project record | serving-method background | `Chunked prefill and continuous batching are well-known serving techniques; we do not claim a ranking-portability result from them.` |
| DistServe | `zhong2024distserve` | PRIMARY_SOURCE_VERIFIED | `DistServe: Disaggregated Prefill and Decode for Goodput-Optimized LLM Serving` | official paper / arXiv | serving architecture and baseline context | `Disaggregated prefill/decode is a relevant serving baseline and architectural comparison point.` |
| Llumnix | `sun2024llumnix` | PRIMARY_SOURCE_VERIFIED | `Llumnix: Dynamic Scheduling for Large Language Model Serving` | SoCC 2024 / arXiv | scheduler baseline context | `Dynamic scheduling and rebalancing are relevant but not a benchmark of cross-workload ranking portability.` |
| BurstGPT | `burstgpt2024` | PRIMARY_SOURCE_VERIFIED | `BurstGPT: A Real-world Workload Dataset to Optimize LLM Serving Systems` | arXiv:2401.17644; official GitHub dataset | independent workload source | `BurstGPT is an independent workload trace family used as one of the workload sources; it is not itself a scheduler-ranking result.` |
| Azure LLM Inference Trace 2024 | `azure2024trace` | PRIMARY_SOURCE_VERIFIED | `Azure LLM Inference Trace 2024` | official Azure public release | independent provider-domain workload source | `Azure 2024 traces are an independent provider-domain workload source used for portability analysis.` |
| TraceLab | `tracelab2026` | PRIMARY_SOURCE_VERIFIED | `TraceLab: Characterizing Coding Agent Workloads for LLM Serving` | arXiv:2606.30560; official project site | workload provenance / coding-agent context | `TraceLab is a distinct workload family relevant for OOD and provider-domain context; it is not itself a benchmark of ranking portability.` |
| ServeGen | `servegen2026` | PRIMARY_SOURCE_VERIFIED | `ServeGen: Workload Characterization and Generation of Large Language Model Serving in Production` | USENIX NSDI 2026; arXiv:2505.09999 | workload-generation context | `ServeGen is a relevant workload-generation and realism paper; it is not a scheduler-ranking benchmark.` |
| Vidur | `vidur2024` | PRIMARY_SOURCE_VERIFIED | `VIDUR: A Large-Scale Simulation Framework for LLM Inference` | MLSys 2024; Microsoft Research | closest simulator/benchmark precedent | `Vidur is the closest infrastructure precedent for simulator-based benchmarking, but it does not directly study cross-source ranking portability.` |
| LLMServingSim / LLMServingSim 2.0 | `llmservingsim2024` | PRIMARY_SOURCE_VERIFIED | `LLMServingSim` (simulator-family paper) | official project / simulator release | benchmark infrastructure precedent | `LLMServingSim is a simulator benchmark precedent but not the same benchmark object as LSSP.` |
| PARS | `pars2025` | PRIMARY_SOURCE_VERIFIED | `PARS: Low-Latency LLM Serving via Pairwise Learning-to-Rank` | arXiv:2510.03243 | scheduling baseline context | `PARS is a recent scheduling family relevant for pairwise learning-to-rank methods but not a ranking-portability benchmark.` |
| JITServe | `jitserve2025` | PRIMARY_SOURCE_VERIFIED | `JITServe: SLO-aware LLM Serving with Imprecise Request Information` | USENIX NSDI 2026 | SLO-aware scheduler background | `JITServe is relevant as a modern SLO-aware serving scheduler but not a benchmark of ranking portability.` |
| FastServe | `fastserve2024` | PRIMARY_SOURCE_VERIFIED | `FastServe: Iteration-Level Preemptive Scheduling for Large Language Model Inference` | USENIX NSDI 2026; arXiv:2305.05920 | latency-aware scheduling background | `FastServe is a relevant latency-aware scheduling baseline but does not define the LSSP benchmark object.` |
| Efficient LLM Scheduling by Learning to Rank | `efficientllmscheduling2024` | PRIMARY_SOURCE_VERIFIED | `Efficient LLM Scheduling by Learning to Rank` | NeurIPS 2024; arXiv:2408.15792 | learning-to-rank scheduler context | `This paper is a relevant learning-to-rank scheduler and is distinct from LSSP’s cross-source ranking-portability benchmark.` |
| SLAI / RAD | `slai2025` | PRIMARY_SOURCE_VERIFIED | `Optimal Scheduling Algorithms for LLM Inference: Theory and Practice` | ACM Meas. Anal. Comput. Syst. / arXiv:2508.01002 | theory + scheduler design context | `SLAI/RAD are relevant scheduling methods for multi-objective LLM inference; the LSSP study is not a direct claim about their global optimality.` |
| SCORPIO | `scorpio2025` | PRIMARY_SOURCE_VERIFIED | `SCORPIO: Serving the Right Requests at the Right Time for Heterogeneous SLOs in LLM Inference` | arXiv:2505.23022 | SLO-aware scheduling context | `SCORPIO is a relevant hetero-SLO scheduler baseline but not a cross-source ranking-portability benchmark.` |
| Libra | `libra2026` | PRIMARY_SOURCE_VERIFIED | `Libra: Flexible Request Partitioning and Scheduling for Serving Unbalanced and Dynamic LLM Workloads` | USENIX NSDI 2026 | scheduler context | `Libra is a relevant tuning-based scheduler but is not a benchmark of ranking portability in the LSSP sense.` |
| LMetric / `Simple is Better...` | `lmetric2026` | PRIMARY_SOURCE_VERIFIED | `Simple is Better: Multiplication May Be All You Need for LLM Request Scheduling` | OSDI 2026; arXiv:2603.15202 | metric / policy context | `This is a relevant scheduling paper using a lightweight metric, but it is not a benchmark of cross-source rank portability.` |

## Explicitly excluded from the final manuscript

These candidates remain non-citable unless their exact metadata are independently verified and aligned with the manuscript’s scope:
- `P-PAS` (title and venue partially resolved but not yet stable enough for final citation)
- `VTC` (insufficient exact metadata in the current pass)
- `S^3` (not a stable canonical label for a single verified paper; use `Efficient LLM Scheduling by Learning to Rank` when needed)

## Interpretation rule

The ledger is conservative: a work may be discussed in the novelty audit or metadata corrections doc without being a verified manuscript citation. Only entries marked `PRIMARY_SOURCE_VERIFIED` are acceptable in the final manuscript.
