import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
from contextlib import asynccontextmanager
from types import SimpleNamespace

import httpx
import pytest

from robustbench.mgpu00.slai import UnsupportedSemantics, validate_deployment
from robustbench.mgpu00.startup import (ServerDiagnostics, require_compatible_smoke,
                                       validate_readiness_timeout)


@pytest.mark.parametrize('value', [0, -1, 1201, float('nan'), float('inf')])
def test_deadline_bounds(value):
    with pytest.raises(ValueError):
        validate_readiness_timeout(value)


@pytest.mark.parametrize('chunked', [False, True])
def test_no_unreviewed_flag_flip(chunked):
    with pytest.raises(UnsupportedSemantics):
        require_compatible_smoke(model='Qwen/Qwen2.5-0.5B-Instruct', version='0.27.1',
                                 chunked_prefill=chunked)


def test_existing_adapter_rejects_supported_upstream_alternative():
    config = SimpleNamespace(
        parallel_config=SimpleNamespace(tensor_parallel_size=1, pipeline_parallel_size=1, data_parallel_size=1),
        scheduler_config=SimpleNamespace(async_scheduling=False, enable_chunked_prefill=True))
    with pytest.raises(UnsupportedSemantics, match='partial-prefill'):
        validate_deployment(config)


def load(path):
    return json.loads(path.read_text())


@pytest.mark.parametrize('status,model,passed', [(200, 'fixture', True), (200, 'wrong', False), (503, 'fixture', False)])
def test_real_subprocess_http_readiness_and_durable_cleanup(tmp_path, status, model, passed):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    program = f'''
from http.server import BaseHTTPRequestHandler, HTTPServer
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response({status})
        self.end_headers()
        self.wfile.write(b'{{"data":[{{"id":"{model}"}}]}}')
    def log_message(self, *args): pass
print('Initializing a V1 LLM engine', flush=True)
print('Loading model from scratch...', flush=True)
HTTPServer(('127.0.0.1', {port}), Handler).serve_forever()
'''
    d = ServerDiagnostics(tmp_path, 'native')
    try:
        d.start([sys.executable, '-u', '-c', program], dict(os.environ))
        with httpx.Client(base_url=f'http://127.0.0.1:{port}', trust_env=False) as client:
            if passed:
                assert d.wait_ready(client, 'fixture', 2., .03) < 2.
            else:
                with pytest.raises(RuntimeError, match='readiness timeout'):
                    d.wait_ready(client, 'fixture', .5, .03)
    finally:
        d.close()
    ready = load(tmp_path / 'native.readiness.json')
    assert ready['ready'] is passed
    assert ready['response']['status_code'] == status
    assert model in ready['response']['body']
    exit_record = load(tmp_path / 'native.exit.json')
    assert exit_record['returncode_before_cleanup'] is None
    assert exit_record['returncode'] is not None
    assert exit_record['cleanup_error'] is None
    events = [json.loads(line) for line in (tmp_path / 'native.startup.events.jsonl').read_text().splitlines()]
    stages = [e['stage'] for e in events]
    assert 'model_loading_started' in stages and 'engine_initializing' in stages
    assert ('api_ready' in stages) is passed
    assert all(e['time_ns'] > 0 and e['monotonic_s'] > 0 for e in events)
    assert 'Loading model from scratch' in (tmp_path / 'native.server.log').read_text()


def test_early_exit_has_code_and_no_readiness_pass(tmp_path):
    d = ServerDiagnostics(tmp_path, 'crash')
    try:
        d.start([sys.executable, '-c', 'raise SystemExit(7)'], dict(os.environ))
        d.process.wait(timeout=2)
        with httpx.Client(base_url='http://127.0.0.1:1', trust_env=False) as client:
            with pytest.raises(RuntimeError, match='exited before readiness: 7'):
                d.wait_ready(client, 'fixture', 1.)
    finally:
        d.close()
    assert load(tmp_path / 'crash.exit.json')['returncode'] == 7
    assert not load(tmp_path / 'crash.readiness.json')['ready']


