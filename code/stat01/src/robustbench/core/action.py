"""
Action schema returned by scheduling policies.

An Action maps each GPU ID to the list of request IDs to admit from the
waiting queue into that GPU's active batch during the current step.
An empty mapping (or all-empty lists) is a valid "do nothing" action.

`preempt` (added for the vllm_faithful baseline; see
docs/vllm_faithful_scheduler_reference.md) is an optional, backward-compatible
extension: it maps each GPU ID to the list of currently-ACTIVE request IDs
that policy wants evicted back to the waiting queue this step, with their
progress discarded (recompute-on-resume semantics -- see
Simulator._apply_action / GPUState.evict). It defaults to empty and every
existing policy leaves it empty, so admit-only behavior is completely
unchanged.

`swap` (added for the distserve_faithful baseline; see
docs/distserve_faithful_scheduler_reference.md) is a second, narrowly-scoped
eviction verb: it maps each GPU ID to the list of currently-ACTIVE (decoding)
request IDs to evict this step WITHOUT discarding progress, re-queuing them
as immediately transfer-ready in the bridge queue rather than the ordinary
waiting queue (see Simulator._apply_action / GPUState.evict(preserve_progress=True)).
DistServe's decode-stage scheduler manages capacity via swap, not recompute,
since by the time a request reaches the decode stage its (potentially
cross-machine) prefill work is a sunk cost not worth re-paying. Defaults to
empty; every pre-existing policy (including vllm_faithful/sarathi_faithful)
leaves it empty, so behavior is completely unchanged for them.

`migrate` (added for the llumnix_faithful baseline; see
docs/llumnix_faithful_scheduler_reference.md) is a fourth, narrowly-scoped
verb: it maps each SOURCE GPU ID to a list of (request_id, destination_gpu_id)
pairs -- live relocation of an already-ACTIVE request from one independent
GPU/instance to a specific OTHER one, preserving progress (see
GPUState.evict(preserve_progress=True)), for load-balancing/fragmentation/
priority reasons. Deliberately distinct from `swap`: a swapped request has
no fixed destination (any decode-role GPU may later re-admit it via the
ordinary bridge queue); a migrated request has a policy-chosen destination
fixed at the moment of migration, tracked by the simulator
(InternalRequest.migration_destination_gpu_id) and exposed per-destination
via ObservableGPUState.incoming_migrations, and admission onto any OTHER
GPU is rejected. Defaults to empty; every pre-existing policy (including
vllm_faithful/sarathi_faithful/distserve_faithful/
tetriinfer_paper_reimplementation) leaves it empty, so behavior is
completely unchanged for them.

`prefill_chunk_override` (added for the Family B v2 PrefillControl composition
child, ``PrefillControlChildPolicy``; see
docs/design/prefill_control_composition_falsification.md and
``robustbench.composition.prefill_control_policy``) is a sixth, narrowly-scoped
verb: it maps each GPU ID to the ``max_prefill_chunk_tokens`` value to use for
THAT GPU on THIS STEP ONLY, overriding ``ServiceModel.max_prefill_chunk_tokens``
(itself frozen/fixed for the whole run) without mutating it. This is what lets
a policy make a genuinely per-step, online-observable-driven prefill-chunk
decision -- the mechanism every fixed-chunk PrefillControl variant
(``full_prefill``, ``chunked_prefill_small``, ``chunk_96``/``128``/``192``) is
a single-decision special case of. Defaults to empty; every pre-existing
policy leaves it empty, so behavior is completely unchanged for them (see
``GPUState._advance_decode_protected`` / ``_advance_shared_contention``,
which fall back to ``service_model.max_prefill_chunk_tokens`` whenever no
override is present for that GPU this step).

`hold_decode` (added for the slai_faithful baseline; see
docs/slai_faithful_scheduler_reference.md) is a fifth, narrowly-scoped verb:
it maps each GPU ID to a list of currently-ACTIVE, currently-DECODING
request IDs whose decode-iteration should be SKIPPED this step only. Unlike
`preempt`/`swap`/`migrate`, a held request is not evicted at all: it stays
active on the same GPU, keeps its KV/slot reservation, keeps its queue
position, and its `tokens_decoded`/`first_token_time` are left completely
untouched for this step -- it simply produces no output token this
iteration, and the token-budget slot it would have consumed becomes
available for prefill instead (see GPUState._advance_decode_protected /
_advance_shared_contention). This is the "decode deferral" primitive the
pinned SLAI reference's last-schedulable-time mechanism requires: SLAI
decides, per decode-phase request, whether it is "critical" (must run now)
or "non-critical" (safe to defer to a later batch) based on that request's
own TBT deadline -- something neither of the simulator's two existing
GLOBAL execution models (decode-protected / shared-contention, see
ServiceModel.enable_decode_prefill_contention) can express, since both
apply one uniform rule to the whole decoding population rather than a
per-request policy decision. Defaults to empty; every pre-existing policy
leaves it empty, so behavior is completely unchanged for them. A request
named here that is not currently active+decoding on that GPU by the time
`Simulator._advance_decode` runs (e.g. because it was also preempted/
swapped/migrated by the same Action, or already completed) is silently
ignored -- there is nothing to hold.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple


@dataclass
class Action:
    admit: Dict[int, List[int]] = field(default_factory=dict)
    preempt: Dict[int, List[int]] = field(default_factory=dict)
    swap: Dict[int, List[int]] = field(default_factory=dict)
    migrate: Dict[int, List[Tuple[int, int]]] = field(default_factory=dict)
    hold_decode: Dict[int, List[int]] = field(default_factory=dict)
    prefill_chunk_override: Dict[int, int] = field(default_factory=dict)

    def all_admitted_ids(self) -> Set[int]:
        ids: Set[int] = set()
        for req_list in self.admit.values():
            ids.update(req_list)
        return ids

    def all_preempted_ids(self) -> Set[int]:
        ids: Set[int] = set()
        for req_list in self.preempt.values():
            ids.update(req_list)
        return ids

    def all_swapped_ids(self) -> Set[int]:
        ids: Set[int] = set()
        for req_list in self.swap.values():
            ids.update(req_list)
        return ids

    def all_migrated_ids(self) -> Set[int]:
        ids: Set[int] = set()
        for pairs in self.migrate.values():
            ids.update(rid for rid, _dest_gpu_id in pairs)
        return ids

    def all_held_decode_ids(self) -> Set[int]:
        ids: Set[int] = set()
        for req_list in self.hold_decode.values():
            ids.update(req_list)
        return ids

    def is_empty(self) -> bool:
        return (
            all(len(v) == 0 for v in self.admit.values())
            and all(len(v) == 0 for v in self.preempt.values())
            and all(len(v) == 0 for v in self.swap.values())
            and all(len(v) == 0 for v in self.migrate.values())
            and all(len(v) == 0 for v in self.hold_decode.values())
            and len(self.prefill_chunk_override) == 0
        )

    def __repr__(self) -> str:
        total = sum(len(v) for v in self.admit.values())
        total_preempted = sum(len(v) for v in self.preempt.values())
        total_swapped = sum(len(v) for v in self.swap.values())
        total_migrated = sum(len(v) for v in self.migrate.values())
        total_held = sum(len(v) for v in self.hold_decode.values())
        extra = ""
        if total_preempted:
            extra += f", total_preempted={total_preempted}, preempt={self.preempt}"
        if total_swapped:
            extra += f", total_swapped={total_swapped}, swap={self.swap}"
        if total_migrated:
            extra += f", total_migrated={total_migrated}, migrate={self.migrate}"
        if total_held:
            extra += f", total_held={total_held}, hold_decode={self.hold_decode}"
        if extra:
            return f"Action(total_admitted={total}, by_gpu={self.admit}{extra})"
        return f"Action(total_admitted={total}, by_gpu={self.admit})"
