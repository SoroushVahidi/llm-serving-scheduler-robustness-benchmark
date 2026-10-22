# Prospective serving contract: lssp-serving-semantics/2.0.0-draft.1

**Every normative rule here is a proposed requirement, conditional on author approval.** This draft adds no runtime support. Source observations are separated in [SOURCE_COMPARISON.md](SOURCE_COMPARISON.md). All profile/configuration choices are explicit; no default may broaden the existing execution contract.

## Scope and profiles

Initial scope: synchronous, one in-flight engine iteration, dense decoder-only text generation, one continuation per request, no speculation, prefix caching, streaming input, LoRA, encoder work, disaggregated KV transfer or PP/context parallelism. A main checkpoint, tokenizer, context L, output limits, token budget B, active limit N, block size and per-group capacities must be approved and pinned; this document supplies no new numerical deployment defaults. Long prompts may require multiple iterations; P+O<=L is required for the fixed-work primary cohort.

Candidate profile IDs:

- `native-vllm-0.27.1-fcfs/v2-draft`: preserve pinned native queue, allocation, preemption and progress behavior. Independent records must verify what the native engine actually did.
- `lssp-slai-nativekv/v2-draft` (**recommended adaptation, UNRESOLVED S01**): SLAI stage ordering and paused-prefill victim preference on the common native execution/allocator, with the explicit adaptations below. This is not literal pinned-SLAI runtime equivalence.
- `slai-reference-5098a7/source-observation`: comparison-only source profile, not deployable. Literal memory gates, sample handling, heap ties and output-limit hazards are retained in the evidence discussion. Implementing a source-compatible alternative requires a new approved profile, not reuse of the adapted profile name.

For the adapted profile, the recommended choices are: binary strict/non-strict admission as in the reference, with per-request TBT still allowed; stable final ordinal tie-breaking; native final-prefill sampling; native incremental KV allocation/full-input-fit admission; source-inspired paused-prefill-tail then self victims for a blocked decode; no waiting admission in an iteration containing preemption; a durable lifetime output limit; a common measured host-batch boundary. These departures are jointly visible in S01–S06. Choosing three-tier admission instead requires another declared profile/version; the old MGPU three-tier contract remains unchanged.

## Identity, ledgers and progress

Key each request by `(run_id, offered_request_id)`, and bind exactly one route/replica, API identity and engine identity. Attempt/epoch IDs distinguish recomputation from a second logical request. No ID reuse, hidden retry or duplicate response is permissible. Stable ordinal resolves only declared policy ties; it cannot rewrite actual native receipt order.

Immutable P is the length of the prepared input vector, including any approved template/special tokens. O is the lifetime new-output-token target/limit; neither changes on preemption. Preserve the original prompt digest and immutable ordered generated prefix `Y`. Let G=len(Y), E be the acknowledged prefix count delivered to the client, and H=P+G the currently known context length. Always 0<=E<=G<=O. Keep generated/committed, transport-emitted and client-observed prefixes distinct.

Each manifest must declare `output_rule` under S07. Recommended length-matched compute-shape replay uses `fixed_target`: successful completion requires G=O, with EOS/stop handling explicitly configured and pinned to preserve the target; early termination remains a visible incomplete/error outcome. A separate `natural_stop` cohort permits declared EOS/stop conditions before O and measures actual output work. These are different workload constructions and cannot be silently pooled. This draft does not change any existing generation flag or approve the choice for future windows.

For each request epoch maintain:

- `C_exec`: successfully acknowledged contiguous KV-computed prefix of the current known context, initially zero; reset only on explicit KV invalidation/recompute. A reset does not erase Y, G, E, original TTFT or arrival.
- `C_plan`: optimistic native/scheduled prefix. With synchronous execution, it equals C_exec when no batch is in flight and C_exec+q after scheduling q positions. Native `num_computed_tokens` is evidence for C_plan, not an ACK.
- `q`, planned span `[C_exec,C_exec+q)`, work kind (`initial_prefill`, `prefill_continuation`, `recompute_prefix`, `decode`), epoch and batch ID. Require 0<q<=H−C_exec for scheduled requests, sum(q)<=B, and admission/ownership count<=N.
- Cumulative executed original-input positions, repeated-input positions and decode-input positions, separately from useful new sampled output. Never count replayed known tokens as new output goodput.

