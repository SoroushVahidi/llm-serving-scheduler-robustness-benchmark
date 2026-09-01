# RANKING_PORTABILITY_POLICY_PANEL.md

Policy panel for `docs/RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md`. Adopts
`docs/POLICY_COMPARABILITY_AUDIT.md`'s PRIMARY panel and fidelity taxonomy
**verbatim** — both frozen 2026-08-31, one full day before Stage 0 ran
(2026-09-01). No policy is added to or removed from that panel in response
to `docs/STAGE0_BURSTGPT_DIAGNOSTIC.md`.

## Selection-independence rule (§6 of the task)

A policy may enter the PRIMARY panel only if, **at the time it was added
to `docs/POLICY_COMPARABILITY_AUDIT.md` (2026-08-31 or earlier)**, all of:

1. Its mechanism/paper predates this pilot's protocol freeze.
2. It occupies a mechanism family (§ table below) not already saturated
   by an existing panel member.
3. It has adequate implementation fidelity (`faithful_reimplementation`
   or `mechanism_reimplementation`, not `scaffolding_only`) and passes its
   own unit tests in this repo.
4. It is simulator-semantically compatible (does not require
   `GPUConfig.role` disaggregation or multi-instance migration — those go
   to the secondary strata, unchanged).
5. It is independently reproducible from a cited reference.

**Not acceptable, ever, for this or any future revision of the panel:**
"this policy differentiates BurstGPT," "this policy produces more
reversals," "including it makes the experiment pass." No policy in the
current panel or its future-candidate list
(`canonical_policy_registry.yaml`'s `candidates_not_yet_implemented`) was
selected or excluded on this basis — verified by the fact that the audit
document itself predates any Stage-0 outcome.

## Policy-mechanism matrix

Mechanism-family letters follow the task's own taxonomy (§4).

| Policy | Mechanism family | Fidelity class | Panel status |
|---|---|---|---|
| `fifo` | (A) Arrival/order baseline | `REPOSITORY_NATIVE_CLASSICAL` | **PRIMARY** (also the load-calibration reference policy) |
| `edf` | (B) Deadline-aware | `REPOSITORY_NATIVE_CLASSICAL` | **PRIMARY** |
| `least_laxity_first` | (C) Slack/urgency-aware | `REPOSITORY_NATIVE_CLASSICAL` | **PRIMARY** |
| `estimated_service_time_first` | (D) Service-length-aware (SJF-family) | `REPOSITORY_NATIVE_CLASSICAL` | **PRIMARY** |
| `weighted_fair_share` | (I) Fairness-aware | `REPOSITORY_NATIVE_CLASSICAL` | **PRIMARY** |
| `kv_constrained_online` | (G) KV/memory-pressure-aware | `SIMULATOR_PROXY` | **PRIMARY** |
| `vllm_faithful` | (E) Token-budget/continuous batching (pre-chunked-prefill era) | `FAITHFUL_EXTERNAL` | **PRIMARY** |
| `vllm_chunked_prefill_faithful` | (F) Chunked-prefill | `FAITHFUL_EXTERNAL` | **PRIMARY** |
| `sarathi_faithful` | (F) Chunked-prefill | `FAITHFUL_EXTERNAL` | **PRIMARY** |
| `slai_faithful` | (H)-adjacent — SLO-aware scheduling | `FAITHFUL_EXTERNAL` | **PRIMARY** |
| `admission_control` | (H) Admission-control/SLO guard | `REPOSITORY_NATIVE_CLASSICAL` | **PRIMARY** |
| `vllm_style_token_budget` | (E) Token-budget proxy | `STYLE_APPROXIMATION` | Executed alongside; **excluded from PRIMARY**, included in the mandatory robustness check |
| `scorpio_style_slo_guard` | (H) SLO-guard proxy | `STYLE_APPROXIMATION` | Executed alongside; **excluded from PRIMARY**, included in the mandatory robustness check |
| `distserve_faithful` | (K) Disaggregated prefill/decode | `FAITHFUL_EXTERNAL` | **Secondary stratum only** — requires `GPUConfig.role`; never pooled with the single-GPU-colocated primary leaderboard |
| `llumnix_faithful` | (K)/(J)-adjacent — cross-instance migration | `FAITHFUL_EXTERNAL` | **Secondary stratum only** — requires multi-instance relocation semantics |
| `apt_serve_faithful` | (K) Hybrid-cache tiering | `scaffolding_only` (unaudited) | **Excluded** — not a validated reimplementation |

**Total executed: 13** (11 PRIMARY + 2 STYLE_APPROXIMATION robustness-only)
— within the task's target 8–12 for the PRIMARY subset (11) while still
running the full comparability-audited panel for the robustness check
(§ `docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md` § Robustness).

## Mechanism families not represented, and why

- **(J) Preemptive/multilevel (FastServe-like):** no implementation
  exists in this repo and none is added here — adding one now, after
  seeing BurstGPT's collapse, would violate the selection-independence
  rule (§ above) regardless of scientific merit. Logged as a genuine
  future-work candidate, same bar as JITServe below.
- **(K) JITServe, LMetric:** `docs/POLICY_COMPARABILITY_AUDIT.md` already
  investigated `JITServe` (2026-08-31) and found no fundamental semantic
  mismatch with this simulator, but explicitly declined to force it into
  the panel without a from-scratch implementation and independent
  validation. That conclusion is **unchanged by this pilot** — JITServe
  remains a `candidates_not_yet_implemented` entry, not fast-tracked in
  response to Stage 0. `LMetric` was not previously audited and is not
  audited now, for the same reason: mid-redesign addition would be
  outcome-adjacent even if well-intentioned.
- **(K) DistServe, Llumnix:** already represented (`distserve_faithful`,
  `llumnix_faithful`), correctly confined to their secondary strata.

## High-fidelity robustness subset

Unchanged from `docs/POLICY_COMPARABILITY_AUDIT.md`: the 11 PRIMARY
policies above **are** the existing "high-fidelity subset" (primary panel
minus `STYLE_APPROXIMATION`). Every RQ1/RQ2/RQ5 headline result from this
pilot must be checked on this 11-policy subset before being reported as
robust to policy-fidelity choice, per that document's existing convention
— no new subset definition was needed.
