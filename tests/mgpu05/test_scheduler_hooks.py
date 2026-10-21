"""Exercise actual vLLM CPU scheduler/KV objects, synthetic runner tokens only."""
import importlib.util
import json
from pathlib import Path
import pytest


def load_file(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


@pytest.fixture
def observed_factory(tmp_path,monkeypatch):
    from robustbench.mgpu05.vllm_scheduler import MeasuredNativeScheduler, MeasuredSlaiScheduler
    path=Path(__file__).parents[1]/'mgpu02'
    support=load_file('mgpu05_cpu_factory',path/'conftest.py')
    helpers=load_file('mgpu05_cpu_helpers',path/'test_scheduler.py')
    monkeypatch.setenv('LSSP_MGPU05_SYNTHETIC','1')
    monkeypatch.setenv('LSSP_MGPU05_TIMING_PROVENANCE','synthetic_test')
    support.WholePrefillNativeScheduler=MeasuredNativeScheduler
    support.WholePrefillSlaiScheduler=MeasuredSlaiScheduler
    return support.scheduler_factory.__wrapped__(tmp_path,monkeypatch),helpers


@pytest.mark.parametrize('slai',[False,True])
def test_actual_receipt_and_sample_capture(observed_factory,capsys,slai):
    make,h=observed_factory; s=make(slai=slai)
    for i,cls in enumerate(['loose','tight','medium']): s.add_request(h.request(i,cls,output=2))
    while s.requests: h.finish(s,s.schedule())
    captured=capsys.readouterr().err
    rows=[json.loads(line.split('MGPU05_EVENT ',1)[1]) for line in captured.splitlines() if 'MGPU05_EVENT ' in line]
    assert [r['seq'] for r in rows]==list(range(len(rows)))
    assert rows[0]['provenance']=='synthetic_test'
    received=[r for r in rows if r['kind']=='request_received']
    assert {r['metadata']['lssp_class_id'] for r in received}=={'loose','tight','medium'}
    samples=[r for r in rows if r['kind']=='runner_tokens']
    assert sum(len(ids) for r in samples for ids in r['token_ids'].values())==6
    assert all(ids==[42] for r in samples for ids in r['token_ids'].values())
    assert all(r['boundary'].startswith('host_runner_output_callback') for r in samples)
    assert all(r['observed_s']<=r['time_s'] for r in samples)


@pytest.mark.parametrize('slai',[False,True])
def test_inherited_partial_and_kv_rejection(observed_factory,slai):
    from robustbench.mgpu00.slai import UnsupportedSemantics
    make,h=observed_factory; s=make(slai=slai)
    with pytest.raises(UnsupportedSemantics): s.add_request(h.request(0,prompt=257))
    s=make(slai=slai,blocks=9); s.add_request(h.request(0)); h.finish(s,s.schedule())
    with pytest.raises(UnsupportedSemantics,match='KV preemption'): s.schedule()


def test_synthetic_capture_guard(observed_factory,monkeypatch):
    make,h=observed_factory
    monkeypatch.delenv('LSSP_MGPU05_SYNTHETIC')
    with pytest.raises(ValueError,match='synthetic'): make()


def test_actual_vllm_api_accepts_token_evidence_fields():
    from vllm.entrypoints.openai.completion.protocol import CompletionRequest
    from robustbench.mgpu05.design import cohort, MODEL
    for p in cohort('boundary','burst'):
        r=CompletionRequest(**p)
        assert r.return_token_ids and not r.skip_special_tokens and r.n==1
        assert r.request_id==p['request_id'] and r.model==MODEL
