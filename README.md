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

Bootstrap stage. No confirmatory experiments have been run — see
`docs/EXPERIMENT_CAMPAIGN_PLAN.md` for the staged plan and
`docs/GO_NO_GO_GATES.md` for current gate status.
