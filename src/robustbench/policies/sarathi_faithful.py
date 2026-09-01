"""
sarathi_faithful: faithful independent reimplementation of Sarathi-Serve's
stall-free chunked-prefill scheduler, inside this project's simulator.

Pinned reference: microsoft/sarathi-serve, branch osdi-sarathi-serve,
commit ceaa0660ea2487976101a8167aad5c8046e85b27. See
docs/sarathi_faithful_scheduler_reference.md for the full source-provenance
record, algorithm summary, and explicit exclusions (dynamic chunking
schedule, pipeline-parallel throttling, prompt-length rejection).

This is NOT:
  - official Sarathi-Serve code (it is a from-scratch Python reimplementation),
  - an exact runtime reproduction (hardware timing is still this
    simulator's ServiceModel's job, unchanged by this policy),
  - a full Sarathi-Serve performance model (only scheduling/memory
    *decisions* are modeled: what gets admitted, chunked, preempted, and when).
It IS a faithful reimplementation of the pinned reference's scheduling
*algorithm* (chunked-prefill admission, decode-first budget reservation,
KV-block memory semantics -- identical to vLLM's, per the reference doc).

Relationship to other Sarathi-labeled things in this repo (see docs/baselines.md):
  - `sarathi_style` (src/robustbench/policies/sarathi_style.py) is a
    lightweight proxy/inspired baseline -- an admission-rate heuristic that
    does not model a separate prefill phase at all. Unchanged by this work.

REQUIRES `enable_prefill_modeling=True` on the simulator's ServiceModel
------------------------------------------------------------------------
This policy's admission decisions assume the simulator is configured with
a genuine prefill/decode split (`ServiceModel(enable_prefill_modeling=True,
decode_first=True, ...)`). Under the Phase 1 default
(`enable_prefill_modeling=False`), the simulator's own GPUState collapses
prefill to zero cost and admission-time chunking has no observable effect
on execution -- the policy will still run and make well-formed admission
decisions, but the chunked-prefill/stall-free *behavior* this baseline
exists to model will not be visible. See
docs/sarathi_faithful_scheduler_reference.md's infrastructure audit.

Deliberately NOT registered as a deployable baseline in this PR (same
rationale as `vllm_faithful` -- see its module docstring and
docs/baselines.md): avoids silently changing the 20-deployable-policy count
and selector candidate pool.

Simulator-timing adaptation (disclosed)
----------------------------------------
The pinned reference's own scheduler chunk-accounting IS the execution
instruction (there is no separate "scheduler decides, executor does
something else" split in real Sarathi-Serve). This simulator's GPUState
independently re-derives actual per-step prefill/decode progress from
ServiceModel's own parameters (`step_token_budget`, `max_prefill_chunk_tokens`,
`decode_first`), not from anything this policy computes. To make
correct ADMISSION decisions (how much of a new request's prompt budget
is left this iteration), this policy maintains its own shadow count of
each tracked request's remaining prefill tokens, assuming
`prefill_cost_per_token=1.0` (ServiceModel's own default: 1 budget-token
consumed per prompt token). If a run overrides that default, this
policy's admission-time budget accounting will drift from the simulator's
true prefill progress; documented here rather than silently wrong.
"""
from __future__ import annotations

from typing import Dict, List

from ..core.action import Action
from ..core.types import ObservableGPUState, ObservableState
from .base import BasePolicy
from .tie_breaking import arrival_then_id
from ..simulator.kv_block_manager import KVBlockSpaceManager

# Representative values from the pinned reference's own OSDI evaluation
# scripts (osdi-experiments/table-6/scheduling_ablation.sh,
# figure-9/prefill_chunking_overhead_runs.sh) -- SarathiSchedulerConfig
# itself declares chunk_size as a required Optional[int] with no built-in
# default. block_size/watermark are inherited unchanged from vLLM's own
# block manager (SarathiBlockSpaceManager is a no-op subclass of it).
DEFAULT_CHUNK_SIZE = 512
DEFAULT_MAX_NUM_SEQS = 128
DEFAULT_BLOCK_SIZE = 16
DEFAULT_WATERMARK = 0.01


