"""slai_faithful: faithful independent reimplementation of the SLAI
(SLO-Aware LLM Inference) scheduler from "Optimal Scheduling Algorithms for
LLM Inference: Theory and Practice" (Bari, Hegde, de Veciana; arXiv:2508.01002;
ACM SIGMETRICS 2026 / POMACS). See docs/slai_faithful_scheduler_reference.md
for the full source-provenance record, algorithm summary, and explicit
exclusions.

Pinned reference: github.com/agrimUT/SLAI, commit
5098a7aba05e3edbcfa3a509d6cc9cd248fc4380 (Apache-2.0). Source files read
directly (cloned and inspected line-by-line, not from memory or the paper's
prose alone):
  - sarathi/core/scheduler/slai_scheduler.py -- SLAIScheduler._schedule(),
    _post_batch_processing(), _tbt_for(), _get_seq_next_num_prefill_tokens()
  - sarathi/core/block_space_manager/slai_scheduler_space_manager.py --
    SLAIBlockSpaceManager(SarathiBlockSpaceManager): pass (no-op subclass;
    SLAI's memory model IS Sarathi-Serve's, unchanged)
  - sarathi/config.py -- SLAISchedulerConfig fields
  - sarathi/core/datatypes/sequence.py -- time_between_tokens, is_strict_tbt,
    prefill_e2e_time_deadline, last_schedulable_time fields
  - Paper Eq. 8 and Section 6 ("Batch construction", steps 1-4) for the
    algorithm's own prose description, cross-checked against the code above.

This is NOT:
  - official SLAI code (it is a from-scratch Python reimplementation),
  - an exact runtime reproduction (hardware timing is still this
    simulator's ServiceModel's job, unchanged by this policy),
  - a reproduction of RAD, the OTHER scheduler in the same paper. RAD is a
    GEMM-tiling-optimal throughput scheduler with a fundamentally different
    design goal (Section 4: "does not consider latency SLOs"); it has no
    continuously-running reference implementation in the pinned repo either
    (only Hold_NScheduler, a single-shot microbenchmark probe used to
    generate one Figure-6c data point, not a deployable RAD scheduler) --
    see docs/slai_faithful_scheduler_reference.md §RAD for the full
    reasoning on why RAD is not implemented here.
It IS a faithful reimplementation of the pinned reference's scheduling
*algorithm*: last-schedulable-time-gated decode deferral, chunked-prefill
admission reusing Sarathi-Serve's own memory model, and dynamic/fixed
offset-based memory-pressure adaptation.

REQUIRES `enable_prefill_modeling=True` on the simulator's ServiceModel
------------------------------------------------------------------------
Same requirement as sarathi_faithful / vllm_chunked_prefill_faithful -- see
their module docstrings.

REQUIRES the new `Action.hold_decode` primitive
------------------------------------------------------------------------
SLAI's central mechanism -- deferring a specific decode-phase request's
iteration for one or more steps while it remains active -- has no analogue
in either of the simulator's two pre-existing GLOBAL execution models
(decode-protected / shared-contention; see ServiceModel.
enable_decode_prefill_contention). Both apply one uniform rule to the
WHOLE decoding population; SLAI needs a PER-REQUEST decision based on that
request's own last-schedulable time. This policy is the reason
`Action.hold_decode` was added (see core/action.py's docstring and
docs/slai_faithful_scheduler_reference.md §Simulator extension).

Disclosed simulator adaptations (see the reference doc for full detail)
------------------------------------------------------------------------
- **TBT-per-request ("user tiers")**: the pinned reference's benchmark
  harness assigns each request an explicit `time_between_tokens` /
  `is_strict_tbt` pair (paying users: strict TBT + priority; free-tier:
  relaxed TBT). This project's `Request` has no such field; the closest
  existing online-observable analogue is `class_id`. This policy maps
  `class_id -> TBT` via a configurable dict (default matching the paper's
  own two-tier experiment: "tight" -> 0.1s, "loose"/other -> 0.5s, "medium"
  -> 0.3s as a disclosed, non-paper-sourced interpolation for this
  project's three-tier class_id convention), and generalizes the paper's
  exactly-two-tier SPF-with-priority ordering to N tiers by sorting
  admission candidates on (tbt(req), prompt_tokens) -- which reduces to the
  paper's exact behavior when there are only two distinct TBT values.
- **Batch execution time (b_batch)**: the pinned reference tracks a
  running average of REAL, GEMM-cost-dependent, variable batch execution
  time, used as the offset safety margin's unit. This simulator's discrete
  step model has NO such variance by construction -- every step is exactly
  `step_size` wall-clock seconds regardless of batch composition. This
  policy therefore uses `step_size` directly wherever the reference would
  use `b_batch`; the offset-margin FORMULA (Eq. 8) is reproduced exactly,
  but the real-world phenomenon it exists to absorb (execution-time
  variability) does not exist in this simulator's execution model. This is
  disclosed here rather than papered over with a fake "running average"
  that would trivially converge to the constant `step_size` anyway.
- **Discrete-step LST anchor**: the pinned reference is an async, continuous
  -time engine where a batch's own wall-clock end time is a natural,
  distinct instant. This simulator's `select_action()` is called once per
  discrete step at the step's START time (`ObservableState.time`); this
  policy uses that same instant as its "batch end" anchor for
  last-schedulable-time (re)computation, for both simplicity and
  consistency -- a constant, disclosed `step_size`-scale timing choice, not
  a source of unbounded drift.
"""
from __future__ import annotations

