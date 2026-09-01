# MANUSCRIPT_RESULT_CONTRACT.md

Maps every result this project can currently support, or plans to
generate via `docs/RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md`, to a
manuscript subsection. For every unavailable result, an explicit
`[PENDING RESULT: ...]` contract is given so drafting can start now
without inventing outcomes. No section below asserts a direction of
finding that has not been generated.

## Section 4 — Workload characterization

**Available now.** `research/workload-characterization-paper-result-20260901`
(leakage-resistant characterization, `SEPARABILITY_RESULT_CONFIRMED_WITH_CAVEATS`)
and `docs/STAGE0_BURSTGPT_DIAGNOSTIC.md` §E's descriptor comparison
(prompt/output-length homogeneity contrast). Usable as-is.

## Section 5 — Policy panel / methodology

**Available now.** `docs/RANKING_PORTABILITY_POLICY_PANEL.md` (frozen
panel, mechanism-family table, fidelity audit, selection-independence
rule) and `docs/RANKING_PORTABILITY_METRIC_DEFINITIONS.md` (metric
contract). Protocol-fixed, citable directly.

## Section 5.x — Stage-0 pilot (methodology/motivation)

**Available now.** `docs/STAGE0_DISCRIMINABILITY_PROTOCOL.md` +
final `STAGE0_NO_GO` result + `docs/STAGE0_BURSTGPT_DIAGNOSTIC.md`. Safe
statement (verified in the diagnostic): *"The preregistered Stage-0 pilot
found broad scheduler differentiation overall, but differentiation was
strongly source-dependent, traced to a near-total collapse of five of six
scheduling policies on BurstGPT's short-prompt, near-constant-output
traffic."* Belongs here as the pilot that motivated this pilot's
mechanism-diverse panel and denser load grid (§ protocol §2) — not
restated as a ranking-portability finding, which Stage 0 never measured.

## Section 6.1 — Source-specific scheduler discriminability

**Partially available** (Stage-0 evidence only, 3 sources × 3 load
regions × 6-policy subset): `docs/STAGE0_BURSTGPT_DIAGNOSTIC.md` §A–C, F.

`[PENDING RESULT: report the fraction of non-tied (window, load-region)
conditions per source, per metric, over the full 13-policy / 6-region
pilot-v2 matrix (docs/RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md), with
Wilson 95% CIs per source (docs/STAGE0_BURSTGPT_DIAGNOSTIC.md §H's
method, reused). Do not claim which source will be more or less
discriminable until the pilot-v2 matrix is complete.]`

## Section 6.2 — Cross-source Kendall tau / Spearman rho

**Not available.**

`[PENDING RESULT: report Kendall's tau and Spearman's rho between each
pair of the 3 sources' policy rankings, per metric (docs/
RANKING_PORTABILITY_METRIC_DEFINITIONS.md's metric contract), per load
region, with block-bootstrap 95% CIs over windows
(docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md §A). Include
n_conditions_excluded_for_undefined_metric per cell. Do not claim
"stable" or "unstable" rankings until this table exists — either outcome
is a complete, reportable result under this design (docs/
RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md §9).]`

## Section 6.3 — Pairwise rank reversals

**Not available.**

`[PENDING RESULT: report every (policy A, policy B) pair's reversal
frequency and practically-meaningful-reversal count (docs/
RANKING_PORTABILITY_ANALYSIS_PLAN.md §A's pre-registered 10%-margin +
CI-excludes-zero threshold), separated from microscopic sign changes.
Do not report a reversal count that mixes the two categories.]`

## Section 6.4 — Temporal / provider / domain portability

**Not available.**

`[PENDING RESULT: within-BurstGPT EARLY/MIDDLE/LATE tau
(docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md §D), Azure-2024 own-window
calendar-split tau, and cross-source (provider/domain) tau from Section
6.2, kept as three separately labeled results, never merged into one
"temporal/domain OOD" number.]`

## Section 6.5 — Load portability

**Not available**, and explicitly **secondary**
(`docs/RESEARCH_QUESTIONS.md`, Gate A resolution) — never a headline claim
of cross-source rank instability by itself.

`[PENDING RESULT: tau/reversal-frequency across the 6-region grid
(docs/RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md §5), per source, reported
as a robustness/sensitivity table, framed as secondary per
docs/CLAIM_BOUNDARIES.md's Gate-A-resolution constraints — never using or
resembling LLM 2026's {1,2,4,8,16,32,64,128} grid or its 60 windows.]`

## Section 6.6 — Metric dependence

**Not available.**

`[PENDING RESULT: tau between metric-M and metric-N rankings, for every
pair of metrics in docs/RANKING_PORTABILITY_METRIC_DEFINITIONS.md's
contract, per source (docs/STATISTICAL_ANALYSIS_PLAN.md §E, reused
unchanged). Report separately whether any exclusion-driven gap
(§ metric contract's ranking-treatment rule) is concentrated in one
source, as a candidate explanation if so — descriptive only.]`

## Section 7 — Sample complexity

**Not available.**

`[PENDING RESULT: probability of recovering the full n=40 ranking at
n ∈ {5,10,20,30,40} (docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md §C),
per source and per metric, plus the concentrated-vs-distributed window
budget comparison. Report the n at which recovery probability first
exceeds the pre-registered 0.9 threshold — do not claim a specific number
in prose before this exists.]`

## Section 8 — Real-system validation

**Design available, not executed.** `docs/REAL_SYSTEM_VALIDATION_PLAN.md`
(reused unchanged) + `docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md` §G's
case-selection rule.

`[PENDING RESULT: sign agreement, Kendall tau, and reversal-agreement
between simulated and real-vLLM rankings for the objectively-selected
validation cases (largest-effect-size reversal + one stable-ordering
control). Selection must be frozen from this pilot's actual §6.2/6.3
results before any real-vLLM run — cannot be written until those exist.]`

## Section 6.1-diagnostic — Source-specific mechanism explanation

**Available now, from Stage 0 only** (single-source case study, not yet
generalized): `docs/STAGE0_BURSTGPT_DIAGNOSTIC.md` §F (policy-pair
collapse), §E (workload descriptors).

`[PENDING RESULT (RQ4): repeat the policy-pair-similarity and
workload-descriptor association analysis (docs/STATISTICAL_ANALYSIS_PLAN.md
§G, pre-specified logistic regression, no post-hoc model search) across
all 3 sources' pilot-v2 data, extended to classify both reversal *and*
equivalence/collapse sites (docs/RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md
§1's RQ4 extension). Use the new mechanism telemetry
(docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md §E) directly, rather than
workload-level proxies, wherever available — this is the specific gap
Stage 0's diagnostic had to work around indirectly.]`

## Explicit non-claims (repeated from `docs/CLAIM_BOUNDARIES.md`, for drafting discipline)

Do not write, at any point before or after pilot-v2 completes: "Stage 0
demonstrated cross-source rank instability" (Stage 0 never measured
ranking; only pilot-v2's Section 6.2 can), "we are the first to study
X" (use `docs/RELATED_WORK_NOVELTY_AUDIT.md`'s wording convention
instead), any restatement of LLM 2026's SBS/VBS/exploitability/selector
concepts, or any claim that simulated absolute latency matches real
hardware latency (Section 8 only claims relative-ranking agreement).
