# RANKING_PORTABILITY_TELEMETRY_IMPLEMENTATION.md

Implements the mechanism-activation telemetry preregistered in
`docs/RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md` section 8 /
`docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md` § E. Schema and collection
path only -- **no Pilot-V2 window is sampled, no load is calibrated, and
no scientific cell of the pilot is executed by this change.**

## Implementation map

| Preregistered field | Semantic definition | Simulator source | Aggregation | Always-defined? | Unit | Origin |
|---|---|---|---|---|---|---|
| `queue_depth_mean` / `queue_depth_max` | Requests admitted-but-not-yet-scheduled, sampled once per step right after enqueueing arrivals and before admission | `Simulator._waiting_queue_history` (pre-existing, already recorded for `contention_diagnostics_summary()`) | mean / max over all steps | Yes | requests (count) | per-step |
| `batch_saturation_mean` / `batch_saturation_max` | mean over GPUs of (active requests ÷ `max_active_sequences`) | `GPUState.step_active_counts` ÷ `GPUConfig.max_active_sequences` (pre-existing history; denominator fixed by config) | per-step cross-GPU mean, then mean/max over steps | Yes | fraction [0,1] | per-step, per-GPU |
| `prefill_decode_contention_fraction` | fraction of steps where at least one request is decoding AND at least one is prefilling, simultaneously | `GPUState.step_contention_diagnostics[i].num_decoding` / `.num_prefilling` (pre-existing, populated only in Phase-1.5 mode) | pooled across GPUs (same convention as `Simulator.contention_diagnostics_summary()`), fraction of pooled steps where both counts > 0 | Yes (0.0 when Phase-1/no separate prefill phase exists -- mechanism absent, not undefined) | fraction [0,1] | per-step, per-GPU |
| `kv_occupancy_mean` / `kv_occupancy_max` | mean over GPUs of (KV tokens used ÷ `max_kv_tokens`) | `GPUState.step_kv_used` ÷ `GPUConfig.max_kv_tokens` (pre-existing history; denominator fixed by config) | per-step cross-GPU mean, then mean/max over steps | Yes | fraction [0,1] | per-step, per-GPU |
| `admission_control_activations` | count of (waiting request, step) pairs where the request was not admitted despite at least one GPU having spare `max_active_sequences` capacity at decision time | NEW: `Simulator._record_admission_telemetry()`, called once per step right after `policy.select_action()` | running sum | Yes (0 whenever every waiting request either got admitted or no spare capacity existed) | count (int) | per-step |
| `preemption_or_reorder_events` | count of requests evicted via `Action.preempt`/`swap`/`migrate` and successfully applied | NEW: one-line accumulation of `len(evicted_ids)` (already computed by `_apply_preemptions`/`_apply_swaps`/`_apply_migrations`) inside `Simulator._apply_action()` | running sum | Yes (0 for any policy that never sets these Action fields -- true for every policy except `vllm_faithful`/`sarathi_faithful` [preempt], `distserve_faithful` [swap], `llumnix_faithful` [migrate]) | count (int) | per-step |
| `token_budget_saturation_fraction` | fraction of steps where consumed token budget ≥ configured `step_token_budget` | `GPUState.step_contention_diagnostics[i].budget_saturated` (pre-existing `StepContentionDiagnostics` property, populated only in Phase-1.5 mode) | pooled across GPUs, fraction of pooled steps saturated | Yes (0.0 when Phase-1/no token-budget model exists -- mechanism absent) | fraction [0,1] | per-step, per-GPU |

Every field above is computed by `robustbench.simulator.telemetry.compute_telemetry_summary()`, called post-hoc via the new `Simulator.telemetry_summary()` method -- the exact same convention as the pre-existing `Simulator.contention_diagnostics_summary()`.

## Instrumentation points and non-interference argument

Three, and only three, changes were made to `src/robustbench/simulator/simulator.py`:

1. **Two new zero-initialized counters** in `__init__`/`_reset`
   (`_admission_control_activations`, `_preemption_reorder_events`) --
   never read by `compute_metrics()` or any policy.
2. **One new line** inside `_apply_action()`, immediately after
   `evicted_ids = preempted_ids | swapped_ids | migrated_ids` (a value
   `_apply_action` already computed for its own eviction logic):
   `self._preemption_reorder_events += len(evicted_ids)`. Reads an
   already-computed value; writes only to the new counter.
3. **One new method call** per step in both `run()` and `continue_run()`,
   immediately after `action = policy.select_action(state)`:
   `self._record_admission_telemetry(state, action)`. This new method
   only *reads* `state.waiting_queue`, `action.admit`, and
   `g.num_active`/`g.config.max_active_sequences` for each GPU -- all
   already fully computed for this step -- and writes only to the new
   counter.

