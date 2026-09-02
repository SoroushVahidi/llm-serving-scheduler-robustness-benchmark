# LLM-Serving Scheduler Portability Benchmark — Project Status

Last verified: 2026-09-02
Canonical mutable status for the integrated scientific state through Phase 10.

PROJECT_STATUS.md is the canonical single source of truth for project-state changes.

## 1. Executive summary

The project is now in a verified, integrated, non-executing Phase-11 preparation state.

- Phase 0-10: DONE
- Phase 11: READY (implementation + protocol handoff prepared; no real calibration run yet)
- Phase 12+: PENDING
- Pilot-V2 scientific outcomes: NONE
- Manuscript drafting remains a separate parallel track and has not been integrated into the scientific branch.

The authoritative Phase-10 scientific branch is:
`research/ranking-portability-windows-20260901` @ `3f5aa6a27e56b2d32f80b471d1201b5ec119c962`

The integrated branch is:
`research/lssp-integrated-phase10-20260901` @ the current integration commit

## 2. Phase map

| Phase | Objective | Status | Evidence |
|---|---|---|---|
| 0 | Bootstrap / provenance + overlap audit | DONE | repository bootstrap plus audit docs |
| 1 | Evidence/source independence | DONE | Independent-source provenance and exclusions |
| 2 | Workload characterization | DONE | `SEPARABILITY_RESULT_CONFIRMED_WITH_CAVEATS` |
| 3 | Characterization paper-facing cleanup | DONE | leakage-resistant grouped evaluation |
| 4 | Stage-0 pilot preparation | DONE | real-data acquisition and calibration setup |
| 5 | Stage-0 execution | DONE | Stage-0 real pilot launched and audited |
| 6 | Stage-0 repair | DONE | `STAGE0_NO_GO` final decision |
| 7 | BurstGPT diagnostic | DONE | root cause documented |
| 8 | Pilot-V2 preregistration | DONE | protocol + policy panel + analysis plan |
| 9 | Telemetry implementation | DONE | telemetry schema and execution path |
| 10 | Pilot-V2 120-window freeze | DONE | canonical 120-window manifest + compact SHA index |
| 11 | Six-region FIFO calibration implementation | READY | implementation and protocol handoff prepared; NOT STARTED |
| 12+ | Smoke run, 18,720-cell campaign, ranking analysis, real-system validation, dataset release | PENDING | not started |

## 3. Current execution state

- frozen windows = YES
- six-region calibration = NOT STARTED
- Pilot-V2 smoke = NOT STARTED
- 18,720-cell campaign = NOT STARTED
- ranking analysis = NOT STARTED
- real-system validation = NOT STARTED
- Pilot-V2 scientific results = NONE

## 4. Canonical scientific freeze

- canonical window scientific hash:
  `0d1aa06ccbee352207327ea369ae75f12e91c0cda006c813a41b381effd29eef`
- compact index SHA:
  `d78ec1087fedae02174ca093a9860c70468be336ccb1d7e6de756c81ba331e53`
- canonical manifest source: `artifacts/manifests/ranking_portability_pilot_v2_windows.json`
- canonical compact Git index: `artifacts/manifests/ranking_portability_pilot_v2_windows_index.json`

## 5. Scientific findings

- Final workload-characterization result remains:
  `SEPARABILITY_RESULT_CONFIRMED_WITH_CAVEATS`
- This is not evidence of scheduler portability and must not be reinterpreted as such.
- Stage-0 final verdict remains `STAGE0_NO_GO`.
- The Pilot-V2 scientific campaign has not started; no scheduler outcomes exist.

## 6. LLM-2026 overlap caveat

The Phase-10 audit reported the historical LLM-2026 byte-level relationship as `UNRESOLVED` where exact reconstruction was not possible from the available public checkout.

This is recorded accurately as:
- exclusion logic is protocol-compliant;
- no known prohibited reuse was identified;
- exact byte-level historical overlap could not be reconstructed from the available checkout.

This is a provenance limitation, not a statement that independence is proven.

## 7. Full-suite test caveat

The Phase-10 targeted tests passed 17/17.
The complete repository test suite was validated in the project environment and passed there.
The previous shell failure due to missing `pandas` is treated as an environment limitation only, not as a scientific failure.

## 8. Manuscript status

- outline = EXISTS
- claim boundaries = EXISTS
- result contract = EXISTS
- primary-source citation ledger = NOT YET COMPLETE
- Introduction prose = NOT YET COMPLETE
- Related Work prose = NOT YET COMPLETE
- Study Design prose = NOT YET COMPLETE

Manuscript work remains on the separate literature/manuscript worktree and was not integrated into the scientific branch.

## 9. Branches and lineage

The authoritative integrated branch contains the committed scientific state through Phase 10, while the manuscript/literature branch remains separate.

Important lineage facts:
- Phase-10 authoritative branch: `research/ranking-portability-windows-20260901` @ `3f5aa6a27e56b2d32f80b471d1201b5ec119c962`
- characterization sibling branch: `research/workload-characterization-paper-result-20260901` @ `9435e87`
- project-status audit branch: `research/project-state-audit-20260901` @ `1909713`
- integrated branch: `research/lssp-integrated-phase10-20260901`

## 10. Immediate next action

The next scientific action is the separate Phase-11 calibration implementation and protocol handoff in its own child branch/worktree, without executing real calibration.

This task does not execute scheduler outcomes or publish any result artifact.
