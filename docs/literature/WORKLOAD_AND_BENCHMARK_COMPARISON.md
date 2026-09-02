# WORKLOAD_AND_BENCHMARK_COMPARISON.md

This document distinguishes known workload traces, benchmark suites, and project-local comparisons without conflating them.

## Workload families

- BurstGPT: bursty request traces from LLM serving workloads.
- Azure LLM traces: production-style provider-domain traces.
- TraceLab: coding-agent workload characterization for LLM serving.
- ServeGen: workload generator and realism framework.

## Benchmark and simulator families

- Vidur: simulation and benchmarking framework for LLM inference.
- LLMServingSim: simulator and serving benchmark infrastructure.
- vLLM, Orca, DistServe, Sarathi-Serve, Llumnix, FastServe, JITServe, PARS, Libra, LMetric, SLAI/RAD, SCORPIO: serving systems and scheduling policies.

## Important distinction

The LSSP project is not claiming that these cited systems are directly comparable as a general scheduler leaderboard. The actual object of study is narrower: whether scheduler rankings remain portable across workload sources, operating regimes, and metrics under a controlled benchmark protocol.

## Safety wording

Any manuscript text should avoid statements such as `Pilot-V2 comparative results exist` or `the scheduler ranking is conclusively superior across all sources.` Instead, prefer wording such as `ranking portability under a controlled benchmarking protocol` and `study-specific scheduler behavior under observed workload sources.`
