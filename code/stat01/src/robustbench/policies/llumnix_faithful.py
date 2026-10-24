"""
llumnix_faithful: faithful independent reimplementation of Llumnix's core
cluster scheduling algorithm (initial dispatch, periodic migration-pair
selection, LCFS migration-candidate selection, destination admission
gating), inside this project's simulator, composing with the existing
`vllm_faithful` baseline for local per-instance scheduling.

Pinned reference: the OSDI 2024 artifact repository
`alibaba/llm-scheduling-artifact`, commit
`a90824307249573f9c7548645c22994c65f83a08` (pushed 2024-06-05, the same day
as the paper's arXiv v1 submission). See
docs/llumnix_faithful_scheduler_reference.md for the full source-provenance
record, exact algorithm summary, and explicit exclusions. **Do not confuse
this pin with `AlibabaPAI/llumnix` ("Llumnix v0") or `llumnix-project/llumnix`
("Llumnix v1") -- both are separate, continuously-evolving repositories
that post-date this artifact; see that doc's §3.**

This is NOT:
  - official Llumnix code (from-scratch Python reimplementation),
  - an exact Ray/vLLM runtime reproduction (hardware timing is still this
    simulator's ServiceModel's job),
  - a reproduction of every dispatch/migration strategy in the pinned
    source -- only the VERIFIED DEFAULTS (`dispatch_strategy='naive'`,
    `migrate_strategy='LCFS'`, `load_metric='consumed_speed'`,
    `enable_load_control_prefill=False`) are implemented; non-default
    alternatives (`'balanced'`/`'load'`/`'block'`/global `FFIT`/`FCFS`/
    `BE`/`SJF`/`LJF` dispatch, `'SJF'`/`'LJF'` migration, the
    load-control-prefill variant) are documented but not implemented (see
    the reference doc's §E).
It IS a faithful reimplementation of the pinned reference's default
cluster-scheduling *decisions*: which instance a new request goes to,
when migration is even considered, which (source, destination) instance
pairs are approved, which specific request migrates, and whether a
destination accepts it.

Scope boundary
--------------
- Cluster-level scheduling (dispatch + migration-pair selection +
  migration-candidate selection + destination admission): IMPLEMENTED
  here.
- Local per-instance scheduling: NOT duplicated -- composed directly with
  `VLLMFaithfulPolicy._run_gpu_schedule` (the same FCFS/paged-KV-block/
  preemption algorithm `vllm_faithful` already implements), called once
  per Llumnix instance with only that instance's own dispatch-assigned
  requests. See docs/llumnix_faithful_scheduler_reference.md §E for the
  one disclosed divergence this composition carries forward: the pinned
  Llumnix source's own local scheduler preempts via SWAP, while
  `vllm_faithful` (pinned to vLLM v0.1.0) models only RECOMPUTE
  preemption -- a difference already disclosed in `vllm_faithful`'s own
  reference doc, not newly introduced here.
- KV-state migration mechanism: uses the new shared `Action.migrate`
  primitive (see core/action.py), NOT the DistServe/TetriInfer bridge
  queue -- see the reference doc's §C for why the two must not be
  conflated.

No session/multi-turn concept in this simulator
------------------------------------------------
The pinned reference's default dispatch (`dispatch_naive`) is
session-sticky: a session's FIRST request round-robins across instances,
every SUBSEQUENT request in the same session reuses that instance. This
project's `Request`/`ObservableRequest` types have no session/conversation
concept at all (every request is independent) -- session-stickiness has
no analogue to preserve or violate here, so this degenerates to plain
per-request round-robin, a disclosed simplification following directly
from the request model, not an invented behavior.

Priority handling
------------------
The pinned reference's `priority_type` is a binary flag (0/1); this
project's `ObservableRequest.priority` is a continuous float ("higher =
more important"). No paper-sourced numeric mapping between the two exists,
so `priority_exempt_threshold` defaults to `None` (the priority-based
migration-source exemption is OFF by default) rather than inventing an
arbitrary cutoff; an experimenter may opt in with a threshold meaningful
for their own workload's priority distribution.

Deliberately NOT registered as a deployable baseline in this PR
-----------------------------------------------------------------
Same rationale as every other faithful baseline in this project: fully
implemented and unit-tested, but requires a genuine multi-instance
topology (N independent, role=None GPUs) that ordinary single-pool
experiment configs do not provide, and promoting any faithful baseline to
deployable/selector-candidate status is a deliberate, separate decision.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from ..core.action import Action
from ..core.types import ObservableGPUState, ObservableRequest, ObservableState
from .base import BasePolicy
from .vllm_faithful import (
    DEFAULT_BLOCK_SIZE,
    DEFAULT_MAX_NUM_BATCHED_TOKENS,
    DEFAULT_MAX_NUM_SEQS,
    DEFAULT_WATERMARK,
    VLLMFaithfulPolicy,
)

# Verified defaults (vllm/engine/arg_utils.py @ pinned commit a908243...):
# dispatch_strategy='naive', migrate_strategy='LCFS',
# load_metric='consumed_speed', enable_load_control_prefill=False,
# need_migrate_frequency=4, migrate_out_threshold=1.5 (raw CLI value;
# request_scheduler.py negates it internally -- reproduced here the same
# way, see __init__).
DEFAULT_NEED_MIGRATE_FREQUENCY = 4
DEFAULT_MIGRATE_OUT_THRESHOLD = 1.5


class LlumnixFaithfulPolicy(BasePolicy):
    """See module docstring and
    docs/llumnix_faithful_scheduler_reference.md for the full fidelity
    record. Stateful across steps -- call `reset()` before reusing an
    instance across multiple simulation runs.
    """

    name = "llumnix_faithful"

    def __init__(
        self,
        need_migrate_frequency: int = DEFAULT_NEED_MIGRATE_FREQUENCY,
        migrate_out_threshold: float = DEFAULT_MIGRATE_OUT_THRESHOLD,
        priority_exempt_threshold: Optional[float] = None,
        block_size: int = DEFAULT_BLOCK_SIZE,
        max_num_batched_tokens: int = DEFAULT_MAX_NUM_BATCHED_TOKENS,
        max_num_seqs: int = DEFAULT_MAX_NUM_SEQS,
        watermark: float = DEFAULT_WATERMARK,
    ) -> None:
        self.need_migrate_frequency = need_migrate_frequency
        # Matches the pinned source's own internal negation
        # (RequestSchedulerConfig.__init__: `migrate_out_load_threshold =
        # migrate_out_threshold * (-1)`) -- see instance_info.py's
        # 'consumed_speed' metric, which is itself negative (more negative
        # = more loaded).
        self.migrate_out_load_threshold = -migrate_out_threshold
        self.priority_exempt_threshold = priority_exempt_threshold
        self.block_size = block_size
        self.max_num_batched_tokens = max_num_batched_tokens
        self.max_num_seqs = max_num_seqs
        self.watermark = watermark

        self._local = VLLMFaithfulPolicy(
            block_size=block_size, max_num_batched_tokens=max_num_batched_tokens,
            max_num_seqs=max_num_seqs, watermark=watermark,
        )
        self._init_stateful()

    def _init_stateful(self) -> None:
        # Dispatch stickiness (degenerate session-stickiness -- see module
        # docstring): request_id -> assigned instance gpu_id, set once,
        # never reassigned (a preempted request naturally reappears in
        # state.waiting_queue and is re-assigned to the SAME instance).
        self._dispatch_assignment: Dict[int, int] = {}
        self._dispatch_ptr_index = 0
        # Per-instance "currently killed (preempted), not yet re-admitted"
        # request_id sets -- mirrors Scheduler.killed's live count
        # (num_killed_request = len(self.killed) in the pinned source).
        self._killed_ids: Dict[int, Set[int]] = {}
        # Mirrors LLMEngineManager.num_instance_info_update, incremented by
        # num_instance every call (this simulator has no separate
        # per-instance-step counter -- every select_action call implicitly
        # advances every instance by one step together).
        self._num_instance_info_update = 0
        # request_id -> exact KV-token footprint at the moment migration
        # was approved (see _run_migration_stage) -- used to gate and
        # perform the destination-side vllm_faithful block-manager
        # allocation once the request actually arrives (see
        # _admit_incoming_migrations), mirroring the pinned reference's
        # own allocate_migrate_seq_groups capacity check. Without this,
        # a migrated-in request would be admitted onto the destination GPU
        # (which only checks the simulator's own raw GPUConfig capacity)
        # without ever being registered in vllm_faithful's OWN block
        # manager, which can then crash trying to retroactively adopt it
        # if the destination has since filled up.
        self._migration_footprint: Dict[int, int] = {}

    def reset(self) -> None:
        self._local.reset()
        self._init_stateful()

    # ------------------------------------------------------------------
    # Main scheduling entry point
    # ------------------------------------------------------------------

    def select_action(self, state: ObservableState) -> Action:
        gpu_states = state.gpu_states
        if not gpu_states:
            raise ValueError(
                "llumnix_faithful requires at least one GPU instance "
                "(see docs/llumnix_faithful_scheduler_reference.md)."
            )
        gpu_by_id = {g.gpu_id: g for g in gpu_states}
        sorted_gpu_ids = sorted(gpu_by_id.keys())

        admit: Dict[int, List[int]] = {gid: [] for gid in sorted_gpu_ids}
        preempt: Dict[int, List[int]] = {gid: [] for gid in sorted_gpu_ids}
        migrate: Dict[int, List[Tuple[int, int]]] = {gid: [] for gid in sorted_gpu_ids}

        # --- 1. Dispatch: naive round-robin (session-sticky degenerates
        # to per-request-sticky -- see module docstring) ---
        by_instance: Dict[int, List[ObservableRequest]] = {gid: [] for gid in sorted_gpu_ids}
        for req in state.waiting_queue:
            gid = self._assign_instance(req.request_id, sorted_gpu_ids)
            by_instance[gid].append(req)

        # --- 2. Local per-instance scheduling (composed with
        # vllm_faithful's own per-GPU worker, not duplicated) ---
        killed_this_round: Dict[int, Set[int]] = {}
        for gid in sorted_gpu_ids:
            gpu = gpu_by_id[gid]
            admitted_ids, preempted_ids, _remaining = self._local._run_gpu_schedule(
                gpu, by_instance[gid],
            )
            admit[gid].extend(admitted_ids)
            preempt[gid] = preempted_ids
            killed_this_round[gid] = set(preempted_ids)

            # Transfer-ready incoming migrations: gated by a capacity
            # check against THIS destination's own vllm_faithful block
            # manager (mirroring the pinned reference's own
            # allocate_migrate_seq_groups) -- destination capacity may
            # have changed between the moment migration was approved
            # (_run_migration_stage's benefit projection) and the moment
            # transfer actually completes, so it must be re-checked here,
            # not assumed. A request that doesn't fit yet is simply left
            # in incoming_migrations for a later round (it remains
            # transfer-ready in the simulator's relocation table) --
            # matching the pinned reference's own per-candidate rejection
            # (not a crash, not a dropped request).
            bm = self._local._get_block_manager(gpu)
            for incoming in gpu.incoming_migrations:
                footprint = self._migration_footprint.get(incoming.request_id, incoming.prompt_tokens)
                if not bm.can_allocate(footprint):
                    continue
                bm.allocate(incoming.request_id, footprint)
                self._migration_footprint.pop(incoming.request_id, None)
                admit[gid].append(incoming.request_id)

        # --- 3. Update per-instance killed-request bookkeeping ---
        for gid in sorted_gpu_ids:
            gpu = gpu_by_id[gid]
            still_active = set(gpu.active_request_ids)
            prev = self._killed_ids.get(gid, set())
            self._killed_ids[gid] = (prev - still_active) | killed_this_round[gid]

        # --- 4. Periodic migration-pair selection + LCFS candidate
        # selection + destination admission gate ---
        self._run_migration_stage(gpu_by_id, sorted_gpu_ids, migrate, killed_this_round)

        return Action(admit=admit, preempt=preempt, migrate=migrate)

    # ------------------------------------------------------------------
    # Dispatch (initial placement)
    # ------------------------------------------------------------------

    def _assign_instance(self, request_id: int, sorted_gpu_ids: List[int]) -> int:
        assigned = self._dispatch_assignment.get(request_id)
        if assigned is not None:
            return assigned
        gid = sorted_gpu_ids[self._dispatch_ptr_index % len(sorted_gpu_ids)]
        self._dispatch_ptr_index += 1
        self._dispatch_assignment[request_id] = gid
        return gid

    # ------------------------------------------------------------------
    # Instance-load metric ('consumed_speed', enable_load_control_prefill=False)
    # ------------------------------------------------------------------

    def _instance_load(self, gpu: ObservableGPUState) -> float:
        bm = self._local._get_block_manager(gpu)
        num_request = len(gpu.active_request_ids)
        if num_request == 0:
            return float("-inf")
        num_available = bm.num_free_blocks - bm.watermark_blocks
        return -(num_available / num_request)

    def _load_after_migrate(
        self, gpu: ObservableGPUState, is_migrate_in: bool, candidate_blocks: int,
    ) -> float:
        bm = self._local._get_block_manager(gpu)
        num_request = len(gpu.active_request_ids) + (1 if is_migrate_in else -1)
        if num_request <= 0:
            return float("-inf")
        free_delta = -candidate_blocks if is_migrate_in else candidate_blocks
        num_available = (bm.num_free_blocks + free_delta) - bm.watermark_blocks
        return -(num_available / num_request)

    # ------------------------------------------------------------------
    # Migration-candidate selection ('LCFS', the verified default)
    # ------------------------------------------------------------------

    def _lcfs_candidate(
        self, gpu: ObservableGPUState, exclude_ids: Set[int],
    ) -> Optional[ObservableRequest]:
        """Scan from the back of `active_request_ids` (most-recently-
        admitted first, since Python dicts -- and this list built from one
        -- preserve insertion order): the first request found that has
        already decoded at least one token (only decoding-phase requests
        are migration candidates -- a request still mid-prefill never is)
        and is not priority-exempt. Exactly one candidate per call, per
        source instance, matching the pinned reference exactly.

        `exclude_ids` must contain this same round's local-scheduler
        preemption decisions for this GPU: `active_request_ids` is a
        snapshot from the START of this select_action call and does not
        yet reflect a preemption `_run_gpu_schedule` (step 2) already
        decided this round (the real eviction only happens once the
        Simulator applies Action.preempt, after select_action returns) --
        but `vllm_faithful`'s own KVBlockSpaceManager already freed that
        request's blocks. Without this exclusion, a just-preempted request
        could be picked as a migration candidate and crash looking up its
        (already-freed) block count."""
        info_by_id = {r.request_id: r for r in gpu.active_requests_info}
        for rid in reversed(gpu.active_request_ids):
            if rid in exclude_ids:
                continue
            if gpu.tokens_decoded_per_request.get(rid, 0) <= 0:
                continue
            req = info_by_id.get(rid)
            if req is None:
                continue
            if self.priority_exempt_threshold is not None and req.priority > self.priority_exempt_threshold:
                continue
            return req
        return None

    # ------------------------------------------------------------------
    # Migration trigger + pair selection ('need_migrate_balanced', the
    # verified default when enable_load_control_prefill=False)
    # ------------------------------------------------------------------

    def _run_migration_stage(
        self, gpu_by_id: Dict[int, ObservableGPUState], sorted_gpu_ids: List[int],
        migrate: Dict[int, List[Tuple[int, int]]], preempted_this_round: Dict[int, Set[int]],
    ) -> None:
        self._num_instance_info_update += len(sorted_gpu_ids)
        period = len(sorted_gpu_ids) * self.need_migrate_frequency
        if period <= 0 or self._num_instance_info_update % period != 0:
            return

        loads = {gid: self._instance_load(gpu_by_id[gid]) for gid in sorted_gpu_ids}
        killed_counts = {gid: len(self._killed_ids.get(gid, ())) for gid in sorted_gpu_ids}

        sorted_desc = sorted(sorted_gpu_ids, key=lambda gid: loads[gid], reverse=True)
        left_ids = [
            gid for gid in sorted_desc
            if killed_counts[gid] > 0 or loads[gid] > self.migrate_out_load_threshold
        ]
        right_ids = [
            gid for gid in reversed(sorted_desc)
            if killed_counts[gid] == 0 and loads[gid] < self.migrate_out_load_threshold
        ]

        for i in range(min(len(left_ids), len(right_ids))):
            src_id, dst_id = left_ids[i], right_ids[i]
            if src_id == dst_id:
                continue

            candidate = self._lcfs_candidate(gpu_by_id[src_id], preempted_this_round.get(src_id, set()))
            if candidate is None:
                continue

            bm_src = self._local._get_block_manager(gpu_by_id[src_id])
            candidate_blocks = bm_src.num_blocks_for(candidate.request_id)

            load_diff_before = loads[src_id] - loads[dst_id]
            left_after = self._load_after_migrate(gpu_by_id[src_id], is_migrate_in=False, candidate_blocks=candidate_blocks)
            right_after = self._load_after_migrate(gpu_by_id[dst_id], is_migrate_in=True, candidate_blocks=candidate_blocks)
            if right_after > self.migrate_out_load_threshold:
                continue
            load_diff_after = left_after - right_after
            if (load_diff_after > 0 and load_diff_before > load_diff_after) or loads[dst_id] == float("-inf"):
                migrate[src_id].append((candidate.request_id, dst_id))
                self._dispatch_assignment[candidate.request_id] = dst_id
                # Record the exact KV-token footprint now, while it is
                # still known via the source's own block manager -- once
                # evicted, this project's ObservableRequest exposes no way
                # to recover decoded-so-far progress (see
                # select_action's incoming-migration admission gate).
                self._migration_footprint[candidate.request_id] = bm_src.kv_tokens_for(candidate.request_id)
                # Free it from the source's own block manager immediately
                # (consistent with distserve_faithful's swap-eviction
                # convention -- explicit free at eviction-decision time,
                # not deferred to next round's reconciliation).
                bm_src.free(candidate.request_id)
