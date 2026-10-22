# Conformance coverage and limits

The 415 distinct inherited CPU tests are retained without edits. P2A adds a separate test directory. The final collected-node list and raw run determine counts; repetitions and exhaustive histories are not counted as separate pytest tests. The original 32-case corpus and P1 case dispositions remain unchanged. P2A adds batch-boundary coverage, not approval of blocked original cases.

| P2A case | Expected outcome and evidence | Executable test(s) |
|---|---|---|
| B01 Split prompt | P300, B128 → spans [0,128), [128,256), [256,300); 0/0/1 valid samples, then decode [300,301) | `test_split` |
| B02 Decode/prefill contention | One decode token leaves 127 for long prefill; active requests include partial prefill | `test_contention_and_slots` |
| B03 Slot boundary | Waiting C remains while two resident slots occupied; admission after cap completion | `test_contention_and_slots` |
| B04 Proposed subset/order/short chunk | Native substitutes extra/larger/reordered work; no ledger planning/ACK commit, permanent stop | `test_native_silently_substitutes_policy_is_no_go` (4 cases) |
| B05 Sufficient no-pressure bound | Insufficient lifetime capacity rejected before schedule; not called native OOM | `test_lifetime_capacity_rejection_before_native` (3 cases) |
| B06 Actual native full-input refusal | Native P256 cannot admit with 8 usable blocks even though a 128-token chunk could fit | `test_actual_native_refusal_without_adapter` |
| B07 Unexpected allocation refusal | Injected allocator refusal leads to raw empty native map and rejection | `test_unexpected_native_refusal_stops` |
| B08 Stale/mismatched/partial ACK | Wrong batch/step/epoch/spans/mask/provenance or false success/quiescence rejected atomically | `test_invalid_ack_atomic` (11 cases) |
| B09 Runner identity/sample rows | Duplicate/missing/wrong/indexed requests, missing/extra/invalid tokens rejected | `test_bad_runner_rows` (8 cases) |
| B10 Invalid proposals | Duplicate/unknown spans, wrong positions/counts/types/budgets/slots rejected before native | `test_bad_proposals` (9 cases) |
| B11 Missing/duplicate ACK | Valid open prefix differs from complete run; repeated ACK poisons | `test_duplicate_ack_and_missing_ack` |
| B12 Partial batch failure | One valid row plus a bad second row commits neither request | `test_partial_batch_failure_no_partial_commit` |
| B13 Identity/immutability | Duplicate IDs or changed prompt tokens rejected | `test_duplicate_request_identity`, `test_immutable_request_guard` |
| B14 Source/opt-in guard | No opt-in or changed selected source hash rejected | `test_source_and_optin_guards` |
| B15 Corrupted native records | Independently rejects acceptance, raw wire, KV ownership, queue, offsets, ACK, ledger, provenance tampering | `test_independent_referee_corruptions` (25 cases), `test_strict_telemetry_types` (5 cases) |
| B16 Faulty producer | Adapter falsely advertises B-only acceptance; referee derives A/B from registry and rejects. Deleted ledger ACK also rejected. | `test_faulty_adapter_invents_acceptance`, `test_faulty_adapter_drops_ledger_ack` |
| B17 Small-state campaign | 216 complete actual native CPU runs, deterministic Cartesian enumeration; independent FCFS proposals/expected masks and end-to-end batch referee | `test_exhaustive_small_native_schedules` |
| B18 Cancellation race | Actual native abort between schedule/update causes refusal; no fabricated ACK or recovery | `test_cancellation_race_stops_without_ack_progress` |
| B19 In-flight overlap | Second proposal before ACK rejected without another native call | `test_second_batch_before_ack_is_rejected` |
| B20 Unsupported configuration | Priority, async, threshold, caching, TP/DP/PP and legacy runner selection rejected | `test_unsupported_configuration` (8 cases) |
| B21 Isolation/reproducibility | Export detached; referee imports without producer/native/heavy libraries; durable synthetic fixture | `test_detached_export_and_no_import_of_producer_in_referee`, `test_fixture_evidence` |
| B22 S02 distinguishing priority | Medium-long vs loose-short distinguishes binary candidate from existing three-tier order | `test_s02_binary_vs_three_tier_literal_case` (comparison only) |
| B23 S02 unresolved heap tie | Equal LST/arrival keys cannot order opaque sequence objects; ordinal resolves tie | `test_s02_explicit_ordinal_resolves_equal_heap_keys` (comparison only) |
| B24 S02 paused vs held decode | Proposed paused-prefill-only work rejected; native runs resident decode first | `test_noncritical_decode_vs_paused_prefill_distinguishing_case` |

| B25 Native runner permutation | Pinned V2 helper orders decode/short/long; output tokens map by ID, preserving scheduler-plan identity | `test_pinned_v2_runner_row_permutation` |

Campaign bounds: two requests, each P ∈ {1,2,3}, O ∈ {1,2}, B ∈ {2,3,4}, N ∈ {1,2}; 3² × 2² × 3 × 2 = **216**. Deterministic enumeration, no randomness/seed. Each starts fresh native/P1 state and drains under the independent reference within 10 steps. Positive native rows are synthetic token IDs; no numerical model correctness is implied. The case is one pytest node, not 216 tests. Larger P300 and concurrent-arrival cases are separately literal-tested.

## Explicitly unresolved / not verified

- Source-backed interface for **enforcing** general SLAI plans, paused FIFO/critical ties (S02); no priority mapping is installed.
- General pressure, victim selection, preempt/recompute/rollback/cancel recovery, shared KV or multiple groups (S04). Raw native refusal characterization does not validate a pressure policy.
- Real GPU executed positions, partial runner failure, physical quiescence, sampler numerics, worker/model state and actual emission/client timestamps.
- Numerical LST settings and feedback update semantics beyond the delegated host-domain distinction.
- Target model/tokenizer/context and realistic Azure/Bailian/BurstGPT eligibility (S07). No source trace truncated or selected. The old short-fixture limitations remain.
- TP2/DP2/PP, all-rank output identity, routing and rank-specific capacity (S08).
- Physical scheduling ranking, timing overhead, A100/L40 portability, four-policy readiness, any new scientific workload/result.

No skipped pytest nodes are used to disguise these gaps. They are documented unsupported domains, not passed tests.
