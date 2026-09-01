"""
distserve_faithful: faithful independent reimplementation of DistServe's
camera-ready core FCFS online scheduling behavior (context-stage +
decoding-stage schedulers + bridge-queue migration + decode-side swap),
inside this project's simulator, using the disaggregated prefill/decode
infrastructure (GPUConfig.role, RequestPhase.MIGRATING, the bridge queue,
Action.swap) added for this baseline.

Pinned reference: LLMServe/DistServe, branch camera-ready-simulator,
commit 0ec355c8743d3fbd2d02f3cd62b5be6eae368f92. See
docs/distserve_faithful_scheduler_reference.md for the full
source-provenance record, architecture audit, and explicit exclusions
(pipeline parallelism, SRPT/MLFQ/proactive-offloading decode-stage
ablations, bandwidth-aware transfer cost, multi-worker load-balancing --
the last of these because the CORE reference's own `LLMEngine` is a
single-context-worker/single-decode-worker system, not a worker pool).

This is NOT:
  - official DistServe code (from-scratch Python reimplementation),
  - an exact runtime/network reproduction,
  - a reproduction of DistServe's OFFLINE parallelism/placement planner
    (the paper's goodput-optimized config-search algorithm) -- this policy
    implements only the ONLINE request-scheduling behavior: context-stage
    admission, decode-stage admission/swap, and bridge-queue handoff.
It IS a faithful reimplementation of the pinned reference's online
scheduling *algorithm* and *memory semantics*.

Scope boundary (explicit, per the reference doc)
--------------------------------------------------
- Online request scheduling: IMPLEMENTED (this policy).
- Context/prefill worker routing, decode worker routing: N/A -- the
  pinned CORE reference is single-worker-per-stage; this policy requires
  and validates exactly one role="prefill" GPU and one role="decode" GPU.
  Multi-worker routing exists only in DistServe's secondary `simdistserve`
  exploratory tool, not the core FCFS baseline, so it is not implemented
  here (would be inventing unverified behavior).
- Bridge-queue handoff: IMPLEMENTED, reusing the existing infrastructure.
- Offline parallelism/resource planning (the paper's placement search):
  NOT implemented and not claimed.

Deliberately NOT registered as a deployable baseline in this PR (same
rationale as vllm_faithful/sarathi_faithful -- see docs/baselines.md).

Parameter defaults (disclosed; see docs/distserve_faithful_scheduler_reference.md)
------------------------------------------------------------------------------------
`waiting_block_prop_threshold=0.05` is a VERIFIED default, read directly
from DecodingStageSchedConfig.__init__. `block_size=16` is inherited from
vLLM's own block manager default (DistServe's own SarathiBlockSpaceManager-
style block manager is a no-op subclass of vLLM's, per the reference doc).
context_max_batch_size/context_max_tokens_per_batch/decode_max_batch_size/
decode_max_tokens_per_batch have NO verified default in the pinned source
(ContextStageSchedConfig/DecodingStageSchedConfig require them as explicit
constructor arguments) and no single representative evaluation-script
value was found in the time available for this audit -- the defaults
below are this project's OWN conservative choices, not sourced from a
paper evaluation run, and are exposed as explicit constructor parameters
precisely so they are never silently assumed.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from ..core.action import Action
from ..core.types import ObservableGPUState, ObservableRequest, ObservableState
from .base import BasePolicy
from .tie_breaking import arrival_then_id
from ..simulator.kv_block_manager import KVBlockSpaceManager

# Verified default (DecodingStageSchedConfig.__init__ @ pinned commit).
DEFAULT_WAITING_BLOCK_PROP_THRESHOLD = 0.05
# Inherited from vLLM's own block manager default (DistServe's is a no-op
# subclass of it -- see docs/distserve_faithful_scheduler_reference.md).
DEFAULT_BLOCK_SIZE = 16
# NOT sourced from a paper evaluation script -- conservative project
# defaults, exposed as explicit constructor parameters (see module docstring).
DEFAULT_CONTEXT_MAX_BATCH_SIZE = 32
DEFAULT_CONTEXT_MAX_TOKENS_PER_BATCH = 4096
DEFAULT_DECODE_MAX_BATCH_SIZE = 128
DEFAULT_DECODE_MAX_TOKENS_PER_BATCH = 4096


class DistServeFaithfulPolicy(BasePolicy):
    """Faithful reimplementation of DistServe's camera-ready core FCFS
    online scheduler (context-stage admission, decode-stage admission +
    swap, bridge-queue migration). See module docstring and
    docs/distserve_faithful_scheduler_reference.md for the full fidelity
    record.

    Requires exactly one GPUConfig(role="prefill") and one
    GPUConfig(role="decode") in every ObservableState it is given --
    raises ValueError otherwise (see module docstring's scope boundary on
    why multi-worker routing is not supported).

    Stateful across steps -- call `reset()` before reusing an instance
    across multiple simulation runs.
    """

    name = "distserve_faithful"

    def __init__(
        self,
        context_max_batch_size: int = DEFAULT_CONTEXT_MAX_BATCH_SIZE,
        context_max_tokens_per_batch: int = DEFAULT_CONTEXT_MAX_TOKENS_PER_BATCH,
        decode_max_batch_size: int = DEFAULT_DECODE_MAX_BATCH_SIZE,
        decode_max_tokens_per_batch: int = DEFAULT_DECODE_MAX_TOKENS_PER_BATCH,
        waiting_block_prop_threshold: float = DEFAULT_WAITING_BLOCK_PROP_THRESHOLD,
        block_size: int = DEFAULT_BLOCK_SIZE,
    ) -> None:
        self.context_max_batch_size = context_max_batch_size
        self.context_max_tokens_per_batch = context_max_tokens_per_batch
        self.decode_max_batch_size = decode_max_batch_size
        self.decode_max_tokens_per_batch = decode_max_tokens_per_batch
        self.waiting_block_prop_threshold = waiting_block_prop_threshold
        self.block_size = block_size

        self._context_bm: KVBlockSpaceManager | None = None
        self._decode_bm: KVBlockSpaceManager | None = None
        # request_ids this policy itself swapped out, in swap order --
        # re-admitted with strict priority over ordinary bridge-queue
        # (newly migrated) candidates, matching the pinned reference's
        # "swapped_queue considered first" behavior.
        self._swapped_out_ids: List[int] = []
        # num_tokens (prompt + tokens_decoded so far) at the moment of
        # swap-out, keyed by request_id -- ObservableRequest.prompt_tokens
        # alone would understate a swapped request's true KV footprint once
        # it has decoded output tokens (swap preserves that decode
        # progress; see GPUState.evict(preserve_progress=True)), so this
        # must be tracked here rather than re-derived from ObservableState.
        self._swapped_out_num_tokens: Dict[int, int] = {}

    def reset(self) -> None:
        self._context_bm = None
        self._decode_bm = None
        self._swapped_out_ids = []
        self._swapped_out_num_tokens = {}

    # ------------------------------------------------------------------
    # Setup / validation
    # ------------------------------------------------------------------

    def _resolve_stage_gpus(
        self, state: ObservableState,
    ) -> Tuple[ObservableGPUState, ObservableGPUState]:
        context_gpus = [g for g in state.gpu_states if g.role == "prefill"]
        decode_gpus = [g for g in state.gpu_states if g.role == "decode"]
        if len(context_gpus) != 1 or len(decode_gpus) != 1:
            raise ValueError(
                "distserve_faithful requires exactly one GPUConfig(role='prefill') "
                "and one GPUConfig(role='decode') -- the pinned reference's core "
                "LLMEngine is a single-context-worker/single-decode-worker system, "
                "not a multi-worker pool (see "
                "docs/distserve_faithful_scheduler_reference.md); got "
                f"{len(context_gpus)} prefill-role and {len(decode_gpus)} decode-role GPUs."
            )
        return context_gpus[0], decode_gpus[0]

    def _get_context_bm(self, gpu: ObservableGPUState) -> KVBlockSpaceManager:
        if self._context_bm is None:
            self._context_bm = KVBlockSpaceManager(
                block_size=self.block_size,
                num_gpu_blocks=gpu.max_kv_tokens // self.block_size,
                watermark=0.0,  # DistServe's own capacity checks have no reserve fraction
            )
        return self._context_bm

    def _get_decode_bm(self, gpu: ObservableGPUState) -> KVBlockSpaceManager:
        if self._decode_bm is None:
            self._decode_bm = KVBlockSpaceManager(
                block_size=self.block_size,
                num_gpu_blocks=gpu.max_kv_tokens // self.block_size,
                watermark=0.0,
            )
        return self._decode_bm

    def _reconcile_decode_completions(
        self, bm: KVBlockSpaceManager, gpu: ObservableGPUState,
    ) -> None:
        """Free decode-side blocks for any request no longer active on the
        decode GPU (it completed). Requests this policy itself swapped out
        are NOT active on the GPU either, but their blocks were already
        freed at swap time (see _run_decode_stage) -- this only ever fires
        for genuine completions."""
        active_ids = set(gpu.active_request_ids)
        for rid in bm.allocated_request_ids():
            if rid not in active_ids:
                bm.free(rid)

    # ------------------------------------------------------------------
    # Main scheduling entry point
    # ------------------------------------------------------------------

    def select_action(self, state: ObservableState) -> Action:
        context_gpu, decode_gpu = self._resolve_stage_gpus(state)

        admitted_context = self._run_context_stage(state.waiting_queue, context_gpu)
        admitted_decode, swapped_decode = self._run_decode_stage(state.migrating_queue, decode_gpu)

        admit = {g.gpu_id: [] for g in state.gpu_states}
        swap = {g.gpu_id: [] for g in state.gpu_states}
        admit[context_gpu.gpu_id] = admitted_context
        admit[decode_gpu.gpu_id] = admitted_decode
        swap[decode_gpu.gpu_id] = swapped_decode
        return Action(admit=admit, swap=swap)

    # ------------------------------------------------------------------
    # Context (prefill) stage: ContextStageFCFSScheduler.get_next_batch_and_pop
    # ------------------------------------------------------------------

    def _run_context_stage(
        self, waiting: List[ObservableRequest], gpu: ObservableGPUState,
    ) -> List[int]:
        """FCFS admission into the context stage. Mirrors the pinned
        source's `get_next_batch_and_pop`: stop admitting entirely (not
        skip-and-continue) once the front-of-queue request cannot be
        allocated, exceeds the batch-size limit, or exceeds the
        per-iteration token budget. Blocks allocated here are held until
        this policy itself migrates the request onto the decode GPU (see
        _run_decode_stage) -- never auto-freed just because the request
        left `_active` (it may be sitting, still context-reserved, in the
        bridge queue), matching the pinned reference's
        num_on_fly_request_block/unaccepted_queue block accounting."""
        bm = self._get_context_bm(gpu)
        admitted: List[int] = []
        batch_tokens = 0

        for req in waiting:
            if len(admitted) >= self.context_max_batch_size:
                break
            if batch_tokens + req.prompt_tokens > self.context_max_tokens_per_batch:
                break
            if not bm.can_allocate(req.prompt_tokens):
                break
            # Final safety net: never attempt an admission the simulator's
            # own GPUConfig constraints would reject (see vllm_faithful's
            # identical safety net for the rationale). This does not change
            # the scheduling algorithm; a request skipped here simply
            # waits for a later step, exactly as it would in an unusually
            # tight simulator-native config.
            if not self._feasible_on_gpu(gpu, req):
                continue

            bm.allocate(req.request_id, req.prompt_tokens)
            admitted.append(req.request_id)
            batch_tokens += req.prompt_tokens
            gpu.active_request_ids.append(req.request_id)
            gpu.current_kv_tokens += req.prompt_tokens

        return admitted

    # ------------------------------------------------------------------
    # Decode stage: DecodingStageFCFSScheduler.get_next_batch + post_process
    # ------------------------------------------------------------------

    def _run_decode_stage(
        self, migrating_queue: List[ObservableRequest], gpu: ObservableGPUState,
    ) -> Tuple[List[int], List[int]]:
        bm = self._get_decode_bm(gpu)
        self._reconcile_decode_completions(bm, gpu)

        # --- Swap-out capacity check (DecodingStageFCFSScheduler.get_next_batch's
        # "while blocks insufficient: swap out" loop). Adapted to this
        # simulator's uniform 1-token/step decode growth: identical
        # LIFO/lowest-priority-first victim selection as vllm_faithful's
        # running-queue loop, but SWAPS (preserves progress) instead of
        # preempting (discards it) -- see docs/distserve_faithful_scheduler_reference.md.
        decoding = sorted(
            (req for req in gpu.active_requests_info if bm.is_allocated(req.request_id)),
            key=arrival_then_id,
        )
        pending = list(decoding)
        kept_ids: List[int] = []
        swapped_ids: List[int] = []

        while pending:
            candidate = pending.pop(0)
            while not bm.can_append_slot(candidate.request_id):
                if pending:
                    victim = pending.pop(-1)
                    self._swapped_out_num_tokens[victim.request_id] = bm.kv_tokens_for(victim.request_id)
                    bm.free(victim.request_id)
                    swapped_ids.append(victim.request_id)
                    self._swapped_out_ids.append(victim.request_id)
                else:
                    self._swapped_out_num_tokens[candidate.request_id] = bm.kv_tokens_for(candidate.request_id)
                    bm.free(candidate.request_id)
                    swapped_ids.append(candidate.request_id)
                    self._swapped_out_ids.append(candidate.request_id)
                    break
            else:
                bm.append_slot(candidate.request_id)
                kept_ids.append(candidate.request_id)

        # --- Admission: swapped-out requests re-admitted FIRST (strict
        # priority over the bridge queue, matching the pinned reference's
        # "consider requests in the swapped queue first"), then bridge-
        # queue (newly migrated) candidates, FCFS. All admissions here
        # reserve blocks for `num_tokens + 1`, not just `num_tokens`: a
        # request admitted this step is already `is_decoding` (see
        # GPUState.admit/request.py's is_decoding) and will advance by one
        # decode token in this SAME simulator step (admission happens
        # before Simulator._advance_decode), exactly the same same-step
        # growth this simulator's synchronous per-step model requires
        # vllm_faithful to compensate for -- see that policy's module
        # docstring for the identical rationale.
        admitted: List[int] = []
        num_curr_seqs = len(kept_ids)
        batch_tokens = len(kept_ids)  # 1 decode token each, mirrors vllm_faithful's convention

        migrating_ids = {r.request_id for r in migrating_queue}
        swap_candidates = [rid for rid in self._swapped_out_ids if rid in migrating_ids]
        # Requests genuinely newly migrated this round (not a swap re-entry).
        new_migration_candidates = [r for r in migrating_queue if r.request_id not in set(self._swapped_out_ids)]

        def _try_admit(num_tokens: int) -> bool:
            nonlocal num_curr_seqs, batch_tokens
            if num_curr_seqs >= self.decode_max_batch_size:
                return False
            if batch_tokens + num_tokens > self.decode_max_tokens_per_batch:
                return False
            if not bm.can_allocate(num_tokens):
                return False
            return True

        # Swapped-back-in candidates: priority, no waiting_block_prop_threshold
        # gate (that gate is specific to accepting NEW migrations, per the
        # pinned reference -- swapped requests never left this GPU's logical
        # ownership, they just released memory temporarily). Uses the exact
        # num_tokens recorded at swap-out time (prompt + decode progress so
        # far), not ObservableRequest.prompt_tokens, which would understate
        # a request that had already decoded output tokens before swap.
        for rid in list(swap_candidates):
            num_tokens = self._swapped_out_num_tokens[rid] + 1
            if not _try_admit(num_tokens):
                break
            bm.allocate(rid, num_tokens)
            admitted.append(rid)
            num_curr_seqs += 1
            batch_tokens += num_tokens
            self._swapped_out_ids.remove(rid)
            del self._swapped_out_num_tokens[rid]
            gpu.active_request_ids.append(rid)
            gpu.current_kv_tokens += num_tokens

        # New migrations: gated by waiting_block_prop_threshold, mirroring
        # the pinned reference's post_process/should_accept EXACTLY --
        # accepted one at a time, FCFS, stopping the instant the running
        # total of blocks accepted so far THIS round would reach the
        # threshold (a backpressure throttle on how much backlog decode
        # pulls from the bridge queue per round, not a one-shot static
        # check against the whole backlog -- that reading starves
        # permanently once the backlog exceeds a few requests, since
        # `waiting_block_prop_threshold` defaults to a small fraction like
        # 0.05). accepted_blocks always starts at 0 each call: this
        # simulator has no separate persistent "accepted but not yet
        # batched" queue distinct from the bridge queue itself.
        total_decode_blocks = gpu.max_kv_tokens // self.block_size
        accepted_blocks = 0
        for req in new_migration_candidates:
            req_blocks = KVBlockSpaceManager.blocks_needed(req.prompt_tokens, self.block_size)
            if accepted_blocks >= self.waiting_block_prop_threshold * total_decode_blocks:
                break
            if req_blocks > bm.num_free_blocks:
                break
            num_tokens = req.prompt_tokens + 1
            if not _try_admit(num_tokens):
                break
            bm.allocate(req.request_id, num_tokens)
            admitted.append(req.request_id)
            num_curr_seqs += 1
            batch_tokens += num_tokens
            accepted_blocks += req_blocks
            gpu.active_request_ids.append(req.request_id)
            gpu.current_kv_tokens += num_tokens

        return admitted, swapped_ids
