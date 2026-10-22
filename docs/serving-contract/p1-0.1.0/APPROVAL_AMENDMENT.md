# Prospective delegated approval: P1 / 0.1.0

Authority: the author's P1 implementation request in this conversation, after review of draft PR #5. Verified base: `ee1868618db9afc89160e1d0daf92b54829a80bc`, stacked on #4 `efc5243898d18bbb62ccb51dcf66a0767827dac6` and #3 `b14992716c20b36d26e6f28e60b2c8e0b8b09a07`. All three were open drafts at inspection. No applicable filesystem AGENTS.md was found in the checked repository/ancestor locations; the conversation's bounded-task and long-job rules apply.

This document records **delegated author approval of working technical choices for CPU-only P1**, not approval of all draft v2 semantics, main-study preregistration, physical execution or numerical settings. Original PR #5 files, cases, hashes and unresolved-decision register remain untouched. This prospective amendment supersedes their unresolved status only for the narrowly scoped choices below. Historical results retain their original contract labels.

| Choice | Working choice selected under delegation | Status and boundary |
|---|---|---|
| S01 | Explicitly named common-vLLM SLAI adaptation; no literal reference equivalence claim | DELEGATED_APPROVAL_P1. No SLAI scheduling or vLLM hook is implemented here. |
| S03 | Final native prefill catch-up commits one valid sample; intermediate prefill commits zero | DELEGATED_APPROVAL_P1. CPU event semantics only; real runner sample eligibility remains a later gate. |
| S05 | Separately labeled common host policy-feedback interval, distinct from GPU execution and user observations | DELEGATED_APPROVAL_P1. Record caller-supplied intervals with clock domains; no LST calculation, numeric offset, threshold, mean population or automatic timing is introduced. |
| S06 | Immutable original prompt/output limit and arrival metadata; lifetime output prefix; preserved emitted prefix; new recomputation epoch; no implicit retries | DELEGATED_APPROVAL_P1. Explicit external preemption/ACK facts only; no allocator/victim implementation. |
| S02 | Priority/class/tie/paused ordering | UNRESOLVED. Opaque validated metadata is stored, never interpreted as priority. |
| S04 | Allocator, reservation, victim selection, budget/slot admission and rollback policy | UNRESOLVED. Typed observations and external admit/preempt events record effects without deciding them. |
| S07 | Main model/tokenizer/context, trace construction and output-stop rule | UNRESOLVED. Abstract positive P/O and prompt digest are inputs. COMPLETE means the cap was reached; early explicit completion is STOPPED, not fixed-target success. No context eligibility or EOS rule is chosen. |
| S08 | Rank/replica/routing/collective semantics | UNRESOLVED. No distributed fields or execution support. |

## P1 abstraction refinements

These refinements make the approved abstract ledger implementable without resolving other choices:

- **ADMITTED** is a request-local bridge between externally observed admission and a plan. It does not choose an active limit or allocate memory. Request-local one-pending-plan enforcement does not prove global batch-budget or single-in-flight-batch compliance; those remain native integration obligations.
- **FAILED_PENDING** parallels CANCEL_PENDING. An outstanding plan must receive an identity-bound ACK. A failed ACK can report a shorter confirmed contiguous prefix; all remaining planned work is **unverified**, not presumed unexecuted. If quiescence is absent, an explicit later quiescence observation is required before terminal disposition. No fabricated success sample or retry is permitted.
- Terminal disposition and resource release are distinct. A quiescent terminal request may retain an observed block table until explicit release evidence arrives. A closed journal requires empty ownership. The ledger does not free blocks itself.
- Malformed inputs/illegal transitions preserve the last accepted request snapshot and append a fault to the export. The entire ledger becomes poisoned, prohibiting further transitions. This realizes CONTRACT_FAILURE at the run boundary rather than overwriting a valid request state with fabricated progress. The referee rejects poisoned runs; tests can separately inspect their accepted prefix.
- Transport emission and client observation have independent append-only cursors. Previously emitted tokens may be observed after cancellation; no new emission is accepted after abort. A stream event with multiple token IDs remains one event.
- Allocation observations describe one explicitly non-sharing pool snapshot, with integer free/system/owned/other counts and unique observation identity. Count reconciliation is a schema invariant, not a memory model or native allocation-fidelity claim. Cross-request simultaneous ownership, reservations, prefix sharing, fragmentation and per-rank accounting remain unimplemented.
- The versioned journal is `lssp-p1-ledger/0.1.0`. It cannot relabel historical v1 or MGPU evidence. Its `provenance` is a caller declaration; the referee always reports physical status NOT_VERIFIED.

No GPU/Slurm/Wulver work, model execution, Actions, manuscript edits, merges or MGPU06 substitutions are authorized by this amendment. P2 still needs the prerequisite decisions and a separate scoped authorization described in README.md.
