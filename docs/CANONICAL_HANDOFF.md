# CANONICAL_HANDOFF.md

Canonical handoff for the LLM-Serving Scheduler Portability Benchmark (LSSP):
integrated Phase-11 scientific state + corrected canonical literature +
manuscript foundation. Written so a completely new chat session (a fresh
ChatGPT/Claude/Copilot instance with no memory of this conversation) can
start here and continue without reconstructing project history.

## 1. Repository / path

- Repository root (this branch's worktree):
  `/home/soroush/repos/llm-serving-scheduler-lssp-authoritative`
- Underlying git repository (all LSSP branches live in the same repo, as
  separate worktrees per branch): the tracked remote is
  `llm-serving-scheduler-robustness-benchmark` on GitHub, user `SoroushVahidi`.

## 2. Authoritative branch / SHA

- **Read this branch:** `research/lssp-authoritative-pre-phase12-20260901`
  (commit SHA recorded at the end of this document's history / in
  `git log -1`, pushed to `origin`).
- It descends from, in order: `research/lssp-integrated-phase11-20260901` @
  `30995d6dc5c9d3bb5db3aecdb975ddb70a92e86a` (scientific state through Phase
  11), then `research/lssp-literature-canonical-20260901` @
  `7e5230f4aa1ea408a7d9580594135ca471dc3e42` (Query-2 canonical literature),
  then this branch's own commit(s) (Query-3 literature corrections +
  manuscript foundation).
- `main` is untouched by all of the above.

## 3. Paper title

Working title (see `paper/main.tex`): *"LLM-Serving Scheduler Portability
Benchmark (LSSP): Does Comparative Scheduler Ranking Generalize Across
Workload Sources, Operating Regions, and Metrics?"* Not locked to a venue;
`paper/OUTLINE.md` records an earlier alternative title from before the
LSSP framing was adopted, kept for history only.

## 4. Benchmark name

- Full: LLM-Serving Scheduler Portability Benchmark
- Short: LSSP Benchmark
- Planned Hugging Face slug: `SoroushVahidi/llm-serving-scheduler-portability`
  (**planned, not yet released** — see `docs/REPRODUCIBILITY_CONTRACT.md`
  and `paper/sections/artifact.tex`)

## 5. Central scientific question

Is the comparative ranking $R(W, M, L)$ induced by a fixed scheduler panel
portable across independent workload sources ($W$), evaluation metrics
($M$), and operating/load regions ($L$)? See RQ1–RQ6 in
`docs/RESEARCH_QUESTIONS.md` and `paper/sections/introduction.tex` /
`study_design.tex`.

## 6. Publication boundaries