from typing import Dict, List

from ..core.action import Action
from ..core.types import ObservableGPUState, ObservableRequest, ObservableState
from .base import BasePolicy
from ..simulator.kv_block_manager import KVBlockSpaceManager

# Representative values from the pinned reference's own evaluation
# (Section 7, "Experimental setup"): "For all SLAI variants, we use the
# same token budget [512, matching Sarathi-Serve's], and set both the
# number of active requests and concurrent decode-phase request limit to
# 128." Dynamic-offset thresholds (Θ=5 below 96% memory utilization, Θ=10
# otherwise) are Section 7.1's own "dynamic offset policy" values -- the
# paper's flagship, best-performing configuration ("SLAI (SPF, dynamic
# offset)"), used here as this baseline's defaults.
DEFAULT_TOKEN_BUDGET = 512
DEFAULT_MAX_NUM_SEQS = 128
DEFAULT_DECODE_LIMIT = 128
DEFAULT_BELOW_MEMORY_LIMIT_OFFSET = 5
DEFAULT_ABOVE_MEMORY_LIMIT_OFFSET = 10
DEFAULT_MEMORY_LIMIT_FRACTION = 0.96
DEFAULT_BLOCK_SIZE = 16
DEFAULT_WATERMARK = 0.01

# Disclosed, non-paper-sourced class_id -> TBT (seconds) mapping (see
# module docstring's "TBT-per-request" adaptation note). The paper's own
# two experimental tiers were 0.1s (paying/strict) and 0.5s (free/relaxed);
# 0.3s for the middle tier is a disclosed interpolation.
#
# This project has TWO independently-authored, pre-existing 3-tier class_id
# vocabularies in active use, not one:
#   - "tight"/"medium"/"loose" (Request.class_id's own docstring convention;
#     workloads/synthetic.py; the SwissAI/TraceLab external sweep scripts'
#     assign_slo(), priorities 3.0/2.0/1.0)
#   - "interactive"/"standard"/"batch" (workloads/augmentation.py's
#     DEFAULT_SLO_AUG, used by the in-repo BurstGPT/Azure loaders,
#     priorities 3.0/2.0/1.0)
# The two vocabularies' priority VALUES already match exactly tier-for-tier
# (3.0/2.0/1.0 in both), and selector/dataset_v2/features.py already treats
# {"tight", "interactive", "critical"} as one equivalence class for its own
# "tight-class fraction" feature. Both facts are used here, not invented, to
# extend that same equivalence to a single canonical TBT mapping across BOTH
# vocabularies -- this is the mapping applied identically regardless of
# which of the four datasets (Azure, BurstGPT, SwissAI, TraceLab) a request
# came from, so it cannot silently favor SLAI on any one of them.
DEFAULT_TBT_BY_CLASS = {
    "tight": 0.1, "interactive": 0.1, "critical": 0.1,
    "medium": 0.3, "standard": 0.3,
    "loose": 0.5, "batch": 0.5,
}
# Any OTHER/unrecognized class_id falls back here -- treated as the loosest
# tier (never accidentally strict) rather than silently landing on whatever
# dict-iteration-order default would otherwise apply.
DEFAULT_TBT_FALLBACK = 0.5


