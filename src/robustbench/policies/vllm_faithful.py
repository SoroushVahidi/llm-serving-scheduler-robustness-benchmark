"""
vllm_faithful: faithful independent reimplementation of vLLM's original
(pre-chunked-prefill) FCFS scheduler and paged-KV block management, inside
this project's simulator.

Pinned reference: vLLM commit 67d96c29fba9b72cb4c4edbc26211c208a00ebdd
(tag v0.1.0). See docs/vllm_faithful_scheduler_reference.md for the full
source-provenance record, algorithm summary, and explicit exclusions
(chunked prefill, copy-on-write/beam-search forking, swap-based preemption).

This is NOT:
  - official vLLM code (it is a from-scratch Python reimplementation),
  - an exact runtime reproduction (hardware timing is still this
    simulator's ServiceModel's job, unchanged by this policy),
  - a full vLLM performance model (only scheduling/memory *decisions* are
    modeled: what gets admitted, preempted, and when).
It IS a faithful reimplementation of the pinned reference's scheduling
*algorithm* and *KV-block memory semantics*.

Relationship to other vLLM-labeled things in this repo (see docs/baselines.md):
  - `vllm_style_token_budget` (src/robustbench/policies/vllm_style_token_budget.py)
    is a lightweight proxy/inspired baseline -- a token-budget heuristic, not
    a scheduler reimplementation. Unchanged by this work.
  - The external real-vLLM HTTP harness (scripts/run_vllm_external_baseline_comparison.py)
    benchmarks THIS project's own admission-control policies as a client-side
    layer in front of a REAL running vLLM server, treating vLLM's internal
    scheduler as a black box. It measures a real system; `vllm_faithful`
    measures a reimplementation. Neither substitutes for the other.

Deliberately NOT registered as a deployable baseline in this PR
-----------------------------------------------------------------
`vllm_faithful` is directly importable/instantiable/testable, but is
intentionally NOT added to registry.py's BASELINE_NAMES/SELECTOR_CANDIDATE_NAMES.
Doing so would silently change the deployable-policy count (currently 20,
see docs/research_status.md) and the selector's candidate pool -- a decision
with real downstream effects (selector retraining, evaluation-sweep counts,
every doc that states "20 deployable policies") that is out of scope for
introducing this baseline. Promoting it to a selectable baseline is a
deliberate follow-up decision for a future PR, not an oversight here.

Simulator-timing adaptation (disclosed)
----------------------------------------
The pinned reference reserves KV blocks for a sequence's PROMPT tokens on
admission, then grows by one token per subsequent iteration it remains
"running" (`append_slot`). This simulator's Phase 1 step model has no
separate prefill iteration: every active request -- including one admitted
this very step -- advances by exactly one decode token in the SAME step
(see simulator/gpu.py's `_step_phase1`). To keep this policy's internal
block accounting synchronized with the simulator's actual per-step token
growth (rather than silently drifting), blocks are reserved for
`prompt_tokens + 1` at admission, and grown by exactly one token every
subsequent step for each still-active tracked request -- matching the
simulator's real `tokens_decoded` growth rate of 1/step precisely.
"""
from __future__ import annotations

from typing import Dict, List

from ..core.action import Action
from ..core.types import ObservableGPUState, ObservableState
from .base import BasePolicy
from .tie_breaking import arrival_then_id
from ..simulator.kv_block_manager import KVBlockSpaceManager

# Defaults exactly matching the pinned reference
# (vllm/engine/arg_utils.py @ 67d96c29): block_size=16,
# max_num_batched_tokens=2560, max_num_seqs=256, watermark=0.01.
DEFAULT_BLOCK_SIZE = 16
DEFAULT_MAX_NUM_BATCHED_TOKENS = 2560
DEFAULT_MAX_NUM_SEQS = 256
DEFAULT_WATERMARK = 0.01


