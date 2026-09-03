# REAL_VLLM_SLAI_FIDELITY.md

`REAL_VLLM_SCIENTIFIC_VALIDATION = NOT_STARTED`. No engineering smoke
result in this document is admissible as RQ6 scientific evidence.

## Simulator source of truth

`src/robustbench/policies/slai_faithful.py::SlaiFaithfulPolicy` -- a
faithful reimplementation of the SLAI scheduler from "Optimal Scheduling
Algorithms for LLM Inference: Theory and Practice" (Bari, Hegde, de
Veciana; arXiv:2508.01002), pinned to `github.com/agrimUT/SLAI`
@ `5098a7a`. Read in full for this task (469 lines); algorithm summary:

- **Admission ordering**: waiting requests sorted by `(tbt(class_id),
  prompt_tokens, request_id)` ascending (TBT-tiered shortest-prompt-first;
  degenerates to FCFS if `fcfs=True`). `tbt(class_id)` is a disclosed,
  non-paper-sourced 3-tier mapping (`{"tight"/"interactive"/"critical":
  0.1, "medium"/"standard": 0.3, "loose"/"batch": 0.5}` seconds).
- **Last-schedulable-time (LST, Eq. 8)**: `lst = now + tbt(req) - offset *
  step_size`, assigned the instant a request becomes decode-ready and
  refreshed every time it is actually served a decode step.
- **Critical/non-critical classification**: a decode-ready request is
  *critical* iff `now >= lst`; critical requests are served first (up to
  `decode_limit`), non-critical requests fill any leftover
  budget/decode-slot capacity in ascending-LST order, and any non-critical
  request that doesn't fit is *held* -- its decode iteration is skipped
  this step, but it remains fully active (no eviction, no KV loss).
- **Offset (Theta)**: `5` below 96% KV utilization, `10` at/above it
  (dynamic-offset variant, the paper's flagship configuration).
- **Memory model**: identical to Sarathi-Serve's (chunked-prefill KV
  block-space management), reused unchanged -- SLAI's algorithmic
  contribution is the priority/LST logic above, not block management.
- RAD (the other scheduler in the same paper) is explicitly NOT part of
  this port -- see `slai_faithful.py`'s own docstring for why (no
  deployable reference implementation exists even in the pinned repo).

## Simulator -> vLLM fidelity map

Installed vLLM version inspected directly at
`/home/soroush/modal-venv/lib/python3.12/site-packages/vllm` (**0.27.1**,
torch 2.13.0+cu130, CUDA 13.0) -- source read, not generic online
examples for a possibly-different version.

