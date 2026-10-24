"""Independent CM-0.1 referee. NO engine or policy imports; reconstructs events."""
import math


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def quantile(values, p):
    if not values:
        return None
    s = sorted(values)
    x = (len(s)-1)*p
    i = int(x)
    return s[i] + (s[min(i+1, len(s)-1)]-s[i])*(x-i)


def validate(requests, config, events, terminal):
    require(len(requests) == len({r['id'] for r in requests}), 'duplicate input identity')
    require([r['id'] for r in requests] == list(range(len(requests))), 'input ID order')
    p = {r['id']: r for r in requests}
    # Separate independent state, not engine snapshots.
    progress = {i: [0, 0] for i in p}
    residents, done = set(), {}
    first, last, anchors = {}, {}, {}
    clock = min(r['arrival'] for r in requests)
    horizon = max(r['arrival'] for r in requests) + config['drain']
    batches = prefill_work = decode_work = max_reserved = max_used = 0
    for e in events:
        require(set(e) == {'time','end','intent','executed','reserved','used','completed'}, 'event schema')
        t, end = e['time'], e['end']
        require(math.isfinite(t) and math.isfinite(end), 'nonfinite time')
        available = [i for i in p if p[i]['arrival'] <= clock and i not in done]
        if available:
            require(t == clock, 'silent gap while work available')
        else:
            future = [r['arrival'] for r in requests if r['arrival'] > clock]
            require(bool(future) and t == min(future), 'invalid idle advance')
        require(abs((end-t)-config['dt']) < 1e-9 and end <= horizon, 'batch duration/horizon')
        require(e['intent'] == e['executed'] and bool(e['intent']), 'intent/execution mismatch')
        seen, work = set(), 0
        for span in e['executed']:
            require(isinstance(span, list) and len(span) == 4, 'span schema')
            i, kind, start, stop = span
            require(i in p and i not in seen and i not in done and p[i]['arrival'] <= t, 'identity/eligibility')
            require(type(start) is int and type(stop) is int and stop > start, 'integer span')
            seen.add(i)
            work += stop-start
            r = p[i]
            before_prompt, before_output = progress[i]
            if kind == 'prefill':
                require(start == before_prompt and stop <= r['prompt'] and before_output == 0, 'prefill progress')
                progress[i][0] = stop
                prefill_work += stop-start
                if stop == r['prompt']:
                    anchors[i] = end
            else:
                require(kind == 'decode' and before_prompt == r['prompt'] and i in residents,
                        'decode before acknowledged prefill')
                require(start == before_output and stop == start+1 and stop <= r['output'], 'decode progress')
                progress[i][1] = stop
                decode_work += 1
                first.setdefault(i, end)
                last[i] = end
                anchors[i] = end
            residents.add(i)
        require(work <= config['budget'], 'budget enforcement')
        reserved = len(residents)*config['context']
        used = sum(((sum(progress[i])+config['block']-1)//config['block'])*config['block'] for i in residents)
        require(len(residents) <= config['max_sequences'] and reserved <= config['kv_capacity'], 'resource enforcement')
        require(all(sum(progress[i]) <= config['context'] for i in residents), 'per-request context')
        require(used <= reserved and e['reserved'] == reserved and e['used'] == used, 'KV ledger')
        expected_done = sorted(i for i in residents if progress[i][1] == p[i]['output'])
        require(e['completed'] == expected_done, 'completion identity/accounting')
        for i in expected_done:
            done[i] = end
            residents.remove(i)
        max_reserved, max_used = max(max_reserved, reserved), max(max_used, used)
        batches += 1
        clock = end
    unfinished = len(done) != len(p)
    require(not unfinished or clock + config['dt'] > horizon, 'premature terminal record')
    expected_end = horizon if unfinished else clock
    require(terminal['observed_end'] == expected_end and terminal['batches'] == batches and
            terminal['administrative_horizon'] == horizon and terminal['unfinished'] == unfinished, 'terminal accounting')
    rows = terminal['requests']
    require(len(rows) == len(p) and [r['id'] for r in rows] == list(p), 'terminal identity')
    for s in rows:
        i = s['id']
        require(s == dict(id=i, prefilled=progress[i][0], generated=progress[i][1],
                          resident=i in residents, anchor=anchors.get(i), first=first.get(i),
                          completion=done.get(i)), 'terminal request mismatch')
    duration = expected_end - min(r['arrival'] for r in requests)
    latencies = [done[i]-p[i]['arrival'] for i in done]
    # Conditional latency/TTFT/TPOT populations are all completed requests;
    # first-output times for incomplete requests remain in terminal raw data.
    ttft = [first[i]-p[i]['arrival'] for i in done]
    tpot = [(done[i]-first[i])/(p[i]['output']-1) for i in done if p[i]['output'] > 1]
    metrics = dict(num_total=len(p), num_completed=len(done), num_unfinished=len(p)-len(done),
                   completion_fraction=len(done)/len(p), observed_seconds=duration,
                   request_throughput=len(done)/duration, token_throughput=sum(p[i]['output'] for i in done)/duration,
                   emitted_token_throughput=decode_work/duration,
                   arrival_normalized_weighted_goodput=sum(p[i]['priority'] for i in done if done[i] <= p[i]['deadline'])/sum(r['priority'] for r in requests),
                   busy_device_seconds=batches*config['dt'], prefill_work=prefill_work,
                   decode_work=decode_work, peak_reserved_kv=max_reserved, peak_used_kv=max_used)
    for name, values in [('latency',latencies),('ttft',ttft),('tpot',tpot)]:
        metrics['n_'+name] = len(values)
        metrics['mean_'+name] = sum(values)/len(values) if values else None
        metrics['p95_'+name] = quantile(values,.95)
    return metrics
