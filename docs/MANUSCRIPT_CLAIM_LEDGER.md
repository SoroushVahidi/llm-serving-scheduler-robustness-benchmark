# MANUSCRIPT_CLAIM_LEDGER.md

Section-indexed companion to `docs/MANUSCRIPT_EVIDENCE_MAP.md` (which is
claim-indexed and experiment-linked). This ledger groups claims by the
manuscript section they belong to, for a reviewer or future agent scanning
section-by-section.

| Claim | Section | Repository evidence | Literature support | Status | Allowed wording | Forbidden wording |
|---|---|---|---|---|---|---|
| Workload heterogeneity (general, literature-level) | 2.2, 2.4 | `docs/literature/NOVELTY_THREAT_LEDGER.md` | `burstgpt2025`, `servegen2026`, `kvcache_wild2025` | ESTABLISHED (literature) | "Prior work has established substantial heterogeneity in LLM-serving workloads." | claiming this as an LSSP finding |
| Workload separability (project-level, 3 sources) | 4.5, 4.6 | `docs/WORKLOAD_CHARACTERIZATION_PAPER_RESULT.md` | none | ESTABLISHED_EVIDENCE (`SEPARABILITY_RESULT_CONFIRMED_WITH_CAVEATS`) | see `MANUSCRIPT_EVIDENCE_MAP.md` row | "intrinsic provider differences were proven" |
| Stage-0 discriminability (historical pilot) | 5.x (methodology motivation only) | `docs/STAGE0_BURSTGPT_DIAGNOSTIC.md`, `docs/GO_NO_GO_GATES.md` | none | ESTABLISHED_EVIDENCE, HISTORICAL PILOT | see `MANUSCRIPT_EVIDENCE_MAP.md` row | using Stage-0 as a ranking-portability finding |
| Calibration (Phase 11 FIFO-only) | 5.4 | `docs/RANKING_PORTABILITY_PHASE11_CALIBRATION_FREEZE.md`, `docs/RANKING_PORTABILITY_CALIBRATION_CHARACTERISTICS.md` | none | ESTABLISHED_EVIDENCE | "FIFO-only calibration establishes six operating regions from 720 deterministic cells." | presenting calibration as a comparative scheduler result |
| Ranking portability (RQ1/RQ2) | 6.2, 6.4 | none | none | RESULT_CONTRACT_ONLY | `[PENDING PILOT-V2 RESULT]` | any stability/instability direction |
| Reversals | 6.3 | none | none | RESULT_CONTRACT_ONLY | `[PENDING PILOT-V2 RESULT]` | mixing practical and microscopic reversal counts |
| Temporal/OOD | 6.4 | none | none | RESULT_CONTRACT_ONLY | `[PENDING PILOT-V2 RESULT]` | merging the three temporal/domain comparisons into one number |
| Sample complexity | 7 | none | none | RESULT_CONTRACT_ONLY | `[PENDING RESULT]` | naming a specific recovery n in advance |
| Real-system agreement | 8 | none | none | RESULT_CONTRACT_ONLY | `[PENDING RESULT]` | claiming absolute-value simulator/hardware equivalence |
| Novelty (ranking portability as benchmark object) | 2.6, 1 | `docs/literature/NOVELTY_THREAT_LEDGER.md` | full related-work set | ESTABLISHED (literature, conservative) | the exact `NOVELTY_VERDICT` wording | "first", "only", "proves" |
| Artifact / public release | 11 | `docs/REPRODUCIBILITY_CONTRACT.md` | none | PLANNED, NOT RELEASED | "planned public release at `SoroushVahidi/llm-serving-scheduler-portability`" | describing the artifact as already released |

See `docs/MANUSCRIPT_EVIDENCE_MAP.md` for the finer-grained, experiment-linked
version of this table (per-claim repository evidence + citation + exact safe
wording).
