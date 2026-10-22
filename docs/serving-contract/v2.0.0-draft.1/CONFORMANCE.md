# State-transition and conformance matrix

**DRAFT; not executable scheduler acceptance.** [SPECIFICATION.md](SPECIFICATION.md) defines the transition table and counters. [cases.json](cases.json) contains 32 independently hand-specified inputs/expected outputs. No implementation generated the expected decisions. `validate_documents.py` checks structural/arithmetic consistency only; it is not a reference scheduler and cannot certify these proposals faithful or physically executed.

Conventions: B is scheduled input-token budget; P original input; Y immutable generated prefix; G=len(Y); C_exec acknowledged KV prefix. `[17,18]` are deterministic synthetic sampler symbols, not expected model predictions. Unless specified, slots/KV are ample, all requests have arrived, output limit is nonbinding, and no prefix cache/speculation/parallelism is enabled. Each named profile comparison starts from the same input snapshot; rows from different profiles are **alternatives**, never successive iterations. C10 and C11 are separate capacity scenarios, not a dynamic increase of hardware resources. Selected requests appear exactly once; absent requests receive zero work.

| Cases | Independent expectation | What future implementation must prove |
|---|---|---|
| C01–C02 | P4/B8 -> q4 then q1, Y=[17] then [17,18]; P10/B4 -> q4/4/2, no samples until final prefill | Optimistic scheduling, successful spans and sample eligibility are distinct. |
| C03–C04 | With B4: critical decode gets 1, long/paused prefill gets 3; a waiting one-token prompt does not bypass paused prefill | Shared budget, paused-first stage and queue conservation. |
| C05 | Held decode keeps LST/KV/slot; next eligible iteration progresses once | Holds do not simulate preemption, emit tokens or refresh deadlines. The other request's between-step cancellation is explicit. |
| C06 | Equal LST/arrival uses stable ordinal in proposed profile | Intentional tie extension; no comparison of opaque Sequence objects. |
| C07–C09 | Temporary fit refusal retains waiting; permanent empty-device mismatch is rejected with ledger; P8/B4 on two usable four-token blocks allocates one block then two total | Full-input fit versus current physical allocation; no token clipping to fit memory. |
| C10–C11 | Preempted generated prefix [17] survives C reset; replay q4 then q1 emits only new token [18] | KV recomputation is repeated work, not a new request or regenerated output prefix. |
| C12–C13 | Native tail victim and adapted-SLAI paused-tail victim differ; source conservative append gate can refuse when native needs no extra block | Exact profile identity, allocator/victim differences and no fallback. |
| C14–C15 | Lifetime O survives reset; reference final-prefill sample is discarded while native final-prefill sample may commit | Do not label the common-execution adaptation literal source sampling equivalence. |
| C16–C19 | Bad class/ID/sample/ACK fails without false success | Invalid-input handling and plan-to-runner binding, including missing/duplicate/unknown IDs. |
| C20–C21 | Mean(.01,.02)=.015; end10+TBT.1−5*.015=10.025, or offset10 ->9.95; held/partial entries unchanged; invalid KV scalar fails | Precisely frozen timing and pressure denominator, no history mutation on invalid input. |
| C22–C25 | Changed prefix, cancellation race, backward timestamps and coalesced chunks cannot become clean measurements | Output conservation, lifetime identity and truthful observability. |
| C26–C27 | Missing TP rank is not acceptance; duplicate DP receipt is a failure | Per-rank ACK fence and exactly-once route semantics. |
| C28–C29 | Terminal rescheduling fails; blocked growing prefill self-preempts under proposed incremental-KV adaptation | Impossible transitions and a case absent from reference eager-prefill allocation. |
| C30–C32 | Persistent pause FIFO is not arrival-sort; non-strict classes share a priority tier; P+O>L rejects without truncation | Distinguish declared policy adaptation from historical tiers and frozen length rules. |

Before implementation, the author must approve the profile/decisions attached to each proposed case and freeze this corpus at a content hash. A second reviewer must check the cases independently. Add exhaustive small-state enumeration of positions/budgets/slots/block counts/classes/ties/cancellations using a separately specified reference, not the production planner or saved adapter PASS flags. Test both expected successes and rejected/unsupported states. Characterization of pinned-source quirks is evidence for a difference, not an acceptance requirement to reproduce a bug.

Before physical use, replay the approved corpus through real native scheduler/KV objects with synthetic ACKs, then the independently authorized model-runner fixtures. Compare intended plan, final native acceptance and ACK spans plus emitted output identity. Zero required-case mismatches; no approximation tolerance for token/identity/block conservation. Timings use separately approved uncertainty/margins; physical performance is not established by exact control-flow agreement.
