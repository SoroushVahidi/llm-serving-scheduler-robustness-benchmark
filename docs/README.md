# Documentation Index

This repository's `docs/` accumulated across many sequential research
phases (Stage-0 discriminability pilot → Pilot-V2 redesign → Phase 10-12
campaign → JSC manuscript polish → real-vLLM RQ6 engineering → this
release prep). Nothing here has been deleted or rewritten to look
retroactively tidy — this index exists so a new reader doesn't have to
guess which of ~70 files is still authoritative.

For the exhaustive internal document map (every doc, grouped by topic),
see `DOCUMENTATION_INDEX.md`. This page is the shorter, public-facing
entry point.

## Current guides (start here)

- `../README.md` — top-level project overview.
- `ARTIFACT_EVALUATION_GUIDE.md` — reviewer-facing reproduction path.
- `LSSP_DATASET_RELEASE_SCHEMA.md` — planned Hugging Face dataset structure.
- `LSSP_HF_DATASET_CARD_DRAFT.md` — draft dataset card (not yet published).
- `LSSP_THIRD_PARTY_SOURCE_LICENSES.md` — license/redistribution status for
  BurstGPT, Azure-2024, Bailian/Qwen.
- `REAL_VLLM_SLAI_FIDELITY.md` — current status of the real-vLLM SLAI
  scheduler plugin (algorithm-validated; scientific RQ6 run not started).
- `PROJECT_STATUS.md` — day-to-day state as of its own last-updated date
  (see the "current status" caveat below — read the top-level README's
  Status table for the state as of this release-prep pass instead if the
  two disagree).

## Scientific freeze records (historical, preserve as-written)

These document the exact state, decisions, and hashes at a specific past
freeze point. They are **not** updated after the fact, by policy — a
prefreeze doc that says "not yet executed" describes that moment
correctly and must keep saying so even after execution completed
elsewhere (that later state lives in a *different*, later freeze doc or
in the current README, never retrofitted into the earlier one):

`RANKING_PORTABILITY_WINDOW_FREEZE.md`,
`RANKING_PORTABILITY_PHASE11_PRELAUNCH_FREEZE.md`,
`RANKING_PORTABILITY_PHASE11_CALIBRATION_FREEZE.md`,
`RANKING_PORTABILITY_PHASE12_SMOKE_FREEZE.md`,
`RANKING_PORTABILITY_PHASE12_CAMPAIGN_PRELAUNCH_FREEZE.md`,
`RANKING_PORTABILITY_PHASE12_CAMPAIGN_FREEZE_VALIDATION.md`,
`RANKING_PORTABILITY_PHASE12_ANALYSIS_PREFREEZE.md`,
`RANKING_PORTABILITY_PHASE12_SMOKE_VALIDATION.md`,
`RANKING_PORTABILITY_PHASE12_SMOKE_DEFECTS.md`,
`RANKING_PORTABILITY_PHASE12_TELEMETRY_SEMANTIC_AMENDMENT.md`,
`ARTIFACT_HASH_LEDGER.md`, `LSSP_ARTIFACT_REPRO_PREFREEZE.md`.

## Historical engineering records (preserve, no longer the current path)

Records of a specific investigation or a since-superseded plan; kept for
provenance, not maintained:

`STAGE0_*.md` (the entire Stage-0 discriminability pilot, superseded by
Pilot-V2/Phase-10-12 after `STAGE0_NO_GO`), `WORKLOAD_CHARACTERIZATION_
PAPER_RESULT.md`, `OVERNIGHT_WORKLOAD_CHARACTERIZATION_HANDOFF_20260901.md`,
`RELATED_WORK_NOVELTY_AUDIT.md`, `SOURCE_SEPARABILITY_AUDIT_20260901.md`,
`TRACELAB_PROVENANCE_RESOLUTION.md`, `SERVEGEN_ADOPTION_AUDIT.md`,
`WORKTREE_AUDIT.md`, `PHASE12_SLO_SENSITIVITY_PROTOCOL_HOLE.md`
(documents a genuine, still-open protocol gap — historical in the sense
that it recorded a decision point, not that the gap is resolved).

