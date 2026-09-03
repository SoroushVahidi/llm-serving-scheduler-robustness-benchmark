# SLO Definition Sensitivity Protocol (2026-09-03)

**Label: `POST_PHASE12_SLO_DEFINITION_SENSITIVITY_EXTENSION`.** This was
**not** part of the original sealed Phase-12 scientific campaign and must
never be described as preregistered evidence. Per
`docs/PHASE12_SLO_SENSITIVITY_PROTOCOL_HOLE.md`, an exhaustive search of
this repository's full history found that no alternative SLO-synthesis
rule was ever actually frozen prior to this document — this is the first
time one is defined. The purpose is robustness testing of the existing
Phase-12 conclusions, not a new headline result.

Machine-readable contract: `configs/analysis/slo_sensitivity_20260903.json`.

## 1. The frozen Phase-12 SLO rule (reconstructed from evidence, verified not assumed)

Source: `src/robustbench/workloads/external/benchmark_synthesis.py`
(`SYNTHESIS_VERSION = "stage0_synthesis_v1"`), used unchanged by the
frozen Phase-12 campaign via
`scripts/ranking_portability/run_phase12_campaign_shard.py`.

```
service_time_proxy = PREFILL_TOKEN_COST_S * prompt_tokens
                    + DECODE_TOKEN_COST_S * predicted_output_tokens
slo_deadline        = arrival_time + SLO_MULTIPLIER * service_time_proxy
```

with `SLO_MULTIPLIER = 20.0`, `PREFILL_TOKEN_COST_S = 0.0004`,
`DECODE_TOKEN_COST_S = 0.02`. This is computed **per request**, once, at
synthesis time (not a global/per-window quantity). `priority` (the ANWG/
weighted-goodput weight) is not an input to this formula, and Stage-0
synthesis sets `priority = 1.0` uniformly for every request in every
Phase-12 window, so weighting is a structural no-op for every cell this
extension touches, regardless of SLO rule.

## 2. Where SLO affects the pipeline (policy audit)

`request.slo_deadline` feeds `CompletedRequest.slo_violated` (`core/types.py`:
`completion_time > request.slo_deadline`) for **every** completed request
under **every** policy — this is what makes SLO-definition sensitivity
worth checking even for policies whose own scheduling logic never reads
the deadline: their realized outcome metrics (`slo_violation_rate`,
`weighted_goodput`, `arrival_normalized_weighted_goodput`) still shift
when the deadline shifts, because the violation judgment is deadline-based
regardless of scheduling mechanism.

Which PRIMARY policies directly consult `request.slo_deadline` in their
own scheduling decisions:

| Policy | Direct SLO use? | Mechanism |
|---|---|---|
| `edf` | YES | primary sort key: `slo_deadline` ascending |
| `least_laxity_first` | YES | `laxity = slo_deadline - now - service_estimate`; tie-break `slo_deadline` |
| `admission_control` | YES | admission laxity = `slo_deadline - now - service_estimate`; ordering also uses `slo_deadline` ascending |
| `estimated_service_time_first` | PARTIAL | primary key is SJF service-time estimate; `slo_deadline` is only a tie-breaker |
| `slai_faithful` | **NO** | uses its own `last_schedulable_time`, derived from a `class_id`-keyed `time_between_tokens` table, entirely independent of `request.slo_deadline`. Stage-0 synthesis sets `class_id = "stage0_uniform"` for every request, so `slai_faithful`'s own scheduling decisions are structurally unaffected by this extension's variants — only its post-hoc violation judgment (see above) moves |
| `fifo`, `vllm_faithful`, `vllm_chunked_prefill_faithful`, `sarathi_faithful`, `weighted_fair_share`, `kv_constrained_online` | NO | no deadline reference anywhere in their scheduling code |

(Non-PRIMARY, executed-alongside `scorpio_style_slo_guard` also uses
laxity directly, same mechanism as `admission_control`.)

This means the sensitivity question is **not** "do SLO-aware policies
behave differently" — most of the panel's realized ANWG will shift with
the SLO rule regardless of scheduling mechanism. The question this
protocol answers is whether the **relative ranking** of the 11-policy
panel, and the specific reversals already found under the primary rule,
survive that shift.

