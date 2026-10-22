# CPU interface and evidence contract

Import `robustbench.serving_v2.p2a.native.NativeBoundary` explicitly. Nothing imports it from a serving/default path. Construct with a newly initialized **exact native Scheduler type**, `enabled=True`, CPU device and the pinned source bytes. Pass no model runner. The tests reuse MGPU02's local model **configuration only**, without weights/tokenizer/model execution.

The supported configuration is synchronous FCFS, one in-flight batch, chunked prefill, no long-prefill threshold, zero watermark, full-input-fit checks, one full-attention KV group, no prefix cache, speculation, encoder, multimodal inputs, LoRA, connectors or distributed execution; the V2 runner configuration is required as the source semantic target. This does not validate that runner. The registered requests use immutable token tuples/digests and fixed positive output caps with `ignore_eos=True` solely for CPU synthetic conformance. This is not an S07 model/tokenizer/stop-rule selection.

| API/type | Contract |
|---|---|
| `enqueue(RequestSpec, prompt_ids, stamp=...)` | P1 application/engine ID binding, immutable prompt digest/count/output limit/arrival. Request tokens are passed to actual native Request objects; no model consumes them. |
| `Proposal(batch_id, spans, token_budget, active_limit)` | Explicit ordered proposed work. Half-open spans bind native engine ID, epoch, start/end. Budget/slots must match the actual configuration. No batch-ID reuse. |
| `schedule(proposal, stamp=...)` | Calls native scheduler once only after domain checks. Accepted raw map, wire starts, optimistic counters and order must equal proposal. Extra/missing work, reordering or unsupported native changes refuse the whole batch. |
| `Acceptance` | Native step, exact spans, total scheduled input positions, resident slot count and sample-validity mask. Resident slots include requests receiving zero tokens. It is **not** execution acknowledgment. |
| `Rejection` | Explicit reason/detail/native-called flag. A capacity-domain refusal is not proof of native OOM. Empty native output is plan disagreement unless separate evidence establishes its cause. Every rejection stops the instance. |
| `RunnerAck` | Caller-supplied batch/step/spans/mask, synthetic provenance, success/quiescence. No helper manufactures ACKs from acceptance. |
| `acknowledge(ack, ModelRunnerOutput, stamp=...)` | All request rows/masks/bindings validated (bijective ID/index mapping permits native runner row permutation) before native update or ledger commit. Then native outputs/counters/completion/blocks are cross-checked. Entire P1 batch commits atomically. On native post-update disagreement the native object is already changed: stop, retain fault/raw observations, never retry. |
| P1 `AllocationObservation` | Actual block IDs and pool counters copied from the native manager, not a shadow allocator. Typed immutable observation remains separate from scheduling and execution facts. |
| `export()` | Detached JSON: profile/source hashes, registry, per-batch before/wire/scheduled/executed snapshots, proposal/acceptance/ACK, ledger event boundaries, faults. Caller persists outside timed paths. |
| `reference.validate(journal, require_complete=True)` | Stdlib independent FCFS reference plus independent P1 referee; does not import adapter/ledger/native/torch. Computes expected work from registered enqueue order and verified previous outputs, then compares native output, acceptance and ledger independently. |

No data races are supported: surrender ownership of the scheduler to the boundary; no external enqueue/cancellation/KV mutation is permitted. Guards catch identified drift and invalid transitions but are not a security sandbox against hostile in-process mutation. Cancellation-race tests prove refusal, not cancellation recovery. Queue ordering follows native insertion order, not re-sorting caller arrival timestamps. S02 metadata is opaque in P1 and never used here.

## Conservation and observation levels

The reference validates full registry/live/queue identity, resident counts, global token budget, per-request positions, final-prefill eligibility, unique non-sharing KV ownership, free/system/owned pool reconciliation, releases and P1 event bindings. It independently derives expected FCFS allocation using known prompt/output frontier and budget; it does not accept the adapter's claimed mask or accepted spans as ground truth. Literal contention/split cases, real native execution of the CPU scheduler, adversarial journals and a deliberately faulty adapter test this independence.

Within this deliberately small domain, `sum(ceil((original_prompt + original_output_limit)/block_size)) <= total_blocks - 1` over live registered requests is a **sufficient lifetime no-pressure precondition**, including waiting requests. One native null block is excluded. This is conservative, is not a physical memory estimate, allocates/reserves no blocks, and is not an admission rule for a scientific workload. Actual native allocation still occurs. Requests can fail this domain check even though native scheduling might successfully run them sequentially. Such requests are refused explicitly, never silently filtered.

`Result.complete` means all registered CPU requests reached output caps, all accepted batches were acknowledged, and native KV ownership drained. `transport_closed` retains the stronger independent P1 result: every generated token also emitted/observed. It remains false in these fixtures. No transport event is invented. `physical_status` is always `NOT_VERIFIED`, including a complete CPU run.

Timestamps are explicit caller-supplied `ClockStamp`s restricted to host-control observations. P1 retains their domain and causality checks. No automatic clock, GPU duration, TTFT/TPOT/ITL, LST update, token-emission timestamp or user latency is inferred from synthetic ACKs. Source-verified sampling validity is not a physical timestamp.

## Costs and limitations

Construction hashes selected installed source files. Per-batch diagnostics copy request state/block tables and the P1 ledger for atomic updates; reference validation reconstructs whole journals. This may be expensive and must stay outside future timed execution until a separate overhead design/measurement is approved. There is no claim of low-overhead instrumentation. The reference checks consistency, not cryptographic authenticity: jointly forged native and registry evidence cannot become physical proof. Source hashes are scoped files, not a complete hermetic dependency/container attestation.
