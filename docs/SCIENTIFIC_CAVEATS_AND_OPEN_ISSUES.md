# SCIENTIFIC_CAVEATS_AND_OPEN_ISSUES.md

Compilation of preserved caveats and open issues for the integrated scientific state.

## Preserved caveats

1. `SEPARABILITY_RESULT_CONFIRMED_WITH_CAVEATS` remains the final characterization result. It is not evidence of scheduler portability.
2. The LLM-2026 overlap limit remains explicitly recorded as `UNRESOLVED` where exact byte-level historical reconstruction was not possible from the available public checkout.
3. Stage-0 final verdict remains `STAGE0_NO_GO` and remains a historical pilot verdict, not a benchmark release verdict.
4. Phase 11 is FIFO-only calibration provenance. It is not a comparative scheduler outcome and must not be reported as one.
5. Manual literature work remains on the parallel manuscript/literature worktree and is intentionally not integrated into the scientific execution branch.

## Open issues

| Issue | Status | Path | Notes |
|---|---|---|---|
| exact historical LLM-2026 overlap reconstruction | unresolved | `docs/OVERLAP_LEDGER.md` | kept explicit and non-ambiguous |
| Pilot-V2 smoke execution | not started | `docs/PROJECT_ROADMAP.md` | deferred until Phase-12 |
| 18,720-cell campaign | not started | `docs/PROJECT_ROADMAP.md` | pending freeze validation |
| ranking analysis | not started | `docs/PROJECT_ROADMAP.md` | depends on campaign completion |
| real-system validation | not started | `docs/REAL_SYSTEM_VALIDATION_PLAN.md` | parallel validation track |
| manuscript/literature consolidation | parallel work only | `docs/CANONICAL_HANDOFF.md` | handled by Query 2 |

## Interpretation boundary

The scientific result boundary is explicit: calibration and protocol freeze are valid scientific artifacts, but they do not establish comparative scheduler performance. Only completed campaign results may be interpreted as benchmark outcomes.
