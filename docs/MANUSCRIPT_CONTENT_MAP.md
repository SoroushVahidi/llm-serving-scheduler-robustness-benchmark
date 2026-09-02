# MANUSCRIPT_CONTENT_MAP.md

Canonical content/evidence map for the LSSP manuscript, produced during Query 3
(pre-Phase-12 authoritative consolidation). One row per subsection of the
structure fixed in `docs/CANONICAL_HANDOFF.md` / this document's own section
list. Statuses:

- `COMPLETE_V1` — full prose exists in `paper/sections/`, ready for review.
- `DRAFTABLE_NOW` — full prose written from established repository evidence; no
  pending result needed.
- `PARTIALLY_DRAFTABLE` — some prose exists now (methodology, design, framing);
  the remainder is an explicit `[PENDING RESULT: ...]` contract.
- `RESULT_CONTRACT_ONLY` — no prose beyond structure + an explicit pending-result
  contract; nothing is invented.

| Section | Purpose | Established evidence | Citations | Result needed | Figure/table | Status | Dependency |
|---|---|---|---|---|---|---|---|
| 1. Introduction | Motivate ranking portability as the benchmark object; define R(W,M,L); state RQs and outcome-neutral contributions | `docs/RESEARCH_QUESTIONS.md`, `docs/CLAIM_BOUNDARIES.md`, `docs/PROJECT_STATUS.md` | `kwon2023vllm`, `yu2022orca`, `agrawal2024sarathi`, `zhong2024distserve`, `patel2024splitwise`, `burstgpt2025`, `azure2024trace`, `servegen2026` | none | Fig 1 (study design) referenced, not required | `COMPLETE_V1` | none |
| 2.1 Serving Architectures and Scheduling Mechanisms | Survey serving-system and scheduler-mechanism literature | `docs/literature/SCHEDULER_BASELINE_LEDGER.md` | `kwon2023vllm`, `yu2022orca`, `agrawal2024sarathi`, `zhong2024distserve`, `sun2024llumnix`, `patel2024splitwise`, `qin2025mooncake`, `sheng2024vtc`, `jin2023s3`, `efficientllmscheduling2024`, `fastserve2024`, `jitserve2025`, `pars2025`, `libra2026`, `lmetric2026`, `slai2025`, `scorpio2025`, `stojkovic2025dynamollm`, `aptserve2025`, `proserve2025` | none | Table: scheduler/fidelity | `COMPLETE_V1` | literature integrity gate |
| 2.2 Production Workloads and Characterization | Survey trace/workload characterization literature | `docs/literature/WORKLOAD_DATASET_LEDGER.md`, `docs/literature/METADATA_CORRECTIONS.md` | `burstgpt2025`, `patel2024splitwise`, `stojkovic2025dynamollm`, `azure2024trace`, `tracelab2026`, `servegen2026`, `kvcache_wild2025`, `ayearinllmserving2026` | none | none | `COMPLETE_V1` | literature integrity gate |
| 2.3 Simulators and Benchmark Frameworks | Position Vidur/LLMServingSim family as closest precedent | `docs/literature/BENCHMARK_SIMULATOR_LEDGER.md` | `vidur2024`, `llmservingsim2024`, `llmservingsim2_2025` | none | Table: prior benchmark comparison | `COMPLETE_V1` | none |
| 2.4 Workload Dependence and Benchmark Sensitivity | Acknowledge prior evidence of workload/load/SLO sensitivity as accepted background, not LSSP novelty | `docs/literature/NOVELTY_THREAT_LEDGER.md`, `docs/literature/RELATED_WORK_POSITIONING.md` | subset of 2.1/2.2 keys | none | none | `COMPLETE_V1` | none |
| 2.5 Ranking Portability and Benchmark Methodology | Position relative to comparative-ranking/statistics literature | `docs/literature/STATISTICAL_METHODS_LEDGER.md` | standard-methods citations only (Kendall, Spearman, bootstrap — no dedicated BibTeX keys; cited generically per `STATISTICAL_METHODS_LEDGER.md`) | none | none | `COMPLETE_V1` | none |
| 2.6 Position of LSSP | State the conservative novelty verdict | `docs/literature/NOVELTY_THREAT_LEDGER.md`'s `NOVELTY_VERDICT` | n/a (project framing) | none | none | `COMPLETE_V1` | none |
| 3.1 Research Questions | Reproduce frozen RQ1–RQ6 + secondary load analysis | `docs/RESEARCH_QUESTIONS.md` (verbatim) | none | none | none | `COMPLETE_V1` | none |
| 3.2 Study Overview | High-level design narrative | `docs/PROJECT_ROADMAP.md`, `docs/EXPERIMENT_CAMPAIGN_PLAN.md` | none | none | Fig 1 | `COMPLETE_V1` | none |
| 3.3 Evidence Independence / Publication Boundaries | State non-overlap with LLM 2026 / SIGMETRICS work | `docs/EVIDENCE_INDEPENDENCE_PLAN.md`, `docs/OVERLAP_LEDGER.md`, `docs/GO_NO_GO_GATES.md` Gate A | none | none | none | `COMPLETE_V1` | none |
| 3.4 Experimental Unit and Paired Design | Define window/source/load-region/metric as factors; workload window as statistical unit | `docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md`, `docs/STATISTICAL_ANALYSIS_PLAN.md` | `STATISTICAL_METHODS_LEDGER.md` keys | none | none | `COMPLETE_V1` | none |
| 3.5 Preregistration | State what was frozen before any Pilot-V2 outcome | `docs/RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md`, `docs/RANKING_PORTABILITY_WINDOW_FREEZE.md` | none | none | none | `COMPLETE_V1` | none |
| 4.1 Sources | Name the 3 primary Pilot-V2 sources + Stage-0/robustness context | `docs/RANKING_PORTABILITY_WINDOW_FREEZE.md`, `docs/literature/WORKLOAD_DATASET_LEDGER.md` | `burstgpt2025`, `azure2024trace`, `patel2024splitwise` | none | Table: workload-source table | `COMPLETE_V1` | none |
| 4.2 Representation and Provenance | Field-level provenance, license status | `docs/DATA_FIELD_PROVENANCE.md`, `docs/DATA_LICENSE_AUDIT.md` | none | none | none | `COMPLETE_V1` | none |
| 4.3 Window Construction | 120-window freeze, 40/source, 10 Stage-0 reused + 30 new, chronology strata | `docs/RANKING_PORTABILITY_WINDOW_FREEZE.md` | none | none | none | `COMPLETE_V1` | none |
| 4.4 Descriptors | 28-feature descriptor set, prompt-token semantic caveat | `docs/WORKLOAD_CHARACTERIZATION_PAPER_RESULT.md` | none | none | Fig 3 | `COMPLETE_V1` | none |
| 4.5 Cross-Source Differences | Report the grouped-CV separability table (RF 1.000/LogReg 0.988/Tree 0.980) | `docs/WORKLOAD_CHARACTERIZATION_PAPER_RESULT.md` | none | none | Fig 2/3 | `COMPLETE_V1` | none |
| 4.6 Source Separability | State `SEPARABILITY_RESULT_CONFIRMED_WITH_CAVEATS` with the leakage-resistant grouped-CV caveat | `docs/SOURCE_SEPARABILITY_AUDIT_20260901.md`, `docs/WORKLOAD_CHARACTERIZATION_PAPER_RESULT.md` | none | none | none | `COMPLETE_V1` | none |
| 4.7 Drivers of Differences | Tier-1/Tier-2 attribution (prompt-length dominance) | `docs/WORKLOAD_CHARACTERIZATION_PAPER_RESULT.md` | none | none | Fig 3 (attribution) | `COMPLETE_V1` | none |
| 4.8 Window-Size Sensitivity | State what is/isn't established about window-size robustness | `docs/WORKLOAD_DISTRIBUTION_CHARACTERIZATION_PROTOCOL.md` | none | partially — no dedicated window-size sweep result exists yet | none | `PARTIALLY_DRAFTABLE` | none blocking; sweep not yet run |
| 5.1 Scheduler Panel | 13 executed policies, 11 PRIMARY + 2 STYLE_APPROXIMATION | `docs/RANKING_PORTABILITY_POLICY_PANEL.md` | scheduler-baseline keys | none | Table: scheduler/fidelity | `COMPLETE_V1` | none |
| 5.2 Fidelity Taxonomy | `FAITHFUL_EXTERNAL` / `REPOSITORY_NATIVE_CLASSICAL` / `SIMULATOR_PROXY` / `STYLE_APPROXIMATION` / `scaffolding_only` | `docs/POLICY_COMPARABILITY_AUDIT.md`, `docs/RANKING_PORTABILITY_POLICY_PANEL.md` | none | none | Table | `COMPLETE_V1` | none |
| 5.3 Execution Model | Simulator execution semantics | `docs/RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md` | none | none | none | `COMPLETE_V1` | none |
| 5.4 Operating-Region Calibration | Phase-11 FIFO-only 6-region calibration, 720 cells, factors LOW..HIGH_PRESSURE | `docs/RANKING_PORTABILITY_PHASE11_CALIBRATION_FREEZE.md`, `docs/RANKING_PORTABILITY_CALIBRATION_CHARACTERISTICS.md` | none | none | none | `COMPLETE_V1` | none |
| 5.5 Metrics | Always-defined vs. completion-conditioned metric contract | `docs/RANKING_PORTABILITY_METRIC_DEFINITIONS.md` | none | none | Table: metric definitions | `COMPLETE_V1` | none |
| 5.6 Paired Design / Repetitions | Statistical unit, determinism, repetition rule | `docs/STATISTICAL_ANALYSIS_PLAN.md`, `docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md` | none | none | none | `COMPLETE_V1` | none |
| 5.7 Mechanism Telemetry | 7-field telemetry schema, mechanism-absent-vs-instrumentation-failure distinction | `docs/RANKING_PORTABILITY_TELEMETRY_IMPLEMENTATION.md` | none | none | none | `COMPLETE_V1` | none |
| 5.8 Robustness Analyses | High-fidelity subset, LOSO, window-size, metric-definition, load-grid, temporal-split, mechanism-family-exclusion | `docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md` §Robustness | none | results pending | Table: robustness | `PARTIALLY_DRAFTABLE` | Pilot-V2 |
| 6.1 Discriminability | Fraction of non-tied conditions per source | Stage-0 only (historical): `docs/STAGE0_BURSTGPT_DIAGNOSTIC.md` | none | Pilot-V2 full matrix | Fig 4 | `RESULT_CONTRACT_ONLY` | Pilot-V2 |
| 6.2 Cross-Source Rankings | Kendall tau-b / Spearman rho / top-k overlap across sources | none (design only) | none | Pilot-V2 | Fig 5, Table: headline ranking result | `RESULT_CONTRACT_ONLY` | Pilot-V2 |
| 6.3 Pairwise Reversals | Reversal frequency with practical-margin + CI-excludes-zero rule | none (design only) | none | Pilot-V2 | Fig 6, Table: reversal | `RESULT_CONTRACT_ONLY` | Pilot-V2 |
| 6.4 Temporal/OOD | EARLY/MIDDLE/LATE and calendar-split tau | none (design only) | none | Pilot-V2 | none | `RESULT_CONTRACT_ONLY` | Pilot-V2 |
| 6.5 Load Conditioning | Tau/reversal across 6 operating regions (secondary, not headline) | Phase-11 calibration design only | none | Pilot-V2 | Fig 7 | `RESULT_CONTRACT_ONLY` | Pilot-V2 |
| 6.6 Metric Conditioning | Tau between metric pairs | none (design only) | none | Pilot-V2 | Fig 8 | `RESULT_CONTRACT_ONLY` | Pilot-V2 |
| 6.7 Robustness | High-fidelity/LOSO/window-size/etc. sensitivity of 6.1–6.6 | none (design only) | none | Pilot-V2 | Table: robustness | `RESULT_CONTRACT_ONLY` | Pilot-V2 |
| 7. Benchmark Sample Complexity | n∈{5,10,20,30,40}, ≥500 draws/n, 0.9 recovery threshold | `docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md` §C (design only) | none | Pilot-V2 + sample-complexity analysis | Fig 9 | `RESULT_CONTRACT_ONLY` | Pilot-V2 |
| 8. Real-System Validation | Sign/tau/reversal agreement, simulator vs. real vLLM | `docs/REAL_SYSTEM_VALIDATION_PLAN.md` (design only) | none | selected-case real-vLLM runs | Fig 10 | `RESULT_CONTRACT_ONLY` | Pilot-V2 §6.2/6.3 |
| 9. Discussion | Two-sided (high-portability / low-portability) discussion structure | `docs/CLAIM_BOUNDARIES.md` | none | none (structure only) | none | `COMPLETE_V1` (structure); content firms up post-results | none |
| 10. Threats to Validity | Simulator abstraction, STYLE_APPROX, 3-source scope, completion-conditioned undefined metrics, Phase-11 zero-completion prevalence, etc. | `docs/SCIENTIFIC_CAVEATS_AND_OPEN_ISSUES.md`, `docs/POLICY_COMPARABILITY_AUDIT.md` | none | none | none | `COMPLETE_V1` | none |
| 11. Reproducibility / LSSP Artifact | Planned HF release, frozen hashes, reproduction scripts | `docs/REPRODUCIBILITY_CONTRACT.md`, `docs/ARTIFACT_HASH_LEDGER.md` | none | none | none | `COMPLETE_V1` | none |
| 12. Conclusion | Outcome-neutral summary + forward pointer to Phase 12 | project framing | none | none | none | `COMPLETE_V1` (structure); content firms up post-results | none |

## Notes

- No subsection in Sections 6–8 states a direction of finding. Every such
  subsection carries an explicit `[PENDING RESULT: ...]` contract reproduced
  verbatim (or lightly re-pointed) from `docs/MANUSCRIPT_RESULT_CONTRACT.md`,
  which remains the single source of truth for exact contract wording.
- Section 9 (Discussion) and Section 12 (Conclusion) have a complete
  *structure* now (both branches of the high/low-portability outcome are
  written out), but their final numeric content cannot be `COMPLETE_V1` in
  the full sense until Pilot-V2 exists — marked accordingly in
  `paper/sections/discussion.tex` and `conclusion.tex` with inline comments,
  not separate contract blocks.