**No existing variable read by `compute_metrics()` is touched.**
`compute_metrics()`'s inputs are `completed`, `dropped`, `sim_duration`,
`gpu_utilization_history`, `active_batch_history`, `policy_decision_times`,
`idle_steps_skipped`, `num_total`, `all_requests` -- none of which this
change reads, writes, or reorders. No policy is called an extra time, no
queue is mutated, no admission/eviction decision is altered, and no
randomness is consumed (the simulator has none to begin with -- it is
fully deterministic given its inputs, confirmed by
`tests/test_ranking_portability_noninterference.py`'s repeated-run
determinism check). All 129 pre-existing tests (Stage-0's schema/runner/
analyzer/calibration suite, `test_anwg_metric.py`, `test_smoke_simulator.py`,
etc.) pass unchanged after this instrumentation -- if any had touched a
mutated code path, at least one numeric assertion would have failed.

**Known, documented approximation** (not a silent inaccuracy):
`admission_control_activations`'s "spare capacity" check uses only
`max_active_sequences`, not the fuller `max_batch_tokens`/`max_kv_tokens`
feasibility (`constraints.incremental_feasible`) a specific request might
also be blocked by. This keeps the check O(1) per waiting request per
step with zero extra function calls into execution-path code, at the cost
of occasionally counting a request as "declined despite spare capacity"
when it was actually infeasible for a KV/token-budget reason. Documented
here per `docs/RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md`'s "known
mismatches" requirement.

**Pre-existing registry gap fixed as a prerequisite, not a policy change:**
`vllm_chunked_prefill_faithful` and `slai_faithful` (both fully
implemented, pre-existing `BasePolicy` subclasses) were never wired into
any `name -> class` registry `make_policy_any()` checks -- the same class
of gap `tests/test_policy_registry_stage0.py` previously found and fixed
for `vllm_faithful`/`sarathi_faithful`. Fixed identically (two entries
added to `_FAITHFUL_REGISTRY`, `src/robustbench/policies/registry.py`) --
required for this change's own 13-policy fixture-coverage test
(`docs/RANKING_PORTABILITY_POLICY_PANEL.md`'s PRIMARY panel) to be able to
instantiate the full preregistered panel at all. Zero lines of either
policy class changed.

## Schema versioning / backward compatibility

`src/robustbench/ranking_portability/schema.py` is a **new, standalone
module** -- `src/robustbench/stage0/schema.py` (`stage0_cell_result_v1`)
is not imported, not modified, and not referenced by it in either
direction. `docs/RANKING_PORTABILITY_METRIC_DEFINITIONS.md`'s contract is
enforced by the new `validate_cell_result()`; telemetry is a required,
non-empty, schema-validated block (`ranking_portability_telemetry_v1`)
for every `success=True` cell -- a hard requirement Stage-0 never had.
`tests/test_ranking_portability_schema.py` proves both directions
explicitly: a historical-shaped Stage-0 cell (no `telemetry` key at all)
still validates under Stage-0's own unmodified validator, and a
Pilot-V2-shaped cell missing telemetry is rejected by the new validator.

## Storage estimate

`TelemetrySummary.to_dict()` is 12 scalar fields (~200-300 bytes as JSON,
~150 bytes packed). At the recommended Design B (18,720 cells,
`docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md` § Compute options), telemetry
adds roughly **18,720 × 250 B ≈ 4.7 MB** on top of the existing
`CellResult`-equivalent scalar fields (themselves low tens of MB per
`docs/EXPERIMENT_CAMPAIGN_PLAN.md`'s storage estimate at 10x this cell
count) -- negligible.

**Two-tier model, as required:**
- **Tier 1 (always persisted):** the 12-field scalar `TelemetrySummary`
  above, for all 18,720 cells -- what this implementation collects.
- **Tier 2 (not implemented here, deliberately):** full per-step event
  traces (every `StepContentionDiagnostics` record, every admission/
  preemption decision) are NOT persisted for every cell -- that would be
  tens of thousands of records per cell, turning an ~5 MB artifact into a
  multi-GB one with no corresponding scientific need for RQ1/RQ2/RQ5.
  `GPUState.step_contention_diagnostics` already exists in-memory during a
  run for exactly this purpose; a future, explicitly-scoped debugging or
  deep-dive analysis (e.g. re-running one specific flagged cell) can
  re-derive it on demand from `docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md`'s
  telemetry fields plus the frozen inputs, rather than pre-persisting it
  for all 18,720 cells.
