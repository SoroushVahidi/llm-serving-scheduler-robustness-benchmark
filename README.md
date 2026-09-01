# LLM-Serving Scheduler Robustness Benchmark

Private, pre-1.0 research repository. Research question (approximately):
**do comparative conclusions about LLM-serving schedulers remain stable when
workload source, workload distribution, load level, time period, and
evaluation metric change?**

This is a new project, deliberately kept distinct from two existing
manuscript lines and one existing dataset — see `docs/OVERLAP_LEDGER.md`
before reading anything else in this repo.

## Start here

- `docs/RESEARCH_QUESTIONS.md` — RQ1–RQ6, frozen.
- `docs/CLAIM_BOUNDARIES.md` — what this paper explicitly does not claim.
- `docs/OVERLAP_LEDGER.md` — classification of every concept against LLM 2026,
  SIGMETRICS 2027, and the seed HF dataset. **One row (load-dependent rank
  reversal) is `NEEDS_REVIEW`** — read it before extending that RQ.
- `docs/PROVENANCE.md` — exactly what infrastructure was reused from where,
  and why it's infrastructure rather than a reused scientific result.
- `docs/GO_NO_GO_GATES.md` — current status of each gate.

## Layout

- `src/robustbench/` — simulator, policy library, and workload-ingestion
  infrastructure (mostly reused, see `docs/PROVENANCE.md`), plus new
  descriptor/schema/window code specific to this project
  (`descriptors/`, `schemas/`).
- `configs/policies/canonical_policy_registry.yaml` — the scheduler panel.
- `configs/workloads/source_registry.yaml` — the workload source registry.
- `configs/splits/` — split manifests (placeholders at bootstrap time; see
  `docs/SPLIT_PROTOCOL.md`).
- `docs/` — the full design/audit document set (see task charter for the
  complete list; all required documents from the bootstrap task exist here).
- `paper/OUTLINE.md` — manuscript skeleton, no populated results.
- `tests/` — bootstrap smoke tests (simulator, workload adapters, window
  descriptors, schema validation).

## Setup

```
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Status

**Project status → `docs/PROJECT_STATUS.md`** (canonical, kept current —
read this first for "where are we right now").
**Roadmap → `docs/PROJECT_ROADMAP.md`** (dependency-ordered plan to
submission/release).
**Branch map → `docs/BRANCH_MAP.md`** (which branch has what; none are
merged to `main` yet).

Summary as of the last status update: the Stage-0 discriminability pilot
ran to completion (`STAGE0_NO_GO`, diagnosed root cause
`POLICY_PANEL_MECHANISM_MISMATCH`); a redesigned ranking-portability
study ("Pilot V2") is preregistered and its workload-window data layer is
under construction. The eventual public dataset for this project is
named the **LLM-Serving Scheduler Portability Benchmark (LSSP
Benchmark)** — see `docs/PROJECT_STATUS.md` §12 for its (not yet
published) release plan.

`docs/PROJECT_STATUS.md` is the single source of truth for current
state; do not infer status from `docs/GO_NO_GO_GATES.md` or
`docs/EXPERIMENT_CAMPAIGN_PLAN.md` alone — both remain useful historical/
frozen references but are not kept in sync with day-to-day status.
