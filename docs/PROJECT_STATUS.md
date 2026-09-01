# LLM-Serving Scheduler Portability Benchmark — Project Status

Last verified: 2026-09-01
Verified against repository SHA: `d252b0b` (research/ranking-portability-telemetry-20260901), with an active in-progress child branch `research/ranking-portability-windows-20260901` not yet committed/pushed at verification time.

Current phase: **Phase 10 — Pilot-V2 40-window/source construction (ACTIVE)**

Current decision: no scientific decision pending; Stage-0 is closed (`STAGE0_NO_GO`, diagnosed `POLICY_PANEL_MECHANISM_MISMATCH`); Pilot-V2 is preregistered and its window layer is being built now.

Next action: retrieve and commit the completed 120-window manifest from the in-progress `research/ranking-portability-windows-20260901` build, then run its freeze/reproducibility/overlap-audit checks (do not start load calibration until that freeze is done).

**PROJECT_STATUS.md is the canonical mutable project-state summary.** Historical/frozen scientific documents (protocols, freeze docs, diagnostic reports) must never be edited merely to keep this file current — update *this* file instead. Update it whenever a major task completes; update `docs/PROJECT_ROADMAP.md` if the dependency plan changes materially; refresh `docs/BRANCH_MAP.md`/`docs/WORKTREE_AUDIT.md` when branches are created, superseded, or integrated.

## 1. Executive status

`main` is an intentionally empty skeleton (`.gitignore`, `LICENSE`, `README.md`, two `.gitkeep`s) — every real result lives on `research/*` branches, none merged yet. All work branches from a common bootstrap (`b7090b8`) into two sibling lineages that have **not been integrated with each other**: (a) workload characterization (`research/workload-characterization-paper-result-20260901`, final: `SEPARABILITY_RESULT_CONFIRMED_WITH_CAVEATS`) and (b) the Stage-0 → ranking-portability lineage (current tip `d252b0b`, plus the uncommitted, in-progress `research/ranking-portability-windows-20260901`). Stage-0 concluded `STAGE0_NO_GO` with a diagnosed, mechanism-level root cause; Pilot-V2 (a redesigned, mechanism-diverse, symmetric ranking-portability study) is fully preregistered and its 120-window data layer is being constructed against real acquired source data at the time of this audit.

## 2. Phase map

