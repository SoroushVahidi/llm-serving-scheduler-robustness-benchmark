import hashlib, json, pathlib, sys
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE/'frozen_c01'))

def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()

def canon(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def save_new(path, obj):
    path = pathlib.Path(path)
    with path.open('x') as f:
        json.dump(obj, f, sort_keys=True, indent=2, allow_nan=False)
        f.write('\n')

def verify_policy(requests, config, policy, events, terminal):
    from policies import Config, View, plan
    cfg = Config(**config)
    state = {r['id']: dict(p=0,d=0,res=False,anchor=None,done=False) for r in requests}
    admission = {}
    def check(t, spans):
        views = tuple(View(r['id'], r['id'], r['arrival'], r['prompt'],
            state[r['id']]['p'], state[r['id']]['d'], state[r['id']]['res'], state[r['id']]['anchor'])
            for r in requests if r['arrival'] <= t and not state[r['id']]['done'])
        if plan(policy, t, views, cfg) != spans:
            raise ValueError('original policy intent mismatch')
    for e in events:
        check(e['time'], e['intent'])
        for i,k,a,b in e['executed']:
            s=state[i]; admission.setdefault(i,e['time'])
            s['res']=True; s['p' if k=='prefill' else 'd']=b
            if k=='decode' or b==requests[i]['prompt']:
                s['anchor']=e['end']
        for i in e['completed']:
            state[i]['done']=True; state[i]['res']=False
    if terminal.get('blocked_batch'):
        check(terminal['blocked_batch']['time'],terminal['blocked_batch']['intent'])
    waits=[t-requests[i]['arrival'] for i,t in admission.items()]
    return dict(n_admitted=len(waits),mean_wait_to_admission=sum(waits)/len(waits) if waits else None)
