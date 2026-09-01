# STAGE0_ZERO_COMPLETION_METRIC_AMENDMENT_20260901.md

## A. Discovery

The real 1,080-cell Stage-0 pilot (array job 1213964, launch SHA `17de339`)
completed all 6 array shards, but 12 of 1,080 cells were rejected by
`validate_cell_result()` (`src/robustbench/stage0/schema.py`) with
`error_category=schema_validation_failed`,
`error_detail="success=True but slo_violation_rate is NaN"`.

All 12 affected cells share exactly:

```
source_family = azure_llm_2024
window_id     in {azure_llm_2024_stage0_w06, azure_llm_2024_stage0_w09}
load_region   in {PRE_KNEE, KNEE, OVERLOAD}
policy_id     = vllm_faithful
repetition    in {0, 1}
```

In every one of these 12 cells, `completion_fraction == 0.0` (zero of the
window's requests completed). `RunMetrics.slo_violation_rate`
(`src/robustbench/core/metrics.py::compute_metrics`) is assigned only inside
`if completed:` — with zero completions it keeps its dataclass default,
`float("nan")`. The frozen schema (Section B5) required
`slo_violation_rate` to be non-NaN whenever `success=True`, so these
scientifically meaningful zero-completion cells were incorrectly rejected as
harness failures rather than accepted as valid (catastrophic) outcomes.

An independent audit of all 1,068 other successful cells found **none**
with `completion_fraction == 0.0` — this boundary condition is confined to
exactly the 12 cells above.

## B. Decision

**`slo_violation_rate` is conditional on completion.** Its population is
"requests that completed." When `completion_fraction == 0.0`, that
population is empty, and `slo_violation_rate` is **UNDEFINED** —
represented as `NaN`, exactly as `compute_metrics()` already produces it.

No numerical value is imputed for this case. Specifically:

- `slo_violation_rate = 0.0` at zero completion is **not used** — it would
  misleadingly resemble a policy that met every SLO deadline.
- `slo_violation_rate = 1.0` at zero completion is **not used** — it would
  retroactively introduce an arrival-normalized definition for this metric
  that was never pre-registered anywhere in this project (unlike ANWG,
  which has an explicit, tested, pre-registered zero-completion rule).

Catastrophic failure at these 12 cells remains fully represented by:

- `completion_fraction = 0.0`
- `arrival_normalized_weighted_goodput = 0.0` (the Stage-0 primary metric,
  per `docs/STAGE0_METRIC_DEFINITIONS.md` — unaffected by this amendment)

The repair changes **validity semantics only**: a `NaN` `slo_violation_rate`
is schema-valid precisely when `completion_fraction == 0.0`, and remains a
schema violation whenever `completion_fraction != 0.0` (i.e., the metric
must still be finite whenever its population is non-empty). No numerator,
denominator, or formula in `compute_metrics()` changes.

## C. Rationale

- Preserves the existing conditional-on-completion semantics that
  `slo_violation_rate`, `mean_latency`, `p95_latency`, `mean_ttft`, and
  other completed-request metrics already share (see
  `docs/STAGE0_METRIC_DEFINITIONS.md` §"Conditional metric audit" below).
- Avoids assigning either a favorable (`0.0`) or unfavorable (`1.0`) value
  to `vllm_faithful` — the specific policy that encountered this
  condition — *after* the fact.
- `ANWG` and `completion_fraction` already capture the non-completion
  outcome in a pre-registered, tested way; no information is lost by
  leaving `slo_violation_rate` undefined here.

## D. Timing disclosure

This amendment was written and decided **after** the real Stage-0 launch
(array 1213964 / merge 1213965) exposed the zero-completion boundary case,
and **after** the identities of the 12 affected cells
(`azure_llm_2024 × {w06,w09} × {PRE_KNEE,KNEE,OVERLOAD} × vllm_faithful ×
{rep0,rep1}`) were known. It was written **before** the frozen five-criterion
Stage-0 analyzer (`src/robustbench/stage0/analyzer.py`) was run against the
real matrix, and before any Stage-0 GO/NO-GO verdict existed.

This is therefore disclosed as a **post-launch, pre-analysis protocol
clarification** — not a pre-registered definition, and not a post-outcome
data-fitting exercise. It closes a genuine gap in the frozen protocol
(`slo_violation_rate`'s zero-completion representation was never specified,
unlike ANWG's), using the narrowest, most literal reading available:
leave the mathematically undefined value undefined.

## E. Safeguard: mandatory convention-sensitivity analysis

Because this decision was made with knowledge of which cells and which
policy it affects, the final Stage-0 analysis must additionally report
Criterion 4 and the overall verdict under two counterfactual conventions
(`FORCE_ZERO`, `FORCE_ONE`) purely as a sensitivity check, in addition to
the primary `UNDEFINED` semantics decided above. If the overall verdict
would differ across these three conventions, the final Stage-0 status must
be reported as `STAGE0_INCONCLUSIVE` regardless of what the primary
convention alone would yield. See
`artifacts/manifests/stage0_zero_completion_repair.json` and the analysis
report for the executed sensitivity table.

## F. Scope note for the future confirmatory campaign

This ambiguity must not recur. The full confirmatory protocol must
pre-register, before any execution: which metrics are arrival-normalized
vs. conditional-on-completion, and the exact representation (not
imputation) of undefined values for every conditional metric used in any
GO/NO-GO or ranking criterion.
