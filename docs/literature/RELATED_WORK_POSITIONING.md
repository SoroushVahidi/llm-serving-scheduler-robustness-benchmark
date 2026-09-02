# RELATED_WORK_POSITIONING.md

This memo states the safe relationship between LSSP and prior work.

## Central statement

LSSP asks a different question than the majority of prior LLM-serving systems and benchmark papers. Prior work generally studies a scheduler, a serving system, a simulation environment, or a workload generator. LSSP studies the portability of comparative scheduler rankings across independently sourced workload families, operating regimes, and metrics.

## Accepted prior-work framing

- Prior work has shown that LLM-serving workloads are heterogeneous and can shift materially by provider, time period, and load region.
- Prior work has also shown that serving systems and schedulers are sensitive to batching, prefill-decode structures, load, and service-level objectives.
- Those facts are contextual background, not evidence of LSSP’s benchmark object.

## Safe manuscript phrasing

- "Prior work has established substantial heterogeneity in LLM-serving workloads and scheduling behavior."
- "This study is motivated by the question of whether comparative scheduler rankings remain portable across independent workload sources and operating regimes."
- "A closest infrastructure precedent is Vidur; relevant simulator families include LLMServingSim and general-purpose serving systems such as vLLM, Orca, and DistServe."

## Prohibited phrasing

- "No previous work studies this problem."
- "Prior work does not consider workload source variation."
- "This is the first benchmark to show load-dependent scheduler differentiation."
- Any wording that turns a contextual literature result into a novel claim about LSSP’s benchmark object without direct evidence from the project’s own protocol and analysis plan.
