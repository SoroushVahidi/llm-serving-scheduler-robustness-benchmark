# PROJECT_ROADMAP.md — LLM-Serving Scheduler Portability Benchmark

`docs/PROJECT_STATUS.md` = where we are right now. This document = how we
get from there to submission/release. No dates are given unless already
fixed elsewhere (none are) — status and prerequisites only.

## Milestone 1 — Data layer

| Task | Status | Prerequisites | Expected output | Authoritative branch/file | Type | Parallel? |
|---|---|---|---|---|---|---|
| Real data acquisition (Azure-2024, Bailian/Qwen, BurstGPT) | DONE | none | verified checksums, `docs/DATA_ACQUISITION_STATUS.md` | `research/stage0-prerequisites-20260901` | Engineering | — |
| Stage-0 10-window/source sample | DONE | acquisition | `stage0_windows.json` (Wulver, gitignored) | `research/stage0-orchestration-prelaunch-20260901` | Engineering | — |
| Pilot-V2 40-window/source extension algorithm | DONE | Stage-0 windows | `window_sampling.py`, 17 passing unit tests | `research/ranking-portability-windows-20260901` (uncommitted) | Engineering | Yes, done in parallel with telemetry (Milestone 3) |
| Pilot-V2 120-window real construction | **ACTIVE** | extension algorithm | `ranking_portability_pilot_v2_windows.json` | same branch | Engineering | No — blocks Milestone 2 |
| Window freeze (reproducibility, overlap audit, `WINDOW_FREEZE.md`) | PENDING | 120-window construction complete | frozen, hashed manifest | same branch | Scientific | No |

## Milestone 2 — Load calibration

| Task | Status | Prerequisites | Expected output | Authoritative branch/file | Type | Parallel? |
|---|---|---|---|---|---|---|
| Six-region (`LOW/PRE_KNEE/KNEE/POST_KNEE/OVERLOAD/HIGH_PRESSURE`) `fifo`-referenced calibration for all 120 windows | PENDING | Milestone 1 window freeze | per-window `lambda_ref` + region multiplier table | not yet created | Scientific | No |

## Milestone 3 — Pilot-V2 execution

| Task | Status | Prerequisites | Expected output | Authoritative branch/file | Type | Parallel? |
|---|---|---|---|---|---|---|
| Telemetry schema + collection path | DONE | none | `ranking_portability` schema/execute_cell, 44 tests | `research/ranking-portability-telemetry-20260901` @ `d252b0b` | Engineering | Done in parallel with Milestone 1 |
| Pilot-V2 smoke test (capability only) | PENDING | Milestone 2 | schema-valid smoke cells, `SCIENTIFIC_STATUS=FIXTURE_ONLY`/`SMOKE_ONLY` | not yet created | Engineering | No |
| Prelaunch freeze (hash every frozen input) | PENDING | smoke test passes | prelaunch freeze manifest | not yet created | Scientific | No |
| 18,720-cell execution (SLURM) | PENDING | prelaunch freeze | 18,720 cell result files | not yet created | Scientific | No |
| Matrix integrity validation | PENDING | execution complete | validation report | not yet created | Scientific | No |

## Milestone 4 — Ranking analyses

| Task | Status | Prerequisites | Expected output | Authoritative branch/file | Type | Parallel? |
|---|---|---|---|---|---|---|
| RQ1 cross-source ranking stability (Kendall tau, Spearman rho, top-k) | PENDING | Milestone 3 matrix | ranking tables + CIs | `docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md` §A (plan only) | Scientific | Can run in parallel with Milestone 5 once matrix exists |
| RQ2 temporal/provider/domain portability | PENDING | Milestone 3 matrix | temporal tau tables | same plan §D | Scientific | Yes |
| RQ4 mechanism-explanation regression | PENDING | Milestone 3 matrix + telemetry | logistic regression result | same plan §G | Scientific | Yes |
| Metric dependence (cross-metric tau) | PENDING | Milestone 3 matrix | metric-pair tau table | same plan §E (via `docs/STATISTICAL_ANALYSIS_PLAN.md` §E) | Scientific | Yes |

## Milestone 5 — Robustness / sample complexity / OOD

| Task | Status | Prerequisites | Expected output | Authoritative branch/file | Type | Parallel? |
|---|---|---|---|---|---|---|
| RQ5 sample complexity (subsampling ladder n∈{5,10,20,30,40}) | PENDING | Milestone 3 matrix | recovery-probability curves | plan §C | Scientific | Yes, with Milestone 4 |
| Robustness suite (high-fidelity subset, leave-one-source-out, etc.) | PENDING | Milestone 4 headline findings | robustness tables | plan §F | Scientific | Yes, after each Milestone 4 finding lands |

## Milestone 6 — Real-system validation

| Task | Status | Prerequisites | Expected output | Authoritative branch/file | Type | Parallel? |
|---|---|---|---|---|---|---|
| Case selection (objective rule: largest-effect reversal + one stable control) | PENDING | Milestone 4 RQ1/RQ2 results | frozen case list | plan §G | Scientific | No — needs real findings first |
| Real-vLLM measurement | PENDING | case selection | sign agreement / tau / reversal-reproduction stats | `docs/REAL_SYSTEM_VALIDATION_PLAN.md` (design only) | Engineering + Scientific | No |

## Milestone 7 — Public LSSP dataset

| Task | Status | Prerequisites | Expected output | Authoritative branch/file | Type | Parallel? |
|---|---|---|---|---|---|---|
| Dataset card, schema finalization | PENDING | Milestones 3-6 | HF dataset card | not yet created | Engineering | Can draft structure early (parallel-safe) |
| Publish to `SoroushVahidi/llm-serving-scheduler-portability` | **NOT YET PUBLISHED** | dataset card ready | live HF dataset | — | Engineering | No |

## Milestone 8 — Manuscript

| Task | Status | Prerequisites | Expected output | Type | Parallel? |
|---|---|---|---|---|---|
| Introduction / Related Work / Study Design drafts | READY_TO_DRAFT now | none | draft sections | Writing | **Yes — safe to start immediately** |
| Workload Corpus and Characterization | PARTIALLY_DRAFTABLE | integrate characterization sibling branch | draft section | Writing | Yes |
| Methodology (panel, telemetry, protocol) | READY_TO_DRAFT now | none | draft section | Writing | Yes |
| Results sections (6-9) | WAITING_FOR_RESULTS | Milestones 4-6 | draft sections | Writing | No |
| Limitations / Artifact / Conclusion | PARTIALLY_DRAFTABLE | Milestones 4-7 for final wording | draft sections | Writing | Partially |

## Milestone 9 — Submission / artifact evaluation

| Task | Status | Prerequisites | Type |
|---|---|---|---|
| Full reproducibility pass (`docs/REPRODUCIBILITY_CONTRACT.md`) | PENDING | Milestones 1-7 complete | Engineering |
| Artifact-evaluation packaging | PENDING | Milestone 7 (public dataset) | Engineering |
| Submission | PENDING | Milestone 8 (manuscript) complete | — |

## Organizational (non-scientific) task, any time

Integrate `research/workload-characterization-paper-result-20260901`'s
unique work into the active Stage-0/ranking-portability lineage (see
`docs/BRANCH_MAP.md`) — pure branch consolidation, safe to do in parallel
with any milestone above, must happen before Milestone 8's Workload
Corpus section is finalized.
