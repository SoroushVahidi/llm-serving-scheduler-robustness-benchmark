"""
vllm_chunked_prefill_faithful: faithful independent reimplementation of
vLLM's chunked-prefill scheduler (v0.4.2 era) and block_manager_v1 paged-KV
management, inside this project's simulator.

Pinned reference: vLLM commit c7f2cf2b7f67bce5842fedfdba508440fe257375
(tag v0.4.2). See docs/vllm_chunked_prefill_faithful_scheduler_reference.md
for the full source-provenance record, algorithm summary, and explicit
exclusions (block_manager_v2, prefix caching, speculative decoding,
disaggregation, LoRA, delay_factor). See
docs/vllm_chunked_prefill_faithful_design_audit.md for the preliminary
design audit that recommended this pin, and
docs/vllm_chunked_prefill_faithful_root_cause_analysis.md for why this
baseline alone is not expected to flip the active_decode_plus_arriving_
prefill/kv_pressure positive-target mismatches (a shared simulator-
execution-layer limitation, not something this policy can fix).

This is NOT:
  - official vLLM code (it is a from-scratch Python reimplementation),
  - an exact runtime reproduction (hardware timing is still this
    simulator's ServiceModel's job, unchanged by this policy),
  - a full vLLM performance model (only scheduling/memory *decisions* are
    modeled: what gets admitted, chunked, preempted, and when).
It IS a faithful reimplementation of the pinned reference's
`_schedule_chunked_prefill` algorithm and (unchanged from v0.1.0)
block_manager_v1 KV-block memory semantics.

Relationship to other vLLM-labeled things in this repo (see docs/baselines.md):
  - `vllm_faithful` (src/robustbench/policies/vllm_faithful.py) is pinned to
    v0.1.0, BEFORE chunked prefill existed -- all-or-nothing prompt
    admission, no partial/chunked prefill at all. Entirely unchanged by
    this addition (separate file, separate registry entry).
  - `vllm_style_token_budget` (src/robustbench/policies/vllm_style_token_budget.py)
    is a lightweight proxy/inspired baseline, not a scheduler
    reimplementation. Unchanged by this work.
  - `sarathi_faithful` (src/robustbench/policies/sarathi_faithful.py) is a
    DIFFERENT chunked-prefill scheduler (Sarathi-Serve's own, with an
    explicit decode-priority phase vLLM's own chunked-prefill scheduler
    does not have -- see the reference doc's algorithm section for the
    verified structural difference). Not a variant of this baseline; a
    separately pinned, independently-sourced reference.

Deliberately NOT registered as a deployable baseline or selector candidate
-----------------------------------------------------------------------------
Registered only in EXTERNAL_BASELINE_REGISTRY
(src/robustbench/policies/external_baselines_registry.py), never in
registry.py's BASELINE_NAMES/SELECTOR_CANDIDATE_NAMES -- same rationale as
vllm_faithful/sarathi_faithful's own module docstrings: promoting any of
these to a selectable, deployable baseline is a deliberate future decision,
not an oversight here.

Simulator-timing adaptation (disclosed)
----------------------------------------
This policy's ADMISSION-time accounting faithfully mirrors the pinned
source's `_schedule_running(enable_chunking=True)`: decode-phase and
still-prefilling ("continuing-prefill") requests share ONE FCFS-by-arrival
budget, with no explicit decode-priority phase (see the reference doc).

UPDATED: the simulator's shared EXECUTION layer, GPUState._step_phase15
(src/robustbench/simulator/gpu.py), used to unconditionally reserve one
decode token per already-decoding request before allocating any leftover
budget to prefill, for every Phase-1.5 policy, regardless of what that
policy's own scheduler decided (docs/vllm_chunked_prefill_faithful_root_
cause_analysis.md Finding 2/3 -- a dead `decode_first` branch). This has
been fixed: when the caller sets `ServiceModel(enable_decode_prefill_
contention=True, decode_first=False)`, GPUState now genuinely reproduces
this baseline's one real vulnerability (a continuing-prefill request
consuming shared budget ahead of a later-arrival decode request, causing
that decode request to receive 0 tokens that step) -- see
docs/decode_prefill_contention_execution_model.md for the full design and
docs/vllm_chunked_prefill_faithful_root_cause_analysis.md's own Finding
2/3 for the pre-fix state this replaces. This is opt-in and backward-
compatible: callers that do not set `enable_decode_prefill_contention`
keep the historical decode-protected execution unconditionally, same as
before.

Like sarathi_faithful, this policy's admission decisions assume the
simulator is configured with enable_prefill_modeling=True (a genuine
prefill/decode split). Under the Phase 1 default
(enable_prefill_modeling=False), prefill is zero-cost and this policy's
chunked-admission behavior has no observable timing effect, though it will
still make well-formed, deterministic admission decisions.

REQUIRES `enable_prefill_modeling=True` on the simulator's ServiceModel to
exhibit chunked-prefill behavior -- see docs/vllm_chunked_prefill_faithful_
root_cause_analysis.md for why evaluating this baseline under the SAME
ServiceModel as sarathi_faithful (not vllm_faithful's zero-prefill-cost
default) is required for a meaningful comparison.

Like sarathi_faithful, this policy maintains its own shadow count of each
tracked request's remaining prefill tokens (assuming
prefill_cost_per_token=1.0, ServiceModel's own default), independent of
GPUState's own InternalRequest.prefill_remaining, purely to make correct
ADMISSION decisions each step. If a run overrides that default, this
policy's admission-time budget accounting will drift from the simulator's
true prefill progress; documented here rather than silently wrong (same
caveat as sarathi_faithful).
"""
from __future__ import annotations

