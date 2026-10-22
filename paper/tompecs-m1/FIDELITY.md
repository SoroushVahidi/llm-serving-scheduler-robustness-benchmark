# Fidelity boundary and manuscript consequences

Pinned PR metadata is in `evidence/pr-stack.json`. Review sources were read in their existing worktrees; their original files and evidence packages are unchanged.

| Evidence | Verified boundary | Manuscript consequence |
|---|---|---|
| Historical simulator / frozen v1.1.0 | Fixed-step service, policy-specific shadow state, simplified demand/KV accounting; deterministic outputs | Say “historical simulator implementation,” retain policy IDs as data keys. No native equivalence from `faithful` suffix. |
| MGPU00 `4332b08…:docs/mgpu00/HISTORICAL_AUDIT.md` | All 240 legacy RQ6 allocations were A100 10 GB MIG, 9.5 GiB CUDA-visible; class transport missing, synthetic scheduling clock, replay/admission issues | Preserve legacy observations, remove claim that faithful native reversal transfer or failure-to-transfer was established. Do not attribute discrepancy uniquely to simulator fidelity. |
| PR #4 `efc5243…:docs/fidelity-review-20261021/REPORT.md` | Partial-prefill, native sampling/admission/KV/recompute differences; request-ID/KV guards; 40/40 Azure and Bailian median prompts >256 | Long-trace coverage not validated by bounded fixtures; no rank effect inferred from source defects. |
| PR #5 `ee18686…:docs/serving-contract/v2.0.0-draft.1/` | Prospective versioned adaptation, unresolved semantics/trace/distributed decisions | Future contract cannot relabel old simulator or physical evidence. |
| PR #6 `810b987…:docs/serving-contract/p1-0.1.0/` | CPU request ledger separates plan/ACK; independent referee; synthetic evidence | CPU conformance is implementation evidence, not GPU output/timing. |
| PR #7 `df4b13d…:docs/serving-contract/p2a-0.1.0/` | Actual native CPU scheduler can enlarge, add or reorder proposed work; native counters optimistic | A proposed policy plan cannot stand in for observed executed work. |
| PR #8 `f1a22fc…:docs/serving-contract/p2b-0.1.0/` | CPU control hook, partial S02 profile; waiting-before-resident plans rejected; no atomic native rollback; general pressure/distributed still disabled | No complete SLAI, hardware or TP2/DP2 claim. No simulation or fabricated ACK presented as physical runner evidence. |
| MGPU03/MGPU05/MGPU06 | Bounded MGPU03 smoke distinct from legacy RQ6; new measurement instrumentation CPU-validated, first-pair physical gate outstanding in retained reports | Mention engineering smoke only as bounded context. No use as evidence of realistic traces, ranking reversals or repeated physical measurements. No new status query/experiment in M1. |

These engineering observations constrain interpretation; they do not prove every historical cell exercised a defect, quantify the effect on rankings, or supply corrected numerical outcomes. A future corrected simulator/native study needs separate versioned evidence and authorization. Manuscript Section 10 states these boundaries without turning the paper into a report of the engineering PR stack.
