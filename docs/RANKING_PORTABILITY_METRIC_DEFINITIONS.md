# RANKING_PORTABILITY_METRIC_DEFINITIONS.md

Extends `docs/STAGE0_METRIC_DEFINITIONS.md`'s "Conditional metric audit"
(added by `docs/STAGE0_ZERO_COMPLETION_METRIC_AMENDMENT_20260901.md`) with
an explicit **ranking-treatment rule** for every conditional metric's
undefined case — closing the exact category of ambiguity Stage 0 exposed,
before this pilot generates a single cell. No metric's numerator,
denominator, or population changes from the Stage-0-repaired definitions;
this document only adds what a ranking analysis must do when a value is
undefined.

## Metric contract

| Metric | Class | Population | Undefined representation | Ranking treatment when undefined |
|---|---|---|---|---|
| `completion_fraction` | `ALWAYS_DEFINED` | All arrivals | Never NaN for a real window (`num_total > 0` always) | N/A |
| `arrival_normalized_weighted_goodput` (ANWG, primary metric) | `ALWAYS_DEFINED` | All arrivals | Never NaN for a real window | N/A |
| `weighted_completion_fraction` | `ALWAYS_DEFINED` | All arrivals | Never NaN for a real window | N/A |
| `slo_violation_rate` | `CONDITIONAL_ON_COMPLETION` | Completed requests only | `NaN` iff `completion_fraction == 0.0` (unchanged from the Stage-0 amendment) | **Exclude that policy from that (window, load-region)'s ranking on this metric only.** Record the exclusion explicitly (§ below); do not impute 0.0/1.0, do not drop the whole condition for the other policies that did complete. |
| `weighted_goodput` | `CONDITIONAL_ON_COMPLETION` | Completed requests only (weight) | `NaN` iff `completion_fraction == 0.0` | Same as `slo_violation_rate`: exclude that policy from that condition's ranking on this metric. |
| `mean_latency` / `p95_latency` / `p99_latency` | `CONDITIONAL_ON_COMPLETION` | Completed requests only | `NaN` iff `completion_fraction == 0.0` | Same rule. |
| `request_throughput` / `token_throughput` | `CONDITIONAL_ON_COMPLETION` | Completed requests, given `sim_duration > 0` | `NaN` iff `completion_fraction == 0.0` | Same rule. |
| `mean_ttft` / `p95_ttft` | `CONDITIONAL_ON_OTHER_PRECONDITION` | Completed requests with a recorded first-token time | `NaN` iff no completed request recorded a first-token time (may occur even with `completion_fraction > 0`, if none captured TTFT) | Same rule — exclude the policy from that metric's ranking for that condition; this is a stricter/rarer precondition than plain completion, so it must be checked independently, not inferred from `completion_fraction`. |

## Ranking treatment when a policy is excluded from one condition's ranking

- **Kendall's tau / Spearman's rho (`docs/STATISTICAL_ANALYSIS_PLAN.md`
  §A):** computed pairwise over the set of policies with a defined value
  in **both** rankings being compared. A policy excluded from one side's
  ranking contributes no pair for that comparison; it is not scored as a
  loss or a tie.
- **Top-k overlap:** computed over whichever policies have a defined value
  in that specific ranking; if fewer than `k` policies have a defined
  value, report the achieved overlap over the available set and flag
  `k_reduced = true` for that condition rather than silently padding with
  excluded policies.
- **Pairwise reversal (§B):** a pair `(A, B)` is only evaluated in a
  condition where **both** have a defined value; if either is undefined,
  that condition contributes no observation to that pair's reversal
  statistic (not a tie, not a reversal — a missing observation).
- **Sample-complexity subsampling (§F):** an excluded-metric condition is
  treated as a missing observation for that metric's ranking only — it
  does not remove the window from other metrics' rankings or from ANWG's
  (always-defined) analysis.
- **Reporting:** every table reporting a ranking-derived statistic must
  also report `n_conditions_excluded_for_undefined_metric` alongside it —
  an exclusion rate that turns out to be non-trivial (e.g. concentrated in
  one source, mirroring Stage 0's BurstGPT pattern) is itself a reportable
  finding under RQ4, not a footnote to bury.

## What must never happen (unchanged from the Stage-0 amendment)

No numerical value is ever imputed for an undefined conditional metric —
neither a favorable nor an unfavorable one, and never chosen after seeing
which policy or source it affects. The schema-validity rule from
`src/robustbench/stage0/schema.py` (accept `NaN` iff
`completion_fraction == 0.0` for `CONDITIONAL_ON_COMPLETION` fields, reject
otherwise) is reused as-is for this pilot's cell schema, extended to cover
`mean_ttft`/`p95_ttft`'s stricter precondition as a **separate** check
(never conflated with `completion_fraction == 0.0`, since TTFT can be
undefined even when completion is not).