At a successful intermediate chunk, C_exec increases by q, G is unchanged and no output sample may be committed. When the scheduled span catches H, a nonterminal native generation step can commit exactly one new sampled token and G increases by one. At an ordinary decode-ready boundary, C_exec=P+G−1, G>0. After invalidation with G>0, replay the complete known P+G context in chunks; only the final catch-up may append the *next* token. Do not re-emit the retained G-token prefix. Terminal/cancelled requests are never scheduled merely to reconcile an equality.

The engine may internally compute a sample that is discarded for an intermediate prefill; distinguish raw sampler slots, valid sampled IDs and committed emissions. A real ACK must attest to executed positions, not be inferred solely from the optimistic counter. A single native callback can contain multiple requests; it is not a GPU generation timestamp.

## Logical state machine

These are observation/contract states, not a renaming of all native enum values. `IN_FLIGHT` carries the originating state and work kind; `HELD` is a per-iteration decision on DECODE_READY, not eviction.

| From | Trigger / preconditions | To | Required changes and invariants |
|---|---|---|---|
| UNSEEN | Valid identity, metadata, prepared payload/context | WAITING | Register exactly once; no KV or executed work. Record receipt separately from offered arrival. |
| UNSEEN | Invalid metadata/identity, impossible fixed context | REJECTED | Explicit reason and retained offered-request record; no queue/KV mutation. |
| WAITING | No active slot, token budget or temporary KV capacity | WAITING | Reasoned wait, no invented admission/sample/progress. No silent drop. |
| WAITING | Approved policy selects q and allocation succeeds | IN_FLIGHT | Record first admission, KV allocation, span and epoch. C_plan advances; C_exec/G do not. |
| PREFILL_PAUSED | Selected next chunk, same epoch | IN_FLIGHT | Continue at C_exec; preserve original prompt, prior KV ownership and FIFO pause order. |
| RECOMPUTE_WAITING | Capacity restored and policy selects replay | IN_FLIGHT | Allocate again, starting at C_exec=0; replay immutable prompt plus retained Y. Original G/E/TTFT persist. |
| RECOMPUTE_PAUSED | Selected continuation of resident replay | IN_FLIGHT | Retain blocks and active slot; continue from acknowledged C_exec. |
| IN_FLIGHT | ACK, C_exec+q<H before sample | PREFILL_PAUSED or RECOMPUTE_PAUSED | Advance executed prefix; zero committed samples; preserve prior LST but do not make a recomputing request decode-eligible. |
| IN_FLIGHT | ACK reaches H and commits one token, G+1<O | DECODE_READY | Append exactly one new ID to Y; update G and LST for this progressed request. First-ever sample establishes server-observation TTFT boundary. |
| DECODE_READY | Selected one-input-token step | IN_FLIGHT | q=1, native block-delta check, no budget/slot theft from holds. |
| DECODE_READY | Policy defers this iteration | DECODE_READY (HELD) | q=0; retain KV/active slot, Y and LST. No fabricated batch or service time. |
| PREFILL_PAUSED, RECOMPUTE_PAUSED or DECODE_READY | Explicit preemption, no outstanding ACK | RECOMPUTE_WAITING | Free owned blocks, increment epoch, C_plan=C_exec=0, retain Y/G/E, output limit, arrival and first-token history. Remove stale policy queue membership. |
| IN_FLIGHT | Valid completion reaches O or permitted EOS/stop | TERMINAL | Commit final token once, terminal reason; release blocks only when safe. No new LST for terminal request. |
| WAITING / paused / decode-ready | Cancel/error | TERMINAL | Preserve prefix/errors, cancel record and resource-release evidence. Never call incomplete response success. |
| IN_FLIGHT | Cancel/error before ACK | CANCEL_PENDING, then TERMINAL | Fence epoch, record/discard late samples rather than deliver after terminal. Free only after device use is known finished; otherwise invalidate/stop execution. |
| Any | Duplicate ACK, wrong epoch/span, invalid KV observation, impossible transition | CONTRACT_FAILURE | Preserve evidence; stop affected execution; no silent repair, restart, pooling or resubmission. |

WAITING and RECOMPUTE_WAITING own no resident KV/active slot. PREFILL_PAUSED, RECOMPUTE_PAUSED and DECODE_READY remain resident and count against N even when not selected; IN_FLIGHT retains that ownership. Queue membership is unique. A resident replay continuation must not be treated as an unadmitted waiting request.

