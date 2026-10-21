# MGPU06 zero-GPU cache amendment: validation record

**Physical submission verdict: BLOCKED. No genuine Slurm job was submitted. GPU-hours consumed/committed by MGPU05/MGPU06: 0.** Only the previously authorized Block 0 could be eligible; no permission or readiness is implied for the remaining 22 executions.

## Preserved configuration and tests

Baseline: `b397b0258e32f5c1277477e0a024040302ebb00e`. Cache/launcher amendment: `f1ad78541591185eacb5223099fa23b67051055d`; GPFS permission correction: `48cb7fc`; diagnostic-only probe refinements: `89d141e` and `c6867da`. Later documentation changes do not alter executable policy, numerical or measurement code. The final checkout is rechecked by CPU preflight and identified in the external evidence report.

- Local regression suite: **250 passed, 0 failed**, 14 existing Torch deprecation warnings, 11.62 seconds. This is the original 225-test suite plus 25 runtime-boundary tests. Existing startup-failure tests now supply an isolated test runtime root.
- Wulver focused suite: **33 passed, 0 failed**, 10.25 seconds (25 runtime tests + eight launcher tests), GPUs hidden, plugin autoload/cache provider disabled. The complete 250-test suite was not run on Wulver.
- Exact clean checkout, model weights, tokenizer/config/generation files, HTTP/API/scheduler source pins, dependency versions, design manifest and B4096/N16/P256 proof: CPU preflight PASS. Source/configuration syntax and whitespace checks pass.
- Final Wulver cache probe: **PASS**, exit 0, CUDA context not initialized. Effective Torch/Triton/vLLM/HF/Transformers paths, Triton cache write, inherited child environment and project Unix socket bind passed. Offline trace inspection found **zero home-write operations** across 181 asset-preflight and 200 cache-probe file-write operations; two relative unlink calls resolve to the immediately preceding project temporary-directory open. This observes CPU paths, not future GPU-only execution. Raw trace hashes are recorded below.
- Cache wrapper additionally pins 17 source files and 44 kernel/runtime distribution versions from the installed Wulver environment. The runtime environment is established before third-party imports and independently exercised in subprocesses. Local/Wulver version differences are explicit, not silently substituted.

Block 0 remains boundary/burst, repetition index 2, native FCFS then checked SLAI, 16 scored requests each plus the identical warmup. Payload SHA-256: `c3d16b156d61e918c1b89725c8ca8855489994b9f64f4164df558fa0a5bd1ca5`. Synthetic prompt-ID lengths repeat 1/256/64/128, output limits repeat 256/128/256/64. All input IDs come from the pinned tokenizer fixture; these are actual API token-vector inputs, not estimates from character counts. TP/DP/PP remain 1; partial-prefill, unexpected KV/preemption and unsupported execution continue to fail explicitly. No realistic trace truncation is introduced.

## Storage and resource evidence

Observed 2026-10-21 22:32 UTC: home usage/hard limit 56,320 MiB, soft quota 51,200 MiB, grace expired; file count 251,056. Home contents were not reclaimed or modified. Project fileset `sata1-project_ikoutis`: 1,106 GiB used /2,048 GiB hard quota, approximately 942 GiB headroom (before in-doubt reservations). Private project write/fsync probes succeed. The private runtime parent is `/project/ikoutis/sv96/r`, with per-experiment/per-process-phase directories described in [CACHE_ISOLATION.md](CACHE_ISOLATION.md).

Account `ikoutis`, partition `gpu` and QoS `standard` are eligible for `gpu:a100:1`; standard's L40 restriction does not authorize a substitute. Account billing allowance 18,000,000 TRES-minutes versus observed usage about 918,488; no running GPU commitment. User fair-share 0.225806 is a priority consideration, not a hard quota rejection. The only existing account/user job is unrelated CPU job 1291889, pending on `DependencyNeverSatisfied`.

All usable full-A100 devices were allocated; unused node n0069 was drained. At **22:36:21 UTC**, `sbatch --test-only` for the exact prepared 50-minute/16-CPU/32-GiB/one-full-A100 script forecast **2026-10-25 07:54:33 in Slurm's displayed time**, on n0024. This exceeds the supervised-start interval. Its displayed test identifier is **not a submitted job ID**. No reservation, allocation, real submission, cancellation or automatic retry occurred. Historical MGPU00/MGPU03 jobs in sacct are separate from the new pilot budget.

## Raw evidence and interpretation

Wulver evidence root:

`/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-mgpu05/artifacts/mgpu06/cache-isolation-20261021T2325Z/`

The directory's timestamp-like suffix is a label, not the measurement timestamp; actual command UTC and strace epoch times govern chronology. This task began its new resource snapshot at 22:32 UTC. Local mirror and supplemental source inspection/tests:

`artifacts/mgpu06/cache-isolation/`

The original failed preflight directory `artifacts/mgpu06/preflight-20261021T2214Z/` and its checksum manifest remain intact. New evidence contains resource queries, original failed diagnostics, CPU test logs, exact-commit asset preflight, filesystem traces, effective runtime records, the scheduling test and a SHA-256 inventory. Raw traces and generated caches remain outside tracked source files; the durable remote evidence is retained for independent review.

Preserved diagnostic failures are not hidden: first, the permissions guard correctly rejected GPFS's inherited 0755 directory; the correction explicitly restricts newly created directories. Second, the broad filesystem-trace probe reached its 120-second diagnostic timeout while inspecting installed package files. Third, a narrower trace exposed an invalid test key for Triton's hexadecimal cache-manager API; the probe key was corrected without changing the serving implementation. These are CPU validation attempts, not physical experiments. The diagnostic timeout is unchanged.

Physical full-A100 identity, both API startups, responses/content transport, physical timestamp causality, scheduler activation/oracle agreement, per-token observation coverage and instrumentation overhead are **NOT VERIFIED for MGPU05/MGPU06**. MGPU03's bounded engineering acceptance is preserved. No startup, throughput, latency, ranking or numerical reproducibility claim is made here.

The next scientific gate remains independent review of one physically completed paired allocation. Before that, refresh resources and rerun the exact-commit/cache/asset preflight; do not leave a pending allocation beyond the authorized supervision window. Long prompts, partial prefills, general KV pressure, extra mechanisms, TP2/DP2, L40 transfer and the full ranking-transfer study remain NO-GO.

## Selected raw trace checksums

| Evidence | SHA-256 |
|---|---|
| execution-preflight.strace | `8069fa6eb45d7a163572d8caee4a94a88436a17be75707aa18a8979e716e68ff` |
| cpu-probe4.strace | `26400b375cf75ad0451ff629b1ee8c5060ed16a8a5fe7963a245433e7c5f8b44` |
