"""CM-0.1 scheduling adaptations. Only immutable, explicitly online views."""
from dataclasses import dataclass

POLICIES = ('whole_fcfs_c01', 'chunked_fcfs_c01', 'decode_first_c01', 'slo_gated_c01')
HISTORICAL = dict(zip(POLICIES, ('vllm_faithful', 'vllm_chunked_prefill_faithful',
                              'sarathi_faithful', 'slai_faithful')))

@dataclass(frozen=True)
class Config:
    budget: int = 32768
    max_sequences: int = 64
    context: int = 32768
    kv_capacity: int = 131072
    block: int = 16
    dt: float = 0.001
    drain: float = 50.0

@dataclass(frozen=True)
class View:
    rid: int
    ordinal: int
    arrival: float
    prompt: int
    prefilled: int
    generated: int
    resident: bool
    anchor: float | None


def plan(policy: str, now: float, views: tuple[View, ...], cfg: Config):
    if policy not in POLICIES:
        raise ValueError('unknown adaptation')
    resident = sorted((v for v in views if v.resident), key=lambda v: v.ordinal)
    waiting = sorted((v for v in views if not v.resident), key=lambda v: v.ordinal)
    decodes = [v for v in resident if v.prefilled == v.prompt]
    prefills = [v for v in resident if v.prefilled < v.prompt]
    slots = min(cfg.max_sequences, cfg.kv_capacity // cfg.context) - len(resident)
    if policy == 'whole_fcfs_c01':
        # All in-domain whole prompts fit an otherwise empty batch.
        order = waiting if slots and waiting and waiting[0].prompt <= cfg.budget else decodes
    elif policy == 'chunked_fcfs_c01':
        order = resident + waiting
    elif policy == 'decode_first_c01':
        order = decodes + prefills + waiting
    else:
        critical = [v for v in decodes if v.anchor is not None and now - v.anchor >= .495]
        residual = [v for v in decodes if v not in critical]
        order = critical + prefills + waiting + residual
    budget = cfg.budget
    spans = []
    for v in order:
        if budget <= 0:
            break
        if not v.resident and slots <= 0:
            continue
        if v.prefilled < v.prompt:
            n = v.prompt - v.prefilled
            if policy == 'whole_fcfs_c01':
                if n > budget:
                    break  # no hidden bypass of FCFS head
            else:
                n = min(n, 512, budget)
            spans.append([v.rid, 'prefill', v.prefilled, v.prefilled + n])
        else:
            n = 1
            spans.append([v.rid, 'decode', v.generated, v.generated + 1])
        budget -= n
        if not v.resident:
            slots -= 1
    return spans
