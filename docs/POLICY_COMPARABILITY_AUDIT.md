# POLICY_COMPARABILITY_AUDIT.md

Every policy in `configs/policies/canonical_policy_registry.yaml` is
independently useful infrastructure (see `docs/PROVENANCE.md`), but not every
pair is fairly comparable in one leaderboard. This audit records, per policy,
its provenance class and known comparability caveats, and defines the
strata used when execution semantics differ materially.

## Provenance classes

- **`official_adapter`** — calls the real upstream system/API.
- **`faithful_reimplementation`** — from-scratch reimplementation pinned to a
  specific upstream commit/paper, validated against that reference's
  documented algorithm (not against real hardware traces).
- **`mechanism_reimplementation`** — implements a well-known scheduling
  discipline (FIFO, EDF, LLF, ...) with no single upstream system to pin to.
- **`inspired_proxy`** — a lightweight heuristic *inspired by* a named system
  but explicitly not a faithful reimplementation (e.g. `vllm_style_token_budget`
  is a token-budget proxy, distinct from `vllm_faithful`).
- **`scaffolding_only`** — interface/type scaffolding for a future faithful
  reimplementation; **not validated, not comparable to anything yet.**

## Per-policy status (primary panel candidates)

| Policy ID | Family | Provenance class | Comparable in PRIMARY analysis? | Caveats |
|---|---|---|---|---|
| `fifo` | Classical | `mechanism_reimplementation` | Yes | None. |
| `edf` | Classical (deadline) | `mechanism_reimplementation` | Yes | Requires SLO deadlines; on sources with no native SLO field, deadlines are synthesized (see `docs/DATA_FIELD_PROVENANCE.md`) — flag any result that depends on this. |
| `least_laxity_first` | Classical (deadline) | `mechanism_reimplementation` | Yes | Same SLO-synthesis caveat as `edf`. |
| `estimated_service_time_first` | Classical (SJF-family) | `mechanism_reimplementation` | Yes | Requires `predicted_output_tokens`; on real traces this is a synthesized prediction (source truth is hidden from the online policy by design — see `core/types.py: ObservableRequest`). |
| `weighted_fair_share` | Fairness | `mechanism_reimplementation` | Yes | None. |
| `kv_constrained_online` | KV-aware | `mechanism_reimplementation` | Yes | KV pressure is computed from the simulator's own `GPUConfig`, not from a real backend — see `docs/LOAD_CALIBRATION_PROTOCOL.md`. |
| `vllm_style_token_budget` | Serving-style proxy | `inspired_proxy` | Yes, but must be labeled as a proxy, not "vLLM" | Do not conflate with `vllm_faithful` in tables or prose. |
| `vllm_faithful` | Serving | `faithful_reimplementation` (pinned to vLLM commit `67d96c29`, pre-chunked-prefill) | Yes | Explicitly excludes chunked prefill, copy-on-write forking, swap-based preemption; not current-vLLM-equivalent. |
| `vllm_chunked_prefill_faithful` | Serving | `faithful_reimplementation` | Yes, in the "chunked-prefill era" stratum | Comparability with `vllm_faithful` (pre-chunked-prefill) across the SAME workload is itself part of what this benchmark can study, not assumed away. |
| `sarathi_faithful` | Serving | `faithful_reimplementation` | Yes | See stratum note above (chunked-prefill family). |
| `distserve_faithful` | Disaggregated P/D | `faithful_reimplementation` | **Secondary analysis only** | Requires disaggregated `GPUConfig.role` semantics that other policies do not use — put in a separate analysis stratum, never pooled into the single-GPU-colocated leaderboard without saying so. |
| `llumnix_faithful` | Migration | `faithful_reimplementation` | **Secondary analysis only** | Requires live cross-instance relocation semantics (`incoming_migrations`) unused by the rest of the panel; multi-instance-only comparison. |
| `apt_serve_faithful` | Hybrid-cache tiering | `scaffolding_only` | **No — excluded from PRIMARY panel** | Source docstring states this is "interface scaffolding... for Apt-Serve's upcoming implementation," not a complete faithful reimplementation, at the audited SHA. Must not be privileged or treated as validated (per project charter). Re-audit before any use beyond a labeled scaffolding note. |
| `slai_faithful` | SLO-aware | `faithful_reimplementation` | Yes | See `docs/slai_faithful_scheduler_reference.md` in the source repo for the pinned reference (not copied here; re-derive citation before publication). |
| `sarathi_style`, `orca_style`, `splitfuse_style` | Serving-style proxies | `inspired_proxy` | Yes, labeled as proxies | Same labeling discipline as `vllm_style_token_budget`. |
| `sola_style_state_aware`, `slai_style_phase_aware`, `scorpio_style_slo_guard` | Literature-inspired heuristics | `inspired_proxy` | Yes, labeled as proxies | Named "-style" in the source registry precisely because they are not pinned faithful reimplementations. |
| `tetriinfer_routing`, `tetriinfer_length_prediction`, `tetriinfer_paper_reimplementation` | Length-prediction routing | Mixed (`inspired_proxy` / `faithful_reimplementation` — re-verify per file) | Re-audit before inclusion | Not yet individually re-verified in this bootstrap; do not include in a confirmatory sweep without confirming which of the three is the faithful one. |
| `admission_control`, `aging_priority`, `adaptive_chunked_prefill`, `flow_control_stability`, `weighted_shortest_processing`, `slo_slack_score`, `shortest_output_first`, `shortest_prompt_first`, `greedy_token_fill`, `least_loaded`, `multi_bin_batching`, `random_feasible`, `first_fit`, `best_fit` | Classical / heuristic baselines | `mechanism_reimplementation` | Yes | Standard baseline set; no special caveats beyond the shared SLO/prediction-synthesis notes above. |
| `oracle_srtf` | Oracle (non-deployable) | `mechanism_reimplementation` | **Never in the deployable leaderboard** | Hindsight upper bound only; report separately as an envelope, never ranked against deployable policies. |

