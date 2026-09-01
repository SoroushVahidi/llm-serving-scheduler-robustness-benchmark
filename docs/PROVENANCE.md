# PROVENANCE.md — Reused Infrastructure Ledger

This file records every source file copied or adapted from an existing repository
into this one. Per `docs/OVERLAP_LEDGER.md`, everything listed here is classified
as `REUSED_INFRASTRUCTURE` (generic engineering), not a reused scientific result.
Nothing here was committed to, or removed from, the source repositories.

## Source repositories audited

| Repo | Branch at audit time | Commit SHA | Working tree state |
|---|---|---|---|
| `SoroushVahidi/llm-serving-heuristic-evolution` | `contextual-compositional-heuristics-20260731` | `94f4621bb6610c2b426e365f659636b1a48a89f5` | Dirty, but confirmed (via `git status --short`) that **no file under `src/llmserveopt/` was modified/untracked** — every copied file reflects exactly this commit. |
| `SoroushVahidi/llm-serving-module-intervention-benchmark` | `private/sigmetrics2027-final-submission-ready-20260831` | `66c87ee88e84044ff1a47417add9f69345d83f63` | Clean. |

Both repos also carry a `no_push` remote pointing at `/dev/null` and/or were only
read from (never `git add`/`git commit`/`git push` executed against them during
this bootstrap). `git status`/`git log` in both were re-verified unchanged after
the copy.

## Why this code is infrastructure, not a reused result

Every module below is: (a) a mechanism implementation, data-ingestion adapter, or
simulation-engine primitive with no scheduler-comparison finding attached to it,
and (b) usable identically by any future scheduler-comparison research question,
including ones unrelated to this project's RQs. None of it contains the LLM 2026
manuscript's decision-criticality / SBS-VBS / exploitability numbers, or the
SIGMETRICS manuscript's module-intervention results.

