"""SLAI decision core with measured time and explicit supported-domain checks.

The tier/LST/critical-prefill-noncritical order follows the repository's pinned
SLAI algorithm. Native KV management is checked at the adapter boundary. Partial
prefill, KV-induced preemption, async scheduling and distributed execution are
NOT silently approximated: unsupported cases fail the engineering gate.
"""
from dataclasses import dataclass
import math

from .metadata import TBT, RequestMetadata


class UnsupportedSemantics(RuntimeError):
    pass


@dataclass(frozen=True)
class Candidate:
    engine_id: str
    metadata: RequestMetadata
    prompt_tokens: int


class SlaiCore:
    def __init__(self, decode_limit):
        if type(decode_limit) is not int or decode_limit < 1:
            raise ValueError("Explicit positive decode limit required")
        self.decode_limit = decode_limit
        self.lst = {}
        self.total_batch_s = 0.
        self.batches = 0

    @property
    def mean_batch_s(self):
        if not self.batches:
            raise UnsupportedSemantics("Decode deadline needs a measured completed prefill/batch")
        return self.total_batch_s / self.batches

    def batch_completed(self, *, start_s, end_s, progressed, kv_utilization):
        duration = end_s - start_s
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("Invalid measured batch duration")
        # An invalid observation must not select a memory-pressure branch or
        # partially mutate the measured batch history used by future LSTs.
        if (type(kv_utilization) not in (int, float)
                or not math.isfinite(kv_utilization) or not 0 <= kv_utilization <= 1):
            raise ValueError("Invalid measured KV utilization; expected a finite fraction in [0, 1]")
        self.total_batch_s += duration
        self.batches += 1
        offset = 5 if kv_utilization < .96 else 10
        for req in progressed:
            self.lst[req.engine_id] = end_s + TBT[req.metadata.class_id] - offset * self.mean_batch_s

    def plan(self, *, now_s, decoding, waiting, token_budget, active_count, max_active):
        if not math.isfinite(now_s) or token_budget < 1:
            raise ValueError("Invalid scheduling time/budget")
        if any(r.engine_id not in self.lst for r in decoding):
            raise UnsupportedSemantics("Missing measured prefill completion/LST")
        ordered = sorted(decoding, key=lambda r: (self.lst[r.engine_id], r.metadata.ordinal))
        critical = [r for r in ordered if now_s >= self.lst[r.engine_id]]
        noncritical = [r for r in ordered if now_s < self.lst[r.engine_id]]
        if min(len(critical), self.decode_limit) > token_budget:
            raise UnsupportedSemantics("Critical decode budget exceeds supported token budget")
        selected = critical[:self.decode_limit]
        budget = token_budget - len(selected)
        admitted = []
        for req in sorted(waiting, key=lambda r: r.metadata.admission_key(r.prompt_tokens)):
            if active_count + len(admitted) >= max_active or budget <= 0:
                break
            if req.prompt_tokens > budget:
                raise UnsupportedSemantics("Faithful partial-prefill scheduling is not implemented; refusing approximation")
            admitted.append(req)
            budget -= req.prompt_tokens
        for req in noncritical:
            if len(selected) >= self.decode_limit or budget <= 0:
                break
            selected.append(req)
            budget -= 1
        scheduled = {r.engine_id: 1 for r in selected}
        scheduled.update({r.engine_id: r.prompt_tokens for r in admitted})
        held = [r for r in decoding if r.engine_id not in scheduled]
        return scheduled, admitted, held


def validate_deployment(vllm_config):
    p = vllm_config.parallel_config
    s = vllm_config.scheduler_config
    if (p.tensor_parallel_size, p.pipeline_parallel_size, p.data_parallel_size) != (1, 1, 1):
        raise UnsupportedSemantics("TP/PP/DP semantics not validated; MGPU00 permits 1x1x1 only")
    if s.async_scheduling or s.enable_chunked_prefill:
        raise UnsupportedSemantics("Async/partial-prefill semantics not validated")
    if vllm_config.speculative_config or vllm_config.kv_transfer_config or vllm_config.lora_config:
        raise UnsupportedSemantics("Speculation, KV transfer and LoRA unsupported by this validation adapter")
    if vllm_config.cache_config.enable_prefix_caching:
        raise UnsupportedSemantics("Prefix caching must be disabled for the checked token-plan contract")