This manuscript must remain distinct from:
- **LLM 2026** (*"The Exploitability Gap in LLM-Serving Scheduler
  Portfolios"*): its 60-canonical-window replay, 8-policy Pext portfolio,
  and SBS/VBS/ANWG-exploitability results are `PRIOR_RESULT_REFERENCE_ONLY`
  — citable as prior motivation, never restated as this project's evidence.
  `docs/OVERLAP_LEDGER.md`, `docs/CLAIM_BOUNDARIES.md`,
  `docs/EVIDENCE_INDEPENDENCE_PLAN.md`.
- **A separate module-intervention manuscript** (*"Module Counterfactuals
  for Attributing LLM Serving Scheduler Effects"*, SIGMETRICS/POMACS
  track): no module-counterfactual/attribution claim belongs in this
  manuscript.
- **An unrelated LAFC/SIGMOD-track research thread**: unconnected, not
  referenced here.

## 7. Phase status

| Phase | Status |
|---|---|
| 0–9 (bootstrap through telemetry implementation) | DONE |
| 10 (Pilot-V2 120-window freeze) | DONE |
| 11 (six-region FIFO calibration) | DONE |
| 12 (smoke / campaign / analysis / validation) | READY, **NOT STARTED** |
| Literature consolidation (Query 2) | DONE |
| Targeted literature integrity gate (Query 3) | DONE, `LITERATURE_INTEGRITY_GATE = PASS` |
| Manuscript foundation (Query 3) | DONE |

Pilot-V2 smoke, the 18,720-cell campaign, ranking analysis,
sample-complexity analysis, and real-system validation are all
**NOT STARTED**. No comparative Pilot-V2 scheduler outcome exists.

## 8. Immutable scientific hashes

| Artifact | SHA-256 |
|---|---|
| Phase-10 scientific window (content hash) | `0d1aa06ccbee352207327ea369ae75f12e91c0cda006c813a41b381effd29eef` |
| Phase-10 compact index | `d78ec1087fedae02174ca093a9860c70468be336ccb1d7e6de756c81ba331e53` |
| Phase-11 prelaunch freeze contract | `e2564ea9484190832de50f63173c4b73ae054d6ae7008bb4ff6648c8dc917f7b` |
| Phase-11 raw FIFO calibration | `201caaf04476ad8737ef6079fc0d6cb4e864601711d0b96c88750a717d8b2a6a` |
| Phase-11 region-assignment output | `9fcb92f9ea1206ce185194527ada35d0e3b91bf4904be7ae23ba9ea997c17574` |

All five were re-verified unchanged (exact string match across every
cross-referencing document, and no commit touching the underlying files
since the Phase-11 tip) immediately before this branch's final commit. See
`docs/ARTIFACT_HASH_LEDGER.md`.

## 9. Established results

- `SEPARABILITY_RESULT_CONFIRMED_WITH_CAVEATS`: the three primary workload
  sources are measurably different and strongly separable in observed
  descriptor distributions under a leakage-resistant, grouped
  chronological evaluation (RF balanced accuracy 1.000, LogReg 0.988, depth-3
  tree 0.980, n=400 windows). Prompt-length structure is the primary driver.
  `docs/WORKLOAD_CHARACTERIZATION_PAPER_RESULT.md`.
- `STAGE0_NO_GO` (historical pilot, not a Pilot-V2 result): Stage-0's
  1,080-cell pilot found broad differentiation overall but a genuine,
  source-concentrated discriminability shortfall traced to a near-total
  collapse of 5/6 policies on BurstGPT's short-prompt, near-constant-output
  traffic. `docs/STAGE0_BURSTGPT_DIAGNOSTIC.md`, `docs/GO_NO_GO_GATES.md`.
- Phase-11 FIFO-only calibration: 720/720 valid, deterministic cells across
  120 windows × 6 regions; 301/720 records show zero completions
  (calibration characteristic, not a comparative finding).
  `docs/RANKING_PORTABILITY_PHASE11_CALIBRATION_FREEZE.md`,
  `docs/RANKING_PORTABILITY_CALIBRATION_CHARACTERISTICS.md`.
- Literature integrity gate (Query 3): BurstGPT corrected to its final
  KDD 2025 published form (was miscited as arXiv-only); S^3 restored as a
  distinct NeurIPS 2023 paper (was wrongly conflated with "Efficient LLM
  Scheduling by Learning to Rank," NeurIPS 2024); Azure/BurstGPT
  provider-independence language corrected to "distinct workload sources"
  (BurstGPT's own traffic is logged from a regional Azure OpenAI GPT
  service customer — the same underlying cloud infrastructure as this
  project's own Azure traces). See `docs/literature/METADATA_CORRECTIONS.md`
  and `docs/literature/SEARCH_COVERAGE_LOG.md`.

## 10. Results not yet existing

Cross-source ranking portability (RQ1/RQ2), pairwise reversals, temporal/OOD
portability, load/metric conditioning, robustness sensitivity, benchmark
sample complexity (RQ5), and real-system validation (RQ6) — all
`RESULT_CONTRACT_ONLY`, with exact contract wording in
`docs/MANUSCRIPT_RESULT_CONTRACT.md` and `paper/sections/results.tex`,
`sample_complexity.tex`, `real_system.tex`.

## 11. Stage-0 role

Stage-0 is historical, preregistered discriminability-pilot evidence that
motivated Pilot-V2's larger panel and denser load grid. It never measured
cross-source ranking portability and must never be cited as if it had.
`docs/STAGE0_DISCRIMINABILITY_PROTOCOL.md`, `docs/STAGE0_BURSTGPT_DIAGNOSTIC.md`.

## 12. Workload characterization

Field-level provenance, license audit, source-separability result, and
Tier-1/Tier-2 attribution are all established (§9 above). Prompt-token
fields compose differently across sources (single-request for BurstGPT vs.
potentially multi-turn-cumulative for Azure/TraceLab) — preserve this
caveat on every prompt-length claim. `docs/WORKLOAD_CHARACTERIZATION_PAPER_RESULT.md`,
`docs/SOURCE_SEPARABILITY_AUDIT_20260901.md`, `docs/DATA_FIELD_PROVENANCE.md`,
`docs/DATA_LICENSE_AUDIT.md`.

## 13. Phase-10 windows

120 windows frozen (40/source: BurstGPT, Azure 2024, Bailian/Qwen; 10
Stage-0-reused + 30 Pilot-V2-new per source), deterministic
outcome-blind sampling, EARLY/MIDDLE/LATE chronology strata (60/30/30).
`docs/RANKING_PORTABILITY_WINDOW_FREEZE.md`.

## 14. Phase-11 calibration

FIFO-only, six regions (LOW 0.5, PRE_KNEE 0.8, KNEE 1.0, POST_KNEE 1.1,
OVERLOAD 1.2, HIGH_PRESSURE 1.5), 720 cells, all valid, deterministic.
`docs/RANKING_PORTABILITY_PHASE11_CALIBRATION_FREEZE.md`.

## 15. Policy panel

13 executed policies: 11 PRIMARY (fifo, edf, least_laxity_first,
estimated_service_time_first, weighted_fair_share, kv_constrained_online,
vllm_faithful, vllm_chunked_prefill_faithful, sarathi_faithful,
slai_faithful, admission_control) + 2 STYLE_APPROXIMATION robustness-only
(vllm_style_token_budget, scorpio_style_slo_guard). Two disaggregation
policies (distserve_faithful, llumnix_faithful) execute in a secondary
stratum only; apt_serve_faithful is excluded (scaffolding-only).
`docs/RANKING_PORTABILITY_POLICY_PANEL.md`.

## 16. Metrics

Always-defined: completion fraction, ANWG (primary), weighted completion
fraction. Completion-conditioned (undefined/NaN, never imputed, when
completion fraction = 0): SLO-violation rate, weighted goodput,
mean/p95/p99 latency, request/token throughput. TTFT has a stricter,
separately checked precondition. `docs/RANKING_PORTABILITY_METRIC_DEFINITIONS.md`.

## 17. Telemetry

Seven-field mechanism-activation schema (queue depth, batch saturation,
prefill/decode contention, KV occupancy, admission-control activations,
preemption/reorder events, token-budget saturation), always defined;
zero means mechanism-absent-for-this-policy, not instrumentation failure.
`docs/RANKING_PORTABILITY_TELEMETRY_IMPLEMENTATION.md`.

## 18. Statistical analysis

Kendall's tau-b, Spearman's rho, block-bootstrap CIs, top-k overlap,
practical-margin + CI-excludes-zero reversal detection, probability-of-
correct-selection sample-complexity design (n∈{5,10,20,30,40}, ≥500
draws/n, 0.9 recovery threshold). `docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md`,
`docs/STATISTICAL_ANALYSIS_PLAN.md`, `docs/literature/STATISTICAL_METHODS_LEDGER.md`.

## 19. Caveats

See `docs/SCIENTIFIC_CAVEATS_AND_OPEN_ISSUES.md` in full; headline items:
LLM-2026 overlap remains `UNRESOLVED` at the byte-level historical
reconstruction level (not a proof issue); Phase 11 is FIFO-only calibration
provenance, never a comparative result; prompt-token semantic differences
across sources (§12); BurstGPT/Azure provider-independence caveat (§9, §20).

## 20. Literature status

`LITERATURE_INTEGRITY_GATE = PASS` (Query 3, 2026-09-02). 30 BibTeX entries
in `docs/literature/verified_related_work.bib` (28 distinct works), 2
verified-metadata related-work-only items (P-PAS, A Year in LLM Serving),
1 unresolved/rejected (XPerf — no primary source locatable). Full
disposition table: `docs/literature/PRIMARY_SOURCE_CITATION_LEDGER.md`.
Corrections record: `docs/literature/METADATA_CORRECTIONS.md`.

**`BROAD_RELATED_WORK_SEARCH_ALREADY_COMPLETED = YES`**
**`FUTURE_AGENT_SHOULD_READ_CANONICAL_LITERATURE_FILES_FIRST = YES`**
**`DO_NOT_REPEAT_BROAD_SEARCH_WITHOUT_TRIGGER = YES`**

Broad search should be repeated only if: (1) substantial time has passed
since the search cutoff (2026-09-01, targeted-gate re-check 2026-09-02);
(2) a new novelty threat appears; (3) reviewers request new references;
(4) paper scope materially changes; or (5) an unresolved citation requires
resolution. (`docs/literature/README.md`.)

## 21. Canonical literature paths

`docs/literature/` — `README.md` (start here),
`PRIMARY_SOURCE_CITATION_LEDGER.md`, `NOVELTY_THREAT_LEDGER.md`,
`WORKLOAD_DATASET_LEDGER.md`, `SCHEDULER_BASELINE_LEDGER.md`,
`BENCHMARK_SIMULATOR_LEDGER.md`, `STATISTICAL_METHODS_LEDGER.md`,
`RELATED_WORK_POSITIONING.md`, `METADATA_CORRECTIONS.md`,
`REJECTED_OR_NONCITABLE_REFERENCES.md`, `SEARCH_COVERAGE_LOG.md`,
`CLAIM_TO_CITATION_MATRIX.md`, `WORKLOAD_AND_BENCHMARK_COMPARISON.md`,
`verified_related_work.bib`.

## 22. Manuscript status

See `docs/PROJECT_STATUS.md` §7 for the per-section status table and
`docs/MANUSCRIPT_CONTENT_MAP.md` for the full per-subsection evidence map.
`paper/main.tex` compiles cleanly via `tectonic` (exit 0, 23 pages, no
undefined references/citations).

## 23. Exact next scientific task

Phase 12: Pilot-V2 smoke → 18,720-cell campaign → ranking analysis →
sample-complexity analysis → real-system validation, in that order, each
gated on the previous step, starting from this branch. **Not started by
this handoff.**

## 24. Exact next manuscript task

Once Phase-12 analyses produce outcomes, populate
`paper/sections/results.tex`, `sample_complexity.tex`, and
`real_system.tex`'s `[PENDING RESULT: ...]` contracts with the actual
tables/figures per `docs/MANUSCRIPT_RESULT_CONTRACT.md` and
`docs/MANUSCRIPT_FIGURE_TABLE_PLAN.md`, then firm up `discussion.tex` and
`conclusion.tex`'s numeric content accordingly. Do not write a direction of
finding into any of those files before the corresponding analysis exists.

## 25. Reading order for a new session

1. `docs/NEW_CHAT_START_HERE.md` (short version of this document)
2. This document (`docs/CANONICAL_HANDOFF.md`)
3. `docs/PROJECT_STATUS.md`
4. `docs/DOCUMENTATION_INDEX.md`
5. `docs/literature/README.md`
6. `docs/MANUSCRIPT_CONTENT_MAP.md` + `docs/MANUSCRIPT_EVIDENCE_MAP.md`
7. `paper/main.tex` (or the compiled `paper/main.pdf`)