class VLLMFaithfulPolicy(BasePolicy):
    """Faithful reimplementation of vLLM v0.1.0's FCFS scheduler + paged KV
    block manager. See module docstring and
    docs/vllm_faithful_scheduler_reference.md for the full fidelity record.

    Stateful across steps (block tables and per-GPU KV block managers
    persist for the lifetime of a simulation run) -- call `reset()` before
    reusing an instance across multiple simulation runs.
    """

    name = "vllm_faithful"

    def __init__(
        self,
        block_size: int = DEFAULT_BLOCK_SIZE,
        max_num_batched_tokens: int = DEFAULT_MAX_NUM_BATCHED_TOKENS,
        max_num_seqs: int = DEFAULT_MAX_NUM_SEQS,
        watermark: float = DEFAULT_WATERMARK,
    ) -> None:
        self.block_size = block_size
        self.max_num_batched_tokens = max_num_batched_tokens
        self.max_num_seqs = max_num_seqs
        self.watermark = watermark
        self._block_managers: Dict[int, KVBlockSpaceManager] = {}

    def reset(self) -> None:
        self._block_managers = {}

    # ------------------------------------------------------------------
    # Per-GPU block manager lifecycle
    # ------------------------------------------------------------------

    def _get_block_manager(self, gpu: ObservableGPUState) -> KVBlockSpaceManager:
        bm = self._block_managers.get(gpu.gpu_id)
        if bm is None:
            num_gpu_blocks = gpu.max_kv_tokens // self.block_size
            bm = KVBlockSpaceManager(
                block_size=self.block_size,
                num_gpu_blocks=num_gpu_blocks,
                watermark=self.watermark,
            )
            self._block_managers[gpu.gpu_id] = bm
        return bm

    def _reconcile_completions(self, bm: KVBlockSpaceManager, gpu: ObservableGPUState) -> None:
        """Free blocks for any request this manager still tracks but that
        is no longer active on this GPU (it completed since our last call).
        A request we ourselves preempted this same call is already freed
        eagerly in _run_gpu_schedule, so this only ever fires for genuine
        completions."""
        active_ids = set(gpu.active_request_ids)
        for rid in bm.allocated_request_ids():
            if rid not in active_ids:
                bm.free(rid)

    def _adopt_untracked_active(self, bm: KVBlockSpaceManager, gpu: ObservableGPUState) -> None:
        """Defensive: allocate for any request active on this GPU that this
        manager has never seen (e.g. this policy instance's very first call
        on a run whose state already had active requests). Never expected
        in normal use, since this policy is the only one deciding
        admissions once selected."""
        for req in gpu.active_requests_info:
            if not bm.is_allocated(req.request_id):
                decoded = gpu.tokens_decoded_per_request.get(req.request_id, 0)
                bm.allocate(req.request_id, req.prompt_tokens + decoded)

    # ------------------------------------------------------------------
    # Main scheduling entry point
    # ------------------------------------------------------------------

    def select_action(self, state: ObservableState) -> Action:
        admit: Dict[int, List[int]] = {g.gpu_id: [] for g in state.gpu_states}
        preempt: Dict[int, List[int]] = {g.gpu_id: [] for g in state.gpu_states}

        # Multiple GPUs are modeled as independent vLLM-style engines, each
        # with its own block manager, considering the same global waiting
        # queue in a fixed (ascending gpu_id) order -- the pinned reference
        # itself models exactly one engine/one waiting queue, so this
        # ordering is this policy's own multi-GPU extension, not part of
        # the pin. See docs/vllm_faithful_scheduler_reference.md.
        remaining_waiting = list(state.waiting_queue)  # already FCFS-with-preemption ordered

        for gpu in sorted(state.gpu_states, key=lambda g: g.gpu_id):
            admitted_here, preempted_here, remaining_waiting = self._run_gpu_schedule(
                gpu, remaining_waiting,
            )
            admit[gpu.gpu_id] = admitted_here
            preempt[gpu.gpu_id] = preempted_here

        return Action(admit=admit, preempt=preempt)

    def _run_gpu_schedule(self, gpu: ObservableGPUState, waiting: List) -> tuple:
        """Runs the pinned reference's `_schedule()` for one GPU/engine.
        Returns (admitted_request_ids, preempted_request_ids, remaining_waiting)."""
        bm = self._get_block_manager(gpu)
        self._reconcile_completions(bm, gpu)
        self._adopt_untracked_active(bm, gpu)

        # --- Step 1: reserve a decode-token slot for every already-running
        # sequence, preempting lowest-priority ones if short on blocks.
        # Mirrors Scheduler._schedule's running-queue loop exactly: process
        # from highest priority (front); if the current candidate can't get
        # a slot, evict from the back of what's LEFT (lowest priority among
        # the remainder); if nothing is left to evict, the candidate itself
        # is preempted.
        running_sorted = sorted(
            (req for req in gpu.active_requests_info if bm.is_allocated(req.request_id)),
            key=arrival_then_id,
        )
        pending = list(running_sorted)
        kept_ids: List[int] = []
        preempted_ids: List[int] = []

        while pending:
            candidate = pending.pop(0)
            while not bm.can_append_slot(candidate.request_id):
                if pending:
                    victim = pending.pop(-1)
                    bm.free(victim.request_id)
                    preempted_ids.append(victim.request_id)
                else:
                    bm.free(candidate.request_id)
                    preempted_ids.append(candidate.request_id)
                    break
            else:
                bm.append_slot(candidate.request_id)
                kept_ids.append(candidate.request_id)

        # --- Step 2 (swap-in): not modeled -- this policy never uses swap
        # preemption (every request is single-sequence, so the pinned
        # reference's own mode-selection always picks recompute; see the
        # reference doc's Exclusions). The `swapped` queue is always empty.

        # --- Step 3: admit from `waiting`, FCFS, honoring the block-
        # capacity watermark, the prompt-token budget for this iteration,
        # and the max-concurrent-sequences cap.
        admitted_ids: List[int] = []
        num_batched_tokens = len(kept_ids)  # 1 token per already-running sequence
        num_curr_seqs = len(kept_ids)
        max_num_seqs_effective = min(self.max_num_seqs, gpu.max_active_sequences)

        still_waiting: List = []
        admission_closed = False
        for req in waiting:
            if admission_closed:
                still_waiting.append(req)
                continue
            if req.request_id in preempted_ids:
                # Mirrors "if seq_group in preempted: break" -- but since a
                # request just preempted THIS call is not yet reflected in
                # `state.waiting_queue` (it only reappears there next step,
                # once the simulator applies the Action), this branch is a
                # defensive no-op today; kept for exact structural fidelity.
                still_waiting.append(req)
                continue
            if not bm.can_allocate(req.prompt_tokens + 1):
                admission_closed = True
                still_waiting.append(req)
                continue
            if num_batched_tokens + req.prompt_tokens > self.max_num_batched_tokens:
                admission_closed = True
                still_waiting.append(req)
                continue
            if num_curr_seqs + 1 > max_num_seqs_effective:
                admission_closed = True
                still_waiting.append(req)
                continue
            # Final safety net: never attempt an admission the simulator's
            # OWN GPUConfig constraints (max_active_sequences/max_batch_tokens/
            # max_kv_tokens) would reject -- covers experiment configs whose
            # simulator-native caps are tighter than this policy's own
            # vLLM-style budget. Does not change the scheduling algorithm
            # being tested; it only guards against spurious rejection
            # warnings in unusual configs.
            if not self._feasible_on_gpu(gpu, req):
                still_waiting.append(req)
                continue

            bm.allocate(req.request_id, req.prompt_tokens + 1)
            admitted_ids.append(req.request_id)
            num_batched_tokens += req.prompt_tokens
            num_curr_seqs += 1
            # Keep the local GPU view consistent for _feasible_on_gpu checks
            # against subsequently-considered waiting requests this step.
            gpu.active_request_ids.append(req.request_id)
            gpu.current_kv_tokens += req.prompt_tokens

        return admitted_ids, preempted_ids, still_waiting