## Internal / process (not essential for a code or dataset user)

Planning, ledgers, and session-handoff documents written for continuity
across the many research sessions that built this project, not for an
external reader: `NEW_CHAT_START_HERE.md`, `CANONICAL_HANDOFF.md`,
`PROJECT_ROADMAP.md`, `BRANCH_MAP.md`, `EXPERIMENT_STATUS.md`,
`EXPERIMENT_CAMPAIGN_PLAN.md`, `GO_NO_GO_GATES.md`, `OVERLAP_LEDGER.md`,
`EVIDENCE_INDEPENDENCE_PLAN.md`, `SCIENTIFIC_EVIDENCE_INVENTORY.md`,
`MANUSCRIPT_CONTENT_MAP.md`, `MANUSCRIPT_EVIDENCE_MAP.md`,
`MANUSCRIPT_CLAIM_LEDGER.md`, `MANUSCRIPT_CITATION_MAP.md`,
`MANUSCRIPT_FIGURE_TABLE_PLAN.md`, `MANUSCRIPT_RESULT_CONTRACT.md`,
`REAL_SYSTEM_ENGINEERING_INVENTORY.md`, `REAL_SYSTEM_MECHANISM_INVENTORY.md`,
`REAL_SYSTEM_METRIC_MAPPING.md`, `real_vllm_engineering_environment.json`
(in `artifacts/manifests/`). These are left in place (not moved or
deleted — cross-references between them are extensive and Git history is
not being rewritten) but are not part of the public reading path.

## Method / protocol references (public, method-level)

`RESEARCH_QUESTIONS.md`, `CLAIM_BOUNDARIES.md`, `RANKING_PORTABILITY_
PILOT_V2_PROTOCOL.md`, `RANKING_PORTABILITY_ANALYSIS_PLAN.md`,
`RANKING_PORTABILITY_POLICY_PANEL.md`, `RANKING_PORTABILITY_METRIC_
DEFINITIONS.md`, `RANKING_PORTABILITY_TELEMETRY_IMPLEMENTATION.md`,
`RANKING_PORTABILITY_CALIBRATION_CHARACTERISTICS.md`,
`STATISTICAL_ANALYSIS_PLAN.md`, `REAL_SYSTEM_VALIDATION_PLAN.md`,
`LOAD_CALIBRATION_PROTOCOL.md`, `POLICY_COMPARABILITY_AUDIT.md`,
`REPRODUCIBILITY_CONTRACT.md`, `SCIENTIFIC_CAVEATS_AND_OPEN_ISSUES.md`,
`DATASET_V2_SCHEMA.md`, `SPLIT_PROTOCOL.md`, `PROVENANCE.md`,
`DATA_ACQUISITION_STATUS.md`, `DATA_FIELD_PROVENANCE.md`,
`DATA_LICENSE_AUDIT.md` (broader six-source audit;
`LSSP_THIRD_PARTY_SOURCE_LICENSES.md` is the LSSP-scoped conclusion),
`WORKLOAD_DISTRIBUTION_CHARACTERIZATION_PROTOCOL.md`.

## Literature

`literature/README.md` and the citation/novelty/metadata ledgers under
`literature/` — read `literature/README.md` first.

---

**Note on staleness**: a handful of internal-process docs (`PROJECT_
STATUS.md`, `GO_NO_GO_GATES.md`, `EXPERIMENT_STATUS.md`) predate the
Phase-12 completion this release-prep pass confirms and were written for
in-session continuity, not as a public status page — they are not
rewritten here to avoid corrupting their own point-in-time record (would
turn a real freeze record into a fabricated one); the top-level `README.md`
Status table is the current, authoritative summary as of 2026-09-02.
