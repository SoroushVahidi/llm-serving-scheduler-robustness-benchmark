# RQ3_SYNTHETIC_TO_REAL_PROTOCOL_20260903.md

Pre-registered 2026-09-03, before any cell of this campaign is executed
against real reference data. **`POST_PHASE12_RESULT_INDEPENDENT_ANALYSIS_EXTENSION`**
-- this analysis was not part of the sealed Phase-12 analysis pipeline
(`research/lssp-phase12-analysis-prefreeze-20260902`, sealed at `eb574a8`
and re-sealed at `bd641d4`) and must never be described as if it had been
executed in that original pipeline. It is a new, independent extension
built on top of that sealed code, on a new branch
(`research/lssp-rq3-synthetic-to-real-prefreeze-20260903`), which does not
modify any sealed file.

## 0. Original RQ3 contract (reconstructed, not invented)

`docs/RESEARCH_QUESTIONS.md`:

> **RQ3.** To what extent do rankings obtained on synthetic stress
> workloads transfer to rankings on independent real-trace-derived
> workloads?

Class: **SECONDARY** (`docs/RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md` §1) --
deliberately never promoted to a headline RQ. `docs/OVERLAP_LEDGER.md`
classifies "Synthetic-to-real ranking transfer" as `NEW_CANDIDATE` (not a
named RQ in either prior manuscript) while noting the *generator*
(`workloads/synthetic.py` / `robustbench.workloads.synthetic` in this
repo) is `REUSED_INFRASTRUCTURE`. `docs/REAL_SYSTEM_VALIDATION_PLAN.md`
(written for RQ6, not RQ3) independently corroborates the same targeted
scale: "3-4 workload families: at minimum one synthetic stress family and
two independent real-trace-derived families" -- i.e. the same order of
magnitude this protocol adopts for RQ3, not a coincidence but the same
project-wide convention for "targeted, not exhaustive" secondary analyses.

**This protocol's scope is exactly this SECONDARY question, targeted, not
a recreation of any larger, never-executed synthetic-workload roadmap.**
No such larger frozen roadmap was found in this repository at any commit
inspected for this protocol (`docs/EXPERIMENT_CAMPAIGN_PLAN.md` describes
the real-source Phase-12 campaign only; no RQ3-specific campaign plan
document exists prior to this one).

## 1. Synthetic generator audit

`src/robustbench/workloads/synthetic.py` (`generate_workload(WorkloadConfig,
seed)` -> `List[Request]`, plus eight named presets) is the *only*
synthetic workload generator in this repository. Audit:

| Generator/family | Path | Status | Mechanism |
|---|---|---|---|
| `generate_workload` (engine) | `src/robustbench/workloads/synthetic.py:68` | **READY** | Configurable arrival process (poisson/bursty), prompt/output token distribution (lognormal/uniform/pareto), SLO-class mixture, prediction noise -- produces `robustbench.core.types.Request`, the exact type `ranking_portability.execute_cell.execute_cell` already consumes for real-source cells. No adapter needed. |
| `make_bursty_trace` | same file:198 | **READY** | Burst arrival (burst_factor=8.0, burst_fraction=0.15) |
| `make_heavy_tail_trace` | same file:183 | **READY** | Pareto prompt+output (heavy-tailed service demand) |
| `make_decode_heavy_trace` | same file:234 | **READY** | Short prompt / long output (decode-time length skew) |
| `make_mixed_slo_trace` | same file:254 | **READY** | Three-class SLO/priority heterogeneity |
| `make_prefill_heavy_trace` | same file:214 | **READY, not selected** | Long prompt / short output (prefill-time length skew -- the mirror of `make_decode_heavy_trace`; not adding both directions of the same axis keeps the panel to 4 mechanism-distinct families rather than 5 with two collinear ones) |
| `make_burst_heavy_tail_trace` | same file:274 | **READY, not selected** | Composite of two already-represented mechanisms (burst + heavy tail) -- excluded to keep each selected family attributable to one mechanism |
| `make_overloaded_prefill_trace` | same file:294 | **READY, not selected** | A single fixed high-load point, not a load-region-orthogonal family -- redundant with this protocol's own KNEE/HIGH_PRESSURE region axis |
| `make_medium_trace`, `make_small_debug_trace` | same file | **READY, not selected** | Debug/baseline traces, not stress mechanisms |