def test_connection_error_is_not_discarded(tmp_path):
    d = ServerDiagnostics(tmp_path, 'unreachable')
    try:
        d.start([sys.executable, '-c', 'import time; time.sleep(10)'], dict(os.environ))
        with httpx.Client(base_url='http://127.0.0.1:1', trust_env=False) as client:
            with pytest.raises(RuntimeError, match='readiness timeout'):
                d.wait_ready(client, 'fixture', .2, .02)
    finally:
        d.close()
    assert 'ConnectError' in load(tmp_path / 'unreachable.readiness.json')['error']


def test_launch_error_records_unlaunched_status(tmp_path):
    d = ServerDiagnostics(tmp_path, 'absent')
    try:
        with pytest.raises(FileNotFoundError):
            d.start([str(tmp_path / 'missing-executable')], dict(os.environ))
    finally:
        d.close()
    assert load(tmp_path / 'absent.exit.json')['launched'] is False
    assert not load(tmp_path / 'absent.readiness.json')['ready']


def test_smoke_rejects_before_gpu_probe_or_server_launch(tmp_path, monkeypatch):
    path = Path(__file__).parents[2] / 'scripts/mgpu00/smoke.py'
    spec = importlib.util.spec_from_file_location('mgpu01_smoke_test', path)
    smoke = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke)
    def forbidden(*args, **kwargs):
        pytest.fail('GPU probe or subprocess must not run for unsupported configuration')
    monkeypatch.setattr(smoke, 'collect_gpu_provenance', forbidden)
    monkeypatch.setattr(smoke.subprocess, 'Popen', forbidden)
    monkeypatch.setattr(smoke.importlib.metadata, 'version', lambda _: '0.27.1')
    monkeypatch.setattr(smoke.signal, 'signal', lambda *args: None)
    output = tmp_path / 'run'
    monkeypatch.setattr(sys, 'argv', [str(path), '--out', str(output), '--model-path', '/absent',
                                    '--vllm-executable', '/absent', '--diagnostic-minimal'])
    with pytest.raises(UnsupportedSemantics, match='does not officially support'):
        smoke.main()
    assert load(output / 'failure.json')['status'] == 'FAILED'
    assert not (output / 'summary.json').exists()
    assert not (output / 'device').exists()


def test_incomplete_warmup_is_saved_and_stops_fixture(tmp_path, monkeypatch):
    path = Path(__file__).parents[2] / 'scripts/mgpu00/smoke.py'
    spec = importlib.util.spec_from_file_location('mgpu01_warmup_test', path)
    smoke = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke)
    calls = []
    class Diagnostics:
        def __init__(self, *args): pass
        def start(self, *args): pass
        def wait_ready(self, *args): return .01
        def close(self): calls.append('closed')
    @asynccontextmanager
    async def client(*args):
        yield object()
    async def incomplete(requests, **kwargs):
        calls.append([r.metadata.request_id for r in requests])
        return {'completed': 0, 'valid_replay': False, 'rows': [{'status': 'INCOMPLETE'}]}
    monkeypatch.setattr(smoke, 'ServerDiagnostics', Diagnostics)
    monkeypatch.setattr(smoke, 'make_client', client)
    monkeypatch.setattr(smoke, 'replay', incomplete)
    provenance = {'devices': [{'model': 'A100'}], 'allocation_kind': 'FULL_GPU_VERIFIED',
                  'software': {k: 'test' for k in ['cuda', 'driver', 'torch', 'vllm', 'nccl']}}
    with pytest.raises(RuntimeError, match='Warmup failed'):
        smoke.run_round(directory=tmp_path, model_path=Path('/unused'), executable='/unused',
                        provenance=provenance, git_sha='a'*40, policy='native_fcfs', repetition=0,
                        tokenizer=SimpleNamespace(encode=lambda *a, **kw: [1, 2]), readiness_timeout_s=1.)
    assert calls == [['fixture-warmup'], 'closed']
    assert load(tmp_path / 'native_fcfs-rep0.warmup.json')['rows'][0]['status'] == 'INCOMPLETE'
    assert not (tmp_path / 'native_fcfs-rep0.validated.json').exists()
    assert not (tmp_path / 'native_fcfs-rep0.raw_replay.json').exists()
