# README.md

This directory is the canonical LSSP literature source.

This directory is the durable primary-source literature record for the LLM-Serving Scheduler Portability Benchmark (LSSP).

## Scope

This directory consolidates the literature and metadata required for:
- primary-source verification of workloads, schedulers, simulator/benchmark infrastructure, and statistical methods;
- novelty positioning for the benchmark and its operator definitions;
- citation mapping for the manuscript and project documents;
- a permanent record of metadata corrections, rejected references, and unresolved provenance.

## Authoritative state

- scientific source branch: `research/lssp-integrated-phase11-20260901` @ `30995d6dc5c9d3bb5db3aecdb975ddb70a92e86a`
- literature branch: `research/lssp-literature-canonical-20260901`
- search cutoff: 2026-09-01
- PRIMARY_SOURCE_LITERATURE_CONSOLIDATED: YES
- FUTURE_AGENTS_SHOULD_NOT_REPEAT_BROAD_SEARCH_WITHOUT_TRIGGER = YES

## Future-agent policy

Do NOT repeat the broad related-work search merely because a new chat starts.

Broad search should be repeated only if:
1. substantial time has passed since the search cutoff;
2. a new novelty threat appears;
3. reviewers request new references;
4. paper scope materially changes; or
5. an unresolved citation requires resolution.

Otherwise future agents must read:
- `PRIMARY_SOURCE_CITATION_LEDGER.md`
- `NOVELTY_THREAT_LEDGER.md`
- `MANUSCRIPT_CITATION_MAP.md`
- `verified_related_work.bib`

## Canonical files

- `PRIMARY_SOURCE_CITATION_LEDGER.md`
- `NOVELTY_THREAT_LEDGER.md`
- `WORKLOAD_DATASET_LEDGER.md`
- `SCHEDULER_BASELINE_LEDGER.md`
- `BENCHMARK_SIMULATOR_LEDGER.md`
- `STATISTICAL_METHODS_LEDGER.md`
- `RELATED_WORK_POSITIONING.md`
- `METADATA_CORRECTIONS.md`
- `REJECTED_OR_NONCITABLE_REFERENCES.md`
- `SEARCH_COVERAGE_LOG.md`
- `CLAIM_TO_CITATION_MATRIX.md`
- `WORKLOAD_AND_BENCHMARK_COMPARISON.md`
- `verified_related_work.bib`

## Safety boundaries

- Pilot-V2 comparative outcomes remain `NONE`.
- Literature consolidation is not a result-generation step.
- No future agent should interpret the literature docs as evidence of comparative scheduler superiority.
- Novelty remains bounded to ranking portability as a benchmark object, not to a single new scheduler or simulator result.
