# Do LLM-Serving Scheduler Rankings Generalize? A Cross-Workload Robustness Benchmark

_(Alternative title: "Benchmarking the Benchmark: Cross-Workload Robustness of
LLM-Serving Scheduler Evaluations")_

Section skeleton only. No unverified results populated. No text copied from
`llm-serving-heuristic-evolution` or `llm-serving-module-intervention-benchmark`.

1. **Introduction** — motivate via RQ1–RQ6 (`docs/RESEARCH_QUESTIONS.md`);
   state claim boundaries up front (`docs/CLAIM_BOUNDARIES.md`).
2. **Related Work** — `docs/RELATED_WORK_NOVELTY_AUDIT.md`.
3. **Benchmark Design** — simulator + policy interface
   (`src/robustbench/{core,simulator,policies}`), load calibration
   (`docs/LOAD_CALIBRATION_PROTOCOL.md`).
4. **Workload Sources and Distribution Shifts** — `configs/workloads/source_registry.yaml`,
   `docs/DATA_FIELD_PROVENANCE.md`, `docs/SPLIT_PROTOCOL.md`.
5. **Scheduler Panel** — `docs/POLICY_COMPARABILITY_AUDIT.md`,
   `configs/policies/canonical_policy_registry.yaml`.
6. **Cross-Workload Ranking Stability** — RQ1/RQ2, `docs/STATISTICAL_ANALYSIS_PLAN.md` §A/§B/§D.
7. **Synthetic-to-Real Transfer** — RQ3, §C.
8. **Explaining Rank Reversals** — RQ4, §G (explanatory only, see `docs/CLAIM_BOUNDARIES.md`).
9. **Real-System Validation** — RQ6, `docs/REAL_SYSTEM_VALIDATION_PLAN.md`.
10. **Limitations** — cite Gate B/D pending items (`docs/GO_NO_GO_GATES.md`), the
    `apt_serve_faithful` scaffolding-only exclusion, the TraceLab
    documentation/artifact discrepancy.
11. **Reproducibility / Data Availability** — `docs/REPRODUCIBILITY_CONTRACT.md`,
    `docs/DATASET_V2_SCHEMA.md`.
