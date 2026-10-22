# P1 case-by-case conformance

The [unchanged PR #5 corpus](../v2.0.0-draft.1/cases.json) remains the source of expectations. No expected result was rewritten to match this implementation. **P1_EXECUTED** identifies the request-local abstract sub-contract, not all scheduling/physical clauses in that case. **P1_PROJECTION** exercises a specified subset without resolving the rest. **BLOCKED** is a documentary gate, not a pytest skip.

| Case | Status | Executed test / remaining boundary |
|---|---|---|
| C01 | P1_EXECUTED | `test_literal_prefill_cases[C01]` — Short prefill, first sample, decode/cap; release is a separate recorded event. |
| C02 | P1_EXECUTED | `test_literal_prefill_cases[C02]` — Literal 4/4/2 spans and 0/0/1 sample transitions. |
| C03 | P1_PROJECTION | `test_C03_prescribed_concurrent_work_is_not_policy_selection` — Prescribed two-request spans/counts; selection, global budget and priority remain S02/S04/native gates. |
| C04 | BLOCKED | `none` — Critical/paused/waiting priority selection requires S02 and native integration. |
| C05 | P1_PROJECTION | `test_C05_hold_C07_wait_are_observations_only` — Hold retains state; no numeric LST or queue-priority behavior is implemented. |
| C06 | BLOCKED | `none` — Tie/class queue order remains S02. |
| C07 | P1_PROJECTION | `test_C05_hold_C07_wait_are_observations_only` — External refusal records wait with no progress; full-input-fit rule remains S04. |
| C08 | BLOCKED | `none` — Permanent memory eligibility requires S04 capacity policy/native evidence. |
| C09 | P1_PROJECTION | `test_C09_literal_allocation_observations_without_allocator` — Literal block observations reconcile; allocation decisions not implemented (S04). |
| C10 | P1_PROJECTION | `test_C10_literal_external_preemption_effect` — External preemption effect matches; self-victim selection and refusal remain S04. |
| C11 | P1_EXECUTED | `test_C11_C14_repeated_recompute_preserves_lifetime` — Known prefix replay without re-emission; observed preemption is supplied, not selected. |
| C12 | BLOCKED | `none` — Native versus SLAI victim decisions require S04 and native integration. |
| C13 | BLOCKED | `none` — Conservative reference allocator comparison requires separate source/native conformance. |
| C14 | P1_EXECUTED | `test_C14_literal_cap_two` — Original lifetime O=2 survives reset; no third output permitted. |
| C15 | P1_PROJECTION | `test_literal_prefill_cases[C01]` — Native-adapted final sampling exercised; reference-runtime discard branch not executed. |
| C16 | P1_PROJECTION | `test_C16_metadata_shape_not_class_policy` — Malformed/duplicate immutable metadata rejected; class semantics unresolved S02. |
| C17 | P1_EXECUTED | `test_C17_identity_unique_for_lifetime` — Request and engine reuse rejected in waiting/running/terminal states. |
| C18 | P1_EXECUTED | `test_C18_sample_on_intermediate_chunk` — Positive sample before catch-up rejected atomically. |
| C19 | P1_EXECUTED | `test_C19_ack_rejection` — Duplicate/stale/out-of-order/unbound ACKs rejected. |
| C20 | BLOCKED | `none` — No LST numeric threshold/offset/mean population frozen by delegated S05. Clock interval validation only. |
| C21 | P1_PROJECTION | `test_allocation_observations_fail_closed` — Typed integer observation checks; original scalar KV/LST guard remains unchanged and tested in existing suite. |
| C22 | P1_EXECUTED | `test_referee_detects_corrupt_snapshot` — Referee detects changed output prefix; export cannot mutate live prefix. |
| C23 | P1_EXECUTED | `test_C23_cancel_race_records_discarded_sample` — Cancellation fence, discarded late sample, ACK/quiescence and terminal accounting. |
| C24 | P1_EXECUTED | `test_C24_same_domain_reversal_and_separate_clocks` — Same-domain causal reversal rejected; separate domains not numerically compared. |
| C25 | P1_PROJECTION | `test_C22_C25_prefix_and_chunk_evidence` — Two tokens retained in one observation event; no invented generation times/SLO classification. |
| C26 | BLOCKED | `none` — TP rank ACK protocol unresolved S08; no TP implementation. |
| C27 | BLOCKED | `none` — DP routing/replica semantics unresolved S08; no DP implementation. |
| C28 | P1_EXECUTED | `test_C28_terminal_cannot_be_replanned` — Terminal rescheduling rejected. |
| C29 | P1_PROJECTION | `test_C29_partial_preemption_effect_not_victim_choice` — Partial-prefill reset/replay effects executed; victim/allocator trigger remains S04. |
| C30 | BLOCKED | `none` — Paused FIFO selection requires S02. |
| C31 | BLOCKED | `none` — Binary/nonbinary priority mapping remains S02. |
| C32 | BLOCKED | `none` — Target context/model/eligibility requires S07; positive abstract P/O is not model-context validation. |

All physical/native-v2 acceptance remains NOT VERIFIED. Existing native-vLLM CPU characterization tests still use synthetic runner outputs and are reported separately from P1. P1 accepts externally supplied plans and allocation observations; it does not certify their priority, budget, victim or model feasibility decisions.

The independent referee uses a separately declared legal-edge table, per-epoch position sets and a work-position history. It imports no producer code. Tests corrupt raw events and advertised snapshots and monkeypatch the producer to invent an intermediate-prefill token; the referee rejects them. This is algorithmic independence within one authoring task, not a claim of a second human/agent review.

## Exhaustive campaign

All possible positive contiguous chunk lengths and optional external preemptions at every admitted/acknowledged boundary are enumerated until the output cap:

| P | O | Maximum preemptions | Complete histories | Maximum journal events |
|---:|---:|---:|---:|---:|
| 1 | 1 | 2 | 3 | 11 |
| 1 | 2 | 2 | 11 | 18 |
| 2 | 1 | 2 | 14 | 17 |
| 2 | 2 | 2 | 70 | 24 |
| 3 | 1 | 1 | 20 | 17 |
| 3 | 2 | 1 | 52 | 22 |

Total **170 complete histories**, deterministic lexical traversal, **no random seed**. Each history checks progress/prefix invariants after every step and complete independent journal validation at the end. Plans never advance acknowledged progress; all generated symbols depend only on lifetime output index. Different P/O configurations are disjoint. Repetitions of the test suite are not counted as additional histories/tests.

Bounds exclude arbitrary concurrency, cancellation/failure interleavings, allocator states, classes and distributed states. Those are covered only by the named focused tests or remain blocked. The campaign is not an exhaustive proof for unbounded requests or native execution. Adversarial tests separately cover cancellation/quiescence, partial failure, duplicate/cross-request/stale ACKs, corrupt snapshots/events, invalid typed observations and clock boundaries.
