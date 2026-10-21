"""CPU-only regression tests for the pre-import runtime boundary."""
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from robustbench.mgpu06 import runtime


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, 'PROJECT', tmp_path)
    monkeypatch.setattr(runtime, 'IPC_LIMIT', 1000)
    return tmp_path


def test_private_paths_inherited_by_child_and_home_unchanged(project):
    home = os.environ['HOME']
    env, record = runtime.prepare(project/'cache', 'bootstrap', project/'repo')
    assert env['HOME'] == home
    assert runtime.verify_environment(env) == record
    for key, path in record['paths'].items():
        assert Path(path).is_relative_to(project/'cache/b')
        directory = Path(path).parent if key == 'HF_TOKEN_PATH' else Path(path)
        assert directory.stat().st_mode & 0o777 == 0o700
    child = subprocess.check_output([sys.executable, '-B', '-c',
        'import json,os,tempfile;print(json.dumps([os.environ["HOME"],tempfile.gettempdir(),os.environ["TRITON_CACHE_DIR"]]))'], env=env,text=True)
    assert json.loads(child) == [home, env['TMPDIR'],env['TRITON_CACHE_DIR']]
    assert not list((project/'cache').rglob('.write-probe'))


def test_separate_fresh_phases_and_reuse_rejected(project):
    records = [runtime.prepare(project/'cache',phase,project/'repo')[1] for phase in runtime.PHASES]
    assert len({r['phase_root'] for r in records}) == 3
    with pytest.raises(FileExistsError): runtime.prepare(project/'cache','bootstrap',project/'repo')


@pytest.mark.parametrize('key',['CCCL_ENABLE_CACHE','FLASHINFER_TRACE_APPLY','FLASHINFER_TRACE_APPLY_PATH'])
@pytest.mark.parametrize('value',['0','1',''])
def test_unsafe_optional_features_rejected_before_writes(project,key,value):
    with pytest.raises(ValueError,match='home-cache'):
        runtime.prepare(project/'cache','bootstrap',project/'repo',dict(os.environ,**{key:value}))
    assert not (project/'cache').exists()


def test_nonprivate_parent_rejected(project):
    (project/'public').mkdir(mode=0o755)
    with pytest.raises(ValueError,match='0700'):
        runtime.prepare(project/'public/job','bootstrap',project/'repo')


def test_symlink_rejected(project):
    (project/'real').mkdir(mode=0o700)
    (project/'link').symlink_to(project/'real')
    with pytest.raises(ValueError,match='symlink'):
        runtime.prepare(project/'link/job','bootstrap',project/'repo')


@pytest.mark.parametrize('location',['relative','checkout','outside','home'])
def test_forbidden_roots(project,location):
    paths={'relative':Path('relative'),'checkout':project/'repo/cache',
           'outside':project.parent/'escape','home':Path.home()/'mgpu06-must-not-create'}
    with pytest.raises(ValueError): runtime.prepare(paths[location],'bootstrap',project/'repo')


def test_ipc_length_rejected(project,monkeypatch):
    monkeypatch.setattr(runtime,'IPC_LIMIT',10)
    with pytest.raises(ValueError,match='IPC'): runtime.prepare(project/'cache','bootstrap',project/'repo')


@pytest.mark.parametrize('key',['TMPDIR','TRITON_CACHE_DIR','VLLM_CONFIG_ROOT','HOME','MGPU06_RUNTIME_ROOT'])
def test_environment_tampering_rejected(project,key):
    env,_=runtime.prepare(project/'cache','bootstrap',project/'repo')
    env[key]='/wrong'
    with pytest.raises(ValueError): runtime.verify_environment(env)


def test_no_runtime_environment_rejected():
    with pytest.raises(KeyError): runtime.verify_environment({})
