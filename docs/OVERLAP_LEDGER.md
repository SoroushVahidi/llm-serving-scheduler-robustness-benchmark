# OVERLAP_LEDGER.md

Compares this project's candidate contributions against the three existing
manuscript lines and the seed Hugging Face dataset. Classification values:

- `NEW_CANDIDATE` — plausible new headline contribution for this paper.
- `PRIOR_RESULT_REFERENCE_ONLY` — an existing finding we may cite, never restate as new.
- `REUSED_INFRASTRUCTURE` — code/data machinery reused; carries no scientific claim.
- `PROHIBITED_OVERLAP` — must not become a headline claim here under any framing.
- `NEEDS_REVIEW` — insufficiently verified at bootstrap time; treat as `PROHIBITED_OVERLAP` until resolved.

Sources compared: (1) LLM 2026 — *The Exploitability Gap in LLM-Serving
Scheduler Portfolios* (`llm-serving-heuristic-evolution`); (2) SIGMETRICS 2027 —
module-intervention manuscript (`llm-serving-module-intervention-benchmark`);
(3) HF dataset `SoroushVahidi/llm-serving-scheduler-baselines`; (4) this
proposed paper.

| Concept | Classification | Notes |
|---|---|---|
| Whole-policy scheduler comparison (many policies, standard metrics) | `REUSED_INFRASTRUCTURE` | The *mechanism* of running N policies on a trace and comparing metrics is common ground across all three lines; not itself a claim. |
| Scheduler complementarity | `PROHIBITED_OVERLAP` | LLM 2026 headline concept. |
| SBS/VBS (single-best-scheduler / virtual-best-scheduler headroom) | `PROHIBITED_OVERLAP` | LLM 2026 headline concept. |
| Selector / regret | `PROHIBITED_OVERLAP` | LLM 2026 headline concept (adaptive selector evaluation, selector regret). |
| Exploitability gap | `PROHIBITED_OVERLAP` | LLM 2026's title concept. |
| Decision criticality | `PROHIBITED_OVERLAP` | LLM 2026 headline concept (`analysis/decision_criticality_*`). |
| Policy synthesis / composition | `PROHIBITED_OVERLAP` | LLM 2026 headline concept (`composition/`, `policies/{genome,portfolio_gp,structural_synthesis}.py`). |
| Module intervention (module-slot causal attribution) | `PROHIBITED_OVERLAP` | SIGMETRICS 2027 headline concept. |
| Public trace replay (mechanism: replaying BurstGPT/Azure/Bailian/Mooncake through the simulator) | `REUSED_INFRASTRUCTURE` | The *ingestion/replay machinery* is legitimate shared infrastructure (see `docs/PROVENANCE.md`). The specific *finding* is separately classified below. |
| TraceLab OOD | `NEEDS_REVIEW` | `llmserveopt/selector/dataset_v2/workload_sources.py` (as of the audited SHA) marks TraceLab `acquired=False` / "recommended for a later acquisition pass." But the HF seed dataset already ships a `tracelab_scheduler_ood_policy_sweep` config (13.8K rows, added per the dataset's `24 Aug 2026` update). **This is a real discrepancy between code-level documentation and the released dataset artifact** — do not assume either source is current. Before using TraceLab as an "already validated" OOD source for this project, independently re-inspect the actual `tracelab_scheduler_ood_policy_sweep` schema/provenance in the HF dataset rather than trusting the source-manifest comment. Until that inspection happens, treat any TraceLab-derived finding as provisional. |
| BurstGPT | `REUSED_INFRASTRUCTURE` | Ingestion adapter reused (`docs/PROVENANCE.md`); using it as one of this project's independent workload sources is a legitimate, non-overlapping use. |
| Azure 2023 | `REUSED_INFRASTRUCTURE` | Same as above. |
| Azure 2024 | `REUSED_INFRASTRUCTURE` | Same as above; treat 2023 and 2024 as **two distinct sources** for cross-source/temporal analysis, not one "Azure" source. |
| Bailian/Qwen | `REUSED_INFRASTRUCTURE` | Loader exists in LLM 2026 repo (`workloads/bailian.py`); not yet ported here (see `docs/DATA_LICENSE_AUDIT.md`), but the *concept* of using it as an independent source is not owned by any existing manuscript. |
| Synthetic stress workloads | `REUSED_INFRASTRUCTURE` | Generator code reused (`workloads/synthetic.py`); LLM 2026 uses synthetic stress families for portfolio/selector evaluation, but "synthetic vs. real ranking transfer" as a formal RQ (RQ3 here) is not their framing. |
| Real-system validation (real vLLM) | `REUSED_INFRASTRUCTURE` for the *harness*; `NEW_CANDIDATE` for *this project's specific question* | LLM 2026 has its own real-vLLM validation results (`real_llm/`) supporting its own selector/portfolio claims — those specific results are `PROHIBITED_OVERLAP` to restate. This project's RQ6 ("do simulated rank reversals reproduce on real vLLM") is a differently-scoped question (relative-ranking / rank-reversal reproduction, not selector validation) and may reuse the measurement *harness* only — see `docs/REAL_SYSTEM_VALIDATION_PLAN.md`. |
| Cross-source rank stability | `NEW_CANDIDATE` | Not the framing of either existing manuscript. **Caveat:** see the "load-dependent rank reversal" row below — must be built as an independent, pre-registered analysis, not a re-labeling of `public_replay_load_scaling_v1/v2`. |
| Temporal rank stability | `NEW_CANDIDATE` | Same caveat. |
| Load-dependent rank reversal (as an LLM 2026 *result*) | `PRIOR_RESULT_REFERENCE_ONLY` — **resolved 2026-08-31, `PASS_WITH_CONSTRAINTS`; see `docs/GO_NO_GO_GATES.md` Gate A.** | Independently inspected against the current LLM 2026 manuscript and the frozen `PUBLIC_REPLAY_LOAD_SCALING_V1`/`V2` design (`docs/design/PUBLIC_REPLAY_LOAD_SCALING_V1.md`, `V2.md`, `experiments/public_replay_load_scaling_v1/summary.json`). Confirmed exact parameters: the **same 60 canonical public-trace windows** used by `public_trace_replay_v1` (20 BurstGPT + 20 Azure-2023-conversation + 20 Azure-2023-code, `WINDOW_SIZE = 200` requests/window, unresampled across v1→v2); the preregistered load-factor grid `{1, 2, 4, 8, 16, 32, 64, 128}`; the 8-policy "Pext" portfolio (6 native P6 baselines + `official_vtc_joint_token_budget_remap` + `vllm_style_continuous_batching`); primary metric ANWG plus per-window SBS/VBS and VBS−SBS headroom diagnostics (`llmserveopt.analysis.public_trace_replay_v1_analysis`). **What this project's own repo-level audit could independently verify:** v1's locally-recorded final verdict was `PUBLIC_LOAD_SCALING_INCONCLUSIVE` (a simulator-harness bug capped simulated wall-clock time independent of λ, corrupting 6.67% of cells — see `PUBLIC_REPLAY_LOAD_SCALING_V2.md` §1); v2's only artifact visible in this repo at audit time is a passing λ=1 reproduction gate (`lambda1_gate_result.json`, 480/480 cells consistent, no full-grid summary file present locally). **The manuscript-level conclusion that the corrected sweep is reported as non-separating under LLM 2026's own objective is taken on the strength of the direct manuscript inspection performed for this resolution, not independently re-derived from local repo artifacts** — this project could not itself locate a v2 full-grid summary file to check that claim byte-for-byte. Given that caveat, this row is `PRIOR_RESULT_REFERENCE_ONLY`: citable as background/motivation, never restated as this project's own finding, and the exact 60-window/load-grid design must not be reused as a "new" experiment (see `docs/CLAIM_BOUNDARIES.md` and `docs/EVIDENCE_INDEPENDENCE_PLAN.md`). |
| Load-dependent rank reversal (as this project's own RQ, using independent windows/grid) | `NEW_CANDIDATE`, demoted to secondary analysis | Per the Gate A resolution, this axis is no longer a headline RQ — see `docs/RESEARCH_QUESTIONS.md` (load-level dependence moved to a secondary robustness/sensitivity analysis, not RQ2) and `docs/STAGE0_DISCRIMINABILITY_PROTOCOL.md`. Must use `docs/LOAD_CALIBRATION_PROTOCOL.md`'s independently frozen calibration, never the `{1,2,...,128}` grid, and must use windows established as independent per `docs/EVIDENCE_INDEPENDENCE_PLAN.md`. |
| Metric-dependent rank reversal | `NEW_CANDIDATE` | Not examined as a formal RQ in either existing manuscript (their metric sets are narrower and tied to utility/decision-criticality, not a cross-metric robustness study). |
| Sample complexity of scheduler rankings | `NEW_CANDIDATE` | Not present in either existing manuscript or the HF dataset card. |
| Workload descriptors predicting rank reversal | `NEW_CANDIDATE` | Framed here as offline/explanatory only (see `docs/CLAIM_BOUNDARIES.md`) — must not become an online selector, which would collide with LLM 2026's selector line. |
| Synthetic-to-real ranking transfer | `NEW_CANDIDATE` | Not a named RQ in either existing manuscript. |

## Verdict at bootstrap time (updated 2026-08-31)

Six of eight target `NEW_CANDIDATE` contribution areas were clear from the
start. The seventh — load-dependent rank reversal — has now been resolved as
**`PASS_WITH_CONSTRAINTS`** (Gate A, `docs/GO_NO_GO_GATES.md`): LLM 2026's
`public_replay_load_scaling_v1/v2` experiment and its exact 60-window/
load-grid/8-policy design are `PRIOR_RESULT_REFERENCE_ONLY`; this project may
study load dependence only as a *secondary* robustness/sensitivity analysis
(`docs/RESEARCH_QUESTIONS.md`), on independently-established windows
(`docs/EVIDENCE_INDEPENDENCE_PLAN.md`) and an independently frozen
calibration protocol (`docs/LOAD_CALIBRATION_PROTOCOL.md`), never by
reproducing or re-citing the old 60-window sweep as new evidence.