from typing import Dict, List

from ..core.action import Action
from ..core.types import ObservableGPUState, ObservableState
from .base import BasePolicy
from .tie_breaking import arrival_then_id
from ..simulator.kv_block_manager import KVBlockSpaceManager

# vllm/config.py @ c7f2cf2b7f67bce5842fedfdba508440fe257375 (tag v0.4.2):
# when enable_chunked_prefill=True and max_num_batched_tokens is not
# explicitly set, SchedulerConfig defaults it to 512 (NOT the non-chunked
# default vllm_faithful uses, max(max_model_len, 2048)/effectively 2560
# in this project's own pin -- see reference doc). max_num_seqs/block_size/
# watermark are unchanged from vllm_faithful's own v0.1.0 pin (confirmed
# unchanged at this pin by direct source comparison).
DEFAULT_BLOCK_SIZE = 16
DEFAULT_MAX_NUM_BATCHED_TOKENS = 512
DEFAULT_MAX_NUM_SEQS = 256
DEFAULT_WATERMARK = 0.01


class _RequestState:
    __slots__ = ("remaining_prefill",)

    def __init__(self, remaining_prefill: int) -> None:
        self.remaining_prefill = remaining_prefill


class VLLMChunkedPrefillFaithfulPolicy(BasePolicy):
    """Faithful reimplementation of vLLM v0.4.2's chunked-prefill scheduler
    (`_schedule_chunked_prefill`) + block_manager_v1 paged KV block manager.
    See module docstring and
    docs/vllm_chunked_prefill_faithful_scheduler_reference.md for the full
    fidelity record.

    Stateful across steps (block tables and per-GPU shadow prefill-progress
    tracking persist for the lifetime of a simulation run) -- call reset()
    before reusing an instance across multiple simulation runs.
    """

    name = "vllm_chunked_prefill_faithful"

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

        # Multiple GPUs are modeled as independent vLLM-chunked-prefill-style
        # engines, each with its own block manager and budget, considering
        # the same global waiting queue in a fixed (ascending gpu_id) order
        # -- the pinned reference itself models exactly one engine/one
        # waiting queue, so this ordering is this policy's own multi-GPU
        # extension, matching vllm_faithful/sarathi_faithful's own identical
        # convention.
        remaining_waiting = list(state.waiting_queue)  # already FCFS-with-preemption ordered

        for gpu in sorted(state.gpu_states, key=lambda g: g.gpu_id):
            admitted_here, preempted_here, remaining_waiting = self._run_gpu_schedule(
                gpu, remaining_waiting,
            )
            admit[gpu.gpu_id] = admitted_here
            preempt[gpu.gpu_id] = preempted_here

        return Action(admit=admit, preempt=preempt)

    def _run_gpu_schedule(self, gpu: ObservableGPUState, waiting: List) -> tuple:
        """Runs the pinned reference's `_schedule_chunked_prefill()` for one
        GPU/engine. Returns (admitted_request_ids, preempted_request_ids,
        remaining_waiting)."""
        bm = self._get_block_manager(gpu)
        states = self._get_request_states(gpu.gpu_id)
        self._reconcile_completions(bm, states, gpu)
        self._adopt_untracked_active(bm, states, gpu)

        # --- Phase 1 (`_schedule_running(..., enable_chunking=True)`):
        # ONE combined FCFS-by-arrival-time pass over every currently
        # active tracked request -- decode-phase AND continuing-prefill-
        # phase mixed together, exactly matching the pinned reference's
        # `self.running` queue in chunked-prefill mode (structurally
        # different from sarathi_faithful's own explicit decode-first
        # Phase 1a/1b split -- see the reference doc's algorithm section).
        tracked = sorted(
            (req for req in gpu.active_requests_info if req.request_id in states),
            key=arrival_then_id,
        )
        pending = list(tracked)
        kept_ids: List[int] = []
        preempted_ids: List[int] = []
        num_batched_tokens = 0
        num_curr_seqs = 0

        while pending:
            candidate = pending[0]
            rstate = states[candidate.request_id]
            remaining_budget = self.max_num_batched_tokens - num_batched_tokens
            if rstate.remaining_prefill == 0:
                num_new_tokens = 1 if remaining_budget >= 1 else 0
            else:
                num_new_tokens = min(rstate.remaining_prefill, max(0, remaining_budget))

            if num_new_tokens == 0:
                # Mirrors `_get_num_new_tokens(...) == 0: break` in the
                # pinned `_schedule_running` (scheduler.py line 415-416):
                # budget exhausted, stop scheduling the REST of the running
                # queue entirely this iteration (not "skip and try the
                # next candidate"). Whatever is left in `pending` simply
                # makes no progress this step; it remains active and is
                # reconsidered next call.
                break

            pending.pop(0)

            if rstate.remaining_prefill == 0:
                # Decode-phase candidate: needs a genuine KV-slot capacity
                # check, exactly as vllm_faithful's/sarathi_faithful's own
                # decode-priority loops -- identical victim-selection
                # algorithm (evict from the back of what's left; if nothing
                # left, preempt the candidate itself).
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
                    num_batched_tokens += num_new_tokens
                    num_curr_seqs += 1
            else:
                # Continuing-prefill candidate: its blocks were already
                # fully reserved for the whole prompt at admission (see
                # reference doc's "why continuing-prefill sequences never
                # actually fail can_append_slots" section) -- no capacity
                # check needed, matching sarathi_faithful's identical Phase
                # 1b rationale. Still eligible to be PICKED as a preemption
                # victim by another candidate's slot search above (mirrors
                # the pinned reference's shared running_queue), just never
                # itself initiates one.
                kept_ids.append(candidate.request_id)
                num_batched_tokens += num_new_tokens
                num_curr_seqs += 1
                rstate.remaining_prefill -= num_new_tokens

        # --- Phase 2 (swap-in): not modeled -- this policy never uses swap
        # preemption (every request is single-sequence, so the pinned
        # reference's own mode-selection always picks recompute; see the
        # reference doc's Exclusions). The `swapped` queue is always empty.

        # --- Phase 3 (`_schedule_prefills(..., enable_chunking=True)`):
        # admit from `waiting`, FCFS, honoring the block-capacity watermark,
        # the shared token budget (leftover from Phase 1), and the
        # max-concurrent-sequences cap. Order verified against source:
        # can_allocate check FIRST, then the combined
        # num_new_tokens==0-or-max_num_seqs-exceeded check -- both close
        # admission entirely (break), not skip-and-continue.
        admitted_ids: List[int] = []
        max_num_seqs_effective = min(self.max_num_seqs, gpu.max_active_sequences)

        still_waiting: List = []
        admission_closed = False
        for req in waiting:
            if admission_closed:
                still_waiting.append(req)
                continue
            if req.request_id in preempted_ids:
                # Mirrors "if seq_group in preempted: break" in the pinned
                # source's own admission loop -- structural fidelity kept
                # even though, as in vllm_faithful/sarathi_faithful, this is
                # a defensive no-op today (a request preempted THIS call is
                # not yet reflected in state.waiting_queue).
                still_waiting.append(req)
                continue
            if not bm.can_allocate(req.prompt_tokens):
                admission_closed = True
                still_waiting.append(req)
                continue
            remaining_budget = self.max_num_batched_tokens - num_batched_tokens
            num_new_tokens = min(req.prompt_tokens, max(0, remaining_budget))
            if num_new_tokens == 0 or num_curr_seqs + 1 > max_num_seqs_effective:
                admission_closed = True
                still_waiting.append(req)
                continue
            # Final safety net: never attempt an admission the simulator's
            # OWN GPUConfig constraints (max_active_sequences/max_batch_tokens/
            # max_kv_tokens) would reject -- same rationale as
            # vllm_faithful's/sarathi_faithful's identical safety net.
            if not self._feasible_on_gpu(gpu, req):
                still_waiting.append(req)
                continue

            bm.allocate(req.request_id, req.prompt_tokens)
            states[req.request_id] = _RequestState(
                remaining_prefill=req.prompt_tokens - num_new_tokens
            )
            admitted_ids.append(req.request_id)
            num_batched_tokens += num_new_tokens
            num_curr_seqs += 1
            # Keep the local GPU view consistent for _feasible_on_gpu checks
            # against subsequently-considered waiting requests this step.
            gpu.active_request_ids.append(req.request_id)
            gpu.current_kv_tokens += req.prompt_tokens

        return admitted_ids, preempted_ids, still_waiting
