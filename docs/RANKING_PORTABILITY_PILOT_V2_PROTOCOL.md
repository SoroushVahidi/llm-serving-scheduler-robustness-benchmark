# RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md

Pre-registered 2026-09-01, before any cell of this pilot is executed.
Companion documents: `docs/RANKING_PORTABILITY_POLICY_PANEL.md`,
`docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md`,
`docs/RANKING_PORTABILITY_METRIC_DEFINITIONS.md`,
`docs/MANUSCRIPT_RESULT_CONTRACT.md`. **Not launched by this document or
this session.**

## 0. Core scientific principle

This is **not** "re-run Stage 0 until BurstGPT passes Criterion 5."
Stage 0 (`research/stage0-zero-completion-undefined-metrics-20260901`,
`STAGE0_NO_GO`, final and unmodified) already established the answer to
its own question — pooled scheduler discriminability is real but strongly
source-dependent — and its diagnostic
(`docs/STAGE0_BURSTGPT_DIAGNOSTIC.md`) explains *why*
(`POLICY_PANEL_MECHANISM_MISMATCH`: on BurstGPT's short, low-variance
prompt/output traffic, 5 of Stage 0's 6 policies collapse into identical
behavior). This pilot asks a different, larger question that Stage 0 was
never designed to answer and that its own protocol explicitly deferred
(`docs/STAGE0_DISCRIMINABILITY_PROTOCOL.md`: "this pilot only answers 'is
there enough signal to be worth building a larger confirmatory campaign
on'... [it] does not compute any cross-source ranking-stability statistic
— that is Stage 2/3's job").

**Primary scientific question:** How portable are comparative scheduler
rankings across independent workload distributions, when the policy panel
spans a mechanism-diverse set of scheduling disciplines and a
policy-independent operating-region grid?

Formally, for workload distribution `W` and metric `M`, define
`R(W, M)` = the ranking the fixed policy panel induces on `W` under `M`.
This pilot studies how `R` varies across source, temporal split, load
region, and metric — not whether any single `(source, load)` cell is
"non-tied."

## 1. Research questions (adopted from the existing frozen freeze, not invented post-hoc)

`docs/RESEARCH_QUESTIONS.md` was frozen **2026-08-31**, a full day before
Stage 0 launched (2026-09-01) — every RQ below predates and is therefore
provably independent of the BurstGPT finding.

| # | Question | Class |
|---|---|---|
| RQ1 | How stable are scheduler rankings across independent workload sources? | **PRIMARY** |
| RQ2 | How stable are scheduler rankings under temporal, provider, and domain shifts? | **PRIMARY** |
| RQ3 | To what extent do rankings on synthetic stress workloads transfer to rankings on independent real-trace-derived workloads? | **SECONDARY** |
| RQ4 | Which source-native observable workload characteristics are associated with cross-distribution scheduler rank reversals *or collapse*? | **SECONDARY** |
| RQ5 | How many independent workload windows are required before a comparative scheduler ranking becomes statistically stable? | **PRIMARY** |
| RQ6 | Do representative simulated scheduler rankings and cross-workload rank reversals reproduce on a real serving engine? | **SECONDARY** (design-only in this pilot; see `docs/REAL_SYSTEM_VALIDATION_PLAN.md`) |

Two items requested by this task map onto the existing frozen set rather
than adding new numbered RQs:

- **Pairwise reversals** (task's "RQ2") is RQ1's own toolkit
  (`docs/STATISTICAL_ANALYSIS_PLAN.md` §B), not a separate question.
- **Metric-conditioned portability** (task's "RQ4") is explicitly listed
  in `docs/OVERLAP_LEDGER.md` as a `NEW_CANDIDATE` ("Metric-dependent
  rank reversal... not examined as a formal RQ in either existing
  manuscript") and is operationalized in
  `docs/STATISTICAL_ANALYSIS_PLAN.md` §E, folded under RQ1's ranking-
  stability umbrella rather than given a new number.

**Load-conditioned portability** (task's "RQ3") is deliberately kept a
**secondary robustness/sensitivity analysis, never a headline RQ** — this
was decided at the Gate A resolution (`docs/GO_NO_GO_GATES.md`,
`docs/RESEARCH_QUESTIONS.md`), specifically to avoid overlap with LLM
2026's `public_replay_load_scaling_v1/v2` (`docs/OVERLAP_LEDGER.md`,
`docs/CLAIM_BOUNDARIES.md`). This pilot does not reopen that decision.

**RQ6 (source-specific discriminability/equivalence)** in the task's
numbering is RQ4 here, extended (see below) to explicitly cover
*equivalence/collapse*, not only reversal — the natural generalization
after Stage 0's diagnostic, still descriptive/explanatory, never a
selector (`docs/CLAIM_BOUNDARIES.md`).

## 2. Stage-0 lesson incorporated

What Stage 0 established: broad discriminability exists (Criteria 1–4
passed comfortably); BurstGPT-style short/uniform traffic causes a
specific, mechanism-identifiable policy collapse, not explained by weak
calibration or sample noise (`docs/STAGE0_BURSTGPT_DIAGNOSTIC.md`).

How this pilot responds, symmetrically (never BurstGPT-only):
1. **Denser, policy-independent load grid for all sources** (§5) — tests
   whether finer resolution reveals a real threshold effect anywhere, not
   just for BurstGPT.
2. **Larger, symmetric window count for all sources** (§4) — the same
   `docs/EXPERIMENT_CAMPAIGN_PLAN.md` target (~40/source) already frozen
   **before** Stage 0, chosen for the sample-complexity study (RQ5), not
   raised in response to BurstGPT.
3. **Mechanism-diverse policy panel** (§6) — reuses the 13-policy PRIMARY
   panel frozen in `docs/POLICY_COMPARABILITY_AUDIT.md` **2026-08-31**,
   which already includes deadline/slack-aware (EDF, LLF), service-length-
   aware (ESTF), fairness-aware, and SLO-aware (`slai_faithful`)
   mechanisms that Stage 0's narrower 6-policy subset omitted — a
   pre-existing, not newly invented, response.
4. **Closed metric-boundary ambiguity** (§7,
   `docs/RANKING_PORTABILITY_METRIC_DEFINITIONS.md`) — Stage 0's
   zero-completion `slo_violation_rate` gap must not recur.
5. **Mechanism telemetry persisted this time** (§8) — Stage 0's schema
   could not explain *why* policies collapsed beyond aggregate metrics;
   this pilot's cell schema adds queue/KV/admission telemetry so a repeat
   diagnostic doesn't need indirect proxies.

**Why this is not "make BurstGPT pass":** every change above applies
identically to Azure-2024 and Bailian/Qwen. No BurstGPT-specific window,
load multiplier, or policy is introduced. The evaluability criteria (§9)
explicitly do not require BurstGPT (or any source) to show non-tied
results — a symmetric, source-agnostic outcome ("rankings are stable
everywhere") is an equally valid, publishable result of this design (§9).

## 3. Workload sources (§7 of the task)

| Source | Independence status (`docs/EVIDENCE_INDEPENDENCE_PLAN.md`) | Included in v2 pilot? |
|---|---|---|
| Azure LLM 2024 | `FULLY_INDEPENDENT` (zero known consumption by LLM 2026 or the HF baselines release) | **Yes — primary** |
| Bailian/Qwen | `FULLY_INDEPENDENT` (zero known consumption; shares a platform with ServeGen, not with any prior study's *windows*) | **Yes — primary** |
| BurstGPT | `PARTIALLY_REUSED_WITH_NEW_WINDOWS` (LLM 2026 consumed 20 windows of a much larger corpus; this project draws its own, disjoint windows) | **Yes — primary** |
| Azure 2023 (conversation, code) | `PARTIALLY_REUSED_WITH_NEW_WINDOWS` | **No** — reserved for the future full confirmatory campaign (`docs/EXPERIMENT_CAMPAIGN_PLAN.md`), not needed to answer RQ1/RQ5 at pilot scale |
| TraceLab | Independence **not fully verifiable** from public artifacts (`docs/TRACELAB_PROVENANCE_RESOLUTION.md`); adapter **does not exist yet** in this repo | **No** — a real implementation blocker, not an outcome-based exclusion. Its own public 512-window sweep already reported "near-saturated" separation (a documented prior, not evidence generated here) — worth flagging as a plausible fourth BurstGPT-like case for a *later* expansion, once the adapter and schema are independently verified, never rushed in now. |
| ServeGen | `PRIOR_RESULT_REFERENCE_ONLY` / same-platform-as-Bailian, not a distinct provider (`docs/SERVEGEN_ADOPTION_AUDIT.md`) | No — never counted as an independent source |

Keeping the pilot at the same **3 primary sources** Stage 0 already used
(not 4–5) is itself a scope-discipline choice: it isolates whether the
*policy panel and load-grid redesign* change the picture, without
confounding that test with a simultaneously-expanded source set.

## 4. Window count and sampling rule

**40 windows/source** (not 10). This is the pre-existing
`docs/EXPERIMENT_CAMPAIGN_PLAN.md` target, frozen **2026-08-31, before
Stage 0 ran** ("targeting the sample-complexity study... to need well
under this") — adopted verbatim, not re-derived to move any Criterion-5-
style threshold. It also directly supports the RQ5 sample-complexity
subsampling ladder (§ `docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md`),
`n ∈ {5, 10, 20, 30, 40}`.

Sampling rule: identical, deterministic, source-independent construction
to Stage 0's 10 windows (`docs/SPLIT_PROTOCOL.md`,
`scripts/stage0/build_stage0_window_freezing.py`-style procedure),
extended to 40 windows/source by continuing the same deterministic
selection rule (not re-sampling the original 10 differently, and not
targeting any particular window's content) — i.e. Stage 0's 10 windows
per source are a strict subset of this pilot's 40, generated by the same
rule, not superseded.

## 5. Load design (§9 of the task)

Base rule unchanged from the already-frozen
`docs/LOAD_CALIBRATION_PROTOCOL.md`: policy-independent capacity search
using the single frozen reference policy `fifo`, against one documented
`GPUConfig`, identical for every window/source — extended from 4 to
**6 symmetric operating regions**, applied identically to every source
(never source- or outcome-adjusted):

| Region | Multiplier of λ_ref |
|---|---|
| `LOW` | 0.5× |
| `PRE_KNEE` | 0.8× |
| `KNEE` | 1.0× |
| `POST_KNEE` | 1.1× |
| `OVERLOAD` | 1.2× |
| `HIGH_PRESSURE` | 1.5× |

Rationale for `POST_KNEE`/`HIGH_PRESSURE`: the diagnostic found BurstGPT
differentiates *more* at OVERLOAD (6/10 non-tied) than at KNEE (4/10) —
denser resolution between and beyond those two points tests whether this
is a genuine, sharper threshold (for BurstGPT or any source) rather than
an artifact of only sampling 3 points. This is the same multiplier table
for every source; no per-source tuning based on any policy-under-study
result (`docs/LOAD_CALIBRATION_PROTOCOL.md`'s existing prohibition,
unchanged).

## 6. Policy panel

Reuses `docs/POLICY_COMPARABILITY_AUDIT.md`'s PRIMARY panel (frozen
2026-08-31) in full. Details, mechanism-family mapping, and the
selection-independence rule are in
`docs/RANKING_PORTABILITY_POLICY_PANEL.md` — summary: **13 policies
executed, 11 designated PRIMARY (`STYLE_APPROXIMATION` excluded per the
existing high-fidelity-subset convention), 2 (`vllm_style_token_budget`,
`scorpio_style_slo_guard`) run alongside for the mandatory robustness
check, never dropped from execution.**

## 7. Metric protocol

Full contract in `docs/RANKING_PORTABILITY_METRIC_DEFINITIONS.md` — every
metric is classified `ALWAYS_DEFINED` / `CONDITIONAL_ON_COMPLETION` /
`CONDITIONAL_ON_OTHER_PRECONDITION` **before** execution (extends
`docs/STAGE0_METRIC_DEFINITIONS.md`'s existing audit), with an explicit
ranking-treatment rule for every conditional metric's undefined case —
closing exactly the gap Stage 0 exposed.

## 8. Mechanism telemetry (new; not in Stage 0's schema)

The new cell schema (`docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md` §
Telemetry) additionally persists, per cell: mean/peak queue depth, mean
active-batch saturation (active batch size ÷ configured max batch), a
prefill/decode contention proxy (fraction of steps with both prefill and
decode work pending), mean KV occupancy, an admission-control activation
count (0 for policies without one), and a preemption/reorder-event count
(0 for non-preemptive policies). This lets a future diagnostic explain a
collapse or reversal directly, without indirect workload-level proxies
(as `docs/STAGE0_BURSTGPT_DIAGNOSTIC.md` §F had to use).

## 9. Evaluability / new GO–NO-GO logic (§18 of the task)

**Explicitly does not reuse Stage 0's Criterion 5** — a source-share
threshold was the right pilot-discriminability gate for Stage 0's
narrower question; it is not the right validity gate for a
ranking-portability study. New criteria, checked once the matrix
completes, none of which require any particular ranking outcome:

1. **Matrix integrity**: expected cells present, 0 missing/duplicate,
   0 unresolved schema failures (reusing the repaired, zero-completion-
   aware schema — §
   `docs/RANKING_PORTABILITY_METRIC_DEFINITIONS.md`).
2. **No universal collapse**: not every (source, window, load-region,
   metric) cell is trivially tied across the *entire* panel (a weaker,
   whole-matrix analogue of Stage 0's Criterion 3 — a sanity floor, not a
   discriminability bar).
3. **Estimable rankings**: each source has enough non-degenerate windows
   to compute a bootstrap CI on Kendall's tau at all (a minimum-data
   check, not a stability requirement).
4. **Reported CI precision**: whatever the bootstrap CI half-width turns
   out to be is *reported*, not gated — a wide CI is a limitation to
   disclose, not a failure condition.

**Explicitly confirmed:** no criterion above requires rank reversals,
non-tied outcomes, or any particular direction of finding to exist.
"Rankings are highly stable across sources, loads, and metrics" is a
complete, valid, publishable result under this design, exactly as much as
finding reversals would be.

## 10. Compute budget

See `docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md` § Compute options for the
full table. **Recommended: 3 sources × 40 windows × 6 load regions × 13
policies × 2 verification reps = 18,720 cells** (~33 estimated CPU-core-
hours) — roughly 3.6% of the previously-estimated ~520,000-cell full
Stage-2 confirmatory campaign (`docs/EXPERIMENT_CAMPAIGN_PLAN.md`), which
remains untouched and unlaunched.

## 11. Overlap safety

No change to any `PROHIBITED_OVERLAP` classification in
`docs/OVERLAP_LEDGER.md`/`docs/CLAIM_BOUNDARIES.md`. This pilot's
contributions (`Cross-source rank stability`, `Metric-dependent rank
reversal`, `Sample complexity of scheduler rankings`,
`Workload descriptors predicting rank reversal/equivalence`) are all
already-logged `NEW_CANDIDATE` rows, unclaimed by LLM 2026 or SIGMETRICS
2027. Load-level dependence remains a secondary analysis only, using this
project's own frozen calibration (§5), never LLM 2026's `{1,...,128}`
grid or its 60 canonical windows.

## 12. Adversarial pre-freeze review (§22 of the task)

1. *Any design choice obviously influenced by seeing Stage 0's result?*
   The RQs (§1) and the 13-policy panel (§6) predate Stage 0 by a day —
   provably not. The load-grid densification (§5) and window-count
   increase (§4) are direct, disclosed responses to Stage 0's finding —
   but applied symmetrically to every source, never to BurstGPT alone.
2. *Implicitly optimizing to make BurstGPT differentiate?* No — §9's
   evaluability criteria require no source to show any particular result.
3. *Meaningful if rankings are almost perfectly stable?* Yes — §9 states
   this explicitly; RQ5's sample-complexity curve and RQ2's temporal/
   provider-shift analysis are both fully defined and reportable
   regardless of RQ1's outcome.
4. *Reversals defined without outcome-dependent thresholds?* Yes — see
   `docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md` § B, effect-size threshold
   fixed before execution.
5. *Panel mechanism-diverse and literature-justified?* Yes — §
   `docs/RANKING_PORTABILITY_POLICY_PANEL.md`.
6. *Sources independent enough?* Yes, per §3 and
   `docs/EVIDENCE_INDEPENDENCE_PLAN.md`, with TraceLab's caveat disclosed,
   not hidden.
7. *Metrics fully defined at boundary cases?* Yes —
   `docs/RANKING_PORTABILITY_METRIC_DEFINITIONS.md`.
8. *Statistical units correct?* Yes — the workload window remains the
   resampling unit throughout (`docs/STATISTICAL_ANALYSIS_PLAN.md`,
   unchanged).
9. *Distinct from LLM 2026/SIGMETRICS?* Yes — §11.
10. *Compute plan reasonable?* Yes — §10, ~3.6% of the full future
    campaign.

No outcome-sensitive design choice was found requiring correction before
freeze.