**Explicitly excluded** (left in the source repo, not copied) because it *is*
tied to an existing scientific narrative: `llmserveopt/selector/*` (adaptive
selector, module-credit, suitability -- LLM 2026 selector line),
`llmserveopt/composition/*` and `policies/{genome,portfolio_gp,structural_synthesis,
primitive_composition_examples,composition,score_aggregation,capabilities}.py`
(portfolio/composition/synthesis line), `llmserveopt/policy_separation/*`
(the `public_trace_replay_v1` / `public_replay_load_scaling_v1`/`v2` load-scaling
experiments feed LLM 2026's decision-criticality analysis directly -- see
`docs/OVERLAP_LEDGER.md` row "load-dependent rank reversal"), `llmserveopt/analysis/*`
(joint240 / decision-criticality result scripts), `llmserveopt/heuristics/*` and
`llmserveopt/llm_generation/*` (LLM-evolved-heuristic DSL/generation, out of scope
per this project's charter), and everything under `module_intervention_benchmark/gate1/*`,
`benchmark_v2/*`, `real_vllm_prefill_validation/*` (SIGMETRICS module-intervention
results and its own real-vLLM validation).

## Reused components

### From `llm-serving-heuristic-evolution` @ `94f4621b`

| Original path (`src/llmserveopt/...`) | Destination (`src/robustbench/...`) | Verbatim / adapted | Reason it is infrastructure |
|---|---|---|---|
| `core/types.py`, `core/action.py`, `core/metrics.py` | `core/` | Adapted (package-name rename `llmserveopt`→`robustbench` only) | Generic request/GPU/action/metric dataclasses; no policy-comparison claims. |
| `simulator/simulator.py`, `gpu.py`, `request.py`, `service_model.py`, `service_model_factory.py`, `kv_block_manager.py`, `hybrid_cache_manager.py`, `constraints.py`, `contention_diagnostics.py`, `calibrated_service_model.py` | `simulator/` | Adapted (package rename) | Deterministic iteration-level simulation engine; a mechanism, not a result. |
| `policies/base.py`, `registry.py`, `feasibility.py`, `tie_breaking.py`, `policy_library_v2_helpers.py` | `policies/` | Adapted (package rename) | Policy interface, registry, and shared scoring/feasibility helpers used by every policy regardless of research question. |
| `policies/fifo.py`, `edf.py`, `least_laxity_first.py`, `estimated_service_time_first.py`, `weighted_fair_share.py`, `weighted_shortest_processing.py`, `kv_constrained_online.py`, `admission_control.py`, `aging_priority.py`, `shortest_output_first.py`, `shortest_prompt_first.py`, `greedy_token_fill.py`, `least_loaded.py`, `multi_bin_batching.py`, `random_feasible.py`, `first_fit.py`, `best_fit.py`, `slo_slack_score.py`, `adaptive_chunked_prefill.py`, `flow_control_stability.py`, `oracle.py`, `sola_style_state_aware.py`, `slai_style_phase_aware.py`, `scorpio_style_slo_guard.py`, `tetriinfer_routing.py`, `tetriinfer_length_prediction.py`, `tetriinfer_paper_reimplementation.py` | `policies/` | Adapted (package rename) | Classical scheduling-mechanism baselines / literature reimplementations, each independently citable; not an experimental finding. |
| `policies/vllm_style_token_budget.py`, `vllm_faithful.py`, `vllm_chunked_prefill_faithful.py`, `sarathi_style.py`, `sarathi_faithful.py`, `splitfuse_style.py`, `orca_style.py`, `distserve_faithful.py`, `llumnix_faithful.py`, `apt_serve_faithful.py`, `slai_faithful.py` | `policies/` | Adapted (package rename) | "Faithful" mechanism reimplementations pinned to specific upstream commits/papers (see `docs/POLICY_COMPARABILITY_AUDIT.md` for each one's validation status — several, notably `apt_serve_faithful`, are scaffolding-only and not yet a complete faithful reimplementation). |
| `evaluation/aggregate.py`, `compare.py`, `run_policy.py` | `evaluation/` | Adapted (package rename) | Generic single-policy-on-single-trace execution harness. |
| `calibration/benchmark_backend.py`, `curve_fitting.py`, `measurement.py`, `simulator_adapter.py`, `prompt_generator.py` | `calibration/` | Adapted (package rename) | Generic latency-curve calibration helpers, reused for `docs/LOAD_CALIBRATION_PROTOCOL.md`. |
| `real_llm/calibration_common.py` | `real_llm/` | Adapted (package rename) | Generic real-vLLM measurement helper, not a validation *result*. |
| `utils/jsonl.py`, `seeding.py` | `utils/` | Adapted (package rename) | Generic serialization/seeding utilities. |
| `workloads/synthetic.py`, `distributions.py` | `workloads/synthetic.py`, `workloads/distributions.py` | Adapted (package rename) | Generic synthetic-arrival/token-length generators used for the synthetic-stress side of RQ3 (synthetic-to-real transfer); contain no scheduler-outcome claims. |

### From `llm-serving-module-intervention-benchmark` @ `66c87ee8`

| Original path (`src/module_intervention_benchmark/workloads/...`) | Destination (`src/robustbench/workloads/external/...`) | Verbatim / adapted | Reason it is infrastructure |
|---|---|---|---|
| `schema.py` | `schema.py` | Verbatim | Canonical `ExternalWorkloadRecord` (Layer 1) with an explicit, honest `field_provenance` vocabulary (`SOURCE_OBSERVED`/`DETERMINISTIC_DERIVED`/`SYNTHESIZED_IMPUTED`/`UNAVAILABLE`) — exactly the discipline this project's charter requires (never treat a synthesized overlay as source-native) and independent of any scheduler-outcome claim. |
| `registry.py` | `registry.py` | Verbatim | A decorator-based name→adapter-class registry; zero science content. |
| `derived_features.py` | `derived_features.py` | Verbatim | Layer-2 deterministic derivatives (e.g. `long_context_flag`) computed *from* Layer-1 fields; documented as proxies, not scheduler results. |
| `adapters/base.py` | `adapters/base.py` | Verbatim | Abstract `TraceAdapter` interface. |
| `adapters/azure_llm.py` | `adapters/azure_llm.py` | Verbatim | Azure LLM Inference 2023/2024 CSV adapter (one class, `dataset_year` parameter distinguishes the two releases). |
| `adapters/burstgpt.py` | `adapters/burstgpt.py` | Verbatim | BurstGPT CSV adapter. |
| `adapters/mooncake.py` | `adapters/mooncake.py` | Verbatim | Mooncake JSONL adapter (kept for schema-parity only — see `docs/DATA_LICENSE_AUDIT.md` for why Mooncake stays `INTERNAL_ONLY`/excluded from any distributable output in this project). |
| `adapters/lmsys.py` | `adapters/lmsys.py` | Verbatim | LMSYS-Chat-1M adapter (secondary/optional source, not one of the five primary sources named in the project charter). |

Small synthetic, schema-equivalent CSV/JSONL fixtures used only by this
project's own tests were also copied from
`configs/external_workloads/fixtures/` — these are not real trace data (see
each adapter's docstring; the same statement holds in the source repo).

## Explicitly not copied (see `docs/OVERLAP_LEDGER.md` for the corresponding claim)

- `llmserveopt/policy_separation/public_trace_replay_v1.py`,
  `public_replay_load_scaling_v1.py`, `public_replay_load_scaling_v2.py`,
  `unified_utility_matrix.py`, and everything else under `policy_separation/`.
- `llmserveopt/analysis/*` (decision-criticality, joint240 result scripts).
- `llmserveopt/selector/*`, `llmserveopt/composition/*`.
- `module_intervention_benchmark/gate1/*`, `benchmark_v2/*`,
  `real_vllm_prefill_validation/*`, `release/*`.
- Any `paper/`, `results/`, or `experiments/` directory contents from either
  source repo.
- `adapters/lmcache_agentic.py` (agentic-workload adapter tied to a
  SIGMETRICS-specific scenario family; not one of this project's named sources).
