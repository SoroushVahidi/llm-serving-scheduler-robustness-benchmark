# MGPU01 startup diagnosis and compatibility decision

2026-10-21. Physical-job state: **FAILED** (1434644, exit 1:0).
**No MGPU01 Slurm job submitted.** Compatibility did not pass the prerequisite
for the one conditional retry. No GPU execution, installation, matrix, pilot,
Actions workflow, merge, or manuscript change was performed in MGPU01.

## Confirmed timeline and limits of attribution

Execution commit `77ddb6fe93fd77ee6bce8883b911696789917b7e`; remote checkout was
still exactly that commit when inspected. Slurm allocated one full A100 on n0003
for 892 seconds. The Python failure file records 887.275 seconds. The program
timed out waiting for readiness; it did not exhaust its 20-minute Slurm limit.
All 15 device identity checks passed. No inference request was sent.

The following times are UTC on 2026-10-21. Original vLLM/Slurm clock strings
are EDT (UTC-4); progress journal nanoseconds provide the UTC anchor. Whole-second
server log stamps do not identify subsecond internal durations.

| Interval | Elapsed | Observation / attribution |
|---|---:|---|
| 16:41:04 allocation → 16:41:07.510 smoke start | 3.510 s | Shell, interpreter and initial module setup combined; no finer trace |
| 16:41:07.513 → 16:41:16.347 device verified | 8.834 s | Probe includes Torch import, CUDA properties, NVML and Slurm checks; CUDA count/properties calls occupy only a small part of this interval |
| 16:41:16.347 → 16:45:23.683 round start | 247.336 s | Code writes provenance, reads Git SHA, imports AutoTokenizer and loads the local tokenizer; individual costs unrecorded |
| 16:45:23.683 → 16:49:30 API configuration banner | ~246.317 s | Fixture/command construction, process startup and API imports/setup; exact Popen time absent |
| 16:49:30 → 16:52:13 architecture resolved | 163 s | API/model configuration and architecture resolution; imports versus filesystem time not separable |
| 16:52:13 → 16:52:14 engine settings | 1 s | Unsupported-prefill warning; eager mode disables torch.compile and CUDA graphs |
| 16:52:14 → 16:54:16 engine initialization message | 122 s | Engine subprocess startup/import/configuration gap, unprofiled |
| 16:54:16 → 16:54:44 distributed init | 28 s | Worker/platform/CUDA setup interval, not a pure CUDA timer |
| 16:54:44 → 16:54:50 ranks assigned | 6 s | NCCL backend, world size 1; observed distributed setup, not proof of a collective bottleneck |
| 16:54:50 → 16:54:54 model loading starts | 4 s | V2 model runner setup |
| ~16:55:24 readiness deadline → 16:55:54.780 failure record | ~31 s | Polling overshoot plus terminate/wait/kill cleanup; old code allows 30 s terminate grace |
| 16:55:56 Slurm end | — | Exit 1:0; no ready response, weights-loaded message or replay output |

Approximately 566 seconds of the 600-second readiness allowance elapsed before
the first model-loading message, leaving only about 34 seconds. The exact
Popen/deadline instant was not persisted, so these are estimates anchored to the
round event, not invented precise launch timestamps. The 247-second tokenizer
interval was outside the readiness timer, but consumed allocated wall time.

**Confirmed immediate cause:** the runner stopped a still-initializing server at
the readiness deadline. Most observed delay preceded weight loading. No traceback
establishes a vLLM engine crash before that deadline. The old cleanup discarded
the child exit code and readiness errors; its final return code is unrecoverable.

**Hypotheses:** slow imports/module discovery and GPFS metadata or small-file
access in API/engine/tokenizer setup; transient compute-node load or cold caches.
There is no resource profile to rank these explanations. A model download/cache
miss, NCCL hang, GPU memory shortage, or torch.compile bottleneck is not established.
Compilation/CUDA graphs were explicitly disabled; other kernel JIT work cannot
be excluded generally, but no completed model load or warmup was logged here.
Increasing the timeout alone is not evidence of a root-cause repair.

## Environment, model and bounded filesystem inspection

- Runtime: Python 3.12.14 environment, vLLM 0.27.1, Torch 2.13.0+cu130,
  transformers 5.16.1, CUDA 13.0, driver 580.159.04, NCCL 2.29.7,
  httpx 0.28.1, nvidia-ml-py 13.610.43. Values come from the job provenance;
  installed package metadata independently agrees where inspected.