No `PARTIAL`, `SCAFFOLDING_ONLY`, `DEPRECATED`, or `UNVERIFIED` generator
exists -- every preset in this module is a complete, directly executable
generator. All parameters used below were frozen in this module before
this protocol existed (attached to Phase 1/1.5 engineering work, dated
before Phase-12), so none of them can have been tuned for an RQ3 outcome.

## 2. Frozen targeted design (do not recreate the huge roadmap)

**Four families, each one clear mechanism** (`src/robustbench/rq3/synthetic_families.py`):

| Family ID | Generator | Mechanism |
|---|---|---|
| `burst_arrival` | `make_bursty_trace` | Arrival-process burstiness/clustering |
| `heavy_tail_service` | `make_heavy_tail_trace` | Heavy-tailed prompt+output service demand |
| `decode_length_skew` | `make_decode_heavy_trace` | Short-prompt/long-output length skew |
| `priority_slo_heterogeneity` | `make_mixed_slo_trace` | Synthesized SLO/priority class heterogeneity |

"Correlated long prompts + tight deadlines" (a fifth candidate mechanism)
was considered and **rejected**: no existing frozen preset implements it,
and constructing one now would mean choosing new parameters after this
task already exists, which section D of the task instructions explicitly
forbids ("no parameter may be tuned after observing scheduler outcomes"
extends, in spirit, to "no family may be *defined* after this task began
if it requires new parameter choices").

- **N_FAMILIES = 4**
- **N_SEEDS_PER_FAMILY = 5** (`seeds = [0,1,2,3,4]`) -- each seed is one
  independent synthetic replicate window (`rq3_<family>_s<seed>`), the
  bootstrap unit on the synthetic side, mirroring how real-source windows
  are the bootstrap unit on the real side.
- **LOAD_REGIONS = (KNEE, HIGH_PRESSURE)** -- the minimal pair the task
  suggests. `KNEE` = 1.0x the window's own FIFO-calibrated `lambda_ref`;
  `HIGH_PRESSURE` = 1.5x `lambda_ref` -- the identical multiplier already
  used by `ranking_portability.calibration.REGION_FACTORS["HIGH_PRESSURE"]`
  and by the RQ6 real-vLLM calibration freeze
  (`real_HIGH_PRESSURE = 1.5 x real_lambda_ref`). Not all six Phase-12
  regions are used, per the task's explicit "do not run all six regions
  unless needed" instruction -- KNEE (saturation onset) and HIGH_PRESSURE
  (the region where Stage-0/Phase-12 found the most policy differentiation)
  are the two most informative for a targeted transfer check.
- **POLICIES = the 11 PRIMARY panel** (`docs/RANKING_PORTABILITY_POLICY_PANEL.md`),
  used verbatim -- `fifo, edf, least_laxity_first,
  estimated_service_time_first, weighted_fair_share, kv_constrained_online,
  vllm_faithful, vllm_chunked_prefill_faithful, sarathi_faithful,
  slai_faithful, admission_control`. No smaller "pilot-only" substitute
  panel is used; the pilot (section 6 below) uses this exact panel on
  fewer seeds, so pilot-vs-headline differ only in N, not in policy
  identity.
- **PRIMARY_METRIC = `arrival_normalized_weighted_goodput`** (HIGHER_BETTER,
  ALWAYS_DEFINED per `ranking_portability/schema.py`).
- **EXPECTED_RQ3_CELLS = 4 families x 5 seeds x 2 regions x 11 policies = 440.**

Calibration is computed once per (family, seed) using the *same*,
unmodified, policy-independent FIFO-bisection calibrator real sources use
(`robustbench.calibration.stage0_load_calibration.calibrate_window`) --
`fifo` only, 30 bisection iterations, log10 bounds [-2, 4], SLO-violation
threshold 0.5%, identical to Stage-0/Phase-11. This means no RQ3-specific
calibration logic was written; the same methodology real windows use is
applied unchanged to synthetic windows, and no policy under study
influences load selection.

Estimated runtime (measured directly, not guessed): one FIFO calibration
~2.3s/window (563-request bursty trace, 30 bisection iterations); one
`execute_cell` call ~0.06s. 20 calibrations + 440 cells: well under one
minute of CPU time total. **No Slurm/tmux job is used for this campaign**
-- it is the same deterministic CPU discrete-event simulator Phase-12
uses, at 1/42nd the cell count (440 vs 18,720), so it runs to completion
as a single local, foreground process faster than any job-scheduling
overhead would justify.

## 3. Synthetic -> real descriptor mapping (descriptor-driven, not outcome-chased)

| Synthetic family | Mechanism | Real descriptor it stresses | Parameterization source |
|---|---|---|---|
| `burst_arrival` | Arrival clustering | `interarrival_cv`, `burstiness_b`, `peak_short_window_arrival_rate_rps` (`src/robustbench/characterization/descriptors.py`) -- an axis present identically in all three real sources' outcome-blind characterization schema | `make_bursty_trace`'s frozen `burst_factor=8.0`/`burst_fraction=0.15` (Phase-1.5 engineering default, predates this protocol) |
| `heavy_tail_service` | Heavy-tailed prompt+output tokens | `prompt_tokens_cv`, `output_tokens_cv`, `total_tokens_gini`, `total_tokens_excess_kurtosis` -- **Bailian/Qwen is this family's closest real analog**: `docs/STAGE0_BURSTGPT_DIAGNOSTIC.md` §E reports Bailian's `output_tokens_cv` up to 5.62 and `prompt_tokens_cv` up to 2.21, the highest tail-heaviness of the three real sources (vs. BurstGPT's 0.03-0.62 and Azure's 0.84-1.02) | `make_heavy_tail_trace`'s frozen Pareto token distributions |
| `decode_length_skew` | Short-prompt/long-output skew | `output_tokens_mean`, `prompt_output_ratio_mean` -- **Azure-2024 and Bailian are the closer analogs** (both have long, high-variance outputs, mean 70-146 tokens, per the same diagnostic table); **BurstGPT is the natural low-analog/near-null comparison point**, since its output is documented as short and near-constant (mean often ~7, CV~0.00-0.09) -- the *opposite* profile this family stresses, an expected-a-priori contrast, not a post-hoc exclusion | `make_decode_heavy_trace`'s frozen prompt/output means (32/512) |
| `priority_slo_heterogeneity` | Synthesized SLO/priority spread | Not a source-native descriptor (SLO/priority is scheduler-synthesized identically for all three real sources' windows, per the outcome-blind-descriptor rule in `descriptors.py`'s own docstring) -- this family instead stresses the shared synthesis scheme's heterogeneity dimension, applicable symmetrically to all three sources | `make_mixed_slo_trace`'s frozen three-class (tight/medium/loose) mixture |

Every synthetic family is compared against **all three real sources x both
regions** (not just its "closest" analog) in section 5 below -- the table
above documents the a-priori expected direction of the strongest match,
it does not restrict which comparisons are computed. This avoids the
appearance of selecting only favorable comparisons after the fact.

## 4. Transfer statistic (frozen before any real-side data was read for comparison)

**Primary:** for each `(synthetic_family, real_source, real_region)`
condition (4 x 3 x 2 = 24 conditions; note `real_region` here always means
the *matching* region name -- a synthetic `KNEE` window is only ever
compared to a real `KNEE` window, never cross-region):

- Kendall's tau-b (`ranking_portability.analysis.stats.compare_rankings`,
  reused unchanged)
