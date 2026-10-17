# Experimental design

This is the completed LSSP Phase-12 simulation campaign reported in [the manuscript](https://www.researchsquare.com/article/rs-10935389/v1). Version 1.1.0 publishes more of its existing evidence. No experiments or analyses were rerun to prepare this package.

## Design and units

The workload window is the unit for statistical inference. The frozen design uses 120 windows of 200 requests, 40 from each of BurstGPT, Azure LLM Inference Trace 2024, and Bailian/Qwen. Each window is evaluated at six FIFO-calibrated operating regions: LOW, PRE_KNEE, KNEE, POST_KNEE, OVERLOAD, and HIGH_PRESSURE. Thirteen policies yield 120 × 6 × 13 = 9,360 policy–window–region configurations. Each configuration was executed twice with the same scientific inputs, producing 18,720 successful rows; the repeated pass is a deterministic verification, not an independent statistical sample. Forty synthesis seed values are reused across the 120 windows.

The eleven primary policies are fifo, edf, least_laxity_first, estimated_service_time_first, weighted_fair_share, kv_constrained_online, vllm_faithful, vllm_chunked_prefill_faithful, sarathi_faithful, slai_faithful, and admission_control. The vllm_style_token_budget and scorpio_style_slo_guard policies are style approximations used for robustness analysis. The policy registry table marks their panel status and fidelity class. Similar names do not imply identical external production schedulers.

The primary ranking metric is arrival-normalized weighted goodput (ANWG). Ten additional measured metrics cover completion, conditional goodput, latency, time to first token, throughput, and SLO behavior; [SCHEMA.md](SCHEMA.md) defines every released field. Some conditional metrics are undefined for valid rows and are retained as NaN, not zero. Telemetry records queue, batching, KV, prefill/decode, admission, and preemption behavior.

## Analysis

The six unchanged canonical files cover pairwise ranking reversals; rank correlations and omnibus statistics; sample-complexity resampling; explanatory telemetry models; temporal robustness; and top-k overlap. These are analyses of the same frozen campaign, not additional scheduler runs. Ranking and uncertainty comparisons are computed across workload windows; deterministic verification passes must not inflate sample sizes. The [repository methods and frozen analysis code](https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark) describe the statistical protocol. The public validator checks the original outputs and all convenience views but does not recalculate the statistical models.

## Simulator boundary

All 18,720 matrix rows are simulator outcomes under one frozen simulator configuration. The separately published selected physical RQ6 experiment covers 240 executions and is not in this matrix. Its largest predicted Azure/BurstGPT reversal was not reproduced physically, which limits claims about hardware transfer. See [LIMITATIONS.md](LIMITATIONS.md).
