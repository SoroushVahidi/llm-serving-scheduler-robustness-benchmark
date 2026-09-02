# NOVELTY_THREAT_LEDGER.md

This ledger records the strongest prior-work claims that could threaten LSSP novelty or require explicit qualification in the manuscript.

## Top novelty threats

| work | threat | overlap | missing relative to LSSP | disposition |
|---|---|---|---|---|
| vLLM / PagedAttention | broad system adoption and serving efficiency work | high | no explicit cross-workload rank-portability benchmark object | background only |
| Orca | iteration-level scheduling | medium | no multiple independent workload sources plus ranking stability analysis | background only |
| Sarathi-Serve | chunked prefill / continuous batching | medium | no rank-portability benchmark design | background only |
| DistServe | disaggregated prefill/decode | medium | no cross-source ranking stability or uncertainty analysis | background only |
| Vidur | closest simulator benchmark precedent | high | no explicit ranking-portability benchmark object across multiple independent workloads | closest infrastructure precedent |
| ServeGen | workload generation and drift realism | medium | not a scheduler-ranking portability benchmark | motivation and context |
| BurstGPT | source-specific workload trace family | medium | not a benchmark of comparative ranking portability by itself | primary workload source |
| TraceLab | coding-agent workload characterization | medium | not a cross-source ranking benchmark | contextual workload source |
| FastServe / JITServe / PARS / Libra / SLAI / SCORPIO / LMetric | recent scheduler-policy papers | medium-high | no explicit benchmark of rank portability across workload sources and metrics | baseline / method context |

## Closest 5–10 threats

1. Vidur / Vidur-Bench: closest simulator and benchmark-infrastructure precedent, but not a cross-source ranking-portability study.
2. LLMServingSim and related simulator families: strong evaluation infrastructure but a different benchmark object.
3. ServeGen: workload generator and realism paper, relevant to workload drift but not to ranking portability itself.
4. BurstGPT: real public workload trace family, relevant as one workload source but not a portability benchmark.
5. Azure trace collections: strong provider-domain sources, relevant as workload families but not a benchmark of ranking stability.
6. TraceLab: coding-agent workload source, relevant as workload diversity context but not a cross-source ranking study.
7. FastServe / JITServe / PARS / Libra / SCORPIO / SLAI / LMetric: relevant recent scheduling mechanisms and policy methods, but not a direct benchmark of comparative ranking portability.
8. vLLM / Orca / DistServe / Sarathi-Serve: foundational design papers, highly relevant to serving infrastructure but not to the benchmark object.

## NOVELTY_VERDICT

The safest supported novelty claim is:

`Prior work has established substantial heterogeneity in LLM-serving workloads and has shown that individual serving mechanisms, schedulers, and load conditions are sensitive to workload source, operating regime, and evaluation metric. To our knowledge, the LSSP benchmark is distinct in treating the portability of comparative scheduler rankings itself as the primary object of study across independent workload sources, operating regimes, and metrics, while explicitly quantifying ranking uncertainty and benchmark sample complexity.`

This wording remains narrower than an unconditional `first` claim and is consistent with the verified literature audit.

## Explicitly prohibited wording

The following claims are not supported by the current primary-source audit and must be avoided unless a later, stronger literature update justifies them:
- `we are the first` ;
- `no prior work studies cross-source ranking portability` ;
- `the benchmark proves scheduler superiority across all workloads` ;
- `the benchmark is the only workload-sensitive scheduling benchmark` ;
- any wording that treats a serving-system paper as if it were a direct LSSP result.
