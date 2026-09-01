# GO_NO_GO_GATES.md

Status as of this bootstrap (2026-08-31). Re-evaluate before Stage 2.

| Gate | Criterion | Status | Notes |
|---|---|---|---|
| **A — overlap** | No planned headline contribution duplicates LLM 2026 or SIGMETRICS. | **`PASS_WITH_CONSTRAINTS`** (resolved 2026-08-31) | LLM 2026's manuscript and its `PUBLIC_REPLAY_LOAD_SCALING_V1/V2` design were independently inspected. Resolution constraints (all recorded in `docs/OVERLAP_LEDGER.md` and `docs/CLAIM_BOUNDARIES.md`, enforced going forward): (1) `public_replay_load_scaling_v1/v2` — same 60 canonical windows (20 BurstGPT + 20 Azure-2023-conversation + 20 Azure-2023-code, 200 req/window), load grid `{1,2,4,8,16,32,64,128}`, 8-policy Pext portfolio, ANWG/SBS-VBS diagnostics — is `PRIOR_RESULT_REFERENCE_ONLY`, never restated as new evidence. (2) This project's own window sets must be independently constructed, never the same 60 windows (`docs/EVIDENCE_INDEPENDENCE_PLAN.md`). (3) Load-level dependence is demoted from a headline RQ to a secondary robustness/sensitivity analysis (`docs/RESEARCH_QUESTIONS.md`), using this project's own frozen calibration protocol, never the `{1,...,128}` grid. (4) Prohibited-claims list extended accordingly (`docs/CLAIM_BOUNDARIES.md`). Remaining caveat: this project's own repo-level audit could confirm v1's design parameters and v1's own recorded `INCONCLUSIVE` verdict, but could not locate a full v2 grid-sweep summary artifact locally to independently re-derive the "non-separating" conclusion byte-for-byte — that conclusion rests on direct manuscript inspection, disclosed as such in `docs/OVERLAP_LEDGER.md`. |
| **B — workload breadth** | ≥4 independent external workload families usable legally and scientifically. | **PENDING** | Four sources now have adapters ported and smoke-tested in this repo: BurstGPT, Azure 2023, Azure 2024, and (as of this update) **Bailian/Qwen** (`docs/PROVENANCE.md`, `tests/test_bailian_adapter.py`). Per `docs/EVIDENCE_INDEPENDENCE_PLAN.md`, Azure 2024 and Bailian/Qwen are fully independent of prior consumption; BurstGPT and Azure 2023 require this project to draw different windows than LLM 2026's 60. TraceLab's adapter does not exist yet and its independence from the existing HF 512-window sweep cannot be fully verified (`docs/TRACELAB_PROVENANCE_RESOLUTION.md`). ServeGen is `OPTIONAL` and explicitly does not count as a distinct provider (shares Bailian's platform, `docs/SERVEGEN_ADOPTION_AUDIT.md`). Gate remains PENDING: 4 adapters exist and 2 are confirmed-independent sources, but the "≥4 *independent*" bar needs either TraceLab's independence resolved or a 4th fully-independent source identified — BurstGPT/Azure-2023 count only if this project's own window sampling is confirmed non-overlapping with LLM 2026's 60 at execution time, not merely by design intent. |
| **C — scheduler breadth** | ≥8 scientifically comparable policies, including multiple strong external baselines. | **PASS** | 13-policy primary panel (`docs/POLICY_COMPARABILITY_AUDIT.md`), including faithful reimplementations of vLLM (two eras), Sarathi, and SLAI-style, plus classical/fairness/KV-aware baselines. All 13 import and execute successfully in this bootstrap's smoke tests. |
| **D — discriminability** | Frozen load protocol yields nontrivial scheduler differentiation without post-hoc load cherry-picking. | **PENDING** | `docs/LOAD_CALIBRATION_PROTOCOL.md` is designed and pilot-tested at the smoke-test level (procedure runs, terminates). `docs/STAGE0_DISCRIMINABILITY_PROTOCOL.md` now defines the exact pilot (3 sources × 10 windows × 3 load regions × 6 policies, 1,080 cells) and pre-registered GO/NO-GO numerical criteria that will resolve this gate — **not yet launched**. |
| **E — ranking phenomenon** | Measurable cross-source/load/metric ranking instability OR a scientifically useful stability finding with sufficiently tight uncertainty. | **NOT YET EVALUATED** | No confirmatory sweep has been run. Cannot be assessed until Stage 2/3. |
| **F — real validation** | A targeted native/vLLM experiment is feasible for representative rank-order claims. | **PASS (feasibility only)** | `real_llm/calibration_common.py` reused successfully (imports cleanly); `docs/REAL_SYSTEM_VALIDATION_PLAN.md` designed. Feasibility, not execution, is what this gate asks for at this stage. |

## Overall (updated 2026-08-31)

**No gate is falsely marked PASS to manufacture a positive story.** Gate A is
now `PASS_WITH_CONSTRAINTS` (real overlap risk found and resolved with
binding constraints, not waved away); Gate C and Gate F (feasibility) pass;
Gates B and D are PENDING with concrete, named next actions (Gate D's next
action is now a fully specified pilot with pre-registered GO/NO-GO
thresholds, `docs/STAGE0_DISCRIMINABILITY_PROTOCOL.md`); Gate E cannot be
evaluated before Stage 2/3 exist.

**SAFE_TO_LAUNCH_STAGE0 = NO.** Stage 0's *discriminability pilot* itself
(`docs/STAGE0_DISCRIMINABILITY_PROTOCOL.md`) is fully designed and could be
launched, but two prerequisites the pilot's own design depends on are not
yet done: (1) BurstGPT's "different, non-overlapping window sample" must be
drawn by an actually-implemented, documented sampling rule, not just
described in prose — this is a small remaining coding task, not a design
gap; (2) real data has not been acquired for any of the three pilot sources
(Azure 2024, Bailian/Qwen, BurstGPT) — this bootstrap worked only against
small synthetic fixtures. Both are mechanical next steps, not open research
or overlap questions — see `docs/EXPERIMENT_CAMPAIGN_PLAN.md` Stage 0 and
the Next Recommended Query below.
