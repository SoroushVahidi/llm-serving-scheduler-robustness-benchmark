import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
from robustbench.mgpu00.metadata import RequestMetadata
from robustbench.mgpu02.audit import audit_events
from robustbench.mgpu02.startup import PinnedPrompt, verify_sources
from test_scheduler import request, finish


@pytest.mark.parametrize('slai', [False, True])
def test_offline_audit_of_real_scheduler(scheduler_factory, slai):
    s = scheduler_factory(slai=slai)
    for i, cls in enumerate(['loose', 'tight', 'medium']):
        s.add_request(request(i, cls, output=3))
    while s.requests:
        finish(s, s.schedule())
    result = audit_events(s.test_events, 'slai_mgpu00_checked' if slai else 'native_fcfs',
                         {f'r{i}': 3 for i in range(3)})
    assert result['request_totals_verified'] == 3
    assert result['execution_verified_steps'] >= 3


@pytest.mark.parametrize('mutation', ['missing_execution', 'duplicate_step', 'both_plans_corrupt',
    'missing_contract', 'wrong_total'])
def test_audit_rejects_corrupted_evidence(scheduler_factory, mutation):
    s = scheduler_factory()
    s.add_request(request(0, output=1))
    finish(s, s.schedule())
    events = copy.deepcopy(s.test_events)
    outputs = {'r0': 1}
    if mutation == 'missing_execution':
        events = [e for e in events if e['event'] != 'execution_verified']
    elif mutation == 'duplicate_step':
        events += [next(e for e in events if e['event'] == 'whole_prefill_verified')]
    elif mutation == 'both_plans_corrupt':
        for e in events:
            if e['event'] in ('whole_prefill_verified', 'execution_verified'):
                e['tokens']['r0'] = 127
    elif mutation == 'missing_contract':
        events = [e for e in events if e['event'] != 'contract_verified']
    else:
        outputs = {'r0': 2}
    with pytest.raises(ValueError):
        audit_events(events, 'slai_mgpu00_checked', outputs)


def fixture(tmp_path):
    model = tmp_path / ('a'*40)
    model.mkdir()
    (model / 'tokenizer.json').write_text('tokenizer fixture')
    data = {'revision': model.name, 'text': 'scheduler integrity fixture', 'body_token_ids': [1, 2],
            'prompt_token_ids': [1, 2]*64, 'tokenizer_files_sha256': {
                'tokenizer.json': hashlib.sha256(b'tokenizer fixture').hexdigest()}}
    manifest = tmp_path / 'prompt.json'
    manifest.write_text(json.dumps(data))
    return model, manifest


def test_pinned_prompt_hashes_and_exact_input(tmp_path):
    model, manifest = fixture(tmp_path)
    tokenizer = PinnedPrompt(model, manifest)
    assert tokenizer.encode('scheduler integrity fixture') == [1, 2]
    with pytest.raises(ValueError, match='exact engineering fixture'):
        tokenizer.encode('other text')
    (model / 'tokenizer.json').write_text('changed')
    with pytest.raises(ValueError, match='hash mismatch'):
        PinnedPrompt(model, manifest)


def test_runtime_source_pins_are_installed_upstream_bytes():
    path = Path(__file__).parents[2] / 'artifacts/mgpu02/source-inspection/upstream.json'
    assert len(verify_sources(path)) == 7


@pytest.mark.parametrize('field,value', [('request_id', 123), ('ordinal', True),
    ('class_id', []), ('arrival_s', True), ('deadline_s', '30'), ('weight', float('nan'))])
def test_metadata_types_are_strict(field, value):
    data = dict(request_id='r0', ordinal=0, class_id='tight', arrival_s=0., deadline_s=30., weight=1.)
    data[field] = value
    with pytest.raises(ValueError):
        RequestMetadata(**data)


def test_mgpu02_launch_contains_supported_flags_and_separate_identity():
    path = Path(__file__).parents[2] / 'scripts/mgpu02/smoke.py'
    spec = importlib.util.spec_from_file_location('mgpu02_smoke_test', path)
    smoke = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke)
    assert smoke.base.SPEC['chunked_prefill'] is True
    assert smoke.base.SPEC['semantic_contract'] == 'mgpu02-whole-prefill-v1'
    assert all('mgpu02' in path for path in smoke.base.SCHEDULERS.values())
    assert smoke.base.load_tokenizer is smoke.load_pinned_prompt