| Phase | Objective | Status | Authoritative branch/SHA | Evidence/artifact | Next dependency |
|---|---|---|---|---|---|
| 0 | Bootstrap / overlap audit vs. LLM-2026 & SIGMETRICS 2027 | DONE | `research/bootstrap-cross-workload-benchmark-20260831` @ `255caca`-`8650cdf` | `docs/OVERLAP_LEDGER.md`, `docs/CLAIM_BOUNDARIES.md` | — |
| 1 | Evidence/source independence | DONE | same, `docs/EVIDENCE_INDEPENDENCE_PLAN.md` | Azure-2024 = fully independent; BurstGPT/Bailian = independent windows from reused sources; TraceLab = unresolved (documented, not blocking) | — |
| 2 | Workload characterization | DONE | `research/workload-characterization-paper-result-20260901` @ `9435e87` (**sibling branch, not merged into the active lineage — see Branch Map**) | `docs/WORKLOAD_CHARACTERIZATION_PAPER_RESULT.md`: `SEPARABILITY_RESULT_CONFIRMED_WITH_CAVEATS` | Integrate into main lineage before manuscript finalization |
| 3 | Characterization paper-facing cleanup | DONE | same branch, `8709151` → `9435e87` | leakage-resistant, grouped-CV separability result | — |
| 4 | Stage-0 pilot preparation | DONE | `research/stage0-prerequisites-20260901` @ `23202e3`, harness at `de9f0a3` | real data acquired (Azure-2024/Bailian/BurstGPT), load calibration frozen, orchestration harness built | — |
| 5 | Stage-0 execution | DONE | `research/stage0-orchestration-prelaunch-20260901` @ `de9f0a3` | array 1213964, merge 1213965 (initially failed) | — |
| 6 | Zero-completion metric amendment/repair | DONE | `research/stage0-zero-completion-undefined-metrics-20260901` @ `848bae3` | `docs/STAGE0_ZERO_COMPLETION_METRIC_AMENDMENT_20260901.md`; final verdict **`STAGE0_NO_GO`** (Criterion 5 fails, BurstGPT 14.3% share) | — |
| 7 | BurstGPT diagnostic | DONE | `research/stage0-burstgpt-diagnostic-20260901` @ `5508e81` | `docs/STAGE0_BURSTGPT_DIAGNOSTIC.md`: **`POLICY_PANEL_MECHANISM_MISMATCH`** | — |
| 8 | Ranking-portability Pilot-V2 preregistration | DONE | `research/ranking-portability-pilot-v2-prereg-20260901` @ `edc4880` | 5 prereg docs (protocol, policy panel, analysis plan, metric definitions, manuscript contract) | — |
| 9 | Pilot-V2 telemetry implementation | DONE | `research/ranking-portability-telemetry-20260901` @ `d252b0b` | `docs/RANKING_PORTABILITY_TELEMETRY_IMPLEMENTATION.md`, 173→(129+44) tests passing | — |
| 10 | Pilot-V2 40-window/source construction | **ACTIVE** | `research/ranking-portability-windows-20260901` (branched from `d252b0b`, **uncommitted, unpushed**) | Extension-sampling algorithm implemented + unit-tested (17 tests, synthetic data only); real 120-window build against actual Azure-2024/Bailian/BurstGPT raw files **running on Wulver at time of audit** (BurstGPT phase complete, Azure-2024 phase in progress, Bailian pending) | Retrieve completed manifest, run freeze/overlap/reproducibility checks, commit + push |
| 11 | Six-region load calibration | PENDING | — | — | Phase 10 window freeze |
| 12 | Pilot-V2 smoke test | PENDING | — | — | Phase 11 |
| 13 | 18,720-cell Pilot-V2 execution | PENDING | — | — | Phase 12 |
| 14 | Ranking-portability analysis (RQ1/RQ2/RQ4) | PENDING | — | `docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md` (plan only) | Phase 13 |
| 15 | Sample complexity (RQ5) | PENDING | — | plan only | Phase 13 |
| 16 | Temporal/OOD analysis | PENDING | — | plan only | Phase 13 |
| 17 | Real-system validation (RQ6) | PENDING | — | `docs/REAL_SYSTEM_VALIDATION_PLAN.md` (design only) | Phase 14 results (case selection depends on them) |
| 18 | Public LSSP dataset release | PENDING — **NOT YET PUBLISHED** | — | — | Phases 13-17 |
| 19 | Manuscript | PARTIALLY DRAFTABLE | — | see §11 | Phases 14-17 for results sections |

## 3. Current scientific findings

- **Workload characterization**: sources are separable (RF 1.000 / logreg 0.987 / depth-3 tree ~0.975-0.980 under leakage-resistant, chronologically-blocked grouped CV), driven primarily by prompt/total-token-length descriptors, not a leakage artifact. Verdict: `SEPARABILITY_RESULT_CONFIRMED_WITH_CAVEATS`.
- **Stage-0 discriminability pilot**: final, closed result **`STAGE0_NO_GO`**. Criteria 1-4 pass comfortably (77.8%/86.7%/100% margins, no universal collapse); Criterion 5 fails — BurstGPT contributes only 14.3% of non-tied conditions vs. 42.9% each for Azure-2024/Bailian-Qwen (a 15% floor).
- **BurstGPT diagnostic**: root cause classified **`POLICY_PANEL_MECHANISM_MISMATCH`** — on BurstGPT's short-prompt, near-constant-output traffic, 5 of Stage-0's 6 policies become behaviorally identical (not a calibration or sample-size artifact; verified against both).
- **Pilot-V2**: **no scientific results exist yet.** Everything on `research/ranking-portability-*` branches to date is preregistration, telemetry infrastructure, and (in progress) window construction — no scheduler policy has been run against a real Pilot-V2 window.

