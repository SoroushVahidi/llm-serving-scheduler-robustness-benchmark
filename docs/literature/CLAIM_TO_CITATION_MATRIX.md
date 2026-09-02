# CLAIM_TO_CITATION_MATRIX.md

This file is the canonical manuscript safety check: each claim type is mapped to the allowed citation strategy.

| claim type | required support | citation keys | prohibited pattern |
|---|---|---|---|
| workload heterogeneity | prior work + project context | `burstgpt2024`, `azure2024trace`, `tracelab2026`, `servegen2026` | treat as a result of the LSSP benchmark without project provenance |
| scheduler sensitivity to load / QoS | prior work + benchmark context | `kwon2023vllm`, `yu2022orca`, `agrawal2024sarathi`, `zhong2024distserve`, `sun2024llumnix`, `fastserve2024`, `jitserve2025`, `pars2025`, `libra2026`, `slai2025`, `scorpio2025` | present a prior scheduler paper as a direct LSSP result |
| cross-source ranking portability | project benchmark only | project protocol docs + benchmark design docs | treat as a prior literature result |
| novel benchmark object | project definition only | project docs + novelty ledger | claim `first` without explicit primary-source validation |
| simulator validation | benchmark design boundary | `vidur2024`, `llmservingsim2024` | claim absolute fidelity to real hardware |
| workload generator realism | generator + trace context | `servegen2026` | misclassify a generator as a benchmark trace source |
| ranking uncertainty / sample complexity | project-defined analysis plan | project docs + statistical methods ledger | claim established statistical results without the LSSP protocol |
