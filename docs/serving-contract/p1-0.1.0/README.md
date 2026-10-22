# P1 execution ledger and independent referee / 0.1.0

Implemented CPU-only P1 on the exact approved PR #5 head. This is an opt-in library and an offline verifier; no historical import, simulator, scheduler, launcher or experiment manifest changes. Start with the [delegated approval/amendment](APPROVAL_AMENDMENT.md), [API](API.md), [case matrix](CONFORMANCE.md), and [validation record](VALIDATION.md).

Source:

- `src/robustbench/serving_v2/ledger.py`: immutable request/plan/ACK/allocation/clock objects and guarded request-local transitions; append-only accepted journal plus fail-closed fault record.
- `src/robustbench/serving_v2/reference.py`: separately implemented declarative transition graph, confirmed-position sets and work history; reconstructs every advertised snapshot from raw events. No production imports, constants, validators or transition helpers.
- `tests/serving_v2/`: literal cases, negative boundaries, journal corruption, a deliberately broken producer, import/CLI checks and exhaustive bounded histories.

A valid plan is not acknowledged work; an ACK is not proof of GPU execution. Referee validity establishes agreement with this abstract CPU contract only. Missing terminal/transport/release evidence prevents `closed`; malformed/faulted evidence prevents validity. No per-token latency, SLO, ranking, numerical-equivalence or scheduler-priority claim follows.

## Remaining gates and P2 decision

**P2 NO-GO as an implementation authorization in this task.** P1 CPU conformance is a prerequisite now supplied, not permission to enable serving. Before P2:

1. Review this draft implementation, its independent referee and the scope of delegated S01/S03/S05/S06 choices. Freeze the accepted source/schema/corpus hashes.
2. Resolve S02 for any SLAI queue/class/tie/paused-priority work. Resolve the relevant S04 subset before native admission, allocation or rollback integration; a no-pressure scope must still define its enforced capacity/refusal boundary. Do not silently adopt the older proposal's victim rules.
3. Approve host-feedback boundaries and any feedback aggregation/parameters that P2 would compute. P1 records labeled intervals but freezes no numeric LST behavior.
4. Pin and independently specify the actual native acceptance/runner-ACK interface: position/sample masks, identity/epoch binding, failure/quiescence evidence, batch budget and active-slot conservation. CPU ledger agreement alone cannot attest execution.
5. Keep S07 and S08 gates closed for realistic trace/model selection and distributed work. No source window, output rule or main context is chosen here.
6. Authorize a narrowly scoped next coding task. Any later physical work requires separate resource authorization and overhead/fidelity gates; none is conferred by this PR.

The existing MGPU06 first-pair commit/configuration remains unchanged. This branch is not a replacement approved execution checkout. General partial-prefill/KV-pressure serving, four-policy, TP2/DP2 and ranking-transfer experiments remain NO-GO.
