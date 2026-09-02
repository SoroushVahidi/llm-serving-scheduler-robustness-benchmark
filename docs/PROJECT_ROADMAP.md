# PROJECT_ROADMAP.md — LLM-Serving Scheduler Portability Benchmark

This roadmap reflects the verified scientific state through Phase 11.

## Immediate dependency chain

Phase-10 120-window freeze
  ↓
Phase-11 FIFO calibration run
  ↓
calibration validity gate
  ↓
Phase-12 smoke check
  ↓
prelaunch matrix freeze
  ↓
18,720-cell campaign
  ↓
benchmark matrix validation
  ↓
ranking portability analysis
  ↓
sample-complexity / temporal / OOD analyses
  ↓
real-system validation
  ↓
LSSP artifact release
  ↓
manuscript finalization

Manuscript work continues in parallel as a separate track and is intentionally not merged into the scientific execution branch.

## Current status by milestone

### Phase 10 — window freeze

| Task | Status | Evidence |
|---|---|---|
| 120-window Pilot-V2 selection frozen | DONE | canonical scientific hash preserved |
| temporal-stratum audit | DONE | quality-controlled and audited |
| Stage-0 / LLM-2026 overlap audit | DONE | unresolved provenance limitation explicitly recorded |
| deterministic reconstruction | DONE | reproducible selection verified |
| data-quality validation | DONE | targeted tests passed |
| compact manifest design | DONE | index hash preserved |

### Phase 11 — FIFO calibration

| Task | Status | Evidence |
|---|---|---|
| protocol freeze | DONE | six-region FIFO-only calibration contract retained |
| execution | DONE | raw FIFO matrix + region assignment output generated |
| validity gate | DONE | `PHASE11_CALIBRATION_VALID = YES` |
| determinism check | DONE | `CALIBRATION_DETERMINISTIC = YES` |
| interpretation boundary | DONE | calibration provenance preserved without ranking claims |

### Phase 12+ — execution pipeline

| Task | Status |
|---|---|
| Pilot-V2 smoke | NOT STARTED |
| prelaunch matrix freeze | NOT STARTED |
| 18,720-cell campaign | NOT STARTED |
| ranking portability analysis | NOT STARTED |
| sample complexity / temporal / OOD analyses | NOT STARTED |
| real-system validation | NOT STARTED |
| public artifact release | NOT STARTED |
| manuscript finalization | PARALLEL / NOT YET STARTED |

## Manuscript parallel track

The manuscript/literature work remains on a separate branch and is intentionally not merged into the scientific integration branch.

Allowed parallel tasks:
- primary-source verification
- literature correction and citation ledger
- claim boundary review
- figure/table plan
- outline + narrative drafting

Not allowed in the scientific execution track:
- Phase-10 scientific file edits
- new comparative scheduler result claims
- Phase-12 execution before Query 2 handoff is complete

## Governance

- `main` remains untouched.
- `research/lssp-integrated-phase11-20260901` is the current authoritative scientific branch.
- The manuscript branch continues in parallel and is not considered part of the scientific execution chain.
