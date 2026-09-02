# BENCHMARK_SIMULATOR_LEDGER.md

This ledger records the primary sources relevant to benchmark and simulator infrastructure and validation claims for LSSP.

| artifact | title | status | primary source | LSSP role | safe claim |
|---|---|---|---|---|---|
| Vidur | `VIDUR: A Large-Scale Simulation Framework for LLM Inference` | verified | MLSys 2024; Microsoft Research | closest benchmark infrastructure precedent | `Vidur is a relevant simulator and benchmark precedent but not a direct benchmark of cross-source ranking portability.` |
| LLMServingSim | `LLMServingSim: A HW/SW Co-Simulation Infrastructure for LLM Inference Serving at Scale` | verified | IEEE ICCD 2024; arXiv:2408.05499 | simulator infrastructure precedent | `LLMServingSim is relevant for simulation-based serving evaluation, but not equivalent to LSSP’s benchmark object.` |
| LLMServingSim 2.0 | `LLMServingSim2.0: A Unified Simulator for Heterogeneous Hardware and Serving Techniques in LLM Infrastructure` | verified | IEEE Computer Architecture Letters 24(2), 2025; arXiv:2511.07229 | successor simulator infrastructure precedent (heterogeneous/disaggregated serving) | `LLMServingSim 2.0 extends the original with heterogeneous-hardware and disaggregated-serving support; still not equivalent to LSSP’s benchmark object.` |
| KVCache in the Wild | `KVCache Cache in the Wild: Characterizing and Optimizing KVCache Cache at a Large Cloud Provider` | verified | USENIX ATC 2025; arXiv:2506.02634 | production KV-cache reuse characterization | `Relevant characterization of KV-cache reuse at a large cloud provider; not a benchmark of scheduler ranking portability.` |
| ServeGen | `ServeGen: Workload Characterization and Generation of Large Language Model Serving in Production` | verified | USENIX NSDI 2026; arXiv:2505.09999 | workload-generation and realism context | `ServeGen motivates workload realism and drift but is not itself a benchmark of scheduler ranking portability.` |
| vLLM / PagedAttention | `vLLM: Easy, Fast, and Cheap LLM Serving with PagedAttention` | verified | OSDI 2023 | serving-system reference | `The benchmark is not claiming simulator equivalence to production serving. It is designed around a fixed protocol and frozen workload sources.` |
| custom LSSP simulator logic | project-local benchmark logic | internal project artifact | local repository source | benchmark implementation | internal project code is a benchmark implementation, not a literature claim |

## Validation-claim boundary

The benchmark does not claim that simulator output equals real-system absolute latency or throughput. The proper manuscript claim is about ranking portability and reversal behavior under a fixed benchmark protocol, not exact hardware reproduction.