class _RequestState:
    __slots__ = ("remaining_prefill",)

    def __init__(self, remaining_prefill: int) -> None:
        self.remaining_prefill = remaining_prefill


class SlaiFaithfulPolicy(BasePolicy):
    """Faithful reimplementation of the SLAI scheduler's last-schedulable-
    time-gated decode deferral + chunked-prefill admission. See module
    docstring and docs/slai_faithful_scheduler_reference.md for the full
    fidelity record.

    Stateful across steps (per-GPU KV block managers, shadow prefill-
    progress tracking, and last-schedulable-time bookkeeping persist for
    the lifetime of a simulation run) -- call `reset()` before reusing an
    instance across multiple runs.
    """

    name = "slai_faithful"

    def __init__(
        self,
        token_budget: int = DEFAULT_TOKEN_BUDGET,
        max_num_seqs: int = DEFAULT_MAX_NUM_SEQS,
        decode_limit: int = DEFAULT_DECODE_LIMIT,
        block_size: int = DEFAULT_BLOCK_SIZE,
        watermark: float = DEFAULT_WATERMARK,
        fcfs: bool = False,
        user_priority: bool = True,
        fixed_offset: bool = False,
        below_memory_limit_offset: int = DEFAULT_BELOW_MEMORY_LIMIT_OFFSET,
        above_memory_limit_offset: int = DEFAULT_ABOVE_MEMORY_LIMIT_OFFSET,
        memory_limit_fraction: float = DEFAULT_MEMORY_LIMIT_FRACTION,
        tbt_by_class: Dict[str, float] = None,
        default_tbt: float = DEFAULT_TBT_FALLBACK,
        step_size: float = 0.001,
    ) -> None:
        self.token_budget = token_budget
        self.max_num_seqs = max_num_seqs
        self.decode_limit = decode_limit
        self.block_size = block_size
        self.watermark = watermark
        self.fcfs = fcfs
        self.user_priority = user_priority
        self.fixed_offset = fixed_offset
        self.below_memory_limit_offset = below_memory_limit_offset
        self.above_memory_limit_offset = above_memory_limit_offset
        self.memory_limit_fraction = memory_limit_fraction
        self.tbt_by_class = dict(tbt_by_class) if tbt_by_class else dict(DEFAULT_TBT_BY_CLASS)
        self.default_tbt = default_tbt
        # Simulator-adapted stand-in for the pinned reference's `b_batch`
        # (running-average batch execution time) -- see module docstring's
        # "Batch execution time" adaptation note. Passed explicitly (same
        # convention as SlaiStylePhaseAwarePolicy/policy_library_v2_helpers)
        # since ObservableState does not expose ServiceModel.step_size directly.
        self.step_size = step_size

        self._block_managers: Dict[int, KVBlockSpaceManager] = {}
        self._request_states: Dict[int, Dict[int, _RequestState]] = {}
        # Last-schedulable-time bookkeeping (Eq. 8): per GPU, per request_id.
        self._lst: Dict[int, Dict[int, float]] = {}

    def reset(self) -> None:
        self._block_managers = {}
        self._request_states = {}
        self._lst = {}

    # ------------------------------------------------------------------
    # Per-GPU state lifecycle (mirrors sarathi_faithful's shadow tracking;
    # SLAI reuses Sarathi-Serve's own memory model unchanged -- see module
    # docstring's "Key finding" cross-reference)
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

    def _get_lst_state(self, gpu_id: int) -> Dict[int, float]:
        lst = self._lst.get(gpu_id)
        if lst is None:
            lst = {}
            self._lst[gpu_id] = lst
        return lst

    def _reconcile_completions(
        self, bm: KVBlockSpaceManager, states: Dict[int, _RequestState],
        lst: Dict[int, float], gpu: ObservableGPUState,
    ) -> None:
        active_ids = set(gpu.active_request_ids)
        for rid in bm.allocated_request_ids():
            if rid not in active_ids:
                bm.free(rid)
        for rid in list(states.keys()):
            if rid not in active_ids:
                del states[rid]
        for rid in list(lst.keys()):
            if rid not in active_ids:
                del lst[rid]

    def _adopt_untracked_active(
        self, bm: KVBlockSpaceManager, states: Dict[int, _RequestState], gpu: ObservableGPUState,
    ) -> None:
        """Defensive: same rationale as sarathi_faithful's identical helper."""
        for req in gpu.active_requests_info:
            if req.request_id not in states:
                decoded = gpu.tokens_decoded_per_request.get(req.request_id, 0)
                remaining = 0 if decoded > 0 else req.prompt_tokens
                bm.allocate(req.request_id, req.prompt_tokens)
                states[req.request_id] = _RequestState(remaining_prefill=remaining)

    # ------------------------------------------------------------------
    # TBT / offset helpers
    # ------------------------------------------------------------------

    def _tbt_for(self, req: ObservableRequest) -> float:
        """Disclosed simulator adaptation: class_id -> TBT (see module
        docstring). Falls back to `default_tbt` for unrecognized classes."""
        return self.tbt_by_class.get(req.class_id, self.default_tbt)

    def _is_strict(self, req: ObservableRequest) -> bool:
        """N-tier generalization of the paper's exactly-two-tier
        is_strict_tbt flag: a request is "strict" if its mapped TBT is the
        minimum configured tier value."""
        return self._tbt_for(req) <= min(self.tbt_by_class.values(), default=self.default_tbt)

    def _offset(self, gpu: ObservableGPUState) -> float:
        """Θ, the last-schedulable-time safety margin (Eq. 8). Fixed, or
        dynamically switched on GPU-memory-utilization (this simulator's
        `current_kv_tokens / max_kv_tokens`, the direct analogue of the
        pinned reference's `get_num_used_gpu_blocks() /
        num_total_gpu_blocks`)."""
        if self.fixed_offset:
            return self.below_memory_limit_offset
        utilization = gpu.current_kv_tokens / gpu.max_kv_tokens if gpu.max_kv_tokens else 0.0
        if utilization < self.memory_limit_fraction:
            return self.below_memory_limit_offset
        return self.above_memory_limit_offset

    # ------------------------------------------------------------------
    # Main scheduling entry point
    # ------------------------------------------------------------------

    def select_action(self, state: ObservableState) -> Action:
        admit: Dict[int, List[int]] = {g.gpu_id: [] for g in state.gpu_states}
        hold_decode: Dict[int, List[int]] = {g.gpu_id: [] for g in state.gpu_states}

        # Multiple GPUs modeled as independent SLAI engines sharing one
        # global waiting queue in ascending gpu_id order -- same
        # deliberate multi-GPU extension convention as sarathi_faithful
        # (the pinned reference itself models exactly one engine).
        remaining_waiting = list(state.waiting_queue)

        for gpu in sorted(state.gpu_states, key=lambda g: g.gpu_id):
            admitted_here, held_here, remaining_waiting = self._run_gpu_schedule(
                gpu, remaining_waiting, state.time,
            )
            admit[gpu.gpu_id] = admitted_here
            hold_decode[gpu.gpu_id] = held_here

        return Action(admit=admit, hold_decode=hold_decode)

    def _run_gpu_schedule(self, gpu: ObservableGPUState, waiting: List, now: float) -> tuple:
        """Runs the pinned reference's `_schedule()` for one GPU/engine.
        Returns (admitted_request_ids, held_decode_request_ids, remaining_waiting)."""
        bm = self._get_block_manager(gpu)
        states = self._get_request_states(gpu.gpu_id)
        lst = self._get_lst_state(gpu.gpu_id)
        self._reconcile_completions(bm, states, lst, gpu)
        self._adopt_untracked_active(bm, states, gpu)

        offset = self._offset(gpu)
        step_size = self.step_size

        decoding = [
            req for req in gpu.active_requests_info
            if req.request_id in states and states[req.request_id].remaining_prefill == 0
        ]
        still_prefilling = [
            req for req in gpu.active_requests_info
            if req.request_id in states and states[req.request_id].remaining_prefill > 0
        ]

        # --- Mirrors _post_batch_processing's LST-assignment rule: ANY
        # request that transitioned to decode-ready (remaining_prefill==0)
        # since we last looked -- whether via a continuing prefill chunk or
        # a new admission that finished prefill in one shot -- gets its
        # FIRST last-schedulable-time set now, uniformly, using THIS
        # decision instant as the "batch end" anchor (see module
        # docstring's discrete-step LST anchor note). Deliberately done
        # BEFORE this step's own critical/non-critical classification, so
        # such a request is immediately eligible to be judged critical or
        # not in the very same call where it becomes decode-ready --
        # exactly matching the pinned reference's one-iteration-lag
        # (prefill completes in iteration N -> LST assigned and
        # critical/non-critical judged starting iteration N+1).
        for req in decoding:
            if req.request_id not in lst:
                lst[req.request_id] = now + self._tbt_for(req) - offset * step_size

        # --- Step 1: classify critical vs non-critical decode-iterations.
        # Every request in `decoding` now has an LST (assigned above, or on
        # a prior call). Sorted by increasing LST, per the reference's
        # "closest to their TBT deadline first" rule (Section 6, batch
        # construction step 2).
        def _lst_key(req: ObservableRequest) -> float:
            return lst.get(req.request_id, float("-inf"))

        decoding_sorted = sorted(decoding, key=lambda r: (_lst_key(r), r.request_id))
        critical = [r for r in decoding_sorted if now >= _lst_key(r)]
        non_critical = [r for r in decoding_sorted if now < _lst_key(r)]

        # --- Step 2: schedule critical decodes, up to decode_limit.
        served_decode_ids: List[int] = []
        for req in critical:
            if len(served_decode_ids) >= self.decode_limit:
                break
            served_decode_ids.append(req.request_id)

        num_batched_tokens = len(served_decode_ids)  # 1 token per decode kept

        # --- Step 3: prefill -- continuing (already-active) prefills get
        # priority, then new admissions from `waiting` (FCFS or
        # SPF/tiered-SPF; see module docstring's TBT-tier adaptation).
        for req in still_prefilling:
            rstate = states[req.request_id]
            chunk = min(rstate.remaining_prefill, self.token_budget - num_batched_tokens)
            if chunk <= 0:
                continue
            rstate.remaining_prefill -= chunk
            num_batched_tokens += chunk
            # If this chunk finishes prefill, the request becomes
            # decode-ready; its first LST is assigned on the NEXT call's
            # top-of-function pass (see above), not here -- matching the
            # pinned reference's one-iteration lag exactly.

        admitted_ids: List[int] = []
        num_curr_seqs = len(served_decode_ids) + len(non_critical) + len(still_prefilling)
        max_num_seqs_effective = min(self.max_num_seqs, gpu.max_active_sequences)

        ordered_waiting = list(waiting)
        if not self.fcfs:
            if self.user_priority:
                ordered_waiting.sort(key=lambda r: (self._tbt_for(r), r.prompt_tokens, r.request_id))
            else:
                ordered_waiting.sort(key=lambda r: (r.prompt_tokens, r.request_id))

        still_waiting: List = []
        admission_closed = False
        for req in ordered_waiting:
            if admission_closed:
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
            chunk = min(req.prompt_tokens, self.token_budget - num_batched_tokens)
            if chunk <= 0:
                admission_closed = True
                still_waiting.append(req)
                continue
            if not self._feasible_on_gpu(gpu, req):
                still_waiting.append(req)
                continue

            bm.allocate(req.request_id, req.prompt_tokens)
            remaining_after = req.prompt_tokens - chunk
            states[req.request_id] = _RequestState(remaining_prefill=remaining_after)
            admitted_ids.append(req.request_id)
            num_batched_tokens += chunk
            num_curr_seqs += 1
            gpu.active_request_ids.append(req.request_id)
            gpu.current_kv_tokens += req.prompt_tokens
            # Same one-iteration-lag note as still_prefilling above: even a
            # tiny prompt that finishes its entire prefill in this same
            # admission gets its first LST on the NEXT call, not here.

        # --- Step 4: leftover budget/decode_limit -> serve additional
        # non-critical decodes, increasing LST order (closest-to-critical
        # first among the ones we could safely defer).
        remaining_budget = self.token_budget - num_batched_tokens
        remaining_decode_slots = self.decode_limit - len(served_decode_ids)
        for req in non_critical:
            if remaining_budget <= 0 or remaining_decode_slots <= 0:
                break
            served_decode_ids.append(req.request_id)
            remaining_budget -= 1
            remaining_decode_slots -= 1

        # --- Refresh LST for every decode actually served this step
        # (critical + any extra non-critical granted leftover budget),
        # mirroring _post_batch_processing's re-derivation-on-service rule.
        served_set = set(served_decode_ids)
        for req in decoding:
            if req.request_id in served_set:
                lst[req.request_id] = now + self._tbt_for(req) - offset * step_size

        held_ids = [r.request_id for r in decoding if r.request_id not in served_set]

        return admitted_ids, held_ids, still_waiting
