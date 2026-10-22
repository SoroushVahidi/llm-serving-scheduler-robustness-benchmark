# P1 API and observability boundaries

Import `robustbench.serving_v2.ledger` explicitly. The package initializer is empty; importing `robustbench.serving_v2.reference` does not import the producer, NumPy, Torch or vLLM. Both modules use only the standard library and support the repository's Python >=3.10 syntax. No clocks, workers, network, devices or inference are started on import.

## Typed immutable inputs

- `RequestSpec(request_id, engine_id, prompt_tokens, output_limit, prompt_digest, arrival, metadata)`: positive integer limits, unique lifetime request/engine IDs, nonempty digest identifier and immutable tuple of unique string metadata keys. Model vocabulary, digest-to-payload verification, class meaning, context fit and trace eligibility are external/unverified. Identity is scoped by the Ledger's immutable intended run association (one instance per run).
- `Plan(plan_id, batch_id, epoch, start, end)`: positive half-open span beginning at the acknowledged offset, bounded by P+G; one pending plan per request, globally unique plan IDs within the ledger. Batch ID is correlation data; the ledger does not select or coordinate batches.
- `Acknowledgment(plan_id, epoch, start, executed_end, samples=(), success=True, quiescent=True, allocation=None)`: exact identity/epoch/start binding. Successful ACKs cover the complete plan; failed ACKs may confirm a shorter contiguous prefix and must carry no committed samples. Intermediate chunks have zero valid samples, catch-up one. Samples are nonnegative symbolic IDs; legality in a tokenizer vocabulary remains external. Quiescence is executor-provided evidence, never inferred from a timer.
- `AllocationObservation(observation_id, pool_id, total_blocks, system_blocks, free_blocks, owned_blocks, other_allocated_blocks)`: frozen non-sharing snapshot; integer counts, unique in-range owned IDs, additive counts equal total, unique observation IDs and fixed pool identity/capacity per request. Admission may have zero observed owned blocks; no eager/incremental choice is imposed. ACKs may omit new allocation observations; retained snapshots are then explicitly old, not inferred current measurements. Preemption/release require explicit empty ownership. No process allocates/frees blocks.
- `ClockStamp(domain, seconds, category)`: finite nonnegative monotonic-domain coordinate; domain must encode clock/host/boot identity externally. Check chronology per request within a domain, including scheduled arrival if comparable. Never subtract across domains. Event-specific categories prevent treating client observations or GPU clocks as host ACK boundaries.
- `TimingInterval(start, end)`: same-domain, same-category (`host_policy_feedback` or `gpu_execution`) ordered endpoints, bound to a known plan ID for that request. These are external annotations, not measured durations produced by the ledger. No batch mean or LST is calculated; a future consumer must specify deduplication/aggregation across requests sharing a batch. GPU-labeled synthetic annotations remain CPU fixtures.

## Transitions

| Call | Required prior state | Effect |
|---|---|---|
| `enqueue` | Unseen request and engine ID | WAITING; freeze metadata and arrival |
| `wait(reason)` | WAITING / RECOMPUTE_WAITING | Record external refusal/wait reason; no progress |
| `admit(observation)` | WAITING / RECOMPUTE_WAITING | ADMITTED; external admission only |
| `plan(plan)` | ADMITTED / PREFILL_PAUSED / RECOMPUTE_PAUSED / DECODE_READY | IN_FLIGHT; only planned offset advances |
| `acknowledge(ack)` | Pending bound plan | Confirm positions; intermediate pause or final sample; at cap, terminal COMPLETE |
| `hold` | DECODE_READY | Preserve progress, output, ownership and clocks in state; append decision event |
| `preempt(empty_observation)` | Admitted/resident, no outstanding plan | Increment epoch, clear computed/planned offsets, retain original limits and output/transport history |
| `cancel(reason)` / `fail(reason)` | Nonterminal, no earlier abort intent | Terminal if no plan outstanding; otherwise pending abort until ACK/quiescence |
| `quiesce(empty_observation)` | Pending abort after ACK | Terminal CANCELLED/FAILED; no new samples or guessed execution |
| `complete(reason)` | DECODE_READY | Explicit early STOPPED; no approved fixed-output/semantic-success inference |
| `release(empty_observation)` | Terminal with retained owned blocks | Record cleanup; duplicate release rejected |
| `emit(start, tokens)` | Already generated prefix, not aborted | Exactly next nonempty output slice; no replay of previously emitted indexes |
| `observe(start, tokens)` | Already emitted prefix | Exactly next observed slice, possibly coalesced; permitted after cancellation for prior emissions |
| `annotate_interval(plan_id, interval)` | Known request/plan, even terminal | Retain separately labeled external time evidence |

All methods require a keyword `stamp`. Control events use `host_control`; plan/ACK also permit `host_policy_feedback`, ACK permits `server_observation`; emission uses `server_observation`; client observation uses `client_observation`. No method can resume a poisoned ledger.

Snapshots distinguish acknowledged and planned positions, epoch, pending work, generated/transport-emitted/client-observed prefixes, first accepted sample's **host observation** and terminal disposition. Work counters separate prompt-position executions, repeated prompt positions, retained generated-output positions replayed after eviction, and ordinary decode inputs. The last known output token may be replayed even if it had not previously been KV-computed; `retained_output_work` intentionally does not imply all of it is repeated computation. A failed ACK's confirmed work is a lower bound; its unconfirmed planned suffix is not classified as zero GPU work.

## Independent verification and durability

`Ledger.export()` returns detached JSON-compatible data. Each accepted event has contiguous sequence, raw inputs, labeled time and an advertised snapshot. The reference checker independently rebuilds state from inputs and compares every snapshot with type-sensitive canonical JSON. Rejection records poison the whole run. Reordering ACKs, changing prefixes, removing events or editing counters cannot be hidden behind the producer's own PASS flag.

```sh
PYTHONPATH=src python -B -m robustbench.serving_v2.reference journal.json --require-complete
```

`validate(journal, require_complete=False)` can establish a valid **prefix**, with `closed=False`. `--require-complete` additionally demands terminal dispositions, no pending work, empty observed ownership and all successful outputs emitted/observed. A closed FAILED/CANCELLED request is accounted for, not successful inference. `physical_status` is always NOT_VERIFIED, including if caller provenance says `physical`.

P1 stores evidence in memory and exports a deterministic detached journal; it does not introduce a disk writer into the serving path. The caller must persist and checksum exports. Crash-safe streaming/fsync, whole-run offered-ID inventory, simultaneous pool reconciliation, actual runner attestations and native ingress integration remain later tasks. A self-consistent export cannot prove that an entire omitted request or a changed physical input ever existed; an independent external manifest is required at integration.

## Cost and limitations

Snapshots copy accumulated output and prompt-position history, and exports serialize the complete journal. Costs grow with event count and context/output length; they are not suitable for silent insertion into timed serving. There are no timings inside transitions and no performance/overhead claims. Future integration must choose a bounded durable event sink, avoid unnecessary hot-path copies, freeze semantics and validate optimized serialization against this independent referee, then measure overhead under separate authorization. Do not interpret synthetic clock values or CPU test wall time as serving latency.