## 4. Current study design (frozen, `docs/RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md` + companions)

- Dataset name: **LLM-Serving Scheduler Portability Benchmark**, short name **LSSP Benchmark** (repo/GitHub name remains `llm-serving-scheduler-robustness-benchmark` — not renamed, see §12).
- Sources: `azure_llm_2024`, `bailian_qwen`, `burstgpt` (3 primary; Azure-2023/TraceLab/ServeGen explicitly deferred/excluded from this pilot).
- Windows: 40/source (Stage-0's original 10/source retained verbatim as a strict, non-overlapping subset; 30 new/source drawn by a pinned-extension of the same deterministic rule).
- Load regions: 6, policy-independent (`LOW/PRE_KNEE/KNEE/POST_KNEE/OVERLOAD/HIGH_PRESSURE`), same `fifo`-referenced calibration rule as Stage-0, applied identically to every source.
- Policy panel: 13 executed (11 PRIMARY + 2 `STYLE_APPROXIMATION` robustness-only), reusing the pre-Stage-0-frozen `docs/POLICY_COMPARABILITY_AUDIT.md` panel verbatim.
- Repetitions: 2 (deterministic verification, not statistical power — simulator has no RNG).
- Telemetry: 7 mechanism-activation fields (queue depth, batch saturation, prefill/decode contention, KV occupancy, admission-control activations, preemption/reorder events, token-budget saturation), schema `ranking_portability_telemetry_v1`, required on every cell.
- Primary analyses: cross-source/temporal/metric ranking stability (Kendall tau, Spearman rho, top-1/top-3 overlap, pre-registered reversal effect-size threshold), sample complexity, mechanism-explanation regression — see `docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md`.
- Evaluability criteria explicitly do **not** require rank reversals or non-tied outcomes to exist — a fully stable-ranking result is a complete, valid outcome under this design.

## 5. Current branches

| Branch | SHA | Purpose | Status | Contains unique work? | Integration relationship |
|---|---|---|---|---|---|
| `main` | `6a82779` | Empty skeleton | HISTORICAL | No | Never touched |
| `research/bootstrap-cross-workload-benchmark-20260831` | `b7090b8` | Project bootstrap, overlap audit, Stage-0 window infra | HISTORICAL (ancestor) | No — fully contained in all downstream branches | Common ancestor of both lineages |
| `research/workload-separability-audit-20260901` | `8709151` | Separability diagnostic | SUPERSEDED | No — superseded by paper-result branch below | Ancestor of `workload-characterization-paper-result` |
| `research/workload-characterization-paper-result-20260901` | `9435e87` | Final characterization result | DONE, **unmerged sibling** | **Yes** — not present on the active Stage-0/ranking-portability lineage | Sibling of the active lineage from `b7090b8`; needs future integration |
| `research/stage0-prerequisites-20260901` | `23202e3` | Real data acquisition, load calibration bootstrap | HISTORICAL (ancestor) | No — fully contained downstream | Ancestor of Stage-0 orchestration |
| `research/stage0-orchestration-prelaunch-20260901` | `de9f0a3` | Stage-0 harness + real launch | HISTORICAL (ancestor) | No — fully contained downstream | Ancestor of metric-repair branch |
| `research/stage0-zero-completion-undefined-metrics-20260901` | `848bae3` | Metric repair + final `STAGE0_NO_GO` | HISTORICAL (ancestor) | No — fully contained downstream | Ancestor of diagnostic branch |
| `research/stage0-burstgpt-diagnostic-20260901` | `5508e81` | `POLICY_PANEL_MECHANISM_MISMATCH` diagnosis | HISTORICAL (ancestor) | No — fully contained downstream | Ancestor of prereg branch |
| `research/ranking-portability-pilot-v2-prereg-20260901` | `edc4880` | Pilot-V2 preregistration (5 docs) | HISTORICAL (ancestor) | No — fully contained downstream | Ancestor of telemetry branch |
| `research/ranking-portability-telemetry-20260901` | `d252b0b` | Telemetry schema + collection path | **ACTIVE (latest fully-committed)** | Yes | Base of the current audit branch and the in-progress windows branch |
| `research/ranking-portability-windows-20260901` | (local only, uncommitted) | 120-window construction | **ACTIVE, IN PROGRESS** | Yes (algorithm + tests done; real 120-window manifest generation running at audit time) | Child of `d252b0b`, not yet pushed |
| `research/project-state-audit-20260901` | (this branch) | This status audit | ACTIVE | Yes (this commit) | Child of `d252b0b` |

No branch has been merged to `main`. No branches were deleted or should be — `workload-separability-audit` and the Stage-0/telemetry ancestor branches remain the historical record even though their content is otherwise superseded/contained.

## 6. Active worktrees

| Path | Branch | Dirty? |
|---|---|---|
| `.../llm-serving-scheduler-robustness-benchmark` | `research/bootstrap-cross-workload-benchmark-20260831` | Yes — see §9 (all changes duplicate already-committed `stage0-prerequisites` content) |
| `.../llm-serving-scheduler-portability-telemetry` | `research/ranking-portability-telemetry-20260901` | No |
| `.../llm-serving-scheduler-ranking-portability-windows` | `research/ranking-portability-windows-20260901` | Yes — active in-progress work (algorithm code + tests, untracked, not yet committed) |
| `.../llm-serving-scheduler-robustness-ranking-portability-prereg` | `research/ranking-portability-pilot-v2-prereg-20260901` | No |
| `.../llm-serving-scheduler-robustness-stage0-burstgpt-diagnostic` | `research/stage0-burstgpt-diagnostic-20260901` | No |
| `.../llm-serving-scheduler-robustness-stage0-prelaunch` | `research/stage0-orchestration-prelaunch-20260901` | No (untracked `logs/` from the real SLURM run — operational, preserve) |
| `.../llm-serving-scheduler-robustness-stage0-prereqs` | `research/stage0-prerequisites-20260901` | No |
| `.../llm-serving-scheduler-robustness-stage0-repair` | `research/stage0-zero-completion-undefined-metrics-20260901` | Yes — one cosmetic uncommitted edit (`repair_sha` placeholder in a manifest-builder script default; see `docs/WORKTREE_AUDIT.md`) |
| `.../llm-serving-scheduler-project-state-audit` (this one) | `research/project-state-audit-20260901` | Active work in progress (this commit) |

Full detail in `docs/WORKTREE_AUDIT.md`.

## 7. Pending work (dependency order)

1. Retrieve + commit the completed Pilot-V2 120-window manifest (in progress on Wulver).
2. Window freeze: reproducibility check (rebuild twice, compare content hash), overlap audit write-up, `docs/RANKING_PORTABILITY_WINDOW_FREEZE.md`.
3. Six-region, policy-independent (`fifo`-referenced) load calibration for the 120 frozen windows.
4. Pilot-V2 smoke test (small-scale, capability-only, on real windows, no comparative analysis).
5. Prelaunch freeze (hash everything, matching Stage-0's own prelaunch-freeze convention).
6. 18,720-cell Pilot-V2 execution.
7. Matrix integrity validation.
8. Ranking analyses (RQ1/RQ2/RQ4), sample complexity (RQ5), temporal/OOD analysis.
9. Real-system validation (RQ6) — case selection depends on step 8's actual results.
10. Public LSSP dataset release.
11. Manuscript finalization.
12. **Separately**: integrate the workload-characterization sibling branch's results into the active lineage before manuscript finalization (currently unmerged, see §5).

## 8. Parallel-safe work

- Manuscript Introduction / Related Work / Study Design drafting (methodology is frozen; no results needed).
- Artifact/reproducibility documentation.
- Literature collection for RQ6/real-system validation framing.
- Integrating the characterization sibling branch's docs into the active lineage (pure documentation consolidation, no new science).

## 9. Known caveats / unresolved issues

- TraceLab's independence from prior HF releases is unverifiable from public artifacts; it is excluded from Pilot-V2 by design (adapter doesn't exist), not by outcome.
- The workload-characterization lineage and the Stage-0/ranking-portability lineage are unmerged siblings (see §5) — a future integration step is required, purely organizational, not scientific.
- `admission_control_activations` telemetry uses a documented capacity-only approximation (`max_active_sequences`, not full `max_batch_tokens`/`max_kv_tokens` feasibility) — disclosed in `docs/RANKING_PORTABILITY_TELEMETRY_IMPLEMENTATION.md`, not yet a blocker.

## 10. Publication boundaries

- `docs/OVERLAP_LEDGER.md` / `docs/CLAIM_BOUNDARIES.md`: LLM-2026's SBS/VBS/exploitability/selector/decision-criticality concepts and its `public_replay_load_scaling_v1/v2` 60-window/`{1..128}` load grid are `PROHIBITED_OVERLAP` — never restated as this project's result.
- `docs/EVIDENCE_INDEPENDENCE_PLAN.md`: Azure-2024 is fully independent; BurstGPT/Bailian windows must remain disjoint from LLM-2026's 60 canonical windows (verified by construction, not by recovered ground truth for BurstGPT — disclosed, not overclaimed).

## 11. Manuscript status

| Section | Status | Evidence available? | Remaining dependency |
|---|---|---|---|
| Abstract | WAITING_FOR_RESULTS | No | Phases 13-17 |
| 1 Introduction | READY_TO_DRAFT | N/A | None |
| 2 Related Work | READY_TO_DRAFT | Yes (`docs/RELATED_WORK_NOVELTY_AUDIT.md`) | None |
| 3 Study Design | READY_TO_DRAFT | Yes (Pilot-V2 protocol frozen) | None |
| 4 Workload Corpus and Characterization | PARTIALLY_DRAFTABLE | Yes (characterization result, on sibling branch) | Integrate sibling branch |
| 5 Scheduler Benchmark Methodology | READY_TO_DRAFT | Yes (policy panel + telemetry docs) | None |
| 6 Cross-Workload Scheduler Results | WAITING_FOR_RESULTS | No | Phase 14 |
| 7 Benchmark Sample Complexity | WAITING_FOR_RESULTS | No | Phase 15 |
| 8 Real-System Validation | WAITING_FOR_RESULTS | No | Phase 17 |
| 9 Discussion | WAITING_FOR_RESULTS | Partial (Stage-0 motivation only) | Phases 14-17 |
| 10 Limitations | PARTIALLY_DRAFTABLE | Yes (TraceLab caveat, admission-control approximation, etc.) | Update after Phases 14-17 |
| 11 Artifact/Reproducibility | PARTIALLY_DRAFTABLE | Yes (reproducibility contract exists) | Phase 18 (dataset release) |
| 12 Conclusion | WAITING_FOR_RESULTS | No | All prior phases |

## 12. Dataset/artifact status

- Canonical name: **LLM-Serving Scheduler Portability Benchmark**
- Short name: **LSSP Benchmark**
- Proposed HF slug: `SoroushVahidi/llm-serving-scheduler-portability`
- Publication state: **NOT YET PUBLISHED**
- Terminology note: the GitHub repository name (`llm-serving-scheduler-robustness-benchmark`) and this project's internal doc titles ("Stage-0 discriminability pilot," "ranking-portability pilot") predate the LSSP naming decision and are **not** renamed by this audit — GitHub repo renaming was explicitly out of scope. `SoroushVahidi/llm-serving-scheduler-baselines` (an existing, separate HF dataset referenced in `docs/OVERLAP_LEDGER.md`/`docs/TRACELAB_PROVENANCE_RESOLUTION.md`) is a **different, pre-existing artifact** from a different project lineage — not to be confused with the future LSSP release.

## 13. Immediate next action

Retrieve the Pilot-V2 120-window manifest currently being generated on Wulver (`research/ranking-portability-windows-20260901`), run its data-quality/overlap/reproducibility checks, and commit + push the window freeze — this is the single blocking prerequisite for Phase 11 (load calibration).
