# MGPU00 measurement and scheduling contract

The new code lives in `robustbench.mgpu00`; historical RQ6 code at its recorded
commits is untouched. Python 3.12, vLLM 0.27.1 and Torch 2.13.0+cu130 are the
inspected environment. The vLLM scheduler source SHA-256 is
`c67bda2886b52865ddafabaae7d797c359e930752f374421a33e537d94a5f45a`, identical
on the local workstation and Wulver; adapters reject a different build.

## Metadata and policy semantics

The supported OpenAI completion field `vllm_xargs` transports a versioned schema,
stable workload request ID, original ordinal, class, arrival, deadline and weight.
vLLM copies this into `SamplingParams.extra_args`. Both adapters require and log
these values. Missing/unknown classes raise an error; no implicit loose class is
created. The existing tier map is preserved: tight/interactive/critical = 0.1 s,
medium/standard = 0.3 s, loose/batch = 0.5 s.

Completion deadlines used for ANWG and class-derived token-between-token targets
are distinct quantities. The scheduler uses the latter for SLAI, not the former.
Its admission key preserves `(TBT tier, input length, original ordinal)` through
an exact bounded integer encoding, replacing the historical floating-point
approximation and arrival-time tie-break. Ordinals >=1,000,000 are rejected.

The SLAI core orders critical decode, prefill admission, then noncritical decode
using residual capacity. It uses monotonic seconds and a cumulative mean of
observed batch turnaround, anchored at completed model-output processing. This
includes host/IPC overhead and is **not claimed to be GPU-kernel time**. LST is
refreshed only after an actually scheduled batch completes. No timer advances
just because another `schedule()` call occurred. The initial prefill supplies
the first observed batch duration; no fabricated 1 ms fallback exists.

The decode limit is mandatory configuration. The engineering fixture sets it to
two to activate holding with 12 requests; this is an explicit mechanism test,
not a tuning decision or the scientific pilot's policy parameter. A future
scientific configuration must freeze its own limit and demonstrate action
opportunity without changing it after seeing outcomes.

Held requests remain in the native running set and retain KV/active capacity.
The pinned engine's `next_decode_eligible_step` gate skips their execution without
eviction. The adapter compares the entire native token-allocation map against
the precomputed SLAI decision; any preemption or mismatch aborts the run.
Structured events record metadata receipt, admission, integer priority, actual
token allocations, holds, checked decisions and measured batch timing.

## Explicit readiness boundary: not a general faithful SLAI port

The adapter is fail-closed, not a fallback approximation. The supported test
domain is synchronous, dense, non-chunked inference with complete prefills and
nonbinding native KV admission. It rejects:

- TP/PP/DP other than 1/1/1;
- async scheduling, speculation, prefix caching, KV transfer and LoRA;
- partial/continuing prefill, skipped/resumable states, token-plan drift, or
  native preemption/KV-induced rejection.

The pure core's decision sets are differentially checked against the existing
simulator in this supported domain. That does **not** validate partial-prefill,
memory-pressure or distributed execution. Supporting those regimes requires
additional engine integration and independent mechanism tests. A successful
restricted smoke is insufficient to launch the 144-run pilot. The adapter
deliberately refuses TP2 rather than treating a CLI flag as validation.

## Replay

`workload.prepare_window` checks the manifest's file hash and prepares every
prompt before injection using the unchanged frozen RQ6 generator. It verifies
tokenization round trips and preserves IDs, order, arrival offsets, output
targets, classes, weights and deadlines. It does not scale arrivals or deadlines.
The prepared client sends token IDs, avoiding timed client prompt generation.
The JSON request bodies are serialized before the replay epoch as well.

Replay creates independent asynchronous arrival timers, not completion-gated
workers. A maximum-inflight overrun produces `CLIENT_SATURATED` and invalidates
the measurement; it never silently shifts the arrival to a later time. HTTP pool
capacity matches the declared concurrency. The client records scheduled arrival,
wake, dispatch, HTTP transport-send, first text-bearing streaming chunk and
completion, plus exact input/output usage, timeouts, errors and incomplete rows.
Transport timing is mandatory for a valid replay. First-token time is a client
observation of a streaming chunk, not an invented GPU-side timestamp.

Scheduler receipt and first scheduling/admission come from correlated server
events. They may be joined to the client's monotonic clock only in the current
single-host smoke. Cross-host clock synchronization is an unresolved multi-node
requirement. Client-observed latency includes network/HTTP overhead; it is not
labeled pure server latency. Server queue time is separately measured between
receipt and admission. Actual offered rate and achieved throughput have explicit
denominators; a simultaneous burst's interarrival rate is undefined.

## Identity and hardware

The device probe runs only in a Slurm compute allocation. It cross-checks CUDA
ordinal UUID/memory against NVML, parent UUID, MIG handle/mode and the Slurm full
A100 request. Parent inventories alone never pass the gate. A manifest contains
GPU model/count/kind, UUIDs, node, TP/PP/DP, immutable model/tokenizer revisions,
precision/context, CUDA/driver/Torch/vLLM/NCCL versions, workload/calibration
hashes, repetition, policy parameters, experiment version and Git SHA.

Canonical experiment IDs include all deployment/scientific identity fields;
execution IDs additionally bind the physical allocation. Writes use exclusive
creation so an existing result cannot be overwritten. Engineering fixture hashes
are explicitly not scientific load-calibration hashes.

## Local and physical validation

Local command (no GPU inference):

```
PYTHONPATH=src /home/soroush/modal-venv/bin/python -m pytest tests/mgpu00 tests/test_anwg_metric.py -q
```

The smoke script is four fresh-server ABBA rounds: native/SLAI/SLAI/native, two
repetitions each, 12 requests/round, 128 input and 128 target output tokens.
Classes and token shapes are fixed before results. Same model/tokenizer revision:
`7ae557604adf67be50417f59c2c2f167def9a775`. Each round checks full completion,
class receipt/priority, admission timestamps and transport timing. SLAI must
produce actual hold events; the native baseline must not. Limits are maximum
dispatch delay 20 ms and p95 10 ms for bursts spaced 200 ms apart. These thresholds
only validate this engineering fixture, not a future high-rate workload.

`smoke.sbatch` requests one full A100, one node, 16 CPUs, 32 GiB, low QoS and
45 minutes, with automatic requeue disabled. A single submission is capped at
0.75 allocated GPU-hour, below the authorized two-hour aggregate ceiling. It
performs no automatic retry and stops at the first failed prerequisite/round.
No scientific workload window or ranking test is executed by this smoke.
