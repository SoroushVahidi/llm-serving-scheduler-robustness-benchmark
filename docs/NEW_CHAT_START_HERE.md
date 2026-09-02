# NEW_CHAT_START_HERE.md

If you are a new chat session picking up this project: read this file, then
`docs/CANONICAL_HANDOFF.md` for full detail. Do not redo broad literature
search by default (see §5).

## What this is

The LLM-Serving Scheduler Portability Benchmark (LSSP) asks whether a
comparative scheduler ranking $R(W, M, L)$ — induced by a fixed panel of
scheduling policies — is portable across independent workload sources
($W$), evaluation metrics ($M$), and operating/load regions ($L$).

## Where you are

- **Branch:** `research/lssp-authoritative-pre-phase12-20260901`
- **Worktree:** `/home/soroush/repos/llm-serving-scheduler-lssp-authoritative`
- This branch is the merge of: scientific state through Phase 11
  (`research/lssp-integrated-phase11-20260901` @
  `30995d6dc5c9d3bb5db3aecdb975ddb70a92e86a`) + corrected canonical
  literature (`research/lssp-literature-canonical-20260901` @
  `7e5230f4aa1ea408a7d9580594135ca471dc3e42`) + the manuscript foundation.
  `main` is untouched.

## Current state (2026-09-02)

- Phase 10, Phase 11: **DONE**. Phase 12 (Pilot-V2 smoke → 18,720-cell
  campaign → ranking analysis → sample-complexity → real-system
  validation): **READY, NOT STARTED**.
- No comparative Pilot-V2 scheduler outcome exists yet.
- Literature: `LITERATURE_INTEGRITY_GATE = PASS`. 30 verified BibTeX
  entries. Do not repeat the broad literature search (§5).
- Manuscript: Introduction, Related Work, Study Design, Workload Corpus,
  and Methodology are `DRAFT_V1` (real prose, in `paper/sections/`).
  Results, Sample Complexity, and Real-System Validation are
  `CONTRACT_ONLY` — no comparative outcome has been invented. The
  manuscript compiles cleanly (`cd paper && tectonic main.tex`).

## If you're continuing the science (Phase 12)

Read, in order: `docs/PROJECT_STATUS.md`, `docs/RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md`,
`docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md`, `docs/GO_NO_GO_GATES.md`. Do
not modify any of the five immutable hashes in
`docs/ARTIFACT_HASH_LEDGER.md` or `docs/CANONICAL_HANDOFF.md` §8.

## If you're continuing the manuscript

Read, in order: `docs/MANUSCRIPT_CONTENT_MAP.md`,
`docs/MANUSCRIPT_EVIDENCE_MAP.md`, `docs/MANUSCRIPT_RESULT_CONTRACT.md`,
`docs/literature/README.md`, then the relevant `paper/sections/*.tex` file.
Never write a comparative result or a direction of finding (stable /
unstable / reversal exists / scheduler X wins) into any file before the
corresponding Phase-12 analysis has actually run.

## Links

- `docs/PROJECT_STATUS.md` — current unambiguous repository/phase state
- `docs/CANONICAL_HANDOFF.md` — full handoff (this file's long version)
- `docs/DOCUMENTATION_INDEX.md` — full documentation map
- `docs/literature/README.md` — canonical literature entry point
- `docs/literature/PRIMARY_SOURCE_CITATION_LEDGER.md` — every citation's disposition
- `docs/literature/NOVELTY_THREAT_LEDGER.md` — safe novelty wording
- `docs/MANUSCRIPT_CITATION_MAP.md` — section-to-citation mapping
- `docs/MANUSCRIPT_EVIDENCE_MAP.md` — claim-to-evidence mapping
- `paper/main.tex` (or `paper/main.pdf`) — the current manuscript draft

## §5: Do not repeat the broad literature search by default

`docs/literature/SEARCH_COVERAGE_LOG.md` records `BROAD_RELATED_WORK_SEARCH_ALREADY_COMPLETED = YES`.
Only repeat it if: substantial time has passed since the 2026-09-01/02
search cutoff, a new novelty threat appears, reviewers request new
references, paper scope materially changes, or a specific unresolved
citation requires resolution (currently only `XPerf`, per
`docs/literature/PRIMARY_SOURCE_CITATION_LEDGER.md`).
