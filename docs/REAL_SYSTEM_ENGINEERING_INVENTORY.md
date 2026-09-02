# REAL_SYSTEM_ENGINEERING_INVENTORY.md

Engineering-capability inventory produced while preparing
`docs/REAL_SYSTEM_VALIDATION_PLAN.md`'s infrastructure
(engineering-preflight task, `engineering/lssp-real-vllm-validation-prep-20260902`).
No scientific validation-case selection is made here.

| Capability | Status | Notes |
|---|---|---|
| vLLM launcher helper | READY (this task) | `real_llm/vllm_process.py`: starts/stops a local `vllm serve` subprocess, polls `/v1/models` for readiness, queries GPU memory via `nvidia-smi`. |
| Request replay driver / measurement plumbing | READY (reused) | `real_llm/calibration_common.py` — generic, provider-agnostic (`execute_one_request`, `run_requests`, `RpmLimiter`, `BudgetTracker`, `JsonlWriter`, resume-by-request-id) — already designated for reuse by `docs/REAL_SYSTEM_VALIDATION_PLAN.md`. |
| vLLM-specific call functions | READY (this task) | `real_llm/vllm_openai_client.py`: streaming + non-streaming call functions against vLLM's OpenAI-compatible `/v1/completions`, matching `calibration_common`'s injected-callable contract. |
| Workload-manifest readers | PARTIAL | `calibration_common.expand_call_plan`/`expand_call_plan_length_targeted` build a `PlannedRequest` list from bucket/token-count grids; no reader exists yet for the Phase-12-specific workload/window manifests (out of scope until scientific cases are frozen). |
| Latency/throughput parsers | READY (reused) | `calibration_common.aggregate_results`, `_percentile`, `_stats_block`. |
| Calibration scripts | PARTIAL (this task) | `real_llm/load_calibration_harness.py` provides the rate-ladder-driving harness; tested only against the fabricated fixture in this task (`ENGINEERING_CALIBRATION_SMOKE_ONLY = YES`). Real-engine knee determination is out of scope here. |
| Scheduler adapters (mechanism-specific server config) | PARTIAL | `vllm_process.start_vllm_server` exposes `scheduling_policy` / `enable_chunked_prefill`, covering the `REAL_NATIVE_PATH` mechanisms in `docs/REAL_SYSTEM_MECHANISM_INVENTORY.md`; `weighted_fair_share` has no adapter (no known native flag). |
| GPU reset/cache reset utilities | MISSING | No between-cell GPU cache/process reset utility exists yet; `vllm_process.VLLMServerHandle.stop()` provides clean process teardown, which is the main mechanism available (a fresh server process per cell is the simplest correct reset strategy pending further design). |
| Environment-recording utilities | READY (this task) | `real_llm/provenance.py::RealRunProvenance` — schema + `validate()`; population from live GPU/software inventory is manual/scripted per platform in this task (see the engineering environment manifest), not yet auto-collected by a single helper function. |
| Run-order / ABBA / resume orchestration | READY (this task) | `real_llm/cell_orchestration.py`: `deterministic_random_order`, `abba_order`, `CompletedLedger`, `filter_pending`, `unique_output_namespace`, duplicate-cell detection in `expand_cells_to_run_units`. Covered by 15 synthetic tests (`tests/test_real_llm_cell_orchestration.py`) against fabricated cell IDs only. |
| Metric semantics mapping | READY (this task) | `docs/REAL_SYSTEM_METRIC_MAPPING.md`. |
| Mechanism real-path inventory | READY (this task) | `docs/REAL_SYSTEM_MECHANISM_INVENTORY.md`. |
