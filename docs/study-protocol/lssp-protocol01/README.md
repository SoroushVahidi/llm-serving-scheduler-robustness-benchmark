# LSSP-PROTOCOL01 — author-review draft

Status: **DRAFT — NOT PREREGISTERED — NO EXECUTION AUTHORIZATION**. Prepared 2026-10-21 against execution/research commit `4332b08b17e5b789e20a4fe042a6b007f0d43dd6`. This is a prospective physical-study protocol, not an amendment to frozen historical measurements.

The proposed contribution is an auditable account of **when a validated scheduler ordering can be reused across deployment configurations, with uncertainty and measured transfer regret**, plus targeted experiments explaining the boundaries. Stable orderings and failure to establish transfer are legitimate outcomes. More benchmark cells alone do not constitute the contribution.

| Read in order | Purpose |
|---|---|
| [RESEARCH_QUESTIONS.md](RESEARCH_QUESTIONS.md) | Contribution and claim boundaries |
| [NOVELTY_AND_OVERLAP.md](NOVELTY_AND_OVERLAP.md) | Primary literature, public versions and overlap |
| [HYPOTHESES.md](HYPOTHESES.md) | Falsifiable tests and decision criteria |
| [EXPERIMENTAL_MATRIX.md](EXPERIMENTAL_MATRIX.md) | Deployments, policies, model, workloads and controls |
| [METRICS_AND_STATISTICS.md](METRICS_AND_STATISTICS.md) | Estimands, uncertainty, inference and held-out evaluation |
| [FIDELITY_AND_EXCLUSION_GATES.md](FIDELITY_AND_EXCLUSION_GATES.md) | Supported/rejected/unverified semantics and evidence gates |
| [STAGED_EXECUTION_PLAN.md](STAGED_EXECUTION_PLAN.md) | Stage 0–4 GO/NO-GO conditions |
| [RESOURCE_BUDGET.md](RESOURCE_BUDGET.md) | Pilot-based sample size and allocated GPU-hours |
| [PREREGISTRATION_DRAFT.md](PREREGISTRATION_DRAFT.md) | Prospective freeze and amendment procedure |
| [AUTHOR_DECISIONS.md](AUTHOR_DECISIONS.md) | Fixed constraints, proposals and unresolved choices |

[design_manifest.json](design_manifest.json) is a non-executable design manifest. Nulls are unresolved freeze blockers, not defaults. [evidence/review_inventory.json](evidence/review_inventory.json) binds the local material reviewed; [evidence/mgpu03_accounting.txt](evidence/mgpu03_accounting.txt) records a single read-only accounting check. No MGPU03 serving outputs or performance summaries were opened to design this protocol.

Validate locally with `python3 docs/study-protocol/lssp-protocol01/validate_protocol.py`. This checks document/manifest integrity and design arithmetic, not implementation or physical serving correctness. The full harness's previously reported 151 local tests are historical MGPU02 evidence, not tests rerun by this documentation change.

The new draft PR is stacked on the existing research branch/PR #1. Only this directory is changed. No GPU jobs, campaign launchers, manuscript edits, or historical-data changes are part of this deliverable.
