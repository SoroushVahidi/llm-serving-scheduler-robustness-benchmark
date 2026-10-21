# MGPU02 — scheduler semantic compatibility and implementation

2026-10-21. Scope: engineering compatibility, CPU-side validation and preparation
of one full-A100 smoke. **No GPU job submitted, no GPU inference, no new physical
ranking evidence.** MGPU00/MGPU01 evidence and frozen historical data are unchanged.
The base reviewed commit is `8d786d60c65c47c39e807f6f865570b2f4f30daf`.

## Recommendation and evidence

Use **vLLM 0.27.1 and the same pinned Qwen model, with chunked prefill enabled,
but an explicitly restricted whole-prefill contract** (`mgpu02-whole-prefill-v1`).
This is a bounded variant of approach A combined with C's execution-configuration
option. It is not general chunked-SLAI support. Both native and SLAI engines
reject splits, resumed prefills, KV admission differences and preemption.

This is the smallest defensible step toward a physical mechanism smoke. It keeps
the decoder/model, precision, fixture, class transport, SLAI decision core and
native baseline version. It changes an unsupported flag to its supported setting
and adds a sufficient no-split bound, actual-native differential tests and
execution checks. It does not claim to solve general scheduler portability.
No broader research question was substituted or new manuscript claim introduced.

Seven relevant installed files were inspected: engine argument support predicate,
model support predicate, scheduler configuration, scheduler implementation,
request queues, requests, and KV manager. Their SHA-256 hashes agree between the
workstation installation, a new bounded read-only cluster login-node inspection,
and upstream tag v0.27.1. See
[upstream manifest](../../artifacts/mgpu02/source-inspection/upstream.json) and
[cluster manifest](../../artifacts/mgpu02/source-inspection/remote.json).
The runtime smoke checks these source pins before GPU probing.

Authoritative sources and interpretation:

- [v0.27.1 argument support predicate](https://github.com/vllm-project/vllm/blob/v0.27.1/vllm/engine/arg_utils.py#L2599)
  warns when a generation model supports chunking but the flag is disabled.
  [Model support predicate](https://github.com/vllm-project/vllm/blob/v0.27.1/vllm/config/model.py#L1906)
  covers ordinary decoder generation models generally; this is not a
  Qwen-size-specific exception. Encoder-decoder generation and some pooling
  models follow different paths.
- [v0.27.1 scheduler](https://github.com/vllm-project/vllm/blob/v0.27.1/vllm/v1/core/sched/scheduler.py#L437)
  schedules running requests before waiting ones. Token/threshold truncation can
  split prefills. `num_computed_tokens` advances at scheduling, before execution;
  it alone cannot prove that model execution completed. The adapter therefore
  checks subsequent runner output and native completion state separately.
- [v0.27.1 optimization documentation](https://docs.vllm.ai/en/v0.27.1/configuration/optimization/#chunked-prefill)
  describes decode-first chunking and KV recomputation under pressure. Its generic
  tuning advice does not supersede model-dependent unsupported-flag warnings.
- [Pinned SLAI source](https://github.com/agrimUT/SLAI/blob/5098a7aba05e3edbcfa3a509d6cc9cd248fc4380/sarathi/core/scheduler/slai_scheduler.py)
  has critical decodes, paused prefills, new admissions, then residual decodes;
  its memory-pressure victim rules differ from native vLLM. Implementing paused
  prefills alone would not establish general algorithm fidelity. Source identity
  is in [the reference hash record](../../artifacts/mgpu02/source-inspection/slai-reference.json).
- [v0.8.5 optimization documentation](https://docs.vllm.ai/en/v0.8.5/performance/optimization.html#chunked-prefill)
  documents an older prefill-first default that does not mix prefills and decodes,
  and an opt-in decode-first chunking mode. A downgrade can restore an older
  documented configuration, but also changes native policy semantics.
  [Its argument implementation](https://github.com/vllm-project/vllm/blob/v0.8.5/vllm/engine/arg_utils.py)
  also distinguishes V0/V1 defaults. This is a candidate historical stack,
  not an established compatible replacement in the installed environment.

## Decision matrix

Engineering effort is a relative estimate of remaining design/validation work,
not a measured project schedule. No alternate package or model was installed.

| Criterion | A: general chunked-SLAI extension | A/C: bounded whole-prefill configuration **selected** | B: alternate model/configuration | C: older vLLM/engine |
|---|---|---|---|---|
| SLAI scientific fidelity | Potentially broad, but paused-prefill, LST and memory-victim semantics all require specification | Existing decision core retained in a formally restricted domain; no partial/KV fidelity claim | Another decoder has the same flag issue; pooling removes autoregressive decode, encoder-decoder adds different stages | Possible within older APIs, but needs a new independent adapter validation |
| Native vLLM compatibility | Native chunking supported; custom policy integration unproven | Supported chunking setting; no split proven by bound and checked per step | Decoder switch alone does not solve support predicate; architectural exceptions change execution | Older documented defaults exist, but installed source/ABI guards reject them |
| Changes required | Paused queues, progress, deadline transition, memory/preemption and execution accounting | Explicit contract, shared native/SLAI checks, independent audit and smoke hooks | New checkpoint/tokenizer, architecture adapter, calibration and provenance | Separate pinned environment, API port, source guards, calibration and retesting |
| Unsupported behavior risk | High until full state-space and integration validation | Bounded and fail-closed; physical integration still unverified | High for unvalidated exception architectures; no advantage for decoder-only swaps | Unknown with current Python/CUDA/Torch stack; not tested |
| Future TP/DP relevance | Strong foundation only after per-rank scheduling/KV validation | Retains current V1/V2 interfaces, explicit topology identity; all distributed modes still rejected | New model may add KV/encoder distribution issues and confounds | Additional migration burden; older runtime is a different comparison axis |
| Reproducibility | Requires a substantial new contract and conformance corpus | Same immutable model, version and source hashes; versioned bounds and fixed input bytes | Requires new immutable assets, tokenization and recalibration | Requires complete older dependency/runtime pinning, not a version-number edit |
| Engineering effort | High: multi-state semantic design and validation | Low/moderate: completed bounded implementation and focused tests | Moderate/high without a demonstrated compatible candidate | Moderate/high: installation and adapter rewrite, no guaranteed payoff |
| Research-question effect | Can preserve intended general algorithm question if validated | Preserves the engineering mechanism question; **cannot answer chunking/KV-stress rankings** | Pooling/encoder-decoder materially changes workload and mechanism question | Changes baseline engine/policy and runtime era; must be treated as a new experimental factor |
| Decision | Defer; do not silently approximate | Proceed to author review of one smoke | Reject as a minimum-effort fix; not ruled out for separate research | Reject for MGPU02; retain as a documented alternative |

Keeping chunking disabled and increasing the timeout is rejected outright. A
sufficient token budget does not remove the upstream warning when the flag is off.

## Exact supported contract and implementation

New modules live in `src/robustbench/mgpu02/`. The MGPU00 adapter retains its old
chunking rejection; the new classes deliberately opt into the new contract.
MGPU00 smoke defaults remain blocked. Shared runner hooks select MGPU02 classes
only through `scripts/mgpu02/smoke.py`.

Let N be the active sequence cap and P the maximum admitted prompt length. With
R running decodes, at most N-R new prompts can enter. Each decode needs one token,
so any permitted batch needs at most `R + (N-R)*P <= N*P` tokens. The smoke fixes
N=16, P=256 and budget B=4096, with long-prefill threshold zero. Existing fixture
prompts remain 128 tokens. This bound includes held decodes in R; they retain
active capacity and native KV allocations. It holds even when waiting demand
exceeds active capacity. Prompt plus requested output must fit the 512-token
context. A request over P is rejected before native admission.

The bound prevents token-budget splitting; it does **not** prove KV availability.
Actual native allocation is compared with the intended plan, and native
preemption is explicitly rejected before its preemption operation executes.
A mismatch may already have mutated scheduler bookkeeping, so the engine/run is
invalid and must terminate; there is no rollback/retry or attempt to salvage data.

- `contract.py`: enforces Qwen2 text generation, enabled chunking, synchronous V2
  runner with one in-flight batch, the N*P bound, zero prefill threshold, no prefix
  cache, speculation, KV/encoder transfer or LoRA, and TP/PP/DP/context-parallel=1.
- `vllm_scheduler.py`: real native Scheduler construction, allocation and update;
  exact admission and one-token decode progress checks; rejection of continuing
  partial progress, resumed/streaming/structured/multimodal requests, overlapping
  batches, throttling, context overflow and duplicate ordinals. It records input
  states, checked plans and separate completion evidence. Missing/extra runner
  requests, wrong token counts/index mapping and reported NaN logits fail.
- SLAI still uses class/TBT → prompt length → stable original ordinal admission;
  critical decodes → prefills → residual decodes; decode limit 2. Native remains
  FCFS and has no SLAI holds. The new contract identifies the restricted variant
  separately in experiment hashes even though existing mechanism names remain.
- LST remains completion time + class TBT minus offset times cumulative measured
  batch duration. Offset is 5 below 96% native KV utilization and 10 otherwise;
  held requests do not refresh LST. Equality at LST is critical. Scheduling time
  and completion use the same host's monotonic clock.
- The measured batch interval includes scheduler/engine callback work and
  instrumentation. It is **not pure GPU kernel time** or Sarathi's identical
  runtime timing. Three-class mapping (including the interpolated 0.3 s middle
  tier), original-ordinal tie breaks, and native KV utilization are disclosed
  project adaptations. Absolute end-to-end workload deadlines are evaluation
  metadata, not replacements for SLAI's per-token LST. Physical timing fidelity
  remains a research risk, not resolved by these local tests.
- `audit.py`: independently computes expected capacity/priority prefixes from
  recorded input state. Because all admissions fit under N*P, the optimal selected
  decode subset is simply the earliest LST prefix up to the decode limit.
  It compares actual native plans and runner completions and reconciles each
  request's compute total `prompt + output - 1` and sampled total `output`.
- Shared `metadata.py` now rejects non-string IDs/classes, Boolean ordinals or
  timing values, nonnumeric/nonfinite timing/weight metadata explicitly.

**Scientific scope limit:** this configuration does not exercise token-budget
competition between prefills and decodes; the budget is deliberately sufficient.
It exercises admission priority, concurrent work, decode-limit/LST holds and
completion fidelity. Small-budget contention is unit tested with explicit
reference decisions; it is not enabled in this physical configuration. General
partial-prefill or memory-pressure ranking claims need a later semantic extension
and author-reviewed experimental design. A strong parallel/distributed journal
submission will also need device-specific load calibration and controlled scaling
studies; this engineering smoke is not that evidence.

## Local validation and boundaries

The focused suite is run directly through Codex, never GitHub Actions:

```sh
PYTHONPATH=src /home/soroush/modal-venv/bin/python -m pytest \
  tests/mgpu00 tests/mgpu02 tests/test_anwg_metric.py -q --tb=short \
  --junitxml=artifacts/mgpu02/local-validation/pytest.xml
bash -n scripts/mgpu00/smoke.sbatch scripts/mgpu02/smoke.sbatch
```

Final result: **151 passed, 0 failed, 0 skipped**, 14 existing Torch deprecation
warnings, 10.39 seconds (73 prior tests + 78 new MGPU02 tests). Output is recorded in
[pytest.log](../../artifacts/mgpu02/local-validation/pytest.log) and
[pytest.xml](../../artifacts/mgpu02/local-validation/pytest.xml).
The suite uses real installed vLLM Request/SamplingParams, Scheduler constructors,
request queues, block allocator and completion updater with a local model
configuration only. No weights, forward pass, GPU execution or serving engine
is instantiated. GPU runner completions and clock intervals are synthetic.

An independent exhaustive subset oracle maximizes a lexicographic SLAI service
vector under admission/decode capacity constraints. Forty seeded mixed-state
cases compare this oracle directly against the real adapter/native allocations;
the oracle imports neither the decision core nor the simulator. Additional
hand-computed cases cover critical equality, residual decode contention and the
96% LST boundary. Native chunking-enabled/disabled differential tests run the
unmodified Scheduler; disabled mode is a CPU counterfactual, not a serving option.

| Status | Coverage |
|---|---|
| Supported, locally checked | Three classes, concurrent arrivals, prompts 1/16/128/255/256, 128-target decode requests, overload beyond active capacity, exact 4096-token/16-prompt boundary, admission ordering, LST holds, complete native state transitions, independent recorded-decision audit |
| Rejected and tested | Prompt 257/context overflow; a real native threshold-induced split; partial running progress; actual KV admission failure and decode preemption; missing/extra/invalid runner output; malformed metadata; TP/PP/DP/DCP/PCP; async/prefix cache/speculation/transfers/LoRA |
| Unverified | Physical model/API execution, full-engine behavior with held requests, startup duration, hardware timing fidelity, model-output numerics, L40, TP2/DP/multi-node, general chunking or KV-stress ranking fidelity |

No coverage percentage is claimed. The complete repository suite/manuscript was
not audited; existing 73 focused checks plus MGPU02 checks are the relevant scope.
An early integration fixture used an incomplete structured-output stub; it was
replaced by the real manager. A rejection test exposed guard evaluation order;
unsupported feature checks now run before dependent vLLM configuration properties.
Neither development failure was bypassed or converted to a skip.

## Startup: justified change, unchanged uncertainty

MGPU01 observed 247.336 seconds between device verification and native round start,
and about 566 seconds of readiness allowance before model loading began. These
intervals did not isolate import/cache/GPFS causes. Raising a timeout cannot
establish a cause or repair.

MGPU02 removes the redundant parent-process AutoTokenizer import/load for this
one fixed fixture. `prompt.json` preserves exactly the prior tokenizer encoding:
body IDs `[63122, 16614, 12507]`, repeated/truncated to 128 tokens. Before use,
`PinnedPrompt` checks the immutable revision and SHA-256 of config, tokenizer,
tokenizer config, vocabulary and merges. A separate CPU command regenerates the
IDs with the actual pinned tokenizer and checks equality. No server tokenization,
model weights, model dtype, prompt contents, sampling settings or warmup changes.
See [prompt equivalence](../../artifacts/mgpu02/local-validation/prompt-equivalence.json).

A bounded read-only cluster check also matched all five tokenizer/config file
hashes; see [remote tokenizer check](../../artifacts/mgpu02/source-inspection/remote-tokenizer.json).
No measured startup speedup is claimed. Shared-filesystem delays in server imports
and engine initialization remain unresolved. Model staging, cache warming, changed
compilation, shared-engine reuse and larger CPU allocations were not justified by
the available measurements and were not introduced. Native/SLAI retain fresh
servers, eager mode and the existing cache policy. Startup/source verification,
readiness and allocated elapsed time remain separate from replay timing.

## Readiness and next steps

**Single-full-A100 engineering smoke: GO for author review and later explicit
submission authorization.** The code/configuration prerequisites now pass locally;
physical gates remain NOT VERIFIED. **Ranking matrix/pilot: NO-GO.**
**TP2: NO-GO separately**, explicitly rejected. DP and context parallelism also
remain rejected. No GPU experiment is authorized by this document alone.

[SMOKE.md](SMOKE.md) contains the exact preparation/submission procedure, acceptance
criteria and resource ceiling. The prepared wrapper uses one full A100, 16 CPUs,
32 GiB and a 35-minute allocation ceiling; no array/requeue/retry. Maximum requested
allocation is **35/60 = 0.583333 GPU-hours** (scheduler teardown overhead excluded).
Actual MGPU02 GPU consumption is **0 GPU-hours**. No job/session ID exists.