Source waiting/preempted/paused distinctions must be logged alongside these logical states. A temporary lack of KV is overload, not invalid input. A request whose current known context cannot fit even in an otherwise empty admitted domain is an explicit unsupported case (preflight when knowable); retain it in the exclusion/coverage ledger. If capacity cannot be known before hardware profiling, eligibility is NOT VERIFIED, not presumed. Native full-input-fit does not reserve the lifetime output allowance. If a later P+G becomes permanently unfit, record that failure and stop the affected run under the approved failure policy; do not spin forever or invent capacity. C10 ends at preemption and deliberately does not claim eventual completion. The separate C11 fixture has sufficient capacity.

## Policy choices and KV rules

Native profile: running order and native FCFS waiting queue are authoritative. Native preemption may revoke earlier plans and restore budget before the iteration returns. The final accepted plan, not an earlier candidate, must match execution. Arrival ordering uses actual engine reception; scheduled source arrival and dispatch drift remain separate evidence.

Adapted SLAI profile proposal:

1. Consume completed-batch updates, then snapshot one finite monotonic `now` and all queues. Select critical decode-ready requests by `(LST, engine_arrival, stable_ordinal)`, where now>=LST. Enforce the declared decode limit K.
2. Continue the persistent paused-prefill FIFO, including replay entries once admitted. Entries append in completion/previous-plan order; do not sort by prompt length or arrival afterward. Each gets min(remaining known context, remaining budget), subject to the declared native per-request chunk cap and KV allocation.
3. Consider already arrived WAITING requests in stable `(strict_class, original_prompt_length, receipt_order, ordinal)` order (strict first). A RECOMPUTE_WAITING request retains the same original length key; this deliberately differs from the reference's folded mutable prompt length. Stop at the first active-capacity or full-input-fit refusal; no opportunistic bypass unless a separately approved policy states it.
4. Use residual budget/decode capacity for noncritical decodes in the same LST order. Holds retain active slots and blocks.
5. For a selected decode whose *actual native block delta* cannot fit, evict paused-prefill tail victims (exclude in-flight work), then self if necessary. Revoke a victim's tentative plan and refund its budget exactly once. If a continuing prefill itself cannot grow under native incremental allocation, self-preempt it; the reference's eager reservation avoids this case, so this is an explicit S04 extension. Victims enter a recompute queue and cannot re-admit in this iteration. Skip waiting admissions on any preempting iteration; remaining valid running work may proceed. No native fallback victim is allowed.

The phases define a candidate contract, not a proven port. Proof obligations include termination/no double-membership, no same-step victim execution, no negative budget or double-free, and no starvation claim. No full-request output-length oracle may influence priority. Exact K/chunk thresholds and binary-class mapping remain author choices; conformance fixture numbers are not deployment settings.

For each KV group/rank, record total, null/system-reserved, free, allocated/pinned and reservation-only blocks separately. For the initial full-attention/no-prefix-sharing profile, disjoint physical ownership plus free and system blocks must equal total. Virtual reservation claims must not be double-counted as physical blocks. Keep per-request logical positions and physical block tables; allocation/refusal/retention/release events must reconcile. Block rounding, head partitioning and dtype affect bytes, so B and N cannot stand in for memory. No KV eviction may erase previously generated output identity or its timing history.

Native current-input fit checks, reference eager allocation and a proposed reservation manager are distinct choices. Recommended native KV accounting applies to every policy in the common-engine study, while explicit SLAI victim rules remain policy-specific. This changes the research claim to a declared SLAI adaptation. Source-exact KV reproduction is a separate alternative; it must model the conservative reference append gate and watermark behavior and cannot share the same policy ID.

## LST and timing proposal

Use a monotonic host clock with recorded host/boot/time-namespace IDs. Define a batch interval from immediately before policy planning to validated runner-output application and safe terminal cleanup. It includes host scheduling/dispatch/processing; it is not kernel time. Update the unweighted arithmetic mean once per successful nonempty batch, including partial-prefill batches. Do not update it on empty steps, failed batches or duplicate ACKs. Keep start/end/duration/mean sample count and KV snapshot in raw evidence.

For each successfully progressed, unfinished decode-ready request only:
`LST = batch_end + TBT(request) - offset(KV_snapshot) * cumulative_mean_duration`.
Partial-only prefills have no first LST. A held request keeps its previous LST; a preempted one may retain a diagnostic LST but cannot use it to skip replay. Upon final replay/sample its next LST uses the successful completion. Snapshot usable-block occupancy after terminal frees, matching the declared denominator; do not call it physical GPU memory utilization. Pin offset mode/threshold/values separately. Illustrative .96 and 5/10 cases mirror the old bounded choice, not new authorization. Native FCFS ignores these policy fields.

