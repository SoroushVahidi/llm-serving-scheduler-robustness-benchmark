# RANKING_PORTABILITY_ANALYSIS_PLAN.md

Extends `docs/STATISTICAL_ANALYSIS_PLAN.md` (unchanged, reused verbatim
for §A–G's core statistics) with the pieces specific to
`docs/RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md`: a pre-registered reversal
effect-size threshold, the new telemetry schema, temporal/OOD design,
robustness plan, compute-budget options, and the real-system validation
summary. Resampling unit throughout remains the **workload window**
(unchanged).

## A. Ranking analyses (reuses `docs/STATISTICAL_ANALYSIS_PLAN.md` §A–B)

- Kendall's tau, Spearman's rho, top-k overlap (`k ∈ {1, 3}`, fixed here
  before outcomes — the task's requested `top-1`/`top-3`, tightened from
  the existing plan's `{3, 5}` to match) — computed per source pair, per
  load region, per metric, with block-bootstrap CIs (≥2,000 resamples of
  windows within a source).
- **Pairwise rank reversal, effect-size threshold (fixed before
  execution, not chosen after seeing results):** a reversal at a given
  (source-pair, window, load-region, metric) is counted as **practically
  meaningful** only if, in *both* directions:
  - the winning margin exceeds **10% of the losing policy's value** on
    that metric (mirrors the already-frozen Criterion-4 relative-range
    rule, `src/robustbench/stage0/analyzer.py::_relative_range_qualifies`,
    reused for consistency rather than inventing a new threshold), and
  - the block-bootstrap CI on the sign of the difference excludes zero at
    the 95% level.
  A reversal failing either test is recorded as a **microscopic/
  statistically-unsupported sign change**, reported separately, never
  pooled with meaningful reversals in a headline count.

## B. Global ranking heterogeneity

Friedman rank-sum test across sources (block = window, treatment =
policy) as an omnibus check before any pairwise decomposition, per metric
and load region — a pre-registered, standard, non-outcome-tuned choice
(no alternative omnibus test was compared against results to pick this
one).

## C. Sample complexity (reuses `docs/STATISTICAL_ANALYSIS_PLAN.md` §F)

Subsampling ladder `n ∈ {5, 10, 20, 30, 40}` (40 = full window count, §
protocol §4). For each `n`: probability of recovering the full-window
ranking (exact and top-k match), via ≥500 draws without replacement,
reported per source and per metric — plus the two comparisons the task
requests, both purely descriptive (no framing of either as "expected"):
- **(i)** more windows concentrated in one source (`n=40` from source X
  alone) vs.
- **(ii)** the same total window budget spread across all three sources
  (`n≈13` each) —
comparing which converges faster to a stable *cross-source* ranking
statistic (tau/top-k against the full 3×40 reference), not to a
single-source ranking.

## D. Temporal / OOD design

- **BurstGPT and Bailian/Qwen** have native (BurstGPT) or relative-only
  (Bailian) chronology (`docs/EVIDENCE_INDEPENDENCE_PLAN.md`). For
  BurstGPT: freeze `EARLY`/`MIDDLE`/`LATE` terciles by native timestamp
  over the 40-window sample, measure within-source RQ2 (temporal)
  portability using the same tau/reversal toolkit as §A, source held
  fixed. Bailian's relative-only chronology supports within-trace
  ordering but not a calendar-anchored split — label any Bailian temporal
  finding `RELATIVE_CHRONOLOGY_ONLY`, never presented as calendar-dated.
- **Azure 2024 vs. a later slice of Azure 2024's own collection window**
  (2024-05-10 to 2024-05-19, `docs/EVIDENCE_INDEPENDENCE_PLAN.md`) is this
  project's calendar-anchored temporal-OOD axis — kept separate from
  provider/domain OOD, per the task's explicit instruction not to
  conflate the two. Provider/domain OOD (a genuinely different source,
  e.g. Azure-2024 vs. Bailian) is RQ1's cross-source analysis, not
  relabeled as "temporal."
- TraceLab's provider/model split (Claude-family vs. Codex-family,
  `docs/TRACELAB_PROVENANCE_RESOLUTION.md`) is noted as a natural future
  domain-OOD axis once its adapter exists (§ protocol §3) — not used here.

## E. Mechanism telemetry (new cell fields)

Added to the pilot's `CellResult`-equivalent schema (extends
`src/robustbench/stage0/schema.py`'s pattern; `ALWAYS_DEFINED` unless
noted):

| Field | Definition | Class |
|---|---|---|
| `mean_queue_depth` | Mean count of admitted-but-not-yet-scheduled requests per simulator step | `ALWAYS_DEFINED` |
| `peak_queue_depth` | Max of the above over the run | `ALWAYS_DEFINED` |
| `batch_saturation_mean` | Mean(active batch size ÷ configured max batch size) | `ALWAYS_DEFINED` |
| `prefill_decode_contention_fraction` | Fraction of steps with both prefill-pending and decode-pending work simultaneously | `ALWAYS_DEFINED` |
| `mean_kv_occupancy` | Mean normalized KV demand relative to configured nominal KV capacity (reuses the existing `kv_pressure_proxy` computation at the simulator level, not the workload-descriptor level). **Not hard-bounded at 1.0** — corrected 2026-09-02 (`docs/RANKING_PORTABILITY_PHASE12_TELEMETRY_SEMANTIC_AMENDMENT.md`): only KV-aware policies enforce `max_kv_tokens` at admission, so this can legitimately exceed 1.0 for policies that do not. | `ALWAYS_DEFINED` |
| `admission_control_activations` | Count of admission-control rejections/deferrals (0 for policies with no such mechanism) | `ALWAYS_DEFINED` |
| `preemption_or_reorder_events` | Count of scheduling decisions that changed a previously-set order (0 for strictly-FIFO-committed policies) | `ALWAYS_DEFINED` |

