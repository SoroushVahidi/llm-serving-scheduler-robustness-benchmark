# REAL_SYSTEM_METRIC_MAPPING.md

Engineering preflight for `docs/REAL_SYSTEM_VALIDATION_PLAN.md`. Maps the
simulator's metric definitions to what the real-vLLM collection layer
(`real_llm/calibration_common.py` + `real_llm/vllm_openai_client.py`
against vLLM's OpenAI-compatible API) can actually observe. **No
scientific values appear in this document** — it is a schema/formula
mapping only, produced before the admitted Phase-12 analysis completes.

Timestamp points, per request, as instrumented by
`vllm_openai_client.call_streaming`:

- `t0` = monotonic clock immediately before the HTTP request is sent.
- `t_first_token` = monotonic clock when the first non-empty `delta.text`
  chunk arrives on the SSE stream.
- `t_done` = monotonic clock when the stream closes (`[DONE]` or the
  response context exits).

| Metric label | Simulator definition (`docs/STAGE0_METRIC_DEFINITIONS.md`, `core/types.py`) | Real-engine observable | Exact match / Approximate / Unavailable | Notes |
|---|---|---|---|---|
| Completed requests | `completion_time is not None` (simulator event) | HTTP 2xx response with a non-null `finish_reason` | EXACT_MATCH | Both count a request as completed only on a clean terminal event, not on client-side abandonment. |
| TTFT | Simulator: time from admission to first output token scheduled. | `t_first_token - t0` (streaming call only; non-streaming calls report `ttft_seconds=None` — see `vllm_openai_client.call_non_streaming`). | APPROXIMATE | Real TTFT includes HTTP connection/queueing overhead the simulator does not model; only comparable in *direction*, not absolute magnitude (per `docs/CLAIM_BOUNDARIES.md`, exact magnitude match was never a validation requirement). |
| End-to-end latency | `completion_time - arrival_time` | `t_done - t0` (`provider_request_latency_seconds` in `RequestResult`) | APPROXIMATE | Same overhead caveat as TTFT; real value also includes response-body transfer time for the full completion, which the simulator has no analogue for. |
| Request throughput | Completed requests / wall-clock window, computed post hoc over the simulator's event log. | Completed requests / wall-clock window, computed post hoc over `requests.jsonl` (`aggregate_results` in `calibration_common.py`). | EXACT_MATCH (as a computed aggregate; the underlying per-request timing is only APPROXIMATE, see above) | |
| Token throughput | `sum(output_tokens) / window` from the simulator's own token accounting. | `sum(usage.completion_tokens) / window`, where `usage.completion_tokens` is vLLM's own reported count (via `stream_options.include_usage`). | EXACT_MATCH for token *counts* (both are exact tokenizer-level counts, not proxies); APPROXIMATE for the *rate* for the same wall-clock-overhead reason as latency. | |
| SLO / goodput (`arrival_normalized_weighted_goodput`) | `sum(weight_i * 1[completion_time_i <= slo_deadline_i] for i in COMPLETED)` (`docs/STAGE0_METRIC_DEFINITIONS.md`). | UNAVAILABLE from the collection layer alone. | UNAVAILABLE | Requires an `slo_deadline` per request, which is a *synthesized* simulator-side field (`docs/DATA_FIELD_PROVENANCE.md`) — the real-engine client fixture would need to attach the same synthesized deadline to each request and compare it against the observed `t_done`, computed client-side, not returned by vLLM itself. Not implemented in this engineering task (no scientific workload attached yet). |
| p95 / p99 tail latency | Percentile of `completion_time - arrival_time` over the cell's completed requests. | Percentile of `provider_request_latency_seconds` over the cell's `requests.jsonl` rows (`calibration_common._percentile`). | EXACT_MATCH (as a computed aggregate over the same APPROXIMATE per-request latency values above) | |

## Explicitly not assumed identical

Per `docs/REAL_SYSTEM_VALIDATION_PLAN.md`'s "Explicitly not required"
section: an exact match between simulated and real absolute
latency/throughput values is never assumed or required. This mapping
exists so that later sign-agreement / Kendall-tau / reversal-agreement
statistics are computed on genuinely comparable *definitions*, not on
metrics that only share a name.

## Known collection-layer gap

`vllm_openai_client.call_non_streaming` cannot report TTFT (no
intermediate token boundary is observable in a non-streaming HTTP
response). Any future real-validation cell that needs TTFT must use the
streaming path.
