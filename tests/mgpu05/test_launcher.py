import importlib.util
from pathlib import Path
import pytest


def launcher():
    p=Path(__file__).parents[2]/'scripts/mgpu05/repeatability.py'
    spec=importlib.util.spec_from_file_location('mgpu05_launcher',p)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize('policy,scheduler,order',[('native_fcfs','MeasuredNativeScheduler','fcfs'),
                                                 ('slai_mgpu00_checked','MeasuredSlaiScheduler','priority')])
def test_launch_command_contract(policy,scheduler,order):
    cmd=launcher().command('/venv/bin/vllm','/pinned/model',1234,policy)
    assert '--enable-chunked-prefill' in cmd and '--no-async-scheduling' in cmd
    for flag,val in [('--max-num-batched-tokens','4096'),('--max-num-seqs','16'),('--max-model-len','512'),
                     ('--tensor-parallel-size','1'),('--data-parallel-size','1'),('--pipeline-parallel-size','1'),
                     ('--scheduling-policy',order),('--long-prefill-token-threshold','0')]:
        assert cmd[cmd.index(flag)+1]==val
    assert cmd[-1]=='robustbench.mgpu05.vllm_scheduler.'+scheduler


def test_cpu_preflight_cannot_launch_and_dirty_ref_rejected(monkeypatch):
    mod=launcher()
    monkeypatch.setattr('sys.argv',['repeatability.py','--check-only','--block','0',
                                  '--model-path','/fake','--expected-sha','wrong'])
    with pytest.raises(ValueError,match='clean tested checkout'): mod.main()


def test_unknown_policy_has_no_fallback():
    with pytest.raises(ValueError,match='no fallback'):
        launcher().command('/venv/bin/vllm','/model',1234,'not-a-policy')


@pytest.mark.parametrize('cleanup_error',[False,True])
def test_startup_failure_cleans_and_seals(tmp_path,monkeypatch,cleanup_error):
    import json
    from types import SimpleNamespace
    from robustbench.mgpu05.design import design
    from robustbench.mgpu05.evidence import verify_seal
    mod=launcher(); calls=[]
    from robustbench.mgpu06 import runtime
    monkeypatch.setattr(runtime,'PROJECT',tmp_path)
    monkeypatch.setattr(runtime,'IPC_LIMIT',1000)
    monkeypatch.setenv('MGPU06_RUNTIME_ROOT',str(tmp_path/'runtime'))
    class Diagnostics:
        def __init__(self,directory,prefix): self.directory=directory
        def start(self,argv,env):
            calls.append('start')
            (self.directory/'server.server.log').write_text('synthetic startup failure\n')
        def wait_ready(self,*args):
            calls.append('readiness')
            raise RuntimeError('synthetic readiness failure')
        def close(self):
            calls.append('cleanup')
            (self.directory/'server.exit.json').write_text(json.dumps({'synthetic':True}))
            if cleanup_error: raise RuntimeError('synthetic cleanup failure')
    monkeypatch.setattr(mod,'ServerDiagnostics',Diagnostics)
    monkeypatch.setenv('OMP_NUM_THREADS','4')
    args=SimpleNamespace(out=tmp_path,model_path=Path('/synthetic-model'),vllm_executable=Path('/fake-vllm'),
                         expected_sha='0'*40,plan=Path(__file__).parents[2]/'scripts/mgpu05/design.json')
    with pytest.raises(RuntimeError,match='synthetic'):
        mod.run_policy(args,design()['blocks'][0],'native_fcfs',{}, {})
    assert calls==['start','readiness','cleanup']
    verify_seal(tmp_path/'native_fcfs')
    failure=json.loads((tmp_path/'native_fcfs/run-end.json').read_text())['failure']
    assert failure['error']=='synthetic cleanup failure' if cleanup_error else failure['error']=='synthetic readiness failure'


@pytest.mark.parametrize('corrupt',[False,True])
def test_offline_cli_missing_vs_corrupt_evidence(tmp_path,corrupt):
    import json, os, subprocess, sys
    if corrupt: (tmp_path/'seal.json').write_text('{"files":{}}')
    root=Path(__file__).parents[2]
    result=subprocess.run([sys.executable,str(root/'scripts/mgpu05/validate.py'),str(tmp_path)],
                          capture_output=True,text=True,env=dict(os.environ,PYTHONPATH=str(root/'src')))
    assert result.returncode==1
    assert json.loads(result.stdout)['acceptance']==('FAIL' if corrupt else 'NOT_VERIFIED')
