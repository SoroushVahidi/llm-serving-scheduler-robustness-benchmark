"""New synthetic common execution model; historical simulator remains unchanged."""
import math
from policies import Config, View, plan


def simulate(requests, policy, cfg: Config, emit):
    if not requests or cfg.budget <= 0 or cfg.dt <= 0 or cfg.context % cfg.block:
        raise ValueError('invalid configuration/input')
    if cfg.kv_capacity < cfg.context or cfg.max_sequences < 1:
        raise ValueError('configuration cannot admit a request')
    if len({r['id'] for r in requests}) != len(requests):
        raise ValueError('duplicate identity')
    if [r['id'] for r in requests] != list(range(len(requests))):
        raise ValueError('noncanonical request identity')
    for r in requests:
        if (not math.isfinite(r['arrival']) or r['arrival'] < 0 or r['prompt'] <= 0 or
            r['output'] <= 0 or r['prompt'] + r['output'] > cfg.context or
            r['prompt'] > cfg.budget or not math.isfinite(r['deadline']) or r['priority'] <= 0):
            raise ValueError('input outside common domain')
    if [r['arrival'] for r in requests] != sorted(r['arrival'] for r in requests):
        raise ValueError('arrival ordering')
    states = [dict(prefilled=0, generated=0, resident=False, anchor=None,
                   first=None, completion=None) for _ in requests]
    t = requests[0]['arrival']
    horizon = requests[-1]['arrival'] + cfg.drain
    batches = 0
    while t + cfg.dt <= horizon:
        live = [i for i, r in enumerate(requests) if r['arrival'] <= t and states[i]['completion'] is None]
        if not live:
            future = [r['arrival'] for r in requests if r['arrival'] > t]
            if not future:
                break
            t = min(future)
            continue
        views = tuple(View(i, i, requests[i]['arrival'], requests[i]['prompt'],
                           states[i]['prefilled'], states[i]['generated'],
                           states[i]['resident'], states[i]['anchor']) for i in live)
        intent = plan(policy, t, views, cfg)
        if not intent:
            raise ValueError('scheduler made no progress with eligible work')
        if len({s[0] for s in intent}) != len(intent) or sum(s[3]-s[2] for s in intent) > cfg.budget:
            raise ValueError('duplicate or over-budget plan')
        end = t + cfg.dt
        executed = []
        for rid, kind, start, stop in intent:
            if rid not in live or stop <= start:
                raise ValueError('invalid identity/span')
            r, s = requests[rid], states[rid]
            if kind == 'prefill':
                if start != s['prefilled'] or stop > r['prompt'] or s['generated']:
                    raise ValueError('prefill continuity')
                s['prefilled'] = stop
                if stop == r['prompt']:
                    s['anchor'] = end
            elif kind == 'decode':
                if s['prefilled'] != r['prompt'] or start != s['generated'] or stop != start + 1:
                    raise ValueError('decode continuity')
                s['generated'] = stop
                s['first'] = end if s['first'] is None else s['first']
                s['anchor'] = end
            else:
                raise ValueError('unknown execution type')
            s['resident'] = True
            executed.append([rid, kind, start, stop])
        active = [i for i, s in enumerate(states) if s['resident']]
        reserved = len(active) * cfg.context
        used = sum(math.ceil((states[i]['prefilled'] + states[i]['generated']) / cfg.block) * cfg.block for i in active)
        if len(active) > cfg.max_sequences or reserved > cfg.kv_capacity or used > reserved:
            raise ValueError('KV/sequence violation')
        completed = []
        for i in active:
            if states[i]['generated'] == requests[i]['output']:
                states[i]['completion'] = end
                states[i]['resident'] = False
                completed.append(i)
            elif states[i]['generated'] > requests[i]['output']:
                raise ValueError('overgeneration')
        emit(dict(time=t, end=end, intent=intent, executed=executed,
                  reserved=reserved, used=used, completed=completed))
        batches += 1
        t = end
    unfinished = any(s['completion'] is None for s in states)
    return dict(requests=[dict(id=i, **s) for i, s in enumerate(states)],
                observed_end=horizon if unfinished else t, batches=batches,
                administrative_horizon=horizon, unfinished=unfinished)
