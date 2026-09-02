# PROJECT_ROADMAP.md — LLM-Serving Scheduler Portability Benchmark

This roadmap reflects the verified scientific state through Phase 10 and the Phase-11 implementation handoff.

## Immediate dependency chain

frozen 120 windows
  ↓
Phase-11 six-region, policy-independent calibration
  ↓
calibration freeze
  ↓
Pilot-V2 smoke
  ↓
prelaunch matrix freeze
  ↓
18,720-cell campaign
  ↓
matrix validation
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

Manuscript work continues in parallel, but it is a separate track from the scientific execution chain.

## Current status by milestone

### Phase 10 — window freeze

| Task | Status | Evidence |
|---|---|---|
| 120-window Pilot-V2 selection frozen | DONE | canonical scientific hash preserved |
| temporal-stratum audit | DONE | quality-controlled and audited |
| Stage-0 / LLM-2026 overlap audit | DONE | unresolved provenance limitation explicitly recorded |
| deterministic reconstruction | DONE | reproducible selection verified |
| data-quality validation | DONE | 17 targeted tests passed |
| storage design for compact manifest | DONE | compact index committed |

### Phase 11 — six-region calibration prep

| Task | Status | Evidence |
|---|---|---|
| protocol read and contract freeze | READY | six-region definition fixed, FIFO-only calibration principle fixed |
| implementation harness | READY | standalone Phase-11 code and tests created in child branch |
| real calibration execution | NOT STARTED | explicitly deferred |
| prelaunch freeze template | READY | template created for hashing inputs before execution |

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

The manuscript/literature work remains a separate branch and is intentionally not merged into the scientific integration branch.

Allowed parallel tasks:
- primary-source verification
- literature correction and citation ledger
- claim boundary review
- figure/table plan
- outline and narrative drafting

Not allowed in the scientific execution track:
- Phase-10 scientific file edits
- Pilot-V2 result generation
- real Phase-11 calibration execution
- scientific branch integration for manuscript drafts

## Governance

- `main` remains untouched.
- The integrated Phase-10 branch is the authoritative scientific branch until a later release decision.
- The manuscript branch continues in parallel and is not considered part of the scientific execution chain.