- Spearman's rho (same function)
- Top-1 agreement
- Top-3 overlap

computed on the mean-per-policy ranking (mean of
`arrival_normalized_weighted_goodput` across that side's windows: 5
synthetic seeds vs. up to 40 real windows), with a whole-window block
bootstrap (`N_BOOTSTRAP = 2000`, 95% CI, resampling synthetic seeds and
real windows independently and with replacement, recomputing the ranking
comparison on every resample) for the tau/spearman CIs.

**Why a new, small two-sided bootstrap wrapper instead of reusing
`block_bootstrap_ci` directly:** `block_bootstrap_ci` resamples one scalar
sequence and applies a scalar `statistic_fn` -- it was not written to
resample two independent, differently-sized window populations (synthetic
seeds vs. real windows) and recompute a *paired* ranking comparison on
each draw. `src/robustbench/rq3/transfer_stats.py` implements this as a
documented, minimal wrapper around the same reused primitive
(`compare_rankings`) rather than reimplementing rank correlation itself.

**Secondary:** policy-pair sign agreement on the same common panel and
same point ranking -- `sign(mean_synthetic(a) - mean_synthetic(b))` vs.
`sign(mean_real(a) - mean_real(b))`, restricted to pairs with no exact tie
on either side. No cross-metric unit-normalization question applies here
(unlike a cross-*metric* comparison): both sides use the identical metric
(`arrival_normalized_weighted_goodput`), so a plain sign-agreement rate is
dimensionally sound without inventing a margin threshold. **No
"reversal"/"practical disagreement" classification with an arbitrary
percent-margin threshold was defined** -- the task's own instructions
require verifying such a threshold is "dimensionally appropriate" before
adopting it, and since both sides already share units, a raw sign-based
statistic is simpler and equally informative; inventing a magnitude
threshold on top of it would add an unjustified free parameter. This
decision is documented here, not silently substituted for the outcome.

