# LLM-Serving Scheduler Portability Benchmark — Project Status

**[HISTORICAL PROVENANCE: This document represents the state of the project as of 2026-09-02 (Phase-12B campaign matrix freeze) and is preserved as an unmodified historical record. For the final, current status of the completed campaign and manuscript, see the top-level `README.md`.]**

Last verified: 2026-09-02 (Phase-12B — campaign matrix freeze)
Canonical mutable status for the integrated scientific state through Phase 11,
the corrected canonical literature, the manuscript foundation, the Phase-12A
engineering smoke, and the Phase-12B campaign-matrix freeze.

PROJECT_STATUS.md was the canonical single source of truth for project-state changes during active execution.

## 1. Executive summary

The repository is now in a verified Phase-11 scientific integration state,
with a corrected, primary-source-verified literature base, a compileable
manuscript foundation, a validated Phase-12A engineering smoke, and a
frozen, independently-verified Phase-12B campaign matrix — **not yet
executed**.

- Phase 10: DONE
- Phase 11: DONE
- Phase-12A (Pilot-V2 engineering smoke, 468 cells): DONE, `PHASE12_PILOT_V2_SMOKE_VALID = YES`
- Phase-12B (18,720-cell campaign matrix freeze): DONE, `PHASE12_CAMPAIGN_FREEZE_VALID = YES`
- 18,720-cell scientific campaign execution: **READY, NOT STARTED**
- ranking analysis: NOT STARTED
- sample-complexity analysis: NOT STARTED
- real-system validation: NOT STARTED
- comparative Pilot-V2 scheduler results: NONE
- literature consolidation (Query 2): DONE
- targeted literature integrity gate (Query 3): DONE, `LITERATURE_INTEGRITY_GATE = PASS`
- manuscript foundation (Query 3): DONE — see §7 below

The authoritative current scientific branch (unchanged, Phase 11 tip) is:
`research/lssp-integrated-phase11-20260901` @ `30995d6dc5c9d3bb5db3aecdb975ddb70a92e86a`

The corrected canonical literature branch is:
`research/lssp-literature-canonical-20260901` @ `7e5230f4aa1ea408a7d9580594135ca471dc3e42`

The final authoritative pre-Phase-12 branch (scientific state + literature +
manuscript, unchanged since Query 3) is:
`research/lssp-authoritative-pre-phase12-20260901` @ `ec12af8ede08cf8b6ebb8f60fce85915fc2ef18d`
(worktree: `/home/soroush/repos/llm-serving-scheduler-lssp-authoritative`).

The Phase-12A engineering-smoke branch (DONE, VALID, unchanged) is:
`research/lssp-phase12-pilotv2-smoke-20260902` @ `38188eca740c3bfeafa0463c80aaaff34b725e5a`
(worktree: `/home/soroush/repos/llm-serving-scheduler-lssp-phase12-smoke`).

**The single branch a new chat should read to continue toward campaign
launch is the Phase-12B campaign-freeze branch**, which descends from all
of the above:
`research/lssp-phase12-campaign-freeze-20260902`
(worktree: `/home/soroush/repos/llm-serving-scheduler-lssp-phase12-freeze`).
See `docs/RANKING_PORTABILITY_PHASE12_CAMPAIGN_PRELAUNCH_FREEZE.md` and
`docs/RANKING_PORTABILITY_PHASE12_CAMPAIGN_FREEZE_VALIDATION.md`.

The previous authoritative Phase-10 integration branch remains preserved as:
`research/lssp-integrated-phase10-20260901` @ `4a545b9ae17ae01312db093e6e350f5822bf0bec`

(Note: an earlier revision of this file recorded the Phase-11 branch tip as
`6e2c02fc46b287a5f741c0907475c92c9e33fc87`; that was a stale intermediate
commit on that branch. `30995d6dc5c9d3bb5db3aecdb975ddb70a92e86a` is the
verified current tip and the SHA this document's immutable-hash table in
§4 was generated against.)

## 2. Phase map

| Phase | Objective | Status | Evidence |
|---|---|---|---|
| 0 | Bootstrap / provenance + overlap audit | DONE | repository bootstrap and audit docs |
| 1 | Evidence/source independence | DONE | provenance + exclusions records |
| 2 | Workload characterization | DONE | `SEPARABILITY_RESULT_CONFIRMED_WITH_CAVEATS` |
| 3 | Characterization paper-facing cleanup | DONE | leakage-resistant grouped evaluation |
| 4 | Stage-0 pilot preparation | DONE | calibration setup and protocol |
| 5 | Stage-0 execution | DONE | real 1,080-cell pilot executed |
| 6 | Stage-0 repair | DONE | `STAGE0_NO_GO` final decision |
| 7 | BurstGPT diagnostic | DONE | root cause documented |
| 8 | Pilot-V2 preregistration | DONE | protocol + policy panel + analysis plan |
| 9 | Telemetry implementation | DONE | telemetry schema and implementation |
| 10 | Pilot-V2 120-window freeze | DONE | canonical phase-10 window hash preserved |
| 11 | Six-region FIFO calibration | DONE | raw FIFO calibration + assignments retained |
| 12A | Pilot-V2 engineering smoke (468 cells) | DONE | `PHASE12_PILOT_V2_SMOKE_VALID = YES` |
| 12B | 18,720-cell campaign matrix freeze | DONE | `PHASE12_CAMPAIGN_FREEZE_VALID = YES`, not executed |
| 12C | 18,720-cell campaign / analysis / validation | READY | not started |

## 3. Current execution state

