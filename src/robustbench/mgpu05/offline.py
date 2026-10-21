"""Recompute acceptance from sealed raw files, without vLLM or a GPU."""
import json
from pathlib import Path
from robustbench.mgpu00.gpu_probe import verify_full_a100
from robustbench.mgpu02.audit import audit_events
from .assets import IndependentTokenizer, file_hash
from .evidence import read_journal, verify_seal
from .validate import read_server_events, validate
from .design import design, cohort
from .evidence import digest


def analyze(directory, *, verify=True):
    directory = Path(directory)
    if verify:
        verify_seal(directory)
    manifest = json.loads((directory/'manifest.json').read_text())
    block = manifest['block']
    if block != design()['blocks'][block['block']]:
        raise ValueError('Unreviewed execution block')
    expected = cohort(block['window'], block['region'])
    if (manifest['payloads'] != expected or digest(expected) != block['payloads_sha256']
            or manifest['payloads_sha256'] != block['payloads_sha256']):
        raise ValueError('Request stream differs from the frozen cell')
    model_path = Path(manifest['model_path'])
    for name, expected in manifest['assets']['tokenizer'].items():
        if file_hash(model_path/name) != expected:
            raise ValueError('Independent tokenizer asset mismatch')
    tokenizer = IndependentTokenizer(model_path)
    hardware = manifest['hardware']
    verify_full_a100(hardware)
    events = read_server_events(directory/'server.server.log')
    engine = [e for e in events if 'event' in e]
    all_payloads = manifest['warmup']+manifest['payloads']
    oracle = audit_events(engine, manifest['policy'], {p['request_id']:p['max_tokens'] for p in all_payloads})
    known = {p['request_id'] for p in all_payloads}
    receipts = [e for e in events if e.get('kind') == 'request_received']
    if {e['request_id'] for e in receipts} != known or len(receipts) != len(known):
        raise ValueError('Unexpected/missing engine request identity')
    engine_ids = {e['engine_id'] for e in receipts}
    admitted = [e for e in engine if e['event'] == 'admitted']
    if (len(engine_ids) != len(known) or len(admitted) != len(known)
            or {e['engine_id'] for e in admitted} != engine_ids
            or {e['request_id'] for e in admitted} != known):
        raise ValueError('Admission identity conservation failed')
    if any(set(e['token_ids']) - engine_ids for e in events if e.get('kind') == 'runner_tokens'):
        raise ValueError('Unmapped runner output identity')
    held = [e for e in engine if e['event']=='held']
    if bool(held) != (manifest['policy']=='slai_mgpu00_checked'):
        raise ValueError('Missing intended mechanism activation or unexpected SLAI hold')
    reports = {}
    for name, payloads, duration in [('warmup',manifest['warmup'],.2),
                                    ('scored',manifest['payloads'],manifest['block']['arrival_duration_s'])]:
        reports[name] = validate(payloads, read_journal(directory/(name+'.jsonl')), events, tokenizer,
                                 arrival_duration_s=duration, physical_identity=hardware)
    scored = reports['scored']
    delays = sorted(r['client_queue_s'] for r in scored['rows'] if r['client_queue_s'] is not None)
    import math
    p95 = delays[math.ceil(.95*len(delays))-1] if delays else None
    transport_delays = [r['transport_send_s']-r['dispatch_s'] for r in scored['rows']
                        if r['transport_send_s'] is not None and r['dispatch_s'] is not None]
    replay_gate = (len(delays)==len(manifest['payloads']) and max(delays)<=.02 and p95<=.01
                   and len(transport_delays)==len(delays) and max(transport_delays)<=.02)
    ready = json.loads((directory/'server.readiness.json').read_text())
    exited = json.loads((directory/'server.exit.json').read_text())
    process_gate = (ready.get('ready') is True and exited['cleanup_error'] is None
                    and exited['returncode_before_cleanup'] is None and exited['returncode'] is not None)
    accepted = replay_gate and process_gate and all(
        r['integrity']=='PASS' and r['physical_timing']=='PASS' and r['evidence_closed']=='PASS'
        and r['completed']==r['scheduled'] for r in reports.values())
    return dict(acceptance='PASS' if accepted else 'FAIL', independent_schedule=oracle,
                replay_gate=replay_gate, process_gate=process_gate, dispatch_p95_s=p95,
                mechanism_hold_events=len(held), reports=reports,
                interpretation='bounded synthetic engineering only; not ranking evidence')
