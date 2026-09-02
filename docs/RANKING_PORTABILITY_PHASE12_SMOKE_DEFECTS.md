# RANKING_PORTABILITY_PHASE12_SMOKE_DEFECTS.md

Defect record for the Phase-12A Pilot-V2 engineering smoke
(`docs/RANKING_PORTABILITY_PHASE12_SMOKE_FREEZE.md`,
`docs/RANKING_PORTABILITY_PHASE12_SMOKE_VALIDATION.md`).

## Defect 1: `kv_occupancy_max` telemetry validator too strict

- **Found:** first smoke run (468 cells), 100/468 cells (21.4%) failed
  schema validation with `telemetry.kv_occupancy_max out of [0,1]: <value>`
  (observed values 1.0031–1.0126, i.e. 0.3%–1.3% over nominal capacity).
- **Scope:** isolated entirely to the `azure_llm_2024_stage0_w00` window,
  across all 6 regions, for 8 of the 13 panel policies (`fifo`, `edf`,
  `least_laxity_first`, `estimated_service_time_first`,
  `weighted_fair_share`, `slai_faithful`, `admission_control`,
  `vllm_style_token_budget` — the last only partially) plus 4/12 cells of
  `kv_constrained_online`. Zero occurrences for `burstgpt_stage0_w00`,
  `bailian_qwen_stage0_w00`, or the `vllm_faithful` /
  `vllm_chunked_prefill_faithful` / `sarathi_faithful` / `scorpio_style_slo_guard`
  policies.
- **Root cause:** `kv_occupancy_{mean,max}` is computed as
  `kv_used / max_kv_tokens` per step
  (`src/robustbench/simulator/telemetry.py::compute_telemetry_summary`).
  Grepping the panel's policy implementations for `max_kv_tokens` shows
  several PRIMARY-panel policies (`fifo`, `edf`, `least_laxity_first`,
  `estimated_service_time_first`, `weighted_fair_share`,
  `admission_control`) never reference it at all — they admit purely on
  `max_active_sequences` (a concurrency-count bound), not on aggregate KV
  token demand. On `azure_llm_2024_stage0_w00` specifically, the mix of
  concurrently active requests' prompt/output token footprints can push
  aggregate KV demand slightly past the configured `max_kv_tokens` for
  these policies. This is genuine, real simulator state (a meaningful
  "demand exceeded nominal KV capacity" signal for non-KV-aware policies),
  not an instrumentation failure — the validator's assumption that
  `kv_occupancy` is always hard-bounded at 1.0 (true for
  `batch_saturation`, which every policy respects via the shared
  `max_active_sequences` admission check) was simply incorrect for this
  field given the panel's actual admission-control diversity.
- **Is this a frozen-scientific-protocol change?** No. It does not touch
  any policy's scheduling/admission behavior, any metric definition
  (`docs/RANKING_PORTABILITY_METRIC_DEFINITIONS.md`), the calibration
  contract (`docs/RANKING_PORTABILITY_PHASE11_CALIBRATION_FREEZE.md`), or
  any of the 5 immutable scientific hashes. It only relaxes an
  over-strict, previously-untested self-consistency bound inside the
  telemetry validator itself — telemetry is new instrumentation
  (`docs/RANKING_PORTABILITY_TELEMETRY_IMPLEMENTATION.md`) that had never
  before been exercised across the full 13-policy panel (Phase-11's
  calibration script never computed telemetry at all; Stage-0 predates
  the telemetry schema entirely) — this smoke is its first real test.
- **Fix:** `src/robustbench/simulator/telemetry.py` — `kv_occupancy_mean`/
  `kv_occupancy_max` now validated by a dedicated `_check_kv_occupancy`
  bound (`[0, 2.0]`, finite, non-negative) instead of the shared
  `_check_fraction` bound (`[0, 1.0]`) used for genuinely
  admission-bounded fractions (`batch_saturation_*`,
  `prefill_decode_contention_fraction`, `token_budget_saturation_fraction`,
  all left unchanged). The relaxed bound still rejects a genuine
  instrumentation failure (non-finite, negative, or a wildly out-of-range
  value such as the `5.0` used in the pre-existing
  `test_validator_rejects_out_of_range_fraction`-style tests) — it does
  not disable the check.
- **Regression tests added:** `tests/test_ranking_portability_telemetry.py`
  — `test_validator_tolerates_small_kv_occupancy_overshoot_above_one`,
  `test_validator_still_rejects_wildly_out_of_range_kv_occupancy`,
  `test_validator_still_rejects_negative_or_nonfinite_kv_occupancy`.
- **Re-run:** all 468 cells re-executed deterministically after the fix
  (same frozen inputs, same synthesis seeds, same load assignments) —
  0 failures, 0/468 schema/telemetry problems. See
  `docs/RANKING_PORTABILITY_PHASE12_SMOKE_VALIDATION.md`.
- **Full test suite after fix:** 218 passed, 0 failed
  (200 pre-existing + 15 Phase-12A smoke-contract tests + 3 new telemetry
  regression tests).

## No other defects found

No other engineering defect was found during this smoke. Matrix,
execution, frozen-input, metric, telemetry, and rep0/rep1 determinism
integrity all pass cleanly on the post-fix run.
