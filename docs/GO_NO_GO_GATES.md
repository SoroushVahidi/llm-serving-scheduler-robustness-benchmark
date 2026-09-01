# GO_NO_GO_GATES.md

Status as of this bootstrap (2026-08-31); Gate D updated 2026-09-01 with the
real Stage-0 pilot's result (array 1213964, repair branch
`research/stage0-zero-completion-undefined-metrics-20260901`, repair SHA
`43277e0`). Re-evaluate remaining gates before Stage 2.

| Gate | Criterion | Status | Notes |
|---|---|---|---|
| **A — overlap** | No planned headline contribution duplicates LLM 2026 or SIGMETRICS. | **`PASS_WITH_CONSTRAINTS`** (resolved 2026-08-31) | LLM 2026's manuscript and its `PUBLIC_REPLAY_LOAD_SCALING_V1/V2` design were independently inspected. Resolution constraints (all recorded in `docs/OVERLAP_LEDGER.md` and `docs/CLAIM_BOUNDARIES.md`, enforced going forward): (1) `public_replay_load_scaling_v1/v2` — same 60 canonical windows (20 BurstGPT + 20 Azure-2023-conversation + 20 Azure-2023-code, 200 req/window), load grid `{1,2,4,8,16,32,64,128}`, 8-policy Pext portfolio, ANWG/SBS-VBS diagnostics — is `PRIOR_RESULT_REFERENCE_ONLY`, never restated as new evidence. (2) This project's own window sets must be independently constructed, never the same 60 windows (`docs/EVIDENCE_INDEPENDENCE_PLAN.md`). (3) Load-level dependence is demoted from a headline RQ to a secondary robustness/sensitivity analysis (`docs/RESEARCH_QUESTIONS.md`), using this project's own frozen calibration protocol, never the `{1,...,128}` grid. (4) Prohibited-claims list extended accordingly (`docs/CLAIM_BOUNDARIES.md`). Remaining caveat: this project's own repo-level audit could confirm v1's design parameters and v1's own recorded `INCONCLUSIVE` verdict, but could not locate a full v2 grid-sweep summary artifact locally to independently re-derive the "non-separating" conclusion byte-for-byte — that conclusion rests on direct manuscript inspection, disclosed as such in `docs/OVERLAP_LEDGER.md`. |
| **B — workload breadth** | ≥4 independent external workload families usable legally and scientifically. | **PENDING** | Four sources now have adapters ported and smoke-tested in this repo: BurstGPT, Azure 2023, Azure 2024, and (as of this update) **Bailian/Qwen** (`docs/PROVENANCE.md`, `tests/test_bailian_adapter.py`). Per `docs/EVIDENCE_INDEPENDENCE_PLAN.md`, Azure 2024 and Bailian/Qwen are fully independent of prior consumption; BurstGPT and Azure 2023 require this project to draw different windows than LLM 2026's 60. TraceLab's adapter does not exist yet and its independence from the existing HF 512-window sweep cannot be fully verified (`docs/TRACELAB_PROVENANCE_RESOLUTION.md`). ServeGen is `OPTIONAL` and explicitly does not count as a distinct provider (shares Bailian's platform, `docs/SERVEGEN_ADOPTION_AUDIT.md`). Gate remains PENDING: 4 adapters exist and 2 are confirmed-independent sources, but the "≥4 *independent*" bar needs either TraceLab's independence resolved or a 4th fully-independent source identified — BurstGPT/Azure-2023 count only if this project's own window sampling is confirmed non-overlapping with LLM 2026's 60 at execution time, not merely by design intent. |
| **C — scheduler breadth** | ≥8 scientifically comparable policies, including multiple strong external baselines. | **PASS** | 13-policy primary panel (`docs/POLICY_COMPARABILITY_AUDIT.md`), including faithful reimplementations of vLLM (two eras), Sarathi, and SLAI-style, plus classical/fairness/KV-aware baselines. All 13 import and execute successfully in this bootstrap's smoke tests. |
| **D — discriminability** | Frozen load protocol yields nontrivial scheduler differentiation without post-hoc load cherry-picking. | **`STAGE0_NO_GO`** (resolved 2026-09-01) | Real 1,080-cell pilot executed (array 1213964, all cells valid after `docs/STAGE0_ZERO_COMPLETION_METRIC_AMENDMENT_20260901.md`'s schema repair — 0 cells missing/failed/duplicated). Criteria 1-4 **PASS** (77.8% non-tied triples, 86.7% non-tied windows, no universal collapse, 100% of non-tied cells show meaningful metric variation). Criterion 5 **FAILS**: BurstGPT contributes only 14.3% of non-tied (source,window,load-region) cells, just under the 15% floor (bailian_qwen and azure_llm_2024 each ~42.9%) — one source (BurstGPT) is discriminatively underrepresented relative to the other two. Verdict is robust to the slo_violation_rate zero-completion convention (UNDEFINED/FORCE_ZERO/FORCE_ONE all agree: `STAGE0_NO_GO`) — Criterion 4 is unaffected by that ambiguity in this dataset. Per `docs/STAGE0_DISCRIMINABILITY_PROTOCOL.md`'s own text, this is reported as a genuine partial failure (BurstGPT under-discriminates), not softened. |
| **E — ranking phenomenon** | Measurable cross-source/load/metric ranking instability OR a scientifically useful stability finding with sufficiently tight uncertainty. | **NOT YET EVALUATED** | Not automatically advanced by any Stage-0 outcome. Since Gate D resolved `STAGE0_NO_GO` (not GO), the confirmatory sweep that would resolve this gate should not proceed under the current design — see Gate D's Criterion-5 finding first. Exploratory rank-portability analysis (Kendall tau/Spearman/rank-reversal across sources) is explicitly out of Stage 0's scope per `analyzer.py`'s own docstring ("that is Stage 2/3's job, on the full sweep, not this pilot") and has no existing frozen implementation in this codebase; none was written in this repair session to avoid inventing unreviewed post-outcome methodology. |
| **F — real validation** | A targeted native/vLLM experiment is feasible for representative rank-order claims. | **PASS (feasibility only)** | `real_llm/calibration_common.py` reused successfully (imports cleanly); `docs/REAL_SYSTEM_VALIDATION_PLAN.md` designed. Feasibility, not execution, is what this gate asks for at this stage. |

## Overall (updated 2026-09-01)

**No gate is falsely marked PASS to manufacture a positive story.** Gate A is
`PASS_WITH_CONSTRAINTS` (real overlap risk found and resolved with binding
constraints, not waved away); Gate C and Gate F (feasibility) pass; Gate B
remains PENDING (unchanged by this update — this repair session produced no
new source-independence evidence); **Gate D is now resolved as
`STAGE0_NO_GO`** (real pilot executed and analyzed; Criterion 5 genuinely
fails, not softened); Gate E cannot be evaluated before a redesigned Stage 0
addresses Gate D's finding.

**SAFE_TO_LAUNCH_STAGE0 = ALREADY LAUNCHED AND RESOLVED (2026-09-01),
NO-GO.** The real 1,080-cell pilot (array 1213964) ran to completion; a
schema bug that incorrectly rejected 12 legitimate zero-completion cells was
identified and repaired
(`docs/STAGE0_ZERO_COMPLETION_METRIC_AMENDMENT_20260901.md`, branch
`research/stage0-zero-completion-undefined-metrics-20260901`) without
altering any frozen scientific input or the analyzer itself. The frozen
five-criterion analyzer returned `STAGE0_NO_GO` (Criterion 5: BurstGPT
under-discriminates at 14.3% of non-tied cells, vs. a 15% floor), robust to
the one metric-definition sensitivity check this repair required. Per
`docs/STAGE0_DISCRIMINABILITY_PROTOCOL.md`'s own stated policy, this is not
a manufactured positive story: **do not proceed to the confirmatory
campaign under the current design.** The concrete next step is to address
BurstGPT's discriminability shortfall (e.g., different/additional BurstGPT
windows or load regions) before re-attempting Stage 0 — see the Next
Recommended Query below.
