"""Policy-blind deterministic model-sensitivity scenario (seconds)."""
import math
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class Timing:
    mode: str = 'fixed'
    overhead_s: float = 0.0005
    prefill_s_per_token: float = 0.0005 / 512
    decode_s_per_token: float = 0.0005 / 8

    def __post_init__(self):
        if self.mode not in ('fixed', 'composition-v1'):
            raise ValueError('unknown timing mode')
        if not all(math.isfinite(x) and x > 0 for x in
                   (self.overhead_s, self.prefill_s_per_token, self.decode_s_per_token)):
            raise ValueError('timing parameters must be positive and finite')

    def duration(self, spans, fixed_dt):
        p, d = composition(spans)
        value = fixed_dt if self.mode == 'fixed' else (
            self.overhead_s + self.prefill_s_per_token*p + self.decode_s_per_token*d)
        if not math.isfinite(value) or value <= 0:
            raise ValueError('invalid batch duration')
        return value

    def identity(self):
        return asdict(self)


def composition(spans):
    p = d = 0
    if not spans:
        raise ValueError('empty batch')
    for _, kind, start, stop in spans:
        if type(start) is not int or type(stop) is not int or stop <= start:
            raise ValueError('invalid span')
        if kind == 'prefill':
            p += stop-start
        elif kind == 'decode' and stop == start+1:
            d += 1
        else:
            raise ValueError('invalid work kind/span')
    return p, d


def urgency(now, views, spans):
    ready = [v for v in views if v.resident and v.prefilled == v.prompt]
    critical = [v for v in ready if v.anchor is not None and now-v.anchor >= .495]
    selected = {s[0] for s in spans if s[1] == 'decode'}
    return dict(ready=len(ready), critical=len(critical),
                selected_critical=sum(v.rid in selected for v in critical),
                omitted=sum(v.rid not in selected for v in ready),
                max_age=max((now-v.anchor for v in ready if v.anchor is not None), default=0.))