class _RequestState:
    __slots__ = ("remaining_prefill",)

    def __init__(self, remaining_prefill: int) -> None:
        self.remaining_prefill = remaining_prefill


class SarathiFaithfulPolicy(BasePolicy):
    """Faithful reimplementation of Sarathi-Serve's stall-free chunked-
    prefill scheduler. See module docstring and
    docs/sarathi_faithful_scheduler_reference.md for the full fidelity
    record.

    Stateful across steps (per-GPU KV block managers and shadow
    prefill-progress tracking persist for the lifetime of a simulation
    run) -- call `reset()` before reusing an instance across multiple runs.
    """

    name = "sarathi_faithful"

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        block_size: int = DEFAULT_BLOCK_SIZE,
        max_num_seqs: int = DEFAULT_MAX_NUM_SEQS,
        watermark: float = DEFAULT_WATERMARK,
    ) -> None:
        self.chunk_size = chunk_size
        self.block_size = block_size
        self.max_num_seqs = max_num_seqs
        self.watermark = watermark
        self._block_managers: Dict[int, KVBlockSpaceManager] = {}
        self._request_states: Dict[int, Dict[int, _RequestState]] = {}

    def reset(self) -> None:
        self._block_managers = {}
        self._request_states = {}

    # ------------------------------------------------------------------
    # Per-GPU state lifecycle
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

    def _get_request_states(self, gpu_id: int) -> Dict[int, _RequestState]:
        states = self._request_states.get(gpu_id)
        if states is None:
            states = {}
            self._request_states[gpu_id] = states
        return states

    def _reconcile_completions(
        self, bm: KVBlockSpaceManager, states: Dict[int, _RequestState], gpu: ObservableGPUState,
    ) -> None:
        """Free blocks and shadow state for any request no longer active on
        this GPU (completed since our last call). A request we ourselves
        preempted this same call is already freed eagerly in
        _run_gpu_schedule, so this only ever fires for genuine completions."""
        active_ids = set(gpu.active_request_ids)
        for rid in bm.allocated_request_ids():
            if rid not in active_ids:
                bm.free(rid)
        for rid in list(states.keys()):
            if rid not in active_ids:
                del states[rid]

    def _adopt_untracked_active(
        self, bm: KVBlockSpaceManager, states: Dict[int, _RequestState], gpu: ObservableGPUState,
    ) -> None:
        """Defensive: track any request active on this GPU that this policy
        has never seen (e.g. this instance's very first call on a run whose
        state already had active requests). Best-effort: assumes a request
        with 0 decoded tokens is still fully prefilling (cannot recover its
        true remaining-chunk progress), and one with >0 decoded tokens has
        already finished prefill. Never expected in normal use."""
        for req in gpu.active_requests_info:
            if req.request_id not in states:
                decoded = gpu.tokens_decoded_per_request.get(req.request_id, 0)
                remaining = 0 if decoded > 0 else req.prompt_tokens
                bm.allocate(req.request_id, req.prompt_tokens)
                states[req.request_id] = _RequestState(remaining_prefill=remaining)

    # ------------------------------------------------------------------
    # Main scheduling entry point
    # ------------------------------------------------------------------

    def select_action(self, state: ObservableState) -> Action:
        admit: Dict[int, List[int]] = {g.gpu_id: [] for g in state.gpu_states}
        preempt: Dict[int, List[int]] = {g.gpu_id: [] for g in state.gpu_states}

        # Multiple GPUs are modeled as independent Sarathi-style engines,
        # each with its own block manager and chunk budget, considering the
        # same global waiting queue in a fixed (ascending gpu_id) order --
        # the pinned reference itself models exactly one engine/one waiting
        # queue, so this ordering is this policy's own multi-GPU extension.
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
        states = self._get_request_states(gpu.gpu_id)
        self._reconcile_completions(bm, states, gpu)
        self._adopt_untracked_active(bm, states, gpu)

        # --- Phase 1a: reserve a decode-token slot for every already-
        # prefill-completed running sequence FIRST (the stall-free /
        # decode-first property), preempting the lowest-priority one if
        # short on blocks. Identical victim-selection algorithm to
        # vllm_faithful / the pinned vLLM scheduler.
        decoding = sorted(
            (req for req in gpu.active_requests_info
             if req.request_id in states and states[req.request_id].remaining_prefill == 0),
            key=arrival_then_id,
        )
        pending = list(decoding)
        kept_ids: List[int] = []
        preempted_ids: List[int] = []

        while pending:
            candidate = pending.pop(0)
            while not bm.can_append_slot(candidate.request_id):
                if pending:
                    victim = pending.pop(-1)
                    bm.free(victim.request_id)
                    del states[victim.request_id]
                    preempted_ids.append(victim.request_id)
                else:
                    bm.free(candidate.request_id)
                    del states[candidate.request_id]
                    preempted_ids.append(candidate.request_id)
                    break
            else:
                bm.append_slot(candidate.request_id)
                kept_ids.append(candidate.request_id)

        num_batched_tokens = len(kept_ids)  # 1 token per decoding sequence kept

        # --- Phase 1b: continuing prefills (already admitted, still mid-
        # chunk from a previous iteration) consume whatever budget Phase 1a
        # left over. Memory was already fully reserved at admission, so
        # only the token budget is checked here -- no block-capacity
        # interaction, matching the pinned reference exactly. This phase
        # emits no Action (the simulator's own GPUState independently
        # advances actual prefill progress); it exists purely so Phase 2's
        # new-admission budget accounting matches the pinned reference.
        still_prefilling = sorted(
            (req for req in gpu.active_requests_info
             if req.request_id in states and states[req.request_id].remaining_prefill > 0),
            key=arrival_then_id,
        )
        for req in still_prefilling:
            rstate = states[req.request_id]
            chunk = min(rstate.remaining_prefill, self.chunk_size - num_batched_tokens)
            if chunk <= 0:
                continue  # no budget left this iteration; no progress accounted
            rstate.remaining_prefill -= chunk
            num_batched_tokens += chunk

        # --- Phase 2: admit from `waiting`, FCFS, chunked. Unlike vLLM's
        # own scheduler (which just skips a non-allocatable request and
        # keeps trying later ones), the pinned Sarathi-Serve source
        # (read directly, not inferred from its own comment) STOPS
        # admitting entirely -- both when a request cannot be allocated
        # AND when its first chunk would be 0 tokens.
        admitted_ids: List[int] = []
        num_curr_seqs = len(kept_ids) + len(still_prefilling)
        max_num_seqs_effective = min(self.max_num_seqs, gpu.max_active_sequences)

        still_waiting: List = []
        admission_closed = False
        for req in waiting:
            if admission_closed:
                still_waiting.append(req)
                continue
            if req.request_id in preempted_ids:
                still_waiting.append(req)
                continue
            if not bm.can_allocate(req.prompt_tokens):
                admission_closed = True
                still_waiting.append(req)
                continue
            if num_curr_seqs + 1 > max_num_seqs_effective:
                admission_closed = True
                still_waiting.append(req)
                continue
            chunk = min(req.prompt_tokens, self.chunk_size - num_batched_tokens)
            if chunk <= 0:
                admission_closed = True
                still_waiting.append(req)
                continue
            # Final safety net: never attempt an admission the simulator's
            # OWN GPUConfig constraints would reject (see vllm_faithful's
            # identical safety net for the rationale).
            if not self._feasible_on_gpu(gpu, req):
                still_waiting.append(req)
                continue

            bm.allocate(req.request_id, req.prompt_tokens)
            states[req.request_id] = _RequestState(remaining_prefill=req.prompt_tokens - chunk)
            admitted_ids.append(req.request_id)
            num_batched_tokens += chunk
            num_curr_seqs += 1
            gpu.active_request_ids.append(req.request_id)
            gpu.current_kv_tokens += req.prompt_tokens

        return admitted_ids, preempted_ids, still_waiting