All seven are `ALWAYS_DEFINED` (simulator-internal counters, defined even
at zero completions) — no new conditional-metric ambiguity is introduced
by adding them.

## F. Robustness plan (§16 of the task)

Distinguished explicitly as `ROBUSTNESS`, run on every RQ1/RQ2/RQ5
headline finding, never used to select which finding to report:

- High-fidelity-policy-only re-analysis (11-policy subset,
  `docs/RANKING_PORTABILITY_POLICY_PANEL.md`).
- Leave-one-source-out (report each RQ1 statistic recomputed on the
  remaining 2 sources).
- Window-size sensitivity (the §C sample-complexity ladder doubles as
  this check).
- Metric-definition sensitivity (§ `docs/RANKING_PORTABILITY_METRIC_DEFINITIONS.md`'s
  exclusion rule vs. a same-family "drop the whole condition instead of
  just the policy" alternative — reported as a sensitivity comparison,
  never used to pick which one is "the" result).
- Load-calibration sensitivity (recompute with the original 4-region grid,
  `LOW/PRE_KNEE/KNEE/OVERLOAD`, as a subset of the 6-region grid — checks
  whether the 2 added points change any headline conclusion).
- Temporal-split sensitivity (bisect instead of tercile the BurstGPT
  chronology; report whether RQ2's conclusion is split-boundary-sensitive).
- Excluding each policy family in turn (one mechanism family removed at a
  time) — checks whether any single mechanism family is silently driving
  a headline reversal/stability finding.
- SLO-definition sensitivity: reused unchanged from
  `docs/DATA_FIELD_PROVENANCE.md` item 3's existing alternative
  SLO-synthesis rule (`docs/EXPERIMENT_CAMPAIGN_PLAN.md` Stage 5), not
  redesigned here.
- Seed sensitivity: **not applicable** — this simulator is deterministic
  given identical inputs (Stage-0 precedent: rep0/rep1 verification, never
  an independent stochastic seed); noted explicitly so a reviewer does not
  expect seed-variance error bars where none exist by construction.

## G. Real-system validation (design only; reuses `docs/REAL_SYSTEM_VALIDATION_PLAN.md` unchanged)

That document's design (~4 representative schedulers spanning strata, 3–4
workload families including ≥2 independent real-trace sources, `PRE_KNEE`
+ `KNEE`/`OVERLOAD` recalibrated on the real engine, ≥5 repetitions,
sign-agreement + Kendall tau + reversal-agreement statistics) is adopted
verbatim for this pilot's RQ6. **Selection of the specific validation
cases** (which pair, which source, which load region) must be frozen
**after this pilot's simulated RQ1/RQ2 results exist** (so a real,
specific predicted reversal can be targeted) **but before any real-vLLM
run is executed** — the objective selection rule is: prefer (a) the
pairwise reversal with the largest bootstrap-CI-excluding-zero effect
size from §A, and (b) one representative *stable* ordering (largest tau,
smallest CI) as a null-result control, so validation isn't confined to
testing only positive findings.

## Compute options (§17 of the task)

| Design | Sources | Windows/source | Load regions | Policies | Reps | Cells | Est. CPU-core-hours |
|---|---|---|---|---|---|---|---|
| A — minimal | 3 | 40 | 4 (existing `LOW/PRE_KNEE/KNEE/OVERLOAD`) | 11 (PRIMARY only) | 2 | 10,560 | ~19 |
| **B — recommended** | 3 | 40 | 6 (§ protocol §5) | 13 (11 PRIMARY + 2 STYLE_APPROXIMATION robustness) | 2 | **18,720** | **~33** |
| C — 4-source expansion (not adopted) | 4 (+ Azure 2023) | 40 | 6 | 13 | 2 | 24,960 | ~44 |
| D — full future confirmatory (already documented, cited not relaunched) | 5 (+ TraceLab) | 40 | 4 | 13+2 secondary | 5 | ~520,000 | ~70–290 |

CPU-hour estimates use Stage-0's real measured per-cell costs
(`docs/STAGE0_LAUNCH_HANDOFF_20260901.md`: ~18–20s/cell for
`FAITHFUL_EXTERNAL` policies, ~0.1–0.6s/cell for the rest), applied to the
4 `FAITHFUL_EXTERNAL` policies in this panel (`vllm_faithful`,
`vllm_chunked_prefill_faithful`, `sarathi_faithful`, `slai_faithful`) vs.
the remaining 9. **Design B is recommended** (§ protocol §10): it
incorporates every redesign element (§5's denser grid, the full 13-policy
panel) at ~3.6% of Design D's cell count, appropriately scaled as a
*second pilot*, not a jump straight back to the full confirmatory
campaign.

Storage/sharding: reuses Stage 0's proven cost-aware
longest-processing-time-first shard balancer
(`scripts/stage0/stage0_harness.py::shard_cells`, already tested against
exactly this kind of 100x policy-cost skew) — no new infrastructure
needed at this scale.