- Venv: `/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-real-vllm-prep/.venv-lssp-vllm-0.27.1`.
  Despite its name, this is a conda environment (`conda-meta` present, no
  `pyvenv.cfg`). Both Python and the vLLM entrypoint resolve to its Python 3.12;
  there is no observed interpreter-path mismatch. Python's exact version is a
  post-job inspection, not a previously persisted per-job micro-version.
- Model and tokenizer: `Qwen/Qwen2.5-0.5B-Instruct`, pinned snapshot/revision
  `7ae557604adf67be50417f59c2c2f167def9a775`, under
  `/home/sv96/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/`.
- Native scheduler: `robustbench.mgpu00.vllm_scheduler.InstrumentedNativeScheduler`,
  inherited FCFS; SLAI round never started. Intended SLAI class is
  `LSSPSlaiVLLMScheduler`, priority admission, explicit decode limit 2.
- BF16; max context 512; token budget 4096; max sequences 16; GPU memory fraction
  0.2; eager; async/chunked-prefill/prefix-cache disabled; TP/PP/DP=1/1/1;
  localhost API; offline HF/transformers; OMP threads 4; FlashInfer sampler off.
- Each round used new per-run VLLM, TorchInductor and CUDA cache paths. These
  are distinct from the existing Hugging Face model cache. The full original
  sbatch command/config and effective server arguments are preserved in evidence.

The read-only login-node inspector had a 60-second process bound, 15-second
subcommand bounds, no framework/GPU imports, no recursive cache scan, and no full
weight read. Both venv and model resolve to `/mmfs1` GPFS. All seven snapshot files
exist with resolving symlinks: config, generation config, tokenizer config,
tokenizer JSON, merges, vocabulary and one safetensors file. The weights file is
988,097,824 bytes; its 32,280-byte header describes 290 tensors, and the final
tensor offset matches file size. Head/tail samples are readable; there are no
extra shards required by this single-file snapshot. This checks structural
availability, **not** every tensor byte or cryptographic weight integrity.

Per-file small checks took about 0.0005–0.139 seconds on login02 after the failure.
They cannot establish n0003's earlier cache warmth, full-file throughput, or absence
of transient GPFS latency. File mtimes predate the job. The installed model runner
prints “Loading model from scratch” unconditionally before invoking the model
loader; this is not a cache-miss report. The default loader selects an existing
local directory without a model-weight download. Exact source excerpts/hashes
and inspection timestamps are retained.

## Historical successful MIG comparison

The existing exhaustive 240-task hardware audit is preserved. For startup
comparison only, MGPU01 selected task 0 (legacy SLAI) and task 1 (native), the first
azure window, with original result JSON, prologue and server log. All six hashes
must match the previous audit; this is a bounded comparison, not a new campaign
or a claim that these two samples characterize every historical startup.

| Setting / observation | Historical samples | MGPU00 1434644 |
|---|---|---|
| Allocation | 10 GB MIG, 9.5 GiB CUDA-visible; n0001 | Full A100, ~79.25 GiB CUDA-visible; n0003 |
| Software | vLLM 0.27.1 in logs; same venv path; requirements pin Torch 2.13.0 / transformers 5.16.1 | Recorded runtime versions above |
| Model | Same Qwen 0.5B family; model/tokenizer revision=None in logs | Explicit immutable local snapshot |
| Context / memory fraction | 32768 / 0.65 | 512 / 0.2 |
| Execution | Compilation and CUDA graphs enabled; reused AOT cache | Eager, both disabled, fresh per-run engine caches |
| Scheduler | Native default or old SLAI plugin | Instrumented native; checked SLAI not reached |
| Chunked prefill | Disabled, same unsupported warning | Disabled, same warning |
| CPU / host RAM | Requested 4 / 16 GiB | 16 / 32 GiB |
| Banner → architecture | 1 s | 163 s |
| Architecture → engine init | 48 s | ~123 s |
| Banner → model load start | 57 s | 324 s |
| Model load | 8.515 / 8.948 s; weight-read timers 0.71 / 0.74 s | No completion observed |
| Banner → API startup | 92 s | Readiness never reached |

Historical requirements and logs agree on the main version pins; historical
installed-source hashes, exact CUDA/NCCL builds and immutable model revision were
not recorded in these files. Same version/path does not prove byte-identical old
environments. Historical serving success is not proof of official support, valid
SLAI semantics, or equivalence to a full GPU. The prior class-transport, timing and
adapter defects remain documented in MGPU00.