## 3. The frozen scientific question

> Are the main scheduler-portability conclusions and supported practical
> reversals robust to reasonable alternative synthesized SLO tightness
> assumptions?

This is explicitly **not**: a search for a favorable multiplier, a new
SLO policy, or a scheduler tuning study.

## 4. Frozen alternative SLO rules (chosen outcome-independently)

| Variant key | Multiplier | Rationale |
|---|---|---|
| `tight_10x` | 10.0 | half the primary multiplier — tests a less-generous, more-binding deadline regime |
| `primary_20x` | 20.0 | the sealed rule itself — used as the reference point for every comparison, and as the primary-equivalence gate |
| `loose_40x` | 40.0 | double the primary multiplier — tests an even more generous regime |

Symmetric halve/double bracket around the primary value, chosen from the
sealed formula's own structure and its own stated rationale ("generous,
chosen before any policy-under-study result was observed, to avoid a
trivially degenerate SLO regime at PRE_KNEE") — **not** selected by
inspecting any scheduler-ranking outcome under any candidate value.

## 5. Held fixed across all three variants

`source_family`, `window_id`, `request_id`, `arrival_time`,
`prompt_tokens`, `predicted_output_tokens`, `actual_output_tokens`,
`priority`, `class_id`, `policy_id`, `load_region`, the frozen
`absolute_load_factor` for that (source, window, region), and the frozen
`synthesis_seed` for that window. Only `slo_deadline` differs.

## 6. Variant transform

`src/robustbench/analysis/slo_variant.py::apply_slo_variant` — never
re-derives `service_time_proxy` from token counts (that would duplicate
the sealed formula's constants). Instead:

```
slack            = primary_deadline - arrival_time     (= 20.0 * service_time_proxy)
variant_slack    = slack * (variant_multiplier / 20.0)
variant_deadline = arrival_time + variant_slack
```

This is an exact algebraic identity: at `variant_multiplier = 20.0` the
ratio is exactly 1.0 and the transform is a provable no-op — this is what
makes primary-equivalence a proof, not an empirical spot-check (see
§7 and `tests/test_slo_variant.py`). Applied via `dataclasses.replace`, so
only `slo_deadline` ever changes; every other `Request` field is copied
byte-for-byte. `validate_slo_variant` (same module) is a structural
validator used as defense-in-depth in tests and the campaign runner: it
fails hard if any non-SLO field differs between an original and a variant
request sequence.

## 7. Primary-equivalence gate (hard STOP condition)

`tests/test_slo_variant.py::test_primary_variant_reproduces_sealed_pipeline_on_real_cells`
regenerates representative real Phase-12 cells through both the unmodified
sealed pipeline (`synthesize_requests_from_window` → `_rebase_and_scale` →
`execute_cell`) and this extension's variant pipeline at the primary
multiplier, and asserts every field of the resulting
`RankingPortabilityCellResult` is identical. **If this test ever fails,
this extension must not proceed past that point** — the variant machinery
would no longer be trusted to reproduce sealed behavior at the reference
point, and neither the pilot nor the full campaign should run.

## 8. Scope

- **Sources**: all 3 (`burstgpt`, `azure_llm_2024`, `bailian_qwen`).
- **Regions**: `PRE_KNEE`, `KNEE`, `POST_KNEE`, `OVERLOAD`, `HIGH_PRESSURE`
  (5 of 6). `LOW` is excluded: the sealed primary campaign's own reversal
  output (`paper/generated/table_data/rq3_reversals.json`,
  `primary_metric_by_region_class_counts`) shows 0 of 36 supported
  practical reversals occur in `LOW`, so there is nothing there for a
  sensitivity check to stress-test. The other five regions each contain
  supported reversals (`PRE_KNEE`=6, `KNEE`=6, `POST_KNEE`=6,
  `OVERLOAD`=10, `HIGH_PRESSURE`=8, total 36) and are all retained —
  dropping `PRE_KNEE`/`POST_KNEE` would have discarded 12/36 (33%) of the
  reversal evidence base this extension exists to check, which would
  materially weaken the sensitivity claim.
- **Policies**: the 11 PRIMARY policies unchanged
  (`ranking_portability/analysis/contract.py::PRIMARY_POLICIES`) — no
  style-approximation policies in the headline design.
- **Windows**: all 40 frozen windows per source (identical to Phase-12,
  never resampled).
- **Repetition**: none. The simulator is deterministic given identical
  `Request`s (`docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md`:
  `SEED_SENSITIVITY_APPLICABLE = false`); each window's frozen
  `synthesis_seed` from the sealed campaign manifest is reused unchanged.

**Expected cells**: 3 SLO rules × 3 sources × 5 regions × 11 policies × 40
windows = **19,800**. Per-cell cost is the same cheap deterministic
simulator Phase-12 itself used (measured ≈15ms/cell locally, including
synthesis + load-rescaling + execution), not real hardware — comparable
order of magnitude to the sealed 18,720-cell campaign, but CPU-only and
expected to complete end-to-end in low tens of minutes on a single
machine, not hours.

## 9. Transfer / robustness statistics

**Primary — ranking robustness.** For each `(source, region)`, compare the
primary-rule policy ranking against each alternative-rule ranking (same
source, same region, same 40 windows) using the sealed, unmodified
`ranking_portability/analysis/ranking_analysis.py::compare_conditions`:
Kendall tau-b, Spearman rho, top-1 agreement, top-3 overlap, with
block-bootstrap CIs over the 40 windows as the resample unit. Bootstrap
count and CI level are **reused unchanged** from the sealed contract
(`BOOTSTRAP_RESAMPLES = 2000`, `BOOTSTRAP_CI_LEVEL = 0.95`) — not
reselected for this extension.

**Secondary — reversal persistence.** For every `SUPPORTED_PRACTICAL_REVERSAL`
in the sealed primary campaign's reversal output (frozen, read-only
reference copy: `configs/analysis/phase12_primary_reversals_reference.json`,
36 records), re-run the sealed, unmodified
`ranking_portability/analysis/reversal_analysis.py::classify_pairwise_reversal`
on the *same* source-pair/region/policy-pair using each variant's
recomputed per-window ANWG values, and classify as `PERSISTS` /
`DISAPPEARS` / `DIRECTION_CHANGE` / `BECOMES_UNSUPPORTED`.

