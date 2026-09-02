# METADATA_CORRECTIONS.md

This document records the metadata corrections and provenance fixes that must be respected in the canonical manuscript narrative.

| work | earlier wrong metadata / ambiguity | verified metadata | official primary source | final citation decision |
|---|---|---|---|---|
| BurstGPT | often treated as a single generic trace without exact release provenance | `BurstGPT: A Real-world Workload Dataset to Optimize LLM Serving Systems` (arXiv:2401.17644; official GitHub dataset) | arXiv + official dataset release | retain as a real workload trace family with exact version provenance |
| FastServe | often cited generically without the exact conference paper title | `FastServe: Iteration-Level Preemptive Scheduling for Large Language Model Inference` | USENIX NSDI 2026; arXiv:2305.05920 | cite as a scheduler background paper only |
| JITServe | often described without exact SLO-aware formulation and authors | `JITServe: SLO-aware LLM Serving with Imprecise Request Information` | USENIX NSDI 2026 | cite as SLO-aware scheduler context only |
| Libra | sometimes appears as a vague benchmark or unverified item | `Libra: Flexible Request Partitioning and Scheduling for Serving Unbalanced and Dynamic LLM Workloads` | USENIX NSDI 2026 | include only as a verified scheduler context paper |
| LMetric | often mislabeled as a generic metric rather than the specific request-scheduling paper | `Simple is Better: Multiplication May Be All You Need for LLM Request Scheduling` | OSDI 2026; arXiv:2603.15202 | cite by the exact title; not as a generic metric standard unless the exact metric semantics are explicitly defined |
| TraceLab | often summarized without exact coding-agent workload semantics | `TraceLab: Characterizing Coding Agent Workloads for LLM Serving` | arXiv:2606.30560 + official repo | cite only with explicit workload-family provenance |
| P-PAS | often described as a loose idea rather than a specific paper | exact title is partially resolved (`P-PAS: Prefill-Pressure Adaptive Scheduling...`) but full official metadata are not yet stable enough for confident citation | arXiv:2608.15171 (partial record) | do not include in final manuscript unless the exact official source is confirmed |
| SLAI / RAD | acronym-level shorthand without canonical paper title | `Optimal Scheduling Algorithms for LLM Inference: Theory and Practice` | ACM Meas. Anal. Comput. Syst.; arXiv:2508.01002 | cite as the paper family for SLAI/RAD when needed |
| ServeGen | often mistaken for a dataset source rather than a generator | `ServeGen: Workload Characterization and Generation of Large Language Model Serving in Production` | USENIX NSDI 2026; arXiv:2505.09999 | cite as workload-generation context, not as a benchmark trace source |
| S^3 | ambiguous acronym label; often used as shorthand with no verified canonical reference | not a stable stand-alone canonical label in this pass; the verified scheduler literature is `Efficient LLM Scheduling by Learning to Rank` | arXiv:2408.15792 | use the exact paper title instead of the shorthand |
| SCORPIO | sometimes described without exact paper title or venue status | `SCORPIO: Serving the Right Requests at the Right Time for Heterogeneous SLOs in LLM Inference` | arXiv:2505.23022 | cite as a verified scheduler paper only when a direct manuscript need is present |
| PARS | can be referenced as a generic scheduler family without the exact pairwise learning-to-rank title | `PARS: Low-Latency LLM Serving via Pairwise Learning-to-Rank` | arXiv:2510.03243 | cite under the exact title |
| Vidur | often summarized without the exact benchmark object and authors | `VIDUR: A Large-Scale Simulation Framework for LLM Inference` | MLSys 2024; Microsoft project page | retain as the closest simulator benchmark precedent |

## Rule

When metadata are ambiguous, the manuscript must err on the side of conservatism: cite the category, state the provenance limitation, and avoid adding a stronger claim than the primary source supports.