| Simulator concept | vLLM observable/hook | Mapping | Fidelity | Limitation |
|---|---|---|---|---|
| Admission-order sort key `(tbt, prompt_tokens, request_id)` | `--scheduling-policy priority`'s heap (`vllm/v1/core/sched/request_queue.py`), ordered by `(Request.priority, arrival_time)` | `Scheduler.add_request()` override sets `request.priority = tbt + prompt_tokens * 1e-6` | SEMANTICALLY_EQUIVALENT | Collapses a 3-key tuple sort into 1 scalar; bounded-safe for this project's TBT tiers (0.2s apart) and any realistic prompt length (<200k tokens) -- disclosed in `slai_priority.admission_priority_scalar`'s docstring, not silently assumed exact. |
| LST computation (Eq. 8) | pure function, no vLLM state needed | `slai_priority.compute_lst` | EXACT | None -- differential-tested (below) against the real policy across 1000 synthetic (now, class, kv_util) triples, 0 mismatches. |
| Critical/non-critical classification + decode-hold decision | pure function operating on decode-ready requests' LSTs | `slai_priority.classify_and_order_decodes` + `select_served_decodes` | EXACT (algorithm level) | Differential-tested against the real, stateful simulator policy across a genuine multi-step, tight-decode-limit scenario that forces real holding -- 0 mismatches (see Test results below). |
| **Realizing a hold** (skip this request's decode iteration for one step, keep it fully active, no eviction) | No first-class vLLM API for this. Precedent found: `Scheduler.schedule()`'s decode loop already has a "skip without evict" branch (`next_decode_eligible_step`, used for PP+async cadence -- `vllm/v1/core/sched/scheduler.py` ~line 503), proving this concept exists in vLLM's own design, not fabricated for this port. | `LSSPSlaiVLLMScheduler.schedule()` temporarily removes held requests from `self.running`, calls `super().schedule()`, then restores them | APPROXIMATION_REQUIRED | **Not validated under live engine load that actually triggers holding.** Basic operational smoke (below) used generous `decode_limit` defaults and 8 light requests, which did not necessarily exercise this exact code path. Possible unaudited interaction with per-step stats, async-scheduling invariants, or KV-connector metadata that assume every previously-running request appears in `scheduler_output` each step. |
| Leftover token-budget accounting for extra non-critical decodes (Step 4) | `self.max_num_scheduled_tokens` | Conservative estimate: `max_num_scheduled_tokens - len(served_critical)` | APPROXIMATION_REQUIRED | Does not replicate vLLM's own multi-factor budget accounting (chunked prefill, spec decode, encoder budget); could over- or under-estimate leftover capacity relative to the simulator's simpler `token_budget - num_batched_tokens`. |
| KV-block-space admission feasibility | vLLM's own `KVCacheManager` | Not ported -- left to vLLM's native admission/preemption logic | N/A BY DESIGN | Per `slai_faithful.py`'s own docstring, SLAI's memory model is unmodified Sarathi-Serve block management, not part of SLAI's algorithmic contribution; real hardware's actual KV capacity is vLLM's own concern, not something to re-simulate. |

## Core semantics representable? **YES, with one disclosed, unvalidated engineering item.**

Not a STOP condition: every core SLAI mechanism (TBT-tiered admission,
LST computation, critical/non-critical decode-hold) has an
algorithm-level EXACT or SEMANTICALLY_EQUIVALENT mapping with real
differential-test evidence. The one item without live-engine validation
(realizing a hold via temporary `self.running` exclusion) has a
documented precedent in vLLM's own scheduler design and did not crash or
error in an initial operational smoke test, but has not been exercised
under conditions where it actually binds on real hardware. This is
reported as the specific, scoped remaining item, not a fundamental
representability blocker.

## Files implemented

- `src/robustbench/real_llm/slai_plugin/slai_priority.py` -- pure
  algorithm core (LST, classification, admission ordering). No
  workload-specific or case-specific logic; identical regardless of
  caller.
- `src/robustbench/real_llm/slai_plugin/slai_vllm_scheduler.py` --
  `LSSPSlaiVLLMScheduler(vllm.v1.core.sched.scheduler.Scheduler)`,
  overriding only `add_request()` and `schedule()`. No other vLLM core
  source modified.

## Unit-fixture results

5 hand-crafted fixtures (1 request; tied class/tied arrival; mixed TBT
tiers; waiting-only varying prompt lengths; high-memory-pressure offset
switch) + 1 dedicated multi-step decode-hold scenario, each run against
the REAL `SlaiFaithfulPolicy` instance (not a reimplementation) and
compared to the shadow scheduler built only from `slai_priority.py`.

```
N_FIXTURES = 6
N_EXACT_MATCH = 6
N_MISMATCH = 0
```

## Differential-test results

Fixed seed `20260902` (chosen before any test was run).

```
seed = 20260902 (admission ordering), 20260901+1 (LST/classification)
n_generated_states = 1000 + 1000 (two independent axes)
comparison_coverage = admission ordering (1000/1000 states with >=1
  waiting request contribute a comparison); LST + critical/non-critical
  classification (1000/1000 states)
exact_match_rate = 100% on both axes (0 mismatches)
exclusions = none
```

Plus the dedicated multi-step decode-hold differential test (4 steps,
6 requests, `decode_limit=2`, run against the real stateful policy
instance): 0 mismatches on served/held sets at every step.

## Local vLLM startup + load smoke (engineering only, NOT scientific evidence)

- Model: `Qwen/Qwen2.5-0.5B-Instruct` (engineering fixture, not a
  scientific model choice).
- Command: `vllm serve Qwen/Qwen2.5-0.5B-Instruct --scheduling-policy
  priority --scheduler-cls
  robustbench.real_llm.slai_plugin.slai_vllm_scheduler.LSSPSlaiVLLMScheduler
  ...` (`VLLM_USE_FLASHINFER_SAMPLER=0`, see local-environment note below).
- Server log confirms: `Using custom scheduler class
  robustbench.real_llm.slai_plugin.slai_vllm_scheduler.LSSPSlaiVLLMScheduler`.
- `REQUESTS_COMPLETED = 8/8` (8 concurrent completions requests, HTTP 200
  each), no traceback/exception from plugin code (the only
  traceback/exception log lines are the same pre-existing, benign
  flashinfer/`deep_gemm` optional-import warning seen in every prior
  session smoke test on this machine, occurring before the scheduler is
  even invoked).
- Clean shutdown (SIGTERM, exited in 2s); GPU memory returned to the same
  15 MiB idle baseline as before the run.
- **Caveat**: `decode_limit` used its generous simulator default (128)
  and only 8 short (`max_tokens=16`) requests were sent -- this smoke
  very likely never exercised the decode-hold code path under real
  contention. It validates operational integration (loads, serves,
  shuts down cleanly), not the specific unvalidated mechanism above.

## Wulver GPU engineering smoke

**Not performed in this task.** The local smoke already surfaced the one
specific remaining validation item (decode-hold under real trigger
conditions); submitting a Wulver GPU job would not add information until
a smoke scenario is designed that actually forces holding (a tight
`decode_limit` + enough concurrent decode-ready requests), which was not
built in this task. Recorded as the concrete next engineering step
(below), not skipped for a scientific reason.

## Calibration-harness readiness (audited, not executed)

`src/robustbench/real_llm/load_calibration_harness.py` (built in an
earlier engineering-prep pass this session) accepts model, workload
manifest, rate ladder, concurrency bounds, and repetitions, and drives
`calibration_common.run_requests` against a live server -- it does not
read or copy the simulator's `lambda_ref`; the real engine's own
saturation point must be determined from its own measurements. Not
exercised against the SLAI scheduler in this task (engineering-only
fabricated calibration was in scope; not performed here for time budget
reasons -- flagged as a remaining item, not silently skipped).

## Future RQ6 provenance

`src/robustbench/real_llm/provenance.py::RealRunProvenance` (built in an
earlier engineering-prep pass) already covers every field
Section P of the engineering task requires (repo/protocol/hardware SHAs,
full software-version stack, model/scheduler/workload identity, run-order
and repetition metadata, timestamps). Extending it with a
`slai_plugin_git_sha` field is a one-line addition, not yet made pending
confirmation this is the final plugin location.

## Known fidelity limitations (for the future RQ6 limitations section)

1. Admission-priority collapses a 3-key sort into 1 scalar (bounded-safe,
   disclosed).
2. Decode-hold's vLLM-side realization mechanism is unvalidated under
   real trigger conditions on hardware.
3. Leftover-budget accounting for extra non-critical decodes is a
   simplified estimate, not a full replica of vLLM's multi-factor budget
   logic.
4. KV-block-space admission feasibility is not ported (by design -- left
   to vLLM's own native mechanism, matching SLAI's own unmodified reuse
   of Sarathi-Serve's memory model).
5. Local workstation requires `VLLM_USE_FLASHINFER_SAMPLER=0` (no system
   CUDA toolkit / `nvcc`); unrelated to the SLAI plugin itself, same
   environment note as the earlier `vllm_faithful` engineering smoke.
