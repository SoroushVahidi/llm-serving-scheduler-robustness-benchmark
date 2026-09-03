"""Pure, framework-independent port of the SLAI/RAD scheduler's own
algorithmic contribution -- last-schedulable-time (LST) computation,
critical/non-critical decode classification, and TBT-tiered admission
ordering -- extracted from
`src/robustbench/policies/slai_faithful.py::SlaiFaithfulPolicy` (the
project's faithful simulator reimplementation, itself pinned to
github.com/agrimUT/SLAI @ 5098a7a).

Deliberately scoped to ONLY this algorithmic core, not KV-cache/block-space
admission feasibility: per `slai_faithful.py`'s own module docstring,
"SLAI's memory model IS Sarathi-Serve's, unchanged" -- block-space
management is not part of SLAI's algorithmic novelty, and on real vLLM
hardware it is vLLM's own KV-cache manager's job, not this module's.

Every function here is pure (no I/O, no hidden state, no randomness) so it
can be:
  1. differential-tested against the real simulator policy
     (tests/test_slai_priority_differential.py), and
  2. reused unchanged by both a future vLLM scheduler adapter and any
     other future faithful-reimplementation host.

This module makes NO decision based on which workload (Azure/BurstGPT/
Bailian) or which RQ6 case is running -- it is pure algorithm, identical
regardless of caller.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Identical defaults to slai_faithful.py -- kept in sync deliberately, not
# re-derived, so a future change to the simulator's defaults is easy to
# notice as a diff here too.
DEFAULT_TBT_BY_CLASS: Dict[str, float] = {
    "tight": 0.1, "interactive": 0.1, "critical": 0.1,
    "medium": 0.3, "standard": 0.3,
    "loose": 0.5, "batch": 0.5,
}
DEFAULT_TBT_FALLBACK = 0.5
DEFAULT_BELOW_MEMORY_LIMIT_OFFSET = 5
DEFAULT_ABOVE_MEMORY_LIMIT_OFFSET = 10
DEFAULT_MEMORY_LIMIT_FRACTION = 0.96


def tbt_for(class_id: Optional[str], tbt_by_class: Dict[str, float] = None, default_tbt: float = DEFAULT_TBT_FALLBACK) -> float:
    """Mirrors SlaiFaithfulPolicy._tbt_for exactly."""
    table = tbt_by_class if tbt_by_class is not None else DEFAULT_TBT_BY_CLASS
    return table.get(class_id, default_tbt)


def offset_for_utilization(
    kv_utilization: float,
    fixed_offset: bool = False,
    below_memory_limit_offset: int = DEFAULT_BELOW_MEMORY_LIMIT_OFFSET,
    above_memory_limit_offset: int = DEFAULT_ABOVE_MEMORY_LIMIT_OFFSET,
    memory_limit_fraction: float = DEFAULT_MEMORY_LIMIT_FRACTION,
) -> float:
    """Mirrors SlaiFaithfulPolicy._offset exactly (Eq. 8's Theta term)."""
    if fixed_offset:
        return below_memory_limit_offset
    if kv_utilization < memory_limit_fraction:
        return below_memory_limit_offset
    return above_memory_limit_offset


def compute_lst(now: float, tbt: float, offset: float, step_size: float) -> float:
    """Last-schedulable time (Eq. 8), mirrors the two identical assignment
    sites in slai_faithful.py::_run_gpu_schedule exactly:
    `now + tbt_for(req) - offset * step_size`."""
    return now + tbt - offset * step_size


def is_critical(now: float, lst: float) -> bool:
    """Mirrors `now >= _lst_key(req)` exactly."""
    return now >= lst


@dataclass(frozen=True)
class DecodeCandidate:
    request_id: int
    class_id: Optional[str]
    lst: Optional[float]  # None if no LST assigned yet this call


def classify_and_order_decodes(
    candidates: List[DecodeCandidate], now: float,
) -> Tuple[List[DecodeCandidate], List[DecodeCandidate]]:
    """Mirrors slai_faithful.py's Step 1 exactly: sort all decode-ready
    requests by (lst, request_id) ascending, then split into
    (critical, non_critical) by `now >= lst`. `lst=None` sorts as
    `-inf` (mirrors `_lst_key`'s `float("-inf")` default), i.e. always
    critical -- a request with no LST recorded yet is never held.
    """
    def _key(c: DecodeCandidate):
        return (c.lst if c.lst is not None else float("-inf"), c.request_id)

    ordered = sorted(candidates, key=_key)
    critical = [c for c in ordered if is_critical(now, c.lst if c.lst is not None else float("-inf"))]
    non_critical = [c for c in ordered if not is_critical(now, c.lst if c.lst is not None else float("-inf"))]
    return critical, non_critical


def select_served_decodes(
    critical: List[DecodeCandidate],
    non_critical: List[DecodeCandidate],
    decode_limit: int,
    remaining_token_budget_after_prefill_and_critical: int,
) -> Tuple[List[int], List[int]]:
    """Mirrors slai_faithful.py's Step 2 (serve all critical, up to
    decode_limit) and Step 4 (leftover budget/slots -> extra non-critical
    decodes, in LST order) exactly. Returns (served_request_ids,
    held_request_ids).

    `remaining_token_budget_after_prefill_and_critical` must already
    account for `token_budget - num_batched_tokens` AFTER critical decodes
    and prefill chunks are counted, per the reference's exact ordering
    (critical decodes are counted into `num_batched_tokens` before prefill
    is scheduled, but the budget check for EXTRA non-critical decodes
    happens after both -- see slai_faithful.py Step 3/4 ordering); callers
    must replicate that ordering, this function only performs the final
    non-critical admission arithmetic.
    """
    served = [c.request_id for c in critical[:decode_limit]]
    remaining_decode_slots = decode_limit - len(served)
    remaining_budget = remaining_token_budget_after_prefill_and_critical
    for c in non_critical:
        if remaining_budget <= 0 or remaining_decode_slots <= 0:
            break
        served.append(c.request_id)
        remaining_budget -= 1
        remaining_decode_slots -= 1
    served_set = set(served)
    held = [c.request_id for c in (critical + non_critical) if c.request_id not in served_set]
    return served, held


def admission_sort_key(class_id: Optional[str], prompt_tokens: int, request_id: int, tbt_by_class: Dict[str, float] = None, default_tbt: float = DEFAULT_TBT_FALLBACK, fcfs: bool = False, user_priority: bool = True) -> Tuple:
    """Mirrors slai_faithful.py's waiting-queue admission sort exactly:
    FCFS -> (prompt_tokens, request_id); TBT-tiered SPF (default) ->
    (tbt(req), prompt_tokens, request_id)."""
    if fcfs:
        return (prompt_tokens, request_id)
    if not user_priority:
        return (prompt_tokens, request_id)
    return (tbt_for(class_id, tbt_by_class, default_tbt), prompt_tokens, request_id)


def admission_priority_scalar(class_id: Optional[str], prompt_tokens: int, tbt_by_class: Dict[str, float] = None, default_tbt: float = DEFAULT_TBT_FALLBACK, prompt_tokens_scale: float = 1e-6) -> float:
    """Collapses admission_sort_key's (tbt, prompt_tokens) tuple into a
    single scalar for vLLM's native `--scheduling-policy priority` queue,
    which orders by a single float `Request.priority` (ascending) plus
    arrival-time tiebreak, not a full composite tuple key.

    APPROXIMATION, disclosed: `tbt * 1.0 + prompt_tokens * prompt_tokens_scale`.
    Correct as long as no two requests' TBT tiers differ by less than
    `prompt_tokens_scale * max_prompt_tokens` -- true for this project's
    TBT tiers (0.1/0.3/0.5, i.e. 0.2 apart) and any realistic prompt-token
    count (prompt_tokens_scale=1e-6 tolerates prompt lengths up to
    200,000 tokens before two tiers could collide); documented as a
    known, bounded fidelity limitation, not silently assumed exact.
    """
    tbt = tbt_for(class_id, tbt_by_class, default_tbt)
    return tbt + prompt_tokens * prompt_tokens_scale
