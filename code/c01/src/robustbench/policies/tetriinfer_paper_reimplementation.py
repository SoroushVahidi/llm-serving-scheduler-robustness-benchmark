"""
tetriinfer_paper_reimplementation: an independent reimplementation of the
TetriInfer paper's core two-level scheduling algorithm, built on this
project's disaggregated prefill/decode infrastructure.

Pinned reference: arXiv:2401.11181 ("Inference without Interference:
Disaggregate LLM Inference for Mixed Downstream Workloads"), v1 (the only
version), 2024-01-20. **No official code repository or artifact exists**
for TetriInfer (verified live via `gh api`/`gh search code`/web search --
see docs/tetriinfer_reference.md section 0). Full source-provenance
record, exact algorithmic details vs. this project's own disclosed
adaptations, and reproducibility determination: docs/tetriinfer_reference.md.

Why this is NOT labeled `tetriinfer_faithful`
----------------------------------------------
This project's `_faithful` label (see `vllm_faithful`, `sarathi_faithful`,
`distserve_faithful`) means "verified against a specific, pinned,
author-maintained source-code commit." TetriInfer has no such commit to
pin -- only an arXiv preprint describing the algorithm in prose. Several
components are genuinely precisely specified in the paper (the dispatcher's
three-step power-of-two routing algorithm; the reserve-static/
reserve-dynamic admission rules; heavy/light thresholds) and are
reimplemented faithfully *to the paper's stated description*. Others are
not reproducible even in principle (the fine-tuned OPT-125M length
predictor's learned weights) or are not given as a closed-form algorithm
(the "least interference" scoring function) and required this project's
own disclosed operationalization -- see docs/tetriinfer_reference.md
section E for the itemized list. `tetriinfer_paper_reimplementation` is
the scientifically defensible label for this mix of confidence levels.

Scope
-----
Implemented: the global scheduler (least-loaded prefill-instance
assignment), the local prefill scheduler (FCFS/SJF/LJF, non-preemptive,
batch-size/token-budget/KV-capacity bounded), the length-prediction
abstraction (see tetriinfer_length_prediction.py), the inter-instance
decode dispatcher (power-of-two + least-interference tie-break, see
tetriinfer_routing.py), and the local decode scheduler (greedy /
reserve-static / reserve-dynamic).

NOT implemented (see docs/tetriinfer_reference.md section E for why):
instance flip (idle-based prefill<->decode role switching), the ML length
predictor itself (replaced with a disclosed, deterministic, non-ML
abstraction), chunk-level (vs. request-level) KV transfer, network-stack/
bandwidth modeling.

Multi-instance topology
------------------------
Unlike `distserve_faithful` (which requires and enforces exactly one
prefill-role and one decode-role GPU, per DistServe's own pinned
single-worker-per-stage architecture), this policy requires **at least
one** GPU of each role and supports **any number** of decode-role GPUs --
this is the first baseline in this project requiring genuine multi-instance
decode-side routing, matching TetriInfer's own dispatcher design.

No swap
-------
TetriInfer's decode-side capacity management is admission-time avoidance
(reserve-static/reserve-dynamic), explicitly aiming to prevent ever
triggering a swap/thrashing event -- the opposite of `distserve_faithful`'s
active swap-based eviction. This policy never sets `Action.swap` or
`Action.preempt`.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ..core.action import Action
from ..core.types import ObservableGPUState, ObservableRequest, ObservableState
from .base import BasePolicy
from .tie_breaking import arrival_then_id
from ..simulator.kv_block_manager import KVBlockSpaceManager
from .tetriinfer_length_prediction import LengthPredictor
from .tetriinfer_routing import PowerOfTwoDecodeRouter, is_heavy_decode

# Paper §3.3.3: "in our test environment, the value is 512 tokens for
# OPT-13B" -- explicitly environment-specific, NOT a universal constant
# (unlike Sarathi's own evaluation-script-wide 512 default). Documented
# here as this project's own recommended starting value for
# `ServiceModel.max_prefill_chunk_tokens` when configuring a
# tetriinfer_paper_reimplementation experiment; not directly consumed by
# this policy's own admission logic (chunked-prefill *compute* progress is
# already the simulator's job via ServiceModel, exactly as for
# `distserve_faithful`/`sarathi_faithful`).
DEFAULT_CHUNK_SIZE = 512
# NOT sourced from a paper evaluation script for THIS admission-batch
# concept (the paper's own `PrefillSchedBatch` values of 16/128 govern a
# different real-system batching knob) -- conservative project defaults,
# exposed as explicit constructor parameters (see docs/tetriinfer_reference.md).
DEFAULT_CONTEXT_MAX_BATCH_SIZE = 32
DEFAULT_CONTEXT_MAX_TOKENS_PER_BATCH = 4096
DEFAULT_DECODE_MAX_BATCH_SIZE = 128
# Paper §3.3.2: granularity 200 achieves 74.9% accuracy in the paper's own
# (non-reproducible) setup; used here only as the bucket-math granularity,
# not a claim about matching their empirical accuracy.
DEFAULT_PREDICTOR_GRANULARITY = 200
DEFAULT_BLOCK_SIZE = 16

PREFILL_POLICIES = ("fcfs", "sjf", "ljf")
DECODE_POLICIES = ("greedy", "reserve_static", "reserve_dynamic")


class TetriInferPaperReimplementationPolicy(BasePolicy):
    """See module docstring and docs/tetriinfer_reference.md for the full
    fidelity record. Stateful across steps -- call `reset()` before
    reusing an instance across multiple simulation runs."""

    name = "tetriinfer_paper_reimplementation"

    def __init__(
        self,
        prefill_local_policy: str = "fcfs",
        context_max_batch_size: int = DEFAULT_CONTEXT_MAX_BATCH_SIZE,
        context_max_tokens_per_batch: int = DEFAULT_CONTEXT_MAX_TOKENS_PER_BATCH,
        decode_local_policy: str = "reserve_dynamic",
        decode_max_batch_size: int = DEFAULT_DECODE_MAX_BATCH_SIZE,
        predictor_granularity: int = DEFAULT_PREDICTOR_GRANULARITY,
        predictor_mode: str = "exact",
        predictor_noise_std_tokens: float = 0.0,
        predictor_seed: int = 0,
        routing_seed: int = 0,
        block_size: int = DEFAULT_BLOCK_SIZE,
    ) -> None:
        if prefill_local_policy not in PREFILL_POLICIES:
            raise ValueError(f"prefill_local_policy must be one of {PREFILL_POLICIES}, got {prefill_local_policy!r}")
        if decode_local_policy not in DECODE_POLICIES:
            raise ValueError(f"decode_local_policy must be one of {DECODE_POLICIES}, got {decode_local_policy!r}")

        self.prefill_local_policy = prefill_local_policy
        self.context_max_batch_size = context_max_batch_size
        self.context_max_tokens_per_batch = context_max_tokens_per_batch
        self.decode_local_policy = decode_local_policy
        self.decode_max_batch_size = decode_max_batch_size
        self.predictor_granularity = predictor_granularity
        self.predictor_mode = predictor_mode
        self.predictor_noise_std_tokens = predictor_noise_std_tokens
        self.predictor_seed = predictor_seed
        self.routing_seed = routing_seed
        self.block_size = block_size

        self._init_stateful()

    def _init_stateful(self) -> None:
        self._length_predictor = LengthPredictor(
            granularity=self.predictor_granularity, mode=self.predictor_mode,
            noise_std_tokens=self.predictor_noise_std_tokens, seed=self.predictor_seed,
        )
        self._router = PowerOfTwoDecodeRouter(seed=self.routing_seed)
        self._context_bms: Dict[int, KVBlockSpaceManager] = {}
        self._decode_bms: Dict[int, KVBlockSpaceManager] = {}
        # Global-scheduler / dispatcher assignment stickiness: each request
        # is assigned to exactly one prefill instance (once, on first
        # sight) and, after migrating, exactly one decode instance (once,
        # on first eligibility) -- mirrors the paper's own architecture,
        # where routing is a one-time event per request, not re-decided
        # every scheduling round. Stale entries after a request completes
        # are harmless (request_ids are unique per run) and are never
        # cleaned up, matching this project's established convention (see
        # distserve_faithful's own tracking dicts).
        self._prefill_assignment: Dict[int, int] = {}
        self._decode_assignment: Dict[int, int] = {}

    def reset(self) -> None:
        self._init_stateful()

    # ------------------------------------------------------------------
    # Per-GPU block manager lifecycle
    # ------------------------------------------------------------------

    def _get_context_bm(self, gpu: ObservableGPUState) -> KVBlockSpaceManager:
        bm = self._context_bms.get(gpu.gpu_id)
        if bm is None:
            bm = KVBlockSpaceManager(
                block_size=self.block_size, num_gpu_blocks=gpu.max_kv_tokens // self.block_size,
                watermark=0.0,
            )
            self._context_bms[gpu.gpu_id] = bm
        return bm

    def _get_decode_bm(self, gpu: ObservableGPUState) -> KVBlockSpaceManager:
        bm = self._decode_bms.get(gpu.gpu_id)
        if bm is None:
            bm = KVBlockSpaceManager(
                block_size=self.block_size, num_gpu_blocks=gpu.max_kv_tokens // self.block_size,
                watermark=0.0,
            )
            self._decode_bms[gpu.gpu_id] = bm
        return bm

    def _reconcile_decode_completions(self, bm: KVBlockSpaceManager, gpu: ObservableGPUState) -> None:
        active_ids = set(gpu.active_request_ids)
        for rid in bm.allocated_request_ids():
            if rid not in active_ids:
                bm.free(rid)

    def _grow_active_decode_requests(self, bm: KVBlockSpaceManager, gpu: ObservableGPUState) -> None:
        """Already-active decoding requests grow their tracked KV
        footprint by one token per step, exactly like vLLM's real paged-
        attention mechanism (TetriInfer is explicitly built on top of
        vLLM, per its own Implementation section) -- reserve-static/
        reserve-dynamic are ADMISSION GATES evaluated against the full
        PREDICTED footprint (see _decode_admission_check), not a bulk
        upfront block reservation; actual block consumption always grows
        incrementally, identical to vllm_faithful/distserve_faithful's own
        `append_slot` usage. If growth ever fails (this request's ACTUAL
        length exceeds what its prediction implied, and no block is free)
        it simply stalls for this one step -- no swap/preempt exists for
        this baseline (see module docstring), and the paper does not
        specify a recovery mechanism for this residual, disclosed risk
        (see docs/tetriinfer_reference.md section E)."""
        for req in sorted(gpu.active_requests_info, key=arrival_then_id):
            if bm.is_allocated(req.request_id) and bm.can_append_slot(req.request_id):
                bm.append_slot(req.request_id)

    # ------------------------------------------------------------------
    # Main scheduling entry point
    # ------------------------------------------------------------------

    def select_action(self, state: ObservableState) -> Action:
        prefill_gpus = [g for g in state.gpu_states if g.role == "prefill"]
        decode_gpus = [g for g in state.gpu_states if g.role == "decode"]
        if not prefill_gpus or not decode_gpus:
            raise ValueError(
                "tetriinfer_paper_reimplementation requires at least one GPUConfig(role='prefill') "
                "and at least one GPUConfig(role='decode') (see docs/tetriinfer_reference.md); got "
                f"{len(prefill_gpus)} prefill-role and {len(decode_gpus)} decode-role GPUs."
            )

        admit: Dict[int, List[int]] = {g.gpu_id: [] for g in state.gpu_states}

        self._run_prefill_stage(state.waiting_queue, prefill_gpus, admit)
        self._run_decode_stage(state.migrating_queue, decode_gpus, admit)

        return Action(admit=admit)

    # ------------------------------------------------------------------
    # Global scheduler + local prefill scheduler (context stage)
    # ------------------------------------------------------------------

    def _assign_prefill_gpu(self, req_id: int, prefill_gpus: List[ObservableGPUState]) -> int:
        """Global scheduler (paper §3.2): "choose a prefill instance with
        the least load," assigned once per request and remembered
        thereafter. Load = current active-sequence count (this codebase's
        existing load signal); tie-break lowest gpu_id (undocumented in
        the paper -- this project's own deterministic default)."""
        assigned = self._prefill_assignment.get(req_id)
        if assigned is not None:
            return assigned
        chosen = min(prefill_gpus, key=lambda g: (len(g.active_request_ids), g.gpu_id))
        self._prefill_assignment[req_id] = chosen.gpu_id
        return chosen.gpu_id

    def _sort_key_for_prefill_policy(self, req: ObservableRequest):
        if self.prefill_local_policy == "fcfs":
            return arrival_then_id(req)
        if self.prefill_local_policy == "sjf":
            return (req.prompt_tokens, req.arrival_time, req.request_id)
        # ljf
        return (-req.prompt_tokens, req.arrival_time, req.request_id)

    def _run_prefill_stage(
        self, waiting: List[ObservableRequest], prefill_gpus: List[ObservableGPUState],
        admit: Dict[int, List[int]],
    ) -> None:
        by_gpu: Dict[int, List[ObservableRequest]] = {g.gpu_id: [] for g in prefill_gpus}
        for req in waiting:
            gpu_id = self._assign_prefill_gpu(req.request_id, prefill_gpus)
            by_gpu[gpu_id].append(req)

        gpu_by_id = {g.gpu_id: g for g in prefill_gpus}
        for gpu_id, candidates in by_gpu.items():
            gpu = gpu_by_id[gpu_id]
            candidates.sort(key=self._sort_key_for_prefill_policy)
            admit[gpu_id] = self._admit_prefill_candidates(candidates, gpu)

    def _admit_prefill_candidates(
        self, candidates: List[ObservableRequest], gpu: ObservableGPUState,
    ) -> List[int]:
        """Local prefill scheduler (paper §3.3.1): non-preemptive
        admission from the (already-sorted) scheduled queue, bounded by
        batch size, per-round token budget, and KV-block capacity. Stops
        entirely (not skip-and-continue) at the first non-admittable
        request -- same established convention as
        distserve_faithful/vllm_faithful's own local schedulers."""
        bm = self._get_context_bm(gpu)
        admitted: List[int] = []
        batch_tokens = 0

        for req in candidates:
            if len(admitted) >= self.context_max_batch_size:
                break
            if batch_tokens + req.prompt_tokens > self.context_max_tokens_per_batch:
                break
            if not bm.can_allocate(req.prompt_tokens):
                break
            if not self._feasible_on_gpu(gpu, req):
                continue

            bm.allocate(req.request_id, req.prompt_tokens)
            admitted.append(req.request_id)
            batch_tokens += req.prompt_tokens
            gpu.active_request_ids.append(req.request_id)
            gpu.current_kv_tokens += req.prompt_tokens

        return admitted

    # ------------------------------------------------------------------
    # Dispatcher (inter-instance decode routing) + local decode scheduler
    # ------------------------------------------------------------------

    def _assign_decode_gpu(
        self, req: ObservableRequest, decode_gpus: List[ObservableGPUState],
    ) -> Optional[int]:
        """Dispatcher (paper §3.3.4): power-of-two choice among decode
        instances with enough predicted resources, tie-broken by the
        paper's own stated "least interference" objective (see
        tetriinfer_routing.py). Assigned once per request and remembered
        thereafter -- a request whose assignment fails (alpha set empty)
        is retried on a later round (no assignment recorded)."""
        assigned = self._decode_assignment.get(req.request_id)
        if assigned is not None:
            return assigned

        prediction = self._length_predictor.predict(req.predicted_output_tokens)
        predicted_heavy = is_heavy_decode(prediction.point_estimate)

        def fits(gpu: ObservableGPUState) -> bool:
            # Eligibility must use the SAME admission criteria as the local
            # scheduler will actually apply (see _decode_admission_check) --
            # not a separate, simpler "immediate capacity only" check.
            # Otherwise, under reserve-dynamic, a single-instance topology
            # could permanently block a request the local scheduler would
            # in fact admit once projected future capacity is considered,
            # since routing happens strictly before local admission and a
            # rejected-at-routing request never gets a second look this
            # round.
            bm = self._get_decode_bm(gpu)
            active_remaining = (
                self._predicted_remaining_for_active(gpu)
                if self.decode_local_policy == "reserve_dynamic" else []
            )
            return self._decode_admission_check(
                bm, req.prompt_tokens, prediction.point_estimate, active_remaining,
            )

        chosen_id = self._router.select_decode_gpu(decode_gpus, predicted_heavy, fits)
        if chosen_id is not None:
            self._decode_assignment[req.request_id] = chosen_id
        return chosen_id

    def _run_decode_stage(
        self, migrating_queue: List[ObservableRequest], decode_gpus: List[ObservableGPUState],
        admit: Dict[int, List[int]],
    ) -> None:
        by_gpu: Dict[int, List[ObservableRequest]] = {g.gpu_id: [] for g in decode_gpus}
        for req in migrating_queue:
            gpu_id = self._assign_decode_gpu(req, decode_gpus)
            if gpu_id is not None:
                by_gpu[gpu_id].append(req)

        gpu_by_id = {g.gpu_id: g for g in decode_gpus}
        for gpu_id, candidates in by_gpu.items():
            gpu = gpu_by_id[gpu_id]
            bm = self._get_decode_bm(gpu)
            self._reconcile_decode_completions(bm, gpu)
            self._grow_active_decode_requests(bm, gpu)
            candidates.sort(key=arrival_then_id)
            admit[gpu_id] = self._admit_decode_candidates(candidates, gpu, bm)

    def _predicted_remaining_for_active(self, gpu: ObservableGPUState) -> List[Tuple[int, int, int]]:
        """(request_id, predicted_remaining_output_tokens,
        predicted_full_sequence_footprint_tokens) for every currently-
        active decoding request -- used by reserve-dynamic's "shortest
        remaining job" projection. `predicted_remaining_output_tokens`
        (predicted total output minus tokens already decoded, floored at
        0) picks out the SOONEST request to finish; `predicted_full_
        sequence_footprint_tokens` (prompt + predicted total output) is
        this project's own estimate of how many blocks it will free once
        done -- NOT `bm.num_blocks_for` (that reflects only growth SO FAR,
        which understates the eventual freed amount for a request that
        has not finished yet)."""
        out = []
        for req in gpu.active_requests_info:
            decoded_so_far = gpu.tokens_decoded_per_request.get(req.request_id, 0)
            predicted_output_total = self._length_predictor.predict(req.predicted_output_tokens).point_estimate
            remaining = max(0, predicted_output_total - decoded_so_far)
            full_footprint = req.prompt_tokens + predicted_output_total
            out.append((req.request_id, remaining, full_footprint))
        return out

    def _admit_decode_candidates(
        self, candidates: List[ObservableRequest], gpu: ObservableGPUState, bm: KVBlockSpaceManager,
    ) -> List[int]:
        """Local decode scheduler (paper §3.3.5-area / Fig. 18): one of
        greedy (vLLM baseline; admits based only on the CURRENT known
        footprint, oblivious to predicted future growth), reserve-static
        (admission GATED on whether the FULL predicted sequence footprint
        fits the currently-available memory), or reserve-dynamic (gated on
        whether it will fit once the shortest-remaining active job
        finishes). All three, once admitted, reserve the SAME initial
        block amount (`prompt_tokens + 1` -- the transferred prompt KV
        plus this step's first decode token); the policies differ only in
        the admission GATE, not in how many blocks get physically
        allocated, since paged-attention grows blocks incrementally no
        matter which admission policy decided to let a request in (see
        _grow_active_decode_requests). None of these use swap --
        TetriInfer's decode-side story is admission-time avoidance, not
        runtime eviction (see module docstring)."""
        admitted: List[int] = []
        num_curr_seqs = len(gpu.active_request_ids)
        active_remaining = self._predicted_remaining_for_active(gpu) if self.decode_local_policy == "reserve_dynamic" else []

        for req in candidates:
            if num_curr_seqs >= self.decode_max_batch_size:
                break

            prediction = self._length_predictor.predict(req.predicted_output_tokens)
            # Same-step growth compensation (a request admitted this step
            # is already `is_decoding` and advances by one decode token
            # this SAME simulator step -- identical rationale as
            # vllm_faithful/distserve_faithful).
            reserve_tokens = req.prompt_tokens + 1

            admit_ok = self._decode_admission_check(
                bm, req.prompt_tokens, prediction.point_estimate, active_remaining,
            )

            if not admit_ok:
                break
            if not self._decode_feasible_on_gpu(gpu, reserve_tokens):
                continue

            bm.allocate(req.request_id, reserve_tokens)
            admitted.append(req.request_id)
            num_curr_seqs += 1
            gpu.active_request_ids.append(req.request_id)
            gpu.current_kv_tokens += reserve_tokens

        return admitted

    def _decode_admission_check(
        self, bm: KVBlockSpaceManager, req_prompt_tokens: int, predicted_output_tokens: int,
        active_remaining: List[Tuple[int, int, int]],
    ) -> bool:
        """Admission GATE only (see _admit_decode_candidates' docstring
        for why this is separate from the actual allocated amount). Shared
        by both the dispatcher's routing-eligibility check
        (_assign_decode_gpu) and the local scheduler's own admission loop
        -- see _assign_decode_gpu's `fits` closure for why these must
        never diverge.

        Always requires `bm.can_allocate(req_prompt_tokens + 1)` (the
        actual incremental amount that would be allocated THIS step) in
        addition to whichever policy-specific gate follows: greedy's own
        gate IS exactly this check, and reserve-static's gate (on the full
        footprint) always implies it too (can_allocate is monotonic in the
        requested size). Only reserve-dynamic can otherwise diverge --
        its gate can pass on a FUTURE projection (blocks not yet actually
        free) even when there isn't currently room for even the small
        incremental allocation; without this conjunction, admission would
        proceed to an actual `bm.allocate()` call that raises
        KVBlockManagerError. Rejecting here just means the candidate is
        not admitted this round (stays in the bridge queue, matching this
        codebase's established stop/retry convention) -- not a crash."""
        if not bm.can_allocate(req_prompt_tokens + 1):
            return False
        if self.decode_local_policy == "greedy":
            # Oblivious to predicted future growth -- vLLM's own baseline
            # behavior per the paper ("as long as the accelerator has
            # spare memory, it will add requests... oblivious to the
            # working set size").
            return True
        # reserve-static/reserve-dynamic gate on the FULL predicted
        # sequence footprint (prompt + predicted total output + 1), not
        # the predicted output alone -- a decode-side request's KV
        # footprint always includes its already-transferred prompt.
        full_predicted_tokens = req_prompt_tokens + predicted_output_tokens + 1
        if self.decode_local_policy == "reserve_static":
            return bm.can_allocate(full_predicted_tokens)
        # reserve_dynamic
        return self._reserve_dynamic_gate(bm, full_predicted_tokens, active_remaining)

    @staticmethod
    def _decode_feasible_on_gpu(gpu: ObservableGPUState, reserve_tokens: int) -> bool:
        """Final safety net analogous to BasePolicy._feasible_on_gpu, but
        checked against `reserve_tokens` (the actual amount being
        allocated -- prompt_tokens + 1, see _admit_decode_candidates)
        rather than re-deriving it, since BasePolicy._feasible_on_gpu
        already assumes `req.prompt_tokens` is the footprint (true here,
        unlike a hypothetical full-prediction reservation)."""
        new_count = len(gpu.active_request_ids) + 1
        new_kv = gpu.current_kv_tokens + reserve_tokens
        return (
            new_count <= gpu.max_active_sequences
            and new_kv <= gpu.max_kv_tokens
            and new_count <= gpu.max_batch_tokens
        )

    def _reserve_dynamic_gate(
        self, bm: KVBlockSpaceManager, full_predicted_tokens: int,
        active_remaining: List[Tuple[int, int, int]],
    ) -> bool:
        needed_blocks = KVBlockSpaceManager.blocks_needed(full_predicted_tokens, self.block_size)
        if bm.num_free_blocks >= needed_blocks:
            return True
        if not active_remaining:
            return False
        # Shortest remaining job = smallest predicted_remaining; estimate
        # freed blocks from its PREDICTED full footprint (not
        # bm.num_blocks_for, which only reflects growth so far).
        _, _, soonest_full_footprint = min(active_remaining, key=lambda x: x[1])
        freed_blocks = KVBlockSpaceManager.blocks_needed(soonest_full_footprint, self.block_size)
        return (bm.num_free_blocks + freed_blocks) >= needed_blocks