- frozen windows = YES
- six-region FIFO calibration = DONE
- Pilot-V2 engineering smoke (Phase-12A, 468 cells) = DONE, VALID
- telemetry semantic amendment (Phase-12B) = RESOLVED (`docs/RANKING_PORTABILITY_PHASE12_TELEMETRY_SEMANTIC_AMENDMENT.md`)
- 18,720-cell campaign matrix freeze (Phase-12B) = DONE, VALID, `campaign_freeze_sha256 = 81fa3d9b48a2241001e6820942d4542dcc5b5e30973ad9d2786e72972494f57a`
- 18,720-cell campaign execution (Phase-12C) = **READY, NOT STARTED**
- ranking analysis = NOT STARTED
- sample-complexity analysis = NOT STARTED
- real-system validation = NOT STARTED
- comparative Pilot-V2 scheduler results = NONE

## 4. Canonical scientific freeze

- phase-10 scientific window hash: `0d1aa06ccbee352207327ea369ae75f12e91c0cda006c813a41b381effd29eef`
- phase-10 compact index hash: `d78ec1087fedae02174ca093a9860c70468be336ccb1d7e6de756c81ba331e53`
- phase-11 prelaunch freeze hash: `e2564ea9484190832de50f63173c4b73ae054d6ae7008bb4ff6648c8dc917f7b`
- phase-11 raw FIFO calibration hash: `201caaf04476ad8737ef6079fc0d6cb4e864601711d0b96c88750a717d8b2a6a`
- phase-11 region assignment hash: `9fcb92f9ea1206ce185194527ada35d0e3b91bf4904be7ae23ba9ea997c17574`
- canonical window manifest: `artifacts/manifests/ranking_portability_pilot_v2_windows_index.json`

## 5. Scientific findings

- Final workload-characterization result remains `SEPARABILITY_RESULT_CONFIRMED_WITH_CAVEATS`.
- Stage-0 final verdict remains `STAGE0_NO_GO`.
- Phase 11 is a FIFO-only calibration provenance artifact; it is not a comparative scheduler result.
- No comparative Pilot-V2 scheduler outcomes exist.

## 6. Caveats and provenance boundaries

The Phase-10 audit recorded the historical LLM-2026 overlap relationship as `UNRESOLVED` where exact reconstruction was not possible from the available public checkout.

This is retained as:
- a provenance limitation,
- not a statement of proof,
- and not a causal claim about benchmark validity.

The zero-completion counts retained in the Phase-11 calibration documentation are descriptive only and must not be reinterpreted as comparative scheduler performance.

## 7. Manuscript status

Manuscript sections, tracked in `docs/MANUSCRIPT_CONTENT_MAP.md` (per-subsection
detail) and `paper/sections/*.tex` (actual prose):

| Section | Status |
|---|---|
| Introduction | `DRAFT_V1` (manuscript-quality prose, outcome-neutral) |
| Related Work | `DRAFT_V1` (all 6 subsections, corrected literature) |
| Study Design | `DRAFT_V1` |
| Workload Corpus / Characterization | `DRAFT_V1` (established numbers included) |
| Scheduler Methodology (panel/fidelity/calibration/metrics/telemetry/robustness) | `DRAFT_V1` |
| Results (ranking portability) | `CONTRACT_ONLY` |
| Sample Complexity | `CONTRACT_ONLY` |
| Real-System Validation | `CONTRACT_ONLY` |
| Discussion | `STRUCTURED_V1` (both outcome branches written; numeric content pending) |
| Threats to Validity | `DRAFT_V1` |
| Reproducibility / Artifact | `DRAFT_V1` |
| Conclusion | `STRUCTURED_V1` |

The manuscript compiles cleanly (`paper/main.tex` via `tectonic`, exit 0, 23
pages, no undefined references/citations, no severe overfull boxes; see
`docs/CANONICAL_HANDOFF.md`). It is now integrated onto the same
authoritative branch as the scientific state and literature (unlike the
prior parallel-track arrangement described in earlier revisions of this
document).

## 8. Branch / lineage summary

- `main` remains untouched.
- `research/lssp-integrated-phase11-20260901` is the current authoritative branch for scientific state through Phase 11 (unchanged, frozen).
- `research/lssp-integrated-phase10-20260901` remains the prior authoritative Phase-10 scientific branch (unchanged, frozen).
- `research/lssp-literature-canonical-20260901` is the Query-2 canonical literature branch (unchanged from Query 2; corrections in Query 3 live on the branch below, not by rewriting this one).
- `research/lssp-authoritative-pre-phase12-20260901` is the **final authoritative branch**: scientific state (Phase 11 tip) + corrected canonical literature + manuscript foundation. This is the branch a new chat should read.

## 9. Immediate next action

- **Next scientific task:** launch and monitor the frozen 18,720-cell Phase-12 scientific campaign exactly from the Phase-12B campaign-freeze identity (`campaign_freeze_sha256 = 81fa3d9b48a2241001e6820942d4542dcc5b5e30973ad9d2786e72972494f57a`, branch `research/lssp-phase12-campaign-freeze-20260902`), then ranking analysis → sample-complexity analysis → real-system validation. Not started by this query, per explicit instruction — the shard-runner entrypoint (`scripts/ranking_portability/run_phase12_campaign_shard.py`) currently supports `--dry-run` only; a future query must implement and review its `--execute` path before launch.
- **Next manuscript task:** populate `paper/sections/results.tex`, `sample_complexity.tex`, and `real_system.tex`'s `[PENDING RESULT: ...]` contracts once the corresponding Phase-12 analyses exist; firm up `discussion.tex` and `conclusion.tex`'s numeric content accordingly.