## Recommended PRIMARY panel (target: 10–15 policies)

`fifo`, `edf`, `least_laxity_first`, `estimated_service_time_first`,
`weighted_fair_share`, `kv_constrained_online`, `vllm_faithful`,
`vllm_chunked_prefill_faithful`, `sarathi_faithful`, `vllm_style_token_budget`,
`slai_faithful`, `scorpio_style_slo_guard`, `admission_control` — 13 policies,
all single-GPU-colocated, all comparable under one workload/load protocol.

## SECONDARY strata (never pooled into the primary leaderboard without saying so)

- **Disaggregated-execution stratum:** `distserve_faithful` (requires
  `GPUConfig.role`).
- **Migration stratum:** `llumnix_faithful` (requires multi-instance
  relocation).
- **Scaffolding / excluded:** `apt_serve_faithful` (not yet a validated
  reimplementation — see above).

## Fidelity classification (added 2026-08-31)

A second, orthogonal taxonomy to `provenance_class` above, used specifically
to define a **high-fidelity subset** on which primary confirmatory
conclusions must also be checked for robustness (i.e., a headline finding
that only holds when `STYLE_APPROXIMATION` policies are included is weaker
evidence than one that survives their removal).

- **`OFFICIAL_ADAPTER`** — calls a real upstream system/API directly.
- **`FAITHFUL_EXTERNAL`** — pinned reimplementation of a specific external
  system/paper (`provenance_class: faithful_reimplementation`, scaffolding
  excluded — see `apt_serve_faithful` below).
- **`REPOSITORY_NATIVE_CLASSICAL`** — a scheduling discipline with an
  identity independent of this repository (real-time-systems or OR
  scheduling theory: FIFO, EDF, LLF, ESTF/SJF-family, fair-share,
  admission control), implemented natively here with no single external
  system to pin to.
- **`SIMULATOR_PROXY`** — a mechanism invented for/native to this
  simulator's own abstractions (e.g. KV-block accounting), representing a
  general idea rather than a textbook algorithm or a named external system.
- **`STYLE_APPROXIMATION`** — an explicitly named "-style"/"-guard" proxy,
  disclaimed as inspired-by rather than faithful to a specific external
  system.

| Policy ID | Fidelity class |
|---|---|
| `fifo`, `edf`, `least_laxity_first`, `estimated_service_time_first`, `weighted_fair_share`, `admission_control` | `REPOSITORY_NATIVE_CLASSICAL` |
| `kv_constrained_online` | `SIMULATOR_PROXY` |
| `vllm_faithful`, `vllm_chunked_prefill_faithful`, `sarathi_faithful`, `slai_faithful` | `FAITHFUL_EXTERNAL` |
| `vllm_style_token_budget`, `scorpio_style_slo_guard` | `STYLE_APPROXIMATION` |
| `distserve_faithful`, `llumnix_faithful` (secondary stratum) | `FAITHFUL_EXTERNAL` |
| `apt_serve_faithful` | Not classified — excluded pending reimplementation (`scaffolding_only`, see above). |
| *(none currently)* | `OFFICIAL_ADAPTER` — no primary-panel policy calls a real upstream system/API at simulation time; `real_llm/calibration_common.py` is used for Stage 4 real-system *validation*, not as an in-simulator policy. |

### High-fidelity subset (primary panel minus `STYLE_APPROXIMATION`)

`fifo`, `edf`, `least_laxity_first`, `estimated_service_time_first`,
`weighted_fair_share`, `kv_constrained_online`, `vllm_faithful`,
`vllm_chunked_prefill_faithful`, `sarathi_faithful`, `slai_faithful`,
`admission_control` — **11 of 13** primary policies (still satisfies Go/No-Go
Gate C's "≥8 scientifically comparable policies" on its own). Every headline
RQ1–RQ6 confirmatory result must be checked for whether it still holds on
this 11-policy subset before being reported as robust to policy-fidelity
choice (`docs/STATISTICAL_ANALYSIS_PLAN.md`).

### JITServe inclusion investigation

`JITServe` (arXiv 2504.20068) schedules using *imprecise* request
information, refining its own internal estimate as generation proceeds
("grouped margin goodput maximization," relaxing conservatism over time).
This project's `ObservableGPUState.tokens_decoded_per_request` already
exposes, per step, how many tokens of each active request have been
decoded — the same kind of "generation-progress" signal JITServe's
refinement mechanism needs. **No fundamental semantic mismatch was
identified** that would block a good-faith reimplementation (unlike
`distserve_faithful`'s disaggregated-role requirement or `llumnix_faithful`'s
multi-instance requirement). JITServe is therefore recorded as a genuine
future-inclusion candidate in `canonical_policy_registry.yaml`'s
`candidates_not_yet_implemented` list, **not forced into the current panel**
— it requires a from-scratch implementation and independent validation
before any inclusion, same bar as `pars_serve`/`vllm_ltr`.

## Candidates requiring re-audit before any use

`tetriinfer_*` (three variants, unclear which is faithful vs. proxy at
bootstrap time), `PARS`/`PARS-Serve` and `vLLM-LTR` (named in the task
charter as candidates — no implementation exists in either source repo;
would need to be implemented from scratch and independently validated before
inclusion), `JITServe` (2026 system named in the charter as a candidate for
inclusion — no implementation exists yet; see `docs/RELATED_WORK_NOVELTY_AUDIT.md`
for the paper reference).
