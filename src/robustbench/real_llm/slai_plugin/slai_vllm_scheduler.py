"""vLLM v1 `--scheduler-cls` adapter for the SLAI/RAD faithful
reimplementation (docs/REAL_VLLM_SLAI_FIDELITY.md has the full fidelity
map and validation status).

FIDELITY STATUS (see docs/REAL_VLLM_SLAI_FIDELITY.md for detail):
  - Admission ordering (TBT-tiered SPF): maps onto vLLM's native
    `--scheduling-policy priority` heap by setting `Request.priority` in
    `add_request()`. Algorithm-level fidelity is differential-tested
    (tests/test_slai_priority_differential.py) against the real simulator
    policy. This part is considered VALIDATED at the algorithm level.
  - Decode-hold (SLAI's central mechanism -- deferring a specific
    decode-ready request's iteration for one or more steps while it
    remains fully active, never evicted): the DECISION of which requests
    to hold each step is the same differential-tested algorithm core
    (slai_priority.py) used for admission ordering, and IS validated at
    the algorithm level (including a genuine multi-step, tight-decode-
    limit differential test against the real, stateful simulator policy).
    What is NOT yet validated is the vLLM-ENGINE-SIDE MECHANISM used here
    to realize a hold: temporarily removing the held request(s) from
    `self.running` for the duration of one `schedule()` call, then
    restoring them immediately afterward, so the base class's decode loop
    simply does not consider them this step (no preemption, no KV-block
    eviction, no state loss). This technique has a precedent in vLLM's
    own scheduler (`next_decode_eligible_step`, used for PP+async cadence
    gating -- see docs/REAL_VLLM_SLAI_FIDELITY.md), which establishes
    that "skip without evict" is an existing, supported concept in this
    codebase, not a fabricated one. It has NOT been tested against a live
    vLLM engine under load (no GPU run performed in this task), and could
    in principle interact with bookkeeping this module has not audited
    (e.g. per-step stats, async-scheduling invariants, KV-connector
    metadata). REAL_VLLM_SCIENTIFIC_VALIDATION = NOT_STARTED.

No workload-specific, case-specific, or result-conditioned logic appears
anywhere in this file -- every constant is either a SLAI paper default or
a disclosed simulator-parity choice, identical regardless of which
workload or RQ6 case a server using this scheduler happens to serve.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List

from vllm.v1.core.sched.scheduler import Scheduler as VLLMDefaultScheduler

from .slai_priority import (
    DecodeCandidate,
    admission_priority_scalar,
    classify_and_order_decodes,
    compute_lst,
    offset_for_utilization,
    select_served_decodes,
)

if TYPE_CHECKING:
    from vllm.v1.request import Request


class LSSPSlaiVLLMScheduler(VLLMDefaultScheduler):
    """Experimental reproduction of the simulator's `slai_faithful` policy
    for real-vLLM RQ6 validation. NOT an official SLAI implementation, and
    NOT yet validated under live GPU execution -- see module docstring.

    Requires `--scheduling-policy priority` (this class only sets
    `Request.priority`; it relies on vLLM's own native priority queue for
    admission ordering, per docs/REAL_VLLM_SLAI_FIDELITY.md).
    """

    #: Deterministic, disclosed defaults -- identical to slai_faithful.py.
    decode_limit = 128
    step_size = 0.001

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._lst: Dict[str, float] = {}

    def add_request(self, request: "Request") -> None:
        # Admission-ordering hook: SLAI's TBT-tiered SPF, collapsed to the
        # single scalar vLLM's native priority queue expects. See
        # slai_priority.admission_priority_scalar's docstring for the
        # disclosed collapse-to-scalar approximation.
        class_id = getattr(request, "lssp_class_id", None)
        request.priority = admission_priority_scalar(class_id, request.num_prompt_tokens)
        super().add_request(request)

    def schedule(self, throttle_prefills: bool = False):
        # Decode-hold hook: compute which currently-running, decode-ready
        # requests SLAI would hold this step, and temporarily exclude them
        # from self.running so the base class's decode loop does not
        # consider them -- see module docstring's fidelity-status note on
        # why this specific mechanism is algorithm-validated but
        # engine-integration-unvalidated.
        now = self.current_step * self.step_size  # disclosed: uses step index as SLAI's "now", consistent with the simulator's own discrete-step time convention (see slai_faithful.py's "Discrete-step LST anchor" note)
        kv_util = self.get_kv_cache_usage()
        offset = offset_for_utilization(kv_util)

        decode_ready = [
            r for r in self.running
            if getattr(r, "num_computed_tokens", 0) >= getattr(r, "num_prompt_tokens", 0)
        ]
        for req in decode_ready:
            if req.request_id not in self._lst:
                class_id = getattr(req, "lssp_class_id", None)
                self._lst[req.request_id] = compute_lst(now, _tbt_lookup(class_id), offset, self.step_size)

        candidates = [
            DecodeCandidate(
                request_id=req.request_id,
                class_id=getattr(req, "lssp_class_id", None),
                lst=self._lst.get(req.request_id),
            )
            for req in decode_ready
        ]
        critical, non_critical = classify_and_order_decodes(candidates, now)
        # Conservative remaining-budget estimate for the leftover-decode
        # step (Step 4): does not attempt to replicate vLLM's own
        # multi-factor token-budget accounting (chunked prefill, spec
        # decode, encoder budget, etc.) -- disclosed approximation, see
        # docs/REAL_VLLM_SLAI_FIDELITY.md.
        remaining_budget = max(0, self.max_num_scheduled_tokens - len(critical[: self.decode_limit]))
        served_ids, held_ids = select_served_decodes(
            critical, non_critical, self.decode_limit, remaining_budget,
        )
        held_set = set(held_ids)

        held_requests: List["Request"] = [r for r in self.running if r.request_id in held_set]
        for r in held_requests:
            self.running.remove(r)
        try:
            output = super().schedule(throttle_prefills=throttle_prefills)
        finally:
            self.running.extend(held_requests)

        served_set = set(served_ids)
        for req in decode_ready:
            if req.request_id in served_set:
                class_id = getattr(req, "lssp_class_id", None)
                self._lst[req.request_id] = compute_lst(now, _tbt_lookup(class_id), offset, self.step_size)

        return output


def _tbt_lookup(class_id) -> float:
    from .slai_priority import tbt_for
    return tbt_for(class_id)