**Practical-effect threshold.** Reused unchanged from the sealed contract:
margin > 10% of the losing policy's value in both directions, both CIs
exclude zero (`REVERSAL_PRACTICAL_MARGIN_FRACTION = 0.10`,
`REVERSAL_CI_LEVEL = 0.95`). This is dimensionally valid here because
every comparison in this extension is ANWG-vs-ANWG under different SLO
rules — the same dimensionless `[0, 1]` metric the threshold was frozen
for. (This is a materially different situation from a cross-metric
extension comparing heterogeneous units, where the same threshold would
need independent justification.)

**Multiple testing.** Benjamini-Hochberg FDR at `q = 0.05`
(`contract.py::FDR_Q`, reused unchanged), applied per `(variant, region)`
family, matching the sealed campaign's own family definition.

## 10. Pilot

Stamped `SLO_SENSITIVITY_PIPELINE_PILOT_NOT_HEADLINE_EVIDENCE`. Exercises
every variant, a representative source, and `KNEE` + `HIGH_PRESSURE`
(both non-trivial-reversal regions) with a small policy/window subset, to
validate the pipeline end-to-end (synthesis, variant transform, structural
validation, simulator execution, schema, output write, manifest
provenance) before the pushed freeze and before the full campaign.

## 11. Output namespace

`artifacts/analysis/slo_sensitivity/<campaign_manifest_sha256>/` —
disjoint from every sealed Phase-12 output path and from the pilot's own
subdirectory. Nothing under this extension modifies:
`artifacts/manifests/ranking_portability_phase12_campaign_freeze.json`,
`artifacts/manifests/ranking_portability_phase12_shard_plan.json`,
`src/robustbench/workloads/external/benchmark_synthesis.py`,
`src/robustbench/ranking_portability/execute_cell.py`, or any file under
`src/robustbench/ranking_portability/analysis/`.
