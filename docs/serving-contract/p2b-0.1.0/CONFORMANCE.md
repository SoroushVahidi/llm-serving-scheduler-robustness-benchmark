# CPU conformance and outstanding gates

The final combined run passes **583 distinct tests: 508 inherited + 75 new**, with zero failures/skips. The inherited **508 distinct tests** run unchanged. P2B tests live only in `tests/serving_v2_p2b/`. Frozen prospective literals are in [literal-cases.json](literal-cases.json); five parameterized tests read their expected spans/masks directly. Expectations do not come from the adapter's acceptance output.

| Requirement | Tests / independent evidence |
|---|---|
| Original P2A larger chunk, extra requests, changed subset/order | Four `test_p2a_substitutions_now_enforced` cases; L01–L03; original P2A rejection tests still pass unchanged |
| Strict/binary vs old three-tier order | `test_s02_class_selection`, `test_s02_literal_and_independent_referee`, L04: tight16, loose2, medium8 |
| Stable equal-key ordinal | `test_equal_s02_keys_stable_unique_ordinal`, L05; lifetime ordinal collision rejected |
| Persistent paused prefill before new strict request; held decode | `test_s02_paused_fifo_and_held_decode`: P7 spans 0:3/3:6/6:7; strict P1 follows; resident decode unchanged until resumed |
| Multiple resident partials and explicit reordered selection | `test_multiple_paused_residents_reorder_exactly`; independent external intents and unchanged canonical membership |
| Intermediate zero samples / final one sample | Partial and final ACKs in literal/multistep cases; invalid sample-mask attestations rejected |
| All active slots including holds | `test_slot_conservation_includes_held_decode`, preflight slot checks; no hidden removal to create capacity |
| Budget bounds / exhaustion / short requested chunks | `test_explicit_budget_overcommit`, exhaustive plan enumeration, per-request clamp and no extra work |
| Pre-mutation invalid-plan refusal | Seven invalid-plan cases; cross-phase, capacity and inconsistent-state tests compare full native snapshots and current step |
| Unexpected native refusal, including partial allocation | `test_unexpected_allocation_refusal_no_rollback_claim`, `test_running_refusal_does_not_select_victim`; actual native allocation retained, no ledger ACK/victim/retry |
| Faulty hook | Larger native chunk and extra-native-request mutations rejected before acknowledgment; no fallback acceptance |
| Wrong/missing/stale/partial/failure/nonquiescent execution attestation | Twelve attestation mutations; missing/duplicate ACK test; clocks bound to planning/application |
| Native row permutation | `test_native_runner_permutation_preserves_output_identity`; canonical positions and bijective native IDs retained |
| Independent oracle corruption | Eleven record mutations, forged intent, wrong patch identity, faulty S02 policy; referee does not import producer decisions |
| No future output-length priority | View schema excludes output limits; swapping caps leaves priority order identical while whole-run no-pressure eligibility remains separate |
| Low-level guards | Direct hook construction requires explicit CPU opt-in; aliased native queue objects rejected before mutation |
| Package/source isolation | Original global `Scheduler.schedule` and installed SHA unchanged; changed insertion anchor rejected; isolated reference import excludes producer/vLLM/torch |

The independent external-plan campaign enumerates **48 feasible plans**, in **one pytest node**: P(a),P(b) ∈ {1,2}; budget ∈ {2,3}; active cap 2; selection/order in {a,b,a→b,b→a}; every positive per-request chunk length up to P with total ≤ budget. The per-prompt-pair counts are 8+12+12+16. No random seed, sampling or claimed physical execution. These are accepted/ACKed CPU prefixes, not necessarily drained runs; open-prefix versus complete validation remains explicit. This campaign supplements, and does not double-count, P2A's inherited 216 histories.

Development diagnostics are preserved: the initial patch-anchor match was ambiguous and correctly refused compilation; a tiny-budget fixture violated native B≥N and was corrected to valid B3/N3 with the same paused-priority purpose; enumeration metadata initially stated 58 instead of the independently counted 48; the first full run inherited a private umask that invalidated a permissions-test setup. No inherited tests or checks were weakened, and no scheduler expectation was changed to permit substitution. Final raw logs/node counts are authoritative.

## Not verified / disabled

Physical executed positions, actual sampler validity/numerics, GPU completion/drain, token emission/user latency and overhead; full SLAI criticality/LST feedback; selected waiting-before-resident interleaving; general pressure/preemption/victims/refund/recomputation; realistic tokenizer/context/trace coverage; TP2/DP2/PP; extra policy ranking or A100/L40 transfer. These are documented gates, not pytest skips or successful physical checks.