The common host-boundary adaptation differs from both exact engine call paths and needs overhead validation. Never subtract raw monotonic times from different hosts. For TP, use coordinator-observed barrier/ACK intervals for policy timing and retain rank-local durations; for cross-host client/router/replica comparisons require clock calibration and bounded uncertainty or report incomparable quantities as NOT VERIFIED.

## Minimum durable data / independent validation contract

| Record | Minimum fields / verification |
|---|---|
| Run and environment | Contract/profile/revision, exact executable/source/model/tokenizer/config hashes, deployment topology, cache/numerical flags, raw capacity measurement, provenance (`physical`, `cpu_fixture`, `simulated`), clock domains, event-sequence schema. |
| Offered request | Stable IDs, raw-source coordinates/hash, source lengths, target IDs/count/hash, rendering/template rules, lifetime O, class/strict/TBT/deadline/weight provenance, scheduled arrival; eligibility/rejection reason without disappearance. |
| Ingress / route | Client dispatch/transport observations, server receipt, immutable DP route and replica; API-engine ID binding; timestamp boundary and domain. Actual receipt requires an ingress hook, not renaming scheduler add_request. |
| Policy snapshot / intent | Iteration/epoch, ordered queues, C_exec/C_plan/G/E, LST/history/now, B/N/K, per-group free/reserved ownership, candidate decisions, hold/wait/refusal/victim reason, final intended token spans. |
| Native acceptance | Exact accepted request/position/token map, block deltas, status/epoch transitions, preemptions, independent native step ID; distinguish candidate and revoked plans. |
| Runner submission / ACK | Batch/epoch/rank IDs, exact input-position spans or their reconstructible hashes, dispatched versus successfully executed positions, valid sample mask/IDs, exceptions, first/last host callback, stale-output disposition. An optimistic counter or empty sample list alone is insufficient execution proof. |
| Output ledger | Append-only original Y, generated/committed/emitted/observed counts, token indexes and IDs/digests, text decode reconciliation where permitted, finish reason, usage, DONE, cancellation/error and incomplete status. Record replayed tokens separately. |
| Timing | Scheduled arrival; dispatch; ingress; admission; schedule/submission/ACK; server token-emission timestamps if instrumented; SSE chunk observations with exact token-index ranges; completion/terminal. Boundary labels are mandatory. |
| Seal / independent audit | Journal sequence continuity, hashes, command/version provenance, failure and cleanup records, raw intended/native/ACK three-way comparison, independent reference version and case results. No reliance on adapter PASS flags. |

For synthetic length-matched replay, retain full prepared token IDs and generated evidence where approved. Real prompt text is not required or assumed; hashes of sensitive text are not automatically anonymized. Tokenizer decode agreement is a content-transport check; re-encoding a decoded BPE string need not reproduce the original IDs. No semantic answer-quality or numerical identity across policies is required by this contract.

TTFT must name its endpoint (first committed host sample, server emission or client observation). E2E uses actual dispatch/completion in a valid domain; arrival-to-completion is separately labeled. TPOT can be an average over observed endpoints and G−1 when G>1; it is not an inter-token latency distribution. Streaming chunks may contain multiple tokens and cannot be relabeled per-token generation/emission times. Without required per-token observations, the draft main-study all-gap SLO goodput remains NOT VERIFIED; retain unknown classifications/coverage and bounds separately from actual timeout/failure classifications. Do not drop unobservable requests from the denominator or treat them as success. Metric changes require prospective A07 approval.

## Distributed extensions: specified gates, not support

TP2: one logical scheduler/commit authority, identical plan/epoch/positions on participating ranks, rank-specific KV ownership/capacity, explicit sampling-owner rank, one committed output stream, collective and failure evidence. Ranks need not have identical physical block IDs or all emit sampled IDs. Coordinator must receive all required execution acknowledgements; a missing rank cannot yield PASS. Recommended future pressure input is the maximum per-rank usable-block fraction (bottleneck), labeled as a new approved scalar rule; TP1 scalar evidence does not establish it.

DP2: recommend an external deterministic round-robin route fixed from offered ordinal before outcomes; independent TP1 engines, per-replica queues/LST/KV, exactly-once ingress and completion, router waiting separately measured. No availability-driven reroute, work stealing or retry in the initial profile. Record per-engine N/B and aggregate resources; DP2 aggregate 2N is not comparable to TP2 N without declaring the estimand. Whether limits should be per-replica or aggregate and how calibration is applied remain A05/A08/A09 decisions. PP/multi-node/context parallelism remain outside this draft's executable scope.
