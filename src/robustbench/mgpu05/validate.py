"""Independent interpretation of raw observations; no collector/scheduler imports.

A stream event may carry several tokens. These are never assigned invented
individual observation times. Decoder round trips need not preserve BPE token IDs.
"""
import hashlib
import json
import math
import re
from collections import Counter


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def read_server_events(path):
    events = []
    for line in path.read_text().splitlines():
        for marker in ('MGPU00_EVENT ', 'MGPU05_EVENT '):
            if marker in line:
                events.append(json.loads(line.split(marker, 1)[1]))
                break
    return events


def classify_slo(*, state, first_s, last_s, completion_s, arrival_s, deadline_s,
                 observation_groups, ttft_limit, gap_limit, observed_until):
    """Three-valued client-observation SLO, not GPU-generation SLO."""
    if state in ('HTTP_ERROR', 'TIMEOUT', 'CANCELLED', 'ERROR', 'CLIENT_SATURATED',
                 'EOF_WITHOUT_DONE', 'INVALID_RESPONSE'):
        return 'FAIL'
    if completion_s is not None and completion_s > deadline_s:
        return 'FAIL'
    if first_s is not None and first_s - arrival_s > ttft_limit:
        return 'FAIL'
    if state != 'COMPLETED':
        return 'FAIL' if observed_until >= deadline_s else 'NOT_VERIFIED'
    if first_s is None or last_s is None or completion_s is None:
        return 'NOT_VERIFIED'
    if any(n != 1 for _, n in observation_groups):
        return 'NOT_VERIFIED'
    times = [t for t, _ in observation_groups]
    return 'PASS' if all(b-a <= gap_limit for a, b in zip(times, times[1:])) else 'FAIL'


