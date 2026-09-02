# SCHEDULER_BASELINE_LEDGER.md

This ledger maps the scheduler literature relevant as method or baseline context for LSSP.

| scheduler / family | exact title | status | primary source | LSSP mapping | caveat |
|---|---|---|---|---|---|
| vLLM / PagedAttention | `vLLM: Easy, Fast, and Cheap LLM Serving with PagedAttention` | verified | USENIX OSDI 2023 | serving-system baseline and reference architecture | not a portability benchmark |
| Orca | `Orca: A Distributed Serving System for Transformer-Based Generative Models` | verified | USENIX OSDI 2022 | scheduler-family background | not a portability benchmark |
| Sarathi-Serve | `Sarathi-Serve: Efficient LLM Serving with Chunked Prefills and Continuous Batching` | verified | arXiv / official project record | prefill/decode batching context | not a ranking-portability benchmark |
| DistServe | `DistServe: Disaggregated Prefill and Decode for Goodput-Optimized LLM Serving` | verified | official paper / arXiv | disaggregation and throughput context | not a direct benchmark of portability |
| Llumnix | `Llumnix: Dynamic Scheduling for Large Language Model Serving` | verified | SoCC 2024 / arXiv | dynamic scheduling context | not a cross-source benchmark |
| FastServe | `FastServe: Iteration-Level Preemptive Scheduling for Large Language Model Inference` | verified | USENIX NSDI 2026; arXiv:2305.05920 | latency-aware scheduling baseline | method context only |
| JITServe | `JITServe: SLO-aware LLM Serving with Imprecise Request Information` | verified | USENIX NSDI 2026 | SLO-aware inference context | no portability benchmark object |
| PARS | `PARS: Low-Latency LLM Serving via Pairwise Learning-to-Rank` | verified | arXiv:2510.03243 | pairwise learning-to-rank context | no portability benchmark object |
| Libra | `Libra: Flexible Request Partitioning and Scheduling for Serving Unbalanced and Dynamic LLM Workloads` | verified | USENIX NSDI 2026 | scheduling context | no ranking-portability benchmark object |
| LMetric / Simple is Better | `Simple is Better: Multiplication May Be All You Need for LLM Request Scheduling` | verified | OSDI 2026; arXiv:2603.15202 | metric / policy context | not used as a direct benchmark result |
| SLAI / RAD | `Optimal Scheduling Algorithms for LLM Inference: Theory and Practice` | verified | ACM Meas. Anal. Comput. Syst.; arXiv:2508.01002 | theory + scheduler design context | not a benchmark of ranking portability |
| SCORPIO | `SCORPIO: Serving the Right Requests at the Right Time for Heterogeneous SLOs in LLM Inference` | verified | arXiv:2505.23022 | hetero-SLO scheduler context | not a rank-portability benchmark |
| Efficient LLM Scheduling by Learning to Rank | `Efficient LLM Scheduling by Learning to Rank` | verified | NeurIPS 2024; arXiv:2408.15792 | learning-to-rank scheduler context | relevant to ranking logic but not to cross-source portability |
| Vidur | `VIDUR: A Large-Scale Simulation Framework for LLM Inference` | verified | MLSys 2024 | closest benchmark infrastructure precedent | still not a rank-portability benchmark |

## Panel interpretation rule

The LSSP benchmark is not built around a claim that any scheduler is universal. It uses a fixed, mechanism-diverse panel only to test whether comparative rankings remain portable across workload sources, operating regimes, and metrics.
