# BRANCH_MAP.md — Branch Lineage

This project now has an authoritative Phase-10 integration branch and a separate manuscript/literature branch. The scientific lineage is preserved and explicit.

## Authoritative scientific lineage

- `main` — untouched skeleton branch
- `research/ranking-portability-windows-20260901` — authoritative Phase-10 branch at `3f5aa6a27e56b2d32f80b471d1201b5ec119c962`
- `research/lssp-integrated-phase10-20260901` — authoritative integrated scientific branch containing the committed Phase-10 + project-state + characterization work
- `research/ranking-portability-phase11-calibration-prep-20260901` — child implementation branch for the Phase-11 design and harness only; no real calibration execution

## Sibling branch evidence

- `research/workload-characterization-paper-result-20260901` @ `9435e87` — final characterization result; preserved as a sibling scientific branch and selectively integrated to the integrated branch without altering frozen Phase-10 data
- `research/project-state-audit-20260901` @ `1909713` — canonical status/audit branch; selectively integrated into the integrated branch

## Parallel manuscript work

- `research/lssp-literature-verification-20260901` — manuscript/literature branch, kept separate and not integrated into the scientific execution branch
- `research/lssp-literature-verification-20260901` is marked as `PARALLEL_WORK / NOT YET INTEGRATED`

## Canonical status

The integrated branch is the new authoritative current branch for scientific work through Phase 10.
Historical branches remain preserved for provenance and audit continuity.