## Chunked-prefill verdict and alternatives

**Current configuration is not officially supported.** In installed
`engine/arg_utils.py:2599–2624`, the warning is selected when the runner generates,
chunked prefill is manually false, and the model supports it. Qwen is a decoder
generation model and satisfies that predicate (`config/model.py:1906–1950`).
It is not triggered by MIG, TP, or the token-budget inequality. Here 4096 exceeds
512 already, so changing only that inequality cannot fix the warning.
This is an independent compatibility blocker, not proof the warning caused delay.
The four inspected source files match both workstation and remote installation
and the authoritative [v0.27.1 upstream sources](https://github.com/vllm-project/vllm/blob/v0.27.1/vllm/engine/arg_utils.py#L2599).

Upstream's [versioned optimization documentation](https://docs.vllm.ai/en/v0.27.1/configuration/optimization/#chunked-prefill)
describes decode-first scheduling, then prefills within the remaining token
budget, with splitting when necessary. Its generic warning about insufficient
budget when disabling chunking is not an endorsement of this model/configuration.
Even matching the context/token budgets does not restore the older prefill-first
policy. We prioritize the explicit model-dependent support check over interpreting
the generic tuning note as support.

| Alternative | Native semantics | Current checked SLAI | Decision |
|---|---|---|---|
| Keep v0.27.1, Qwen, chunking disabled; extend timeout | Preserves configured behavior, but unsupported upstream | Existing declared domain | Reject GPU execution |
| Enable chunking, retain the generous budget and small fixture | Candidate for identical token allocations when no prefill ever splits; not a general non-chunked baseline | `validate_deployment` explicitly rejects it | Requires explicit contract change and validation before launch |
| Enable chunking with genuine partial-prefill workloads | Supported native V1 family, different admission/partial-progress behavior | Partial-prefill state, LST updates, capacity and KV-pressure handling are not implemented | New semantic design and independent tests required |
| Use another release/engine/model with official non-chunked support | Must re-establish the intended baseline and all identity/calibration fields | Version and scheduler-source hash guard rejects another engine | Separate compatibility investigation, no automatic downgrade |

For the second candidate, the 12-request, 128-token fixture suggests ample token
budget (1536 initial prompt tokens versus 4096), but that calculation is not an
engine-integrated proof of equivalence under all states. A restricted extension
would need explicit naming/versioning, a no-split invariant on native and SLAI,
validation of prefill thresholds/running-state behavior, actual-engine differential
allocation tests, and all existing KV/preemption/metadata/clock gates retained.
The SLAI ordering must remain critical decode → prefill → residual noncritical
decode; merely using native priority scheduling is not SLAI. This change has not
been made or represented as validated. There is **no established configuration
compatible with both official support and the current checked adapter**.

## Diagnostic repairs and local validation

`startup.py` provides durable per-round launch, readiness and exit records; a
fsynced event stream; timestamped log-derived engine/model/distributed/API
milestones; expected-model validation on `/v1/models`; and bounded process-group
cleanup. Log timestamps are receipt times, not claimed internal execution times.
Raw errors/responses survive timeout or server exit. Unknown child status remains
null when no process launched. A readiness success is not an inference pass.

The smoke records tokenizer import/load boundaries, warmup replay even on failure,
and durable raw/validated outputs. Incomplete warmup, incomplete replay, early
server exit or missing scheduling evidence still fails. The compatibility gate
rejects both the unsupported current flags and an unreviewed chunking switch
before hardware probing/server launch. No scheduler algorithm or flag was changed.

Readiness is `--readiness-timeout-s`, finite and at most 1200 s. The sbatch wrapper
defaults it from `MGPU01_READINESS_TIMEOUT_S` (1200), requests exactly one
`gpu:a100`, account ikoutis, gpu/standard, 16 CPUs, 32 GiB, no requeue, and a
35-minute Slurm ceiling. An independent 1950-second process timeout plus 45-second
kill grace leaves cleanup margin. The total deadline applies across both rounds;
it never promises two independent 20-minute startup allowances will fit.
The wrapper is **not authorized by a passing compatibility gate today**.

Local validation command (no inference/GPU workload):

```sh
PYTHONPATH=src /home/soroush/modal-venv/bin/python -m pytest \
  tests/mgpu00 tests/test_anwg_metric.py -q \
  --junitxml=artifacts/mgpu01/local-validation/pytest.xml
bash -n scripts/mgpu00/smoke.sbatch
git diff --cached --check -- docs scripts src tests
```

Tests cover successful local HTTP readiness, wrong model, HTTP failure, connection
error, early subprocess exit, failed exec, deadline limits, durable cleanup,
milestones, existing adapter rejection, and pre-GPU rejection. Existing physical
identity, replay completeness, metadata, SLAI decision-core and ANWG tests remain.
Final focused suite: **73 passed**, 14 existing Torch deprecation warnings,
10.61 seconds. Bash syntax, focused Python syntax and source diff checks passed.
Copied raw logs retain original carriage returns/trailing whitespace for hash
integrity; an unrestricted staged whitespace check flags those archival bytes.
The added warmup test verifies incomplete warmup is persisted, cleanup runs, and
the fixture/validated output is never reached. These are local engineering
checks, not physical validation.

## Physical checklist, accounting and decisions

| Gate | Verdict | Evidence |
|---|---|---|
| Full A100 identity | PASS | 15/15 checks from 1434644; not a new MGPU01 observation |
| Official compatibility of selected setup | FAIL | Installed/upstream warning predicate; no approved common configuration |
| Native API readiness | FAIL | 600-second deadline in 1434644 |
| Minimal native inference / complete token counts | NOT VERIFIED | Never sent |
| Actual request metadata receipt and admission | NOT VERIFIED | No inference/scheduler request events |
| SLAI activation, holds and intended-vs-observed decisions | NOT VERIFIED | SLAI server never started |
| Physical request timings and completion/error rates | NOT VERIFIED | No physical requests |
| Reproducibility / full-A100 load calibration | NOT VERIFIED | No completed physical smoke |
| TP2 | NOT VERIFIED | Adapter explicitly refuses TP2 |

MGPU01 incremental GPU-hours: **0**. Job 1434644 used **892/3600 = 0.247778**
allocated GPU-hours; preceding 1434545 used **156/3600 = 0.043333**. Combined known
MGPU00 smoke allocation: **0.291111 GPU-hours**. Count parent job rows only, not
batch/extern steps; these are allocation hours, not measured GPU utilization.

**24-execution single-A100 matrix: NO-GO.** Resolve official support plus adapter
semantics, then obtain physical readiness/inference/mechanism evidence and frozen
full-device calibration before proposing a matrix. **TP2: NO-GO separately**;
no distributed metadata/timing/KV/scheduler equivalence or two-device identity
validation exists, and the adapter deliberately rejects TP>1.

## Exact evidence and later inspection

Repository-relative evidence root: `artifacts/mgpu01/`.

- `mgpu00-final/probe-retry/`: final original logs, progress, device records,
  provenance and failure for 1434644, copied without altering the originals;
  the model-info cache also records decoder/text-generation architecture.
- `mgpu00-final/smoke/`: original 1434545 logs/failure.
- `inspection/remote.jsonl`: bounded cache/filesystem inspection, installed source
  excerpts/hashes, launch wrapper, package metadata, final Slurm accounting.
- `inspection/remote-followup.json`: interpreter/entrypoint and local-loader
  evidence, including the conda environment identification.
- `inspection/upstream-source-hashes.json`: upstream/local hash comparison.
- `inspection/historical-selection.json` and `inspection/historical/`: explicitly
  selected historical originals and frozen launcher/requirements source.
- `local-validation/pytest.log`, `pytest.xml`, `checks.txt`: focused validation.
- `evidence-sha256.json`: size/hash ledger for these retained evidence files.

No new job ID, launch commit or two-minute health snapshot exists because no job
was submitted. The remote original run remains at execution commit `77ddb6f`;
the MGPU01 repair commit is recorded in Git/PR history, not mislabeled as executed.
Original remote evidence parent:
`/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-mgpu00/artifacts/mgpu00/probe-retry`.

Read-only commands for later inspection, with no submission:

```sh
ssh -T -o BatchMode=yes wulver '/apps/slurm/current/bin/sacct -n -P -j 1434644 --format=JobID,State,ExitCode,ElapsedRaw,AllocTRES,NodeList'
ssh -T -o BatchMode=yes wulver 'cat /project/ikoutis/sv96/github/llm-serving-scheduler-lssp-mgpu00/artifacts/mgpu00/probe-retry/job-1434644/failure.json'
ssh -T -o BatchMode=yes wulver 'cat /project/ikoutis/sv96/github/llm-serving-scheduler-lssp-mgpu00/artifacts/mgpu00/probe-retry/job-1434644/native_fcfs-rep0.server.log'
```