def validate(payloads, client, server, tokenizer, *, arrival_duration_s,
             physical_identity=None):
    """Validate one scored cohort. tokenizer supplies independent decode/encode.

    The caller must verify file seals before trusting immutable artifacts. Input
    events are raw dictionaries, not collector PASS flags. Failure observations
    can be internally valid measurements while failing the execution gate.
    """
    violations = []

    def check(value, reason):
        if not value:
            violations.append(reason)
        return bool(value)

    def finite(t):
        return type(t) in (float, int) and math.isfinite(t)

    ids = [p['request_id'] for p in payloads]
    if not payloads or len(ids) != len(set(ids)) or not finite(arrival_duration_s) or arrival_duration_s <= 0:
        raise ValueError('Unique nonempty cohort and positive arrival interval required')
    known = set(ids)
    starts = [e for e in client if e['kind'] == 'run_start']
    if len(starts) != 1:
        raise ValueError('Exactly one client run_start required')
    start = starts[0]['data']
    epoch = start['epoch_s']
    if not finite(epoch):
        raise ValueError('Invalid replay epoch')
    check(start['requests'] == ids, 'planned request identity mismatch')
    check(start['provenance'] in ('physical_candidate', 'synthetic_test'), 'unknown timing provenance')
    check(all(e['request_id'] is None or e['request_id'] in known for e in client), 'unexpected client request identity')
    previous = -math.inf
    for event in client:
        t = event['time_s']
        if not check(finite(t) and t >= previous, 'invalid/nonmonotonic client timestamp'):
            raise ValueError('Unusable client clock')
        previous = t
    until = previous
    ends = [e for e in client if e['kind'] == 'run_end']
    closed = len(ends) == 1 and ends[0] == client[-1] and ends[0]['data'].get('state') == 'FINISHED'
    check(len(ends) <= 1, 'duplicate run_end')
    contracts = [e for e in server if e.get('kind') == 'measurement_contract']
    domain_ok = len(contracts) == 1 and contracts[0]['clock_domain'] == start['clock_domain']
    check(domain_ok, 'missing or mismatched server/client clock domain')
    observed_events = [e for e in server if 'kind' in e]
    check([e['seq'] for e in observed_events] == list(range(len(observed_events))), 'server measurement event sequence gap')
    check(all(finite(e['time_s']) for e in observed_events), 'invalid server timestamp')
    check(all(a['time_s'] <= b['time_s'] for a, b in zip(observed_events, observed_events[1:])), 'nonmonotonic server event clock')
    executions = [e for e in server if e.get('event') == 'execution_verified']
    callbacks_all = [e for e in server if e.get('kind') == 'runner_tokens']
    execution_map = {e['step']: e for e in executions}
    check(len(execution_map) == len(executions), 'duplicate execution step')
    check(len(callbacks_all) == len(execution_map), 'runner/execution step conservation')
    for e in callbacks_all:
        check(e['step'] in execution_map and
              execution_map[e['step']]['sampled_tokens'] == {k: len(v) for k,v in e['token_ids'].items()},
              'runner/execution sample count mismatch')
    physical = False
    if physical_identity and domain_ok and start['provenance'] == 'physical_candidate':
        d = physical_identity.get('devices', [{}])[0]
        physical = (physical_identity.get('allocation_kind') == 'FULL_GPU_VERIFIED'
                    and physical_identity.get('node') == start['clock_domain'].get('host')
                    and physical_identity.get('cuda_device_count') == 1
                    and d.get('cuda_memory_bytes', 0) >= 75 * 2**30
                    and d.get('mig_device') is False and d.get('mig_mode_current') == 0
                    and contracts[0].get('provenance') == 'physical_candidate')
    result = []
    allowed_states = {'STREAM_DONE', 'HTTP_ERROR', 'TIMEOUT', 'CANCELLED', 'ERROR',
                      'CLIENT_SATURATED', 'EOF_WITHOUT_DONE'}
    for p in payloads:
        rid = p['request_id']
        initial_errors = len(violations)
        events = [e for e in client if e['request_id'] == rid]
        arr = epoch + p['vllm_xargs']['lssp_arrival_s']
        deadline = epoch + p['vllm_xargs']['lssp_deadline_s']
        check(epoch <= arr < epoch + arrival_duration_s, rid + ': arrival outside cohort')
        terminals = [e for e in events if e['kind'] == 'terminal']
        check(len(terminals) <= 1, rid + ': duplicate terminal')
        terminal = terminals[0] if terminals else None
        state = terminal['data']['state'] if terminal else 'ADMINISTRATIVELY_INCOMPLETE'
        check(state in allowed_states or terminal is None, rid + ': unknown terminal state')
        check(not terminal or events[-1] == terminal, rid + ': observations after terminal')
        completion = terminal['time_s'] if terminal else None
        dispatches = [e for e in events if e['kind'] == 'dispatch']
        transports = [e for e in events if e['kind'] == 'transport_send']
        check(len(dispatches) <= 1 and len(transports) <= 1, rid + ': duplicate dispatch')
        dispatch = dispatches[0]['time_s'] if dispatches else None
        transport = transports[0]['time_s'] if transports else None
        http = [e for e in events if e['kind'] == 'http']
        check(len(http) <= 1, rid + ': duplicate HTTP response')
        if state == 'HTTP_ERROR':
            check(len(http) == 1 and http[0]['data']['status'] != 200, rid + ': unsupported HTTP failure claim')
        if state == 'TIMEOUT':
            check(dispatch is not None and completion-dispatch >= start['timeout_s'], rid + ': timeout before its deadline')
        if state == 'CLIENT_SATURATED':
            check(dispatch is None and not transports and not http, rid + ': saturated request was dispatched')
        if dispatch is not None:
            check(dispatch >= arr, rid + ': dispatch before planned arrival')
        if transport is not None:
            check(dispatch is not None and transport >= dispatch, rid + ': transport before dispatch')
        wire_ids, texts, groups, usage, finishes, prompt_reports = [], [], [], [], [], []
        done_times = []
        observed_response_ids = set()
        response_id = 'cmpl-' + rid
        for e in events:
            if e['kind'] != 'sse':
                continue
            value = e['data']['value']
            if value.strip() == '[DONE]':
                done_times.append(e['time_s'])
                continue
            check(not done_times, rid + ': data after DONE')
            try:
                data = json.loads(value)
                if not isinstance(data, dict):
                    raise ValueError('Object required')
                if 'error' in data:
                    state = 'INVALID_RESPONSE'
                    continue
                if isinstance(data.get('id'), str):
                    observed_response_ids.add(data['id'])
                check(data.get('id') == response_id, rid + ': wrong response ID')
                check(data.get('model') == p['model'], rid + ': wrong served model')
                check(data.get('object') == 'text_completion', rid + ': wrong response type')
                choices = data.get('choices')
                if not isinstance(choices, list) or len(choices) > 1:
                    raise ValueError('Expected n=1 choices')
                if data.get('usage') is not None:
                    usage.append(data['usage'])
                for choice in choices:
                    check(choice.get('index') == 0, rid + ': wrong choice index')
                    token_ids = choice.get('token_ids')
                    if not isinstance(token_ids, list) or not all(type(i) is int and i >= 0 for i in token_ids):
                        raise ValueError('Missing/invalid output token IDs')
                    if finishes and (token_ids or choice.get('text')):
                        check(False, rid + ': output after finish')
                    wire_ids.extend(token_ids)
                    if token_ids:
                        groups.append((e['time_s'], len(token_ids)))
                    if not isinstance(choice.get('text'), str):
                        raise ValueError('Missing text')
                    texts.append(choice['text'])
                    if choice.get('prompt_token_ids') is not None:
                        prompt_reports.append(choice['prompt_token_ids'])
                    if choice.get('finish_reason') is not None:
                        finishes.append(choice['finish_reason'])
            except (ValueError, KeyError, TypeError) as exc:
                check(False, rid + ': invalid SSE: ' + str(exc))
                state = 'INVALID_RESPONSE'
        complete = (state == 'STREAM_DONE' and len(done_times) == 1 and finishes == ['length']
                    and len(http) == 1 and http[0]['data']['status'] == 200)
        if state == 'STREAM_DONE':
            check(complete, rid + ': false stream completion')
        if complete:
            check(prompt_reports == [p['prompt']], rid + ': prompt token identity mismatch')
            expected_usage = {'prompt_tokens': len(p['prompt']), 'completion_tokens': len(wire_ids),
                              'total_tokens': len(p['prompt']) + len(wire_ids)}
            check(len(usage) == 1 and all(usage[0].get(k) == v for k, v in expected_usage.items()), rid + ': usage mismatch')
            check(len(wire_ids) == p['max_tokens'], rid + ': wrong output target count')
            check(transport is not None, rid + ': missing physical transport timestamp')
        receipts = [e for e in server if e.get('kind') == 'request_received' and e['request_id'] == rid]
        admissions = [e for e in server if e.get('event') == 'admitted' and e['request_id'] == rid]
        check(len(receipts) <= 1 and len(admissions) <= 1, rid + ': duplicate server identity')
        if complete or wire_ids:
            check(len(receipts) == len(admissions) == 1, rid + ': missing receipt/admission')
        engine_ids, callbacks = [], []
        received = admitted = None
        if receipts:
            receipt = receipts[0]
            engine = receipt['engine_id']
            check(re.fullmatch(re.escape(response_id) + r'-0-[0-9a-f]{8}', engine) is not None,
                  rid + ': response/engine ID binding mismatch')
            check(receipt['metadata'] == p['vllm_xargs'] and receipt['prompt_sha256'] == _hash(p['prompt'])
                  and receipt['prompt_tokens'] == len(p['prompt']) and receipt['output_limit'] == p['max_tokens'],
                  rid + ': server input metadata mismatch')
            received = receipt['observed_s']
            check(finite(received) and received <= receipt['time_s'], rid + ': invalid receipt clock')
            if admissions:
                check(admissions[0]['engine_id'] == engine, rid + ': admission engine mismatch')
                admitted = admissions[0]['monotonic_s']
            previous_step = -1
            for e in server:
                if e.get('kind') == 'runner_tokens' and engine in e['token_ids']:
                    check(e['request_ids'].get(engine) == rid, rid + ': runner identity mismatch')
                    check(e['step'] > previous_step, rid + ': duplicate/reordered runner step')
                    previous_step = e['step']
                    tids = e['token_ids'][engine]
                    check(len(tids) == 1 and all(type(i) is int and i >= 0 for i in tids), rid + ': non-autoregressive callback')
                    check(finite(e['observed_s']) and e['observed_s'] <= e['time_s'], rid + ': invalid runner clock')
                    engine_ids.extend(tids)
                    callbacks.extend([e['observed_s']] * len(tids))
            check(engine_ids == wire_ids if complete else engine_ids[:len(wire_ids)] == wire_ids,
                  rid + ': client/runner token IDs differ')
            # Every observed token must have physically reached the host callback first.
            offset = 0
            if domain_ok:
                for observed, count in groups:
                    check(all(t <= observed for t in callbacks[offset:offset+count])
                          and len(callbacks[offset:offset+count]) == count,
                          rid + ': client token precedes runner observation')
                    offset += count
                chain = [x for x in (arr, dispatch, transport, received, admitted) if x is not None]
                check(all(finite(x) for x in chain) and all(a <= b for a, b in zip(chain, chain[1:])), rid + ': arrival/admission causality')
                check(not callbacks or admitted is not None and admitted <= callbacks[0], rid + ': callback before admission')
                check(all(a <= b for a, b in zip(callbacks, callbacks[1:])), rid + ': callback clock order')
        if complete:
            check(dispatch is not None and groups and completion >= groups[-1][0], rid + ': completion causality')
        text = ''.join(texts)
        content_ok, retokenized = None, None
        if complete and wire_ids:
            try:
                decoded = tokenizer.decode(wire_ids)
                retokenized = list(tokenizer.encode(text))
                content_ok = decoded == text
                check(content_ok, rid + ': text does not decode from output IDs')
            except Exception as exc:
                check(False, rid + ': independent tokenizer failed: ' + type(exc).__name__)
        if len(violations) > initial_errors:
            state = 'INVALID_RESPONSE'
        elif complete:
            state = 'COMPLETED'
        first = groups[0][0] if groups else None
        last = groups[-1][0] if groups else None
        gap_limits = {'tight': .1, 'medium': .3, 'loose': .5}
        slo = classify_slo(state=state, first_s=first, last_s=last,
                           completion_s=completion if state == 'COMPLETED' else None,
                           arrival_s=arr, deadline_s=deadline, observation_groups=groups,
                           ttft_limit=1., gap_limit=gap_limits[p['vllm_xargs']['lssp_class_id']],
                           observed_until=until)
        result.append(dict(request_id=rid,
            response_id=next(iter(observed_response_ids)) if len(observed_response_ids)==1 else None,
            expected_response_id=response_id, observed_response_ids=sorted(observed_response_ids), state=state,
            prompt_tokens=len(p['prompt']), finish_reasons=finishes, streaming_done_count=len(done_times),
            syntactic_api_validity='PASS' if state == 'COMPLETED' else 'FAIL' if state == 'INVALID_RESPONSE' else 'NOT_VERIFIED',
            token_count_consistency='PASS' if state == 'COMPLETED' else 'NOT_VERIFIED',
            output_tokens=len(wire_ids), output_ids_sha256=_hash(wire_ids),
            text_sha256=hashlib.sha256(text.encode()).hexdigest(),
            content_transport_consistency='PASS' if content_ok else 'NOT_VERIFIED',
            semantic_answer_correctness='NOT_VERIFIED', numerical_reproducibility='NOT_VERIFIED',
            independent_retokenized_count=None if retokenized is None else len(retokenized),
            canonical_retokenization_equal=None if retokenized is None else retokenized == wire_ids,
            scheduled_arrival_s=arr, dispatch_s=dispatch, transport_send_s=transport,
            scheduler_receipt_s=received if domain_ok else None,
            admission_s=admitted if domain_ok else None,
            first_runner_observation_s=callbacks[0] if callbacks and domain_ok else None,
            last_runner_observation_s=callbacks[-1] if callbacks and domain_ok else None,
            first_client_token_group_s=first, last_client_token_group_s=last,
            terminal_observation_s=completion,
            completion_s=completion if state == 'COMPLETED' else None,
            censoring='none' if state == 'COMPLETED' else 'terminal_failure' if terminal else 'administrative',
            client_queue_s=None if dispatch is None else dispatch-arr,
            server_queue_s=admitted-received if admitted is not None and received is not None and domain_ok else None,
            http_server_receipt_s=None, gpu_generation_times=None, http_emission_times=None,
            client_ttft_s=None if first is None else first-arr,
            dispatch_to_first_token_group_s=None if first is None or dispatch is None else first-dispatch,
            e2e_s=completion-arr if state == 'COMPLETED' else None,
            client_observed_tpot_s=(last-first)/(len(wire_ids)-1) if complete and len(wire_ids)>1 and first is not None else None,
            client_inter_token_gaps_s=[b[0]-a[0] for a,b in zip(groups,groups[1:])] if groups and all(n==1 for _,n in groups) else None,
            runner_callback_gaps_s=[b-a for a,b in zip(callbacks,callbacks[1:])] if domain_ok else None,
            client_slo=slo))
    counts = Counter(r['state'] for r in result)
    slo_counts = Counter(r['client_slo'] for r in result)
    drain_interval = max(0., until-epoch)
    completed_tokens = sum(r['output_tokens'] for r in result if r['state']=='COMPLETED')
    return dict(schema='mgpu05-validation-v1', integrity='FAIL' if violations else 'PASS',
        evidence_closed='PASS' if closed else 'NOT_VERIFIED',
        violations=violations, physical_timing='PASS' if physical and not violations and closed else 'NOT_VERIFIED',
        scheduled=len(payloads), dispatched=sum(r['dispatch_s'] is not None for r in result),
        completed=counts['COMPLETED'], states=dict(counts), rows=result,
        client_slo_counts=dict(slo_counts), arrival_duration_s=arrival_duration_s,
        client_slo_goodput_lower=slo_counts['PASS']/arrival_duration_s,
        client_slo_goodput_upper=(slo_counts['PASS']+slo_counts['NOT_VERIFIED'])/arrival_duration_s,
        cohort_and_drain_s=drain_interval,
        completed_request_throughput=counts['COMPLETED']/drain_interval if drain_interval else None,
        completed_output_token_throughput=completed_tokens/drain_interval if drain_interval else None,
        goodput_scope='finite offered cohort; client observations; no GPU-generation SLO claim',
        emission_timing='NOT_VERIFIED', ranking_eligibility='NOT_VERIFIED')
