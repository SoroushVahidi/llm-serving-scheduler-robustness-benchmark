# REAL_VLLM_SLAI_FIDELITY.md

`REAL_VLLM_SCIENTIFIC_VALIDATION = NOT_STARTED`. No engineering smoke
result in this document is admissible as RQ6 scientific evidence.

## Frozen decode-hold invariants

Frozen BEFORE the forced-contention fixture below was run (see
`slai_priority.py`'s "FROZEN DECODE-HOLD SEMANTICS" docstring for the
restated -- not redefined -- trigger/duration/re-eligibility/state-effect/
tie-break semantics this section's invariants are checked against):

1. **TRIGGER**: under a state satisfying the hold condition, >=1 decode-
   ready, otherwise-runnable request is not scheduled this step.
2. **NO EVICTION**: a held request is never removed from the active/
   decode-ready set solely because of the hold.
3. **PROGRESS OF SELECTED WORK**: served requests' LST is refreshed.
4. **RE-ELIGIBILITY**: a held request becomes schedulable once `now >=`
   its (unchanged) LST.
5. **EVENTUAL PROGRESS**: every held request in a finite fixture is
   eventually served before the fixture ends.
6. **PRIORITY FIDELITY**: held/served sets match the real simulator
   policy's decision for the equivalent state, every step.
7. **DETERMINISM**: repeating the identical fixture reproduces an
   identical step-by-step decision trace (pure-function / shadow-
   scheduler level; see the live-server caveat in "Local real-vLLM
   contention test" below for what this means under real I/O timing).

All seven implemented as executable tests in
`tests/test_slai_decode_hold_invariants.py`; see "Unit-fixture and
invariant results" below.

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
| **Realizing a hold** (skip this request's decode iteration for one step, keep it fully active, no eviction) | No first-class vLLM API for this. Precedent found: `Scheduler.schedule()`'s decode loop already has a "skip without evict" branch (`next_decode_eligible_step`, used for PP+async cadence -- `vllm/v1/core/sched/scheduler.py` ~line 503), proving this concept exists in vLLM's own design, not fabricated for this port. | `LSSPSlaiVLLMScheduler.schedule()` temporarily removes held requests from `self.running`, calls `super().schedule()`, then restores them | **SEMANTICALLY_EQUIVALENT, validated under live GPU contention** (upgraded from APPROXIMATION_REQUIRED -- see "Local real-vLLM contention test" below: a purpose-designed fixture with `decode_limit=2` and 10 concurrent real requests produced 1600+ genuine `SLAI_HOLD` and ~490 `SLAI_RELEASE` events per run across 3 repetitions, all 10/10 requests completed every run, no crash/deadlock/starvation, clean shutdown, GPU memory returned to idle each time). | No audited interaction with per-step stats, async-scheduling invariants, or KV-connector metadata beyond what the smoke's absence-of-errors implies; not tested under multi-GPU, speculative decoding, or KV-connector-enabled configurations. |
| Leftover token-budget accounting for extra non-critical decodes (Step 4) | `self.max_num_scheduled_tokens` | Conservative estimate: `max_num_scheduled_tokens - len(served_critical)` | APPROXIMATION_REQUIRED | Does not replicate vLLM's own multi-factor budget accounting (chunked prefill, spec decode, encoder budget); could over- or under-estimate leftover capacity relative to the simulator's simpler `token_budget - num_batched_tokens`. |
| KV-block-space admission feasibility | vLLM's own `KVCacheManager` | Not ported -- left to vLLM's native admission/preemption logic | N/A BY DESIGN | Per `slai_faithful.py`'s own docstring, SLAI's memory model is unmodified Sarathi-Serve block management, not part of SLAI's algorithmic contribution; real hardware's actual KV capacity is vLLM's own concern, not something to re-simulate. |

## Core semantics representable? **YES.**

Every core SLAI mechanism (TBT-tiered admission, LST computation,
critical/non-critical decode-hold, and its live-engine realization via
temporary `self.running` exclusion) has an algorithm-level EXACT or
SEMANTICALLY_EQUIVALENT mapping, backed by real differential-test
evidence AND, for the decode-hold realization mechanism specifically, a
forced-contention live-GPU test showing 1600+ real `SLAI_HOLD` events
and ~490 real `SLAI_RELEASE` events per run across 3 repetitions, with
all requests completing and no errors. Remaining limitations (below) are
narrower engineering-completeness items (budget-accounting precision,
multi-GPU/spec-decode/KV-connector configurations not exercised,
cross-hardware confirmation not yet run), not open representability
questions.

## Files implemented

- `src/robustbench/real_llm/slai_plugin/slai_priority.py` -- pure
  algorithm core (LST, classification, admission ordering). No
  workload-specific or case-specific logic; identical regardless of
  caller.
- `src/robustbench/real_llm/slai_plugin/slai_vllm_scheduler.py` --
  `LSSPSlaiVLLMScheduler(vllm.v1.core.sched.scheduler.Scheduler)`,
  overriding only `add_request()` and `schedule()`. No other vLLM core
  source modified.

## Unit-fixture and invariant results

5 hand-crafted fixtures (1 request; tied class/tied arrival; mixed TBT
tiers; waiting-only varying prompt lengths; high-memory-pressure offset
switch) + 1 dedicated multi-step decode-hold scenario, each run against
the REAL `SlaiFaithfulPolicy` instance (not a reimplementation) and
compared to the shadow scheduler built only from `slai_priority.py`,
plus the 7 frozen invariants above (`tests/test_slai_decode_hold_invariants.py`),
including a purpose-designed forced-hold fixture (6 decode-ready
requests -- 2 tight/2 medium/2 loose TBT tiers -- with `decode_limit=2`;
derivation of why this must force a hold, not tuned by trial-and-error,
is in the fixture's own module docstring), a negative control
(`decode_limit=6 >= n_requests` => 0 holds), and boundary tests
(`decode_limit` at 5/6/7 against 6 requests; LST-equality inclusive
`>=` semantic).

```
N_FIXTURES = 6 (hand-crafted) + 4 (invariant-suite fixtures: forced-hold,
  negative-control, capacity-boundary, LST-equality-boundary) = 10
N_EXACT_MATCH = 10
N_MISMATCH = 0
```

Full step-by-step trace for the forced-hold fixture (STEP / NOW /
SIM_SELECTED / VLLM_SELECTED / SIM_HELD / VLLM_HELD / MATCH), all 9
steps MATCH=True:

```
   0  0.000  [1, 2]  [1, 2]  [3, 4, 5, 6]  [3, 4, 5, 6]  True
   1  0.050  [1, 2]  [1, 2]  [3, 4, 5, 6]  [3, 4, 5, 6]  True
   2  0.095  [1, 2]  [1, 2]  [3, 4, 5, 6]  [3, 4, 5, 6]  True
   3  0.150  [1, 2]  [1, 2]  [3, 4, 5, 6]  [3, 4, 5, 6]  True
   4  0.295  [1, 2]  [1, 2]  [3, 4, 5, 6]  [3, 4, 5, 6]  True
   5  0.400  [3, 4]  [3, 4]  [1, 2, 5, 6]  [1, 2, 5, 6]  True
   6  0.495  [1, 2]  [1, 2]  [3, 4, 5, 6]  [3, 4, 5, 6]  True
   7  0.600  [5, 6]  [5, 6]  [1, 2, 3, 4]  [1, 2, 3, 4]  True
   8  0.700  [1, 2]  [1, 2]  [3, 4, 5, 6]  [3, 4, 5, 6]  True
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

## Local vLLM startup smoke (light load, engineering only)

Initial smoke with vLLM's generous default `decode_limit=128` and 8
light requests: server starts, log confirms `Using custom scheduler
class ...LSSPSlaiVLLMScheduler`, 8/8 HTTP 200, clean shutdown, GPU
memory returned to the 15 MiB idle baseline. This smoke alone did NOT
prove decode-hold triggers (capacity never bound) -- superseded by the
forced-contention test below, which does.

## Local real-vLLM contention test (engineering only, NOT scientific evidence)

Purpose-designed fixture to force and observe the decode-hold path
under real engine contention, per the task's Section E: `LSSP_SLAI_DECODE_LIMIT=2`
(engineering-only env override, see `slai_vllm_scheduler.py`, never set
based on which workload is being served) + 10 concurrent synthetic
requests (`ENGINEERING_ONLY_NOT_SCIENTIFIC_EVIDENCE`: synthetic prompts,
no real trace, deterministic `contention_{i}`/`rep{N}_{i}` request IDs),
`max_tokens=60` (long enough to span many decode steps, so holding has
room to manifest repeatedly, not just once). `decode_limit=2 < 10`
concurrent decode-ready requests structurally forces contention, by the
same reasoning as the forced-hold unit fixture -- not tuned to a
scientific outcome.

Structured observability (`LSSP_SLAI_LOG_EVENTS=1`, an opt-in env flag;
unset/0 by default and fully inert -- see `slai_vllm_scheduler.py`'s
logger setup) emits `SLAI_HOLD` / `SLAI_RELEASE` / `SLAI_SCHEDULE`
events strictly AFTER each scheduling decision, so it cannot influence
scheduling; verified the plugin still passes all tests and the log
setup attaches its own handler to its own named logger only (does not
touch vLLM's root logger or its handlers).

Ran 3 repetitions (fresh server process each time, same fixture):

| Run | Requests completed | SLAI_HOLD events | SLAI_RELEASE events | Traceback/exception (plugin code) | GPU mem after shutdown |
|---|---|---|---|---|---|
| 1 | 10/10 | 1610 | 491 | 0 | 15 MiB (idle baseline) |
| 2 | 10/10 | 1608 | 492 | 0 | 15 MiB (idle baseline) |
| 3 | 10/10 | 1628 | 490 | 0 | 15 MiB (idle baseline) |

Every run: all 10 request IDs appear in BOTH the held set and the
scheduled set at least once (no request starved, none skipped
scheduling entirely); final log state shows `Running: 0 reqs, Waiting: 0
reqs` (clean drain, no orphaned requests); only traceback/exception log
line in any run is the same pre-existing, benign flashinfer/`deep_gemm`
optional-import warning seen in every prior session smoke test on this
machine (occurs at process startup, before the scheduler is invoked).

**Determinism, honestly scoped**: the *logical* decision rule
(`slai_priority.py`) is proven byte-for-byte deterministic via the pure-
function/shadow-scheduler tests above (invariant 7, `test_invariant_7_determinism_three_repetitions`,
exact trace equality across repetitions with no I/O involved). Across
the 3 *live-server* repetitions, event counts vary by a few percent
(1608-1628 holds) because real concurrent HTTP/thread scheduling
introduces run-to-run timing jitter in exactly which engine step each
request happens to arrive on -- this is expected, disclosed, and does
not indicate non-determinism in the scheduling *rule* itself, only in
real wall-clock request arrival timing, which was never claimed to be
controlled. All 3 runs are structurally identical: contention forced,
holds occur, releases occur, all requests complete, clean shutdown.

## Wulver GPU engineering smoke: STOPPED on a genuine version-compatibility gap

**Not performed.** Preflight found Wulver's existing real-vLLM
environment (`/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-real-vllm-prep-venv`,
built earlier this session) has **vLLM 0.11.0** (torch 2.8.0+cu126,
Python 3.9), materially different from the **vLLM 0.27.1** (torch
2.13.0+cu130, Python 3.12) validated locally:

- `vllm serve --help=SchedulerConfig` on Wulver's venv shows **no**
  `--scheduler-cls` or `--scheduling-policy` flag at all.
- `vllm/v1/core/sched/` on Wulver is missing `interface.py` and
  `request_queue.py` entirely (present in 0.27.1) -- the pluggable-
  scheduler-class (`SchedulerInterface`) and native priority-queue
  (`SchedulingPolicy.PRIORITY`) abstractions `LSSPSlaiVLLMScheduler`
  depends on do not exist in this installed version.

Per this task's explicit instruction ("If Wulver uses a materially
different scheduler API/version, STOP and report the compatibility
issue rather than silently adapting scientific semantics"), no attempt
was made to port, downgrade-test, or otherwise force compatibility. GPU
allocation itself was confirmed available (`debug_gpu` partition, 1 idle
A100 node) -- the blocker is purely the installed vLLM version, not
Wulver access or scheduling.

**Concrete next step for Wulver validation**: rebuild (or create a new)
Wulver venv pinned to vLLM 0.27.1 (matching the locally validated
version exactly, per `docs/REAL_VLLM_SLAI_FIDELITY.md`'s own
provenance discipline -- never silently substitute a "close enough"
version), then repeat this exact forced-contention fixture there for
Section O's cross-hardware semantic check.

**Superseded 2026-09-02**: a new venv (`.venv-lssp-vllm-0.27.1`, pinned
to vLLM 0.27.1 / torch 2.13.0+cu130 / Python 3.12, matching the local
validation exactly) was built for the RQ6 Wulver engineering gate
(`scripts/real_vllm/wulver_engineering_gate.sbatch`). Its own history is
three engineering/environment-preflight failures, none of them a
scientific result and none of them a scheduling-semantic problem:

1. **Job 1218904** (2026-09-02, exit 1, ~51s): crashed inside the
   gate's `_env_probe` step, immediately on startup, before any server
   was launched. `nvidia-smi --query-gpu=index,name,driver_version,`
   `cuda_version,memory.total` exits 2 on this node's driver
   (580.159.04): `Field "cuda_version" is not a valid field to query.`
   -- `cuda_version` is simply not a supported per-GPU CSV field on this
   nvidia-smi version, and the probe used `subprocess.check_output`,
   which raises on any nonzero exit. Confirmed via a standalone
   diagnostic (job 1219295): basic `nvidia-smi`, `nvidia-smi -L`, and
   the reduced query (`index,name,driver_version,memory.total`) all
   succeed on the same node/driver; only the `cuda_version` field is
   rejected. `torch.cuda.is_available()` was `True` throughout -- no
   driver or GPU fault. Fixed in commit `a1f8595`
   (`engineering/lssp-rq6-wulver-recovery-20260902`): the probe now
   queries only supported fields via a best-effort runner that never
   raises, and reads CUDA version from `torch.version.cuda` separately.
2. **Job 1219300** (2026-09-02, exit 1, ~5m33s): got past `_env_probe`
   (fix from job 1218904 applied) and both the `forced_hold` and
   `negative_control` fixture rounds -- both completed cleanly, all 6/6
   requests each, SLAI_HOLD/SLAI_RELEASE events observed as expected --
   then crashed in the `calibration_vllm_faithful` round with
   `ModuleNotFoundError: No module named 'pandas'` inside
   `calibration_common.aggregate_results`. The venv had `vllm`/`torch`
   installed directly but was never given the rest of this repo's
   declared runtime dependencies (`pandas`, `scipy`, and pandas's own
   `python-dateutil` dependency) -- an incomplete, undocumented,
   ad-hoc venv, not a code or scheduling defect. `pip check` was clean
   otherwise (torch/vllm pins untouched).
3. **Job 1219334** (2026-09-02, exit 0, ~4m21s, node n0111): replacement
   run from the same SHA (`a1f8595`) after installing `pandas`, `scipy`,
   and `python-dateutil` into the existing venv (verified via
   `pip install --dry-run` beforehand that this would not touch
   `numpy`/`torch`/`vllm`). **`pass_gate: true`** -- all four sub-gates
   (`forced_hold`, `negative_control`, `calibration_vllm_faithful`,
   `calibration_slai`) passed; 0 CUDA errors; 0 starved requests; clean
   shutdown on every round; the only `Traceback` occurrences in any
   server log are the same pre-existing benign `deep_gemm` optional-
   import warning and the expected `EngineDeadError` printed when the
   harness's own `handle.stop()` sends SIGTERM between rounds.

`REAL_VLLM_SCIENTIFIC_VALIDATION` remains `NOT_STARTED` at the time of
this update -- job 1219334 is
`STAMP=ENGINEERING_ONLY_NOT_SCIENTIFIC_EVIDENCE` per its own manifest,
same as every other fixture in this document. The reproducibility gap
that caused job 1219300 is now closed by
`requirements-real-vllm.txt` (pinned versions for the whole real-vLLM
stack, not just vllm/torch) and
`src/robustbench/real_llm/env_preflight.py`, which
`wulver_engineering_gate.py` now calls at the top of `main()` --
before any GPU allocation is used for a server -- so a missing
dependency now fails in milliseconds with an explicit module list
instead of after paying for a model load and two server rounds.

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
2. Leftover-budget accounting for extra non-critical decodes is a
   simplified estimate, not a full replica of vLLM's multi-factor budget
   logic.
3. KV-block-space admission feasibility is not ported (by design -- left
   to vLLM's own native mechanism, matching SLAI's own unmodified reuse
   of Sarathi-Serve's memory model).
4. Decode-hold realization is validated on a single local GPU
   (RTX 5060 Ti, vLLM 0.27.1) under a synthetic contention fixture; not
   yet cross-confirmed on Wulver hardware, and not exercised under
   multi-GPU, speculative decoding, or KV-connector-enabled
   configurations.
5. Live-server event counts (SLAI_HOLD/SLAI_RELEASE) vary run-to-run by
   a few percent due to real request-arrival timing jitter -- expected
   and disclosed, not a defect in the deterministic decision rule
   (proven separately via the pure-function/shadow-scheduler tests).
6. Local workstation requires `VLLM_USE_FLASHINFER_SAMPLER=0` (no system
   CUDA toolkit / `nvcc`); unrelated to the SLAI plugin itself, same
   environment note as the earlier `vllm_faithful` engineering smoke.
