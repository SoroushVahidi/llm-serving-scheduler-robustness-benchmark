# REAL_SYSTEM_MECHANISM_INVENTORY.md

Engineering preflight for `docs/REAL_SYSTEM_VALIDATION_PLAN.md`'s "~4
representative schedulers/mechanisms" selection. Classifies each
candidate mechanism's REAL execution path by code inspection
(`docs/POLICY_COMPARABILITY_AUDIT.md`, `src/robustbench/policies/registry.py`)
and actual vLLM 0.27.1 CLI capability inspection (`vllm serve
--help=SchedulerConfig`, local workstation, 2026-09-02). **No comparative
benchmarking was performed** — this is a static capability audit only.

Classification vocabulary: `REAL_NATIVE_PATH` (an existing real serving
engine directly implements this scheduling behavior via a documented
config flag — only a launcher/adapter is missing, not the capability
itself), `REAL_REIMPLEMENTABLE_PATH` (approximable by tuning/composing
existing native flags, not an exact match), `SIMULATOR_ONLY` (no known
real-engine equivalent), `INCOMPLETE` (explicitly excluded or not yet a
validated reimplementation per the project's own audit), `UNKNOWN`
(not yet investigated).

| Mechanism | Stratum (`POLICY_COMPARABILITY_AUDIT.md`) | Classification | Evidence |
|---|---|---|---|
| `fifo` | `REPOSITORY_NATIVE_CLASSICAL` | `REAL_NATIVE_PATH` | vLLM 0.27.1 `SchedulerConfig` exposes `--scheduling-policy {fcfs,priority}`; `fcfs` = FIFO admission order. No launcher/adapter exists yet in this repo — `vllm_process.start_vllm_server(scheduling_policy="fcfs")` added this task, not yet exercised beyond a default-config smoke. |
| `vllm_faithful` (pinned to vLLM commit `67d96c29`, pre-chunked-prefill) | `FAITHFUL_EXTERNAL` | `REAL_NATIVE_PATH` (for the *current* vLLM release's non-chunked-prefill mode; not literally the pinned old commit) | `--no-enable-chunked-prefill` disables chunked prefill in vLLM 0.27.1. Running current vLLM with this flag is the closest real analogue, but is a different vLLM version than the faithfully-reimplemented commit — must be reported as "current vLLM, chunked-prefill disabled," never as identical to the pinned-commit simulator policy. |
| `vllm_chunked_prefill_faithful` | `FAITHFUL_EXTERNAL` | `REAL_NATIVE_PATH` | `--enable-chunked-prefill` (vLLM's current default). Directly running vLLM with default scheduler settings is the real analogue. |
| `sarathi_faithful` | `FAITHFUL_EXTERNAL` | `REAL_REIMPLEMENTABLE_PATH` | Sarathi-Serve's chunked-prefill + decode-prioritized batching ideas were substantially upstreamed into vLLM's own chunked-prefill scheduler, but there is no `--scheduling-policy sarathi` flag and no separate Sarathi-Serve engine available on either platform. Approximable via `--enable-chunked-prefill` plus `--long-prefill-token-threshold`/`--max-num-batched-tokens` tuning, but not an exact match to the simulator's faithful reimplementation — must be labeled an approximation if used. |
| `weighted_fair_share` | `REPOSITORY_NATIVE_CLASSICAL` | `SIMULATOR_ONLY` (as far as this inspection found) | No vLLM `SchedulerConfig` flag implements proportional weighted-fair-share scheduling; `--scheduling-policy priority` is priority-ordering, not weight-proportional sharing, and is not the same discipline. No real-engine adapter identified. |
| `admission_control` | `REPOSITORY_NATIVE_CLASSICAL` | `UNKNOWN` | Not yet investigated against vLLM's admission/queueing surface in this pass. |
| `apt_serve_faithful` | Hybrid-cache tiering (`scaffolding_only`) | `INCOMPLETE` | Explicitly excluded by the project's own `POLICY_COMPARABILITY_AUDIT.md` ("not yet a complete faithful reimplementation... must not be privileged or treated as validated"). Excluded from real validation for the same reason it is excluded from the simulator's primary panel. |

## Functional smoke performed in this task

For any mechanism above with a `REAL_NATIVE_PATH`, this task performed at
most a tiny functional smoke (server starts, the fixture's ~6 requests
flow, logs are produced, server exits cleanly) using **default**
scheduler settings — not one smoke per mechanism/flag combination, and
never a comparison between them. See the "Local vLLM smoke result" /
"Wulver vLLM smoke result" sections of the final report for which
platform(s) this ran on and its pass/fail outcome.

## Explicitly out of scope for this task

Selecting the final ~4 mechanisms for the scientific validation campaign,
tuning any scheduler-specific flag for realism, and running any
comparative benchmark between mechanisms. Those decisions are frozen
only after the admitted Phase-12 statistical analysis completes and
passes structural validation (`docs/REAL_SYSTEM_VALIDATION_PLAN.md`).