**Undefined handling:** `MIN_COMMON_POLICIES = 6` (of 11 PRIMARY) --
frozen for statistical validity (rank correlation over fewer than ~half
the panel is not meaningful), not tuned to outcomes. A condition with
fewer than 6 policies defined on both sides is marked
`UNDEFINED_INSUFFICIENT_COMMON_POLICIES` and never zero-imputed or
silently dropped from the output.

## 5. Real-side reference data (read-only, provenance-verified)

Real per-(source, region, policy, window) `arrival_normalized_weighted_goodput`
values are read directly (read-only; nothing regenerated, nothing
modified) from the validated Phase-12 consolidated result matrix on
Wulver: `/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-phase12-provenance-repair/artifacts/campaign_results_enriched/81fa3d9b48a22410/consolidated.json`
(18,720 cells; `campaign_freeze_sha256 = 81fa3d9b48a2241001e6820942d4542dcc5b5e30973ad9d2786e72972494f57a`,
`execution_repo_sha = 2b9a21fb58798292c95980d35d05e53b3c6f14f6`), filtered
to the 11 PRIMARY policies and the 2 selected regions (KNEE, HIGH_PRESSURE)
across all 3 real sources -- 40 real windows per (source, region), 66
(source, region, policy) rows total. This filtered extract is committed at
`artifacts/manifests/rq3/real_reference_conditions_20260903.json` (its own
provenance fields, including the source consolidated file's hash, travel
with it) so the RQ3 analysis pipeline's real-side input is itself frozen
and reproducible, not re-fetched non-deterministically on every run.

## 6. Pilot (engineering validation only, not headline scientific evidence)

**`RQ3_PIPELINE_PILOT_NOT_HEADLINE_SCIENTIFIC_EVIDENCE`**

The pilot exercises every synthetic family and both load regions with a
reduced seed count (2 seeds/family instead of 5) and the full 11-policy
panel: 4 families x 2 seeds x 2 regions x 11 policies = **176 pilot
cells**. It validates: synthetic generation, FIFO calibration, simulator
execution via the unmodified `execute_cell` path, schema validation
(`RankingPortabilityCellResult`/`validate_cell_result`), telemetry
presence, output-file writing, and that the analysis pipeline
(`scripts/rq3/run_rq3_analysis.py`) can consume the pilot's own outputs
end-to-end. It does **not** count as evidence for or against RQ3's
scientific question -- 2 seeds is too few for the frozen `N_BOOTSTRAP`
block bootstrap to be meaningful, by design.

**Pilot gate (PASS requires all):**
1. All 176 expected pilot cells present, `success: true`, no missing/duplicate keys.
2. No schema-validation failures (`error_category == "schema_validation_failed"` count == 0).
3. No telemetry errors (`validate_telemetry` passes on every cell, enforced inside `execute_cell` already).
4. Deterministic regeneration: re-running cell generation for the same (family, seed) reproduces the identical `requests_content_sha256`.
5. `scripts/rq3/run_rq3_analysis.py` runs against the pilot's own output directory without crashing and produces well-formed (if `UNDEFINED_INSUFFICIENT_COMMON_POLICIES`-flagged, since 2 seeds may fall below what full-scale interpretation would want -- structurally valid either way) output records.
6. Every cell's `repo_sha`/`calibration` provenance fields are present and non-empty.

If the pilot fails, only engineering is fixed -- no parameter, family, or
region choice above is altered in response to which rankings the pilot
happened to produce.

## 7. Freeze-before-execution sequence

1. This document + `configs/rq3/rq3_synthetic_to_real_20260903.json` +
   `src/robustbench/rq3/*` + `tests/test_rq3_synthetic_to_real.py` +
   `artifacts/manifests/rq3/real_reference_conditions_20260903.json` +
   the campaign manifest, committed and pushed as one "prefreeze" commit.
2. Only after that push: the pilot is run, gated, and reported.
3. Only after the pilot gate passes: the full 440-cell targeted campaign
   is run (still no Slurm/tmux needed, per the runtime estimate above) and
   the real transfer analysis is executed against the already-committed,
   already-hashed real reference extract.
