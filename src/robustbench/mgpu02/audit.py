"""Offline invariant audit, independent of the SLAI core and engine adapter.

In the proven N*P domain ALL available admissions fit with ANY permitted decode
subset, so reference decisions reduce to ordered capacity/decode prefixes. This
closed-form specification does not reproduce the implementation's budget loops.
"""
from .contract import CONTRACT, MAX_PROMPT_TOKENS


def audit_events(events, policy, request_outputs):
    contracts = [e for e in events if e['event'] == 'contract_verified']
    if len(contracts) != 1 or contracts[0]['contract'] != CONTRACT:
        raise ValueError('Missing or ambiguous MGPU02 contract')
    if any(e['event'] == 'semantic_mismatch' for e in events):
        raise ValueError('Semantic mismatch in event log')
    if policy not in ('native_fcfs', 'slai_mgpu00_checked'):
        raise ValueError('Unknown audit policy')
    maps = {}
    for kind in ('decision_input', 'whole_prefill_verified', 'execution_verified'):
        rows = [e for e in events if e['event'] == kind]
        maps[kind] = {e['step']: e for e in rows}
        if len(maps[kind]) != len(rows):
            raise ValueError('Duplicate scheduling step')
    inputs, plans, completed = (maps[k] for k in maps)
    if not inputs or inputs.keys() != plans.keys():
        raise ValueError('Missing input/plan evidence')
    nonempty = {step for step, plan in plans.items() if plan['tokens']}
    if nonempty != completed.keys():
        raise ValueError('Scheduled decisions lack matching execution evidence')
    observed_samples, observed_compute = {}, {}
    names = {}
    tbt = {'tight': .1, 'interactive': .1, 'critical': .1,
           'medium': .3, 'standard': .3, 'loose': .5, 'batch': .5}
    for step, state in inputs.items():
        running, waiting = state['running'], state['waiting']
        if state['token_budget'] < state['max_active'] * MAX_PROMPT_TOKENS:
            raise ValueError('Whole-prefill bound absent from recorded configuration')
        if len(running) > state['max_active']:
            raise ValueError('Active capacity exceeded')
        for r in running + waiting:
            if not 1 <= r['prompt_tokens'] <= MAX_PROMPT_TOKENS:
                raise ValueError('Prompt outside declared bound')
            names[r['engine_id']] = (r['request_id'], r['prompt_tokens'])
        if policy == 'slai_mgpu00_checked':
            running = sorted(running, key=lambda r: (r['lst_s'], r['ordinal']))[:state['decode_limit']]
            waiting = sorted(waiting, key=lambda r: (tbt[r['class_id']], r['prompt_tokens'], r['ordinal']))
        waiting = waiting[:state['max_active'] - len(state['running'])]
        expected = {r['engine_id']: 1 for r in running}
        expected.update({r['engine_id']: r['prompt_tokens'] for r in waiting})
        if plans[step]['tokens'] != expected:
            raise ValueError('Independent reference decision differs from native allocation')
        if expected:
            e = completed[step]
            if e['tokens'] != expected or e['sampled_tokens'] != {rid: 1 for rid in expected}:
                raise ValueError('Executed progress differs from independently checked decision')
            for rid, tokens in expected.items():
                observed_samples[rid] = observed_samples.get(rid, 0) + 1
                observed_compute[rid] = observed_compute.get(rid, 0) + tokens
    for name, output in request_outputs.items():
        matches = [rid for rid, (request_id, _) in names.items() if request_id == name]
        if len(matches) != 1:
            raise ValueError('Missing/ambiguous request execution identity')
        rid = matches[0]
        if (observed_samples.get(rid) != output
                or observed_compute.get(rid) != names[rid][1] + output - 1):
            raise ValueError('Request token totals do not match actual execution evidence')
    return dict(contract=CONTRACT, independently_verified_steps=len(inputs),
                execution_verified_steps=len(nonempty), request_totals_verified=len(request_outputs))
