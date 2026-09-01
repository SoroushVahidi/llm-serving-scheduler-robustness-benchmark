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
| Load-dependent rank reversal | `NEEDS_REVIEW` — **highest overlap risk in this ledger.** | `llmserveopt/policy_separation/public_replay_load_scaling_v1.py` and its bugfix rerun `_v2.py` already run public-trace-replay windows through a fixed 8-policy portfolio across a preregistered load-factor grid and report scheduler differentiation under load, explicitly to support LLM 2026's decision-criticality / exploitability argument ("addresses the external-validity criticism that public_trace_replay_v1 is effectively unloaded... and therefore cannot expose scheduler differences"). This project's RQ2/RQ4 must (a) use an independently designed load-calibration protocol (`docs/LOAD_CALIBRATION_PROTOCOL.md`) rather than reusing that grid or its results, (b) frame the contribution as ranking-stability/robustness (Kendall tau, rank-reversal rate, pre-registered stats across LOW/PRE_KNEE/KNEE/OVERLOAD) rather than "headroom that a selector could exploit," and (c) never cite `public_replay_load_scaling_*` result numbers as this project's own evidence. Until a person familiar with the LLM 2026 manuscript's final claims confirms no headline overlap, treat this row as `NEEDS_REVIEW`, not cleared. |
| Metric-dependent rank reversal | `NEW_CANDIDATE` | Not examined as a formal RQ in either existing manuscript (their metric sets are narrower and tied to utility/decision-criticality, not a cross-metric robustness study). |
| Sample complexity of scheduler rankings | `NEW_CANDIDATE` | Not present in either existing manuscript or the HF dataset card. |
| Workload descriptors predicting rank reversal | `NEW_CANDIDATE` | Framed here as offline/explanatory only (see `docs/CLAIM_BOUNDARIES.md`) — must not become an online selector, which would collide with LLM 2026's selector line. |
| Synthetic-to-real ranking transfer | `NEW_CANDIDATE` | Not a named RQ in either existing manuscript. |

## Verdict at bootstrap time

Six of eight target `NEW_CANDIDATE` contribution areas are clear. **One row —
load-dependent rank reversal — is a genuine, non-trivial overlap risk** with
the LLM 2026 manuscript's supporting evidence and must be resolved (by reading
the current LLM 2026 draft's actual claim list, not just the code) before any
confirmatory sweep on this axis. This should be Go/No-Go Gate A's first
checklist item (`docs/GO_NO_GO_GATES.md`).
