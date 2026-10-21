"""Create private, fresh runtime directories before importing serving libraries."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import stat
import sys

PROJECT = Path('/project/ikoutis/sv96')
IPC_LIMIT = 60  # Leave room for vLLM's UUID and AF_UNIX's 107-byte path limit.
PHASES = {'bootstrap':'b','native_fcfs':'n','slai_mgpu00_checked':'s'}
DIRECTORIES = {
    'TRITON_CACHE_DIR':'triton/cache', 'TRITON_HOME':'triton/home',
    'TRITON_DUMP_DIR':'triton/dump', 'TRITON_OVERRIDE_DIR':'triton/override',
    'VLLM_CACHE_ROOT':'vllm/cache', 'VLLM_CONFIG_ROOT':'vllm/config',
    'VLLM_ASSETS_CACHE':'vllm/assets', 'VLLM_RPC_BASE_PATH':'ipc',
    'XDG_CACHE_HOME':'xdg/cache', 'XDG_CONFIG_HOME':'xdg/config',
    'XDG_DATA_HOME':'xdg/data', 'XDG_STATE_HOME':'xdg/state', 'XDG_RUNTIME_DIR':'xdg/run',
    'TORCHINDUCTOR_CACHE_DIR':'torch/inductor', 'TORCH_HOME':'torch/home',
    'TORCH_EXTENSIONS_DIR':'torch/extensions', 'CUDA_CACHE_PATH':'cuda/compute',
    'TMPDIR':'tmp', 'TMP':'tmp', 'TEMP':'tmp',
    'HF_HOME':'hf', 'HF_HUB_CACHE':'hf/hub', 'HF_ASSETS_CACHE':'hf/assets',
    'HUGGINGFACE_HUB_CACHE':'hf/hub', 'HUGGINGFACE_ASSETS_CACHE':'hf/assets',
    'HF_XET_CACHE':'hf/xet', 'HF_MODULES_CACHE':'hf/modules',
    'FLASHINFER_WORKSPACE_BASE':'flashinfer', 'FLASHINFER_CUBIN_DIR':'flashinfer/cubins',
    'VLLM_FLASHINFER_AUTOTUNE_CACHE_DIR':'flashinfer/autotune',
    'DG_JIT_CACHE_DIR':'deep-gemm', 'CUTE_DSL_CACHE_DIR':'cute',
    'FLASH_ATTENTION_CUTE_DSL_CACHE_DIR':'flash-attention-cute',
    'CUDA_TILE_CACHE_DIR':'cutile', 'NUMBA_CACHE_DIR':'numba',
    'PYTHONPYCACHEPREFIX':'python/pycache',
}
FLAGS = {'PYTHONDONTWRITEBYTECODE':'1', 'HF_HUB_OFFLINE':'1',
         'TRANSFORMERS_OFFLINE':'1', 'HF_HUB_DISABLE_TELEMETRY':'1',
         'VLLM_NO_USAGE_STATS':'1', 'VLLM_DO_NOT_TRACK':'1'}


def reject_home_cache_features(env):
    # CCCL tests presence, not truthiness (even "0" enables its home cache).
    for key in ('CCCL_ENABLE_CACHE', 'FLASHINFER_TRACE_APPLY', 'FLASHINFER_TRACE_APPLY_PATH'):
        if key in env:
            raise ValueError('Unsupported optional home-cache feature: '+key)


def private_directory(path):
    if path.is_symlink():
        raise ValueError('Runtime symlink rejected: '+str(path))
    path.mkdir(mode=0o700, exist_ok=True)
    info = path.stat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError('Runtime directory must be owned by this user and mode 0700: '+str(path))


def prepare(root, phase, repo, base_env=None):
    """No HOME change, no reuse of a phase, no writes to model or checkout."""
    if phase not in PHASES:
        raise ValueError('Unknown execution phase')
    root, repo = Path(root), Path(repo).resolve()
    if not root.is_absolute():
        raise ValueError('Absolute runtime root required')
    project = PROJECT.resolve()
    resolved = root.resolve()
    home = Path.home().resolve()
    env = dict(os.environ if base_env is None else base_env)
    reject_home_cache_features(env)
    if (not (root.is_relative_to(PROJECT) or root.is_relative_to(project))
            or not resolved.is_relative_to(project) or resolved == project
            or resolved.is_relative_to(repo) or resolved.is_relative_to(home)):
        raise ValueError('Runtime root must be inside project, outside HOME and checkout')
    # Reject symlinks below the project mount, including existing parents.
    canonical = project
    for part in root.relative_to(PROJECT).parts if root.is_relative_to(PROJECT) else resolved.relative_to(project).parts:
        canonical = canonical/part
        if canonical.is_symlink():
            raise ValueError('Runtime symlink rejected')
        private_directory(canonical)
    root = resolved
    phase_root = root/PHASES[phase]
    if len(str(phase_root/'ipc').encode()) > IPC_LIMIT:
        raise ValueError('Runtime root too long for vLLM IPC sockets')
    phase_root.mkdir(mode=0o700)  # exclusive: never reuse a kernel/temporary cache
    paths = {}
    for key, relative in DIRECTORIES.items():
        path = phase_root/relative
        current = phase_root
        for part in Path(relative).parts:
            current = current/part
            private_directory(current)
        # This probe only touches newly created project directories.
        with (path/'.write-probe').open('xb') as stream:
            stream.write(b'mgpu06\n'); stream.flush(); os.fsync(stream.fileno())
        (path/'.write-probe').unlink()
        paths[key] = str(path)
    paths['HF_TOKEN_PATH'] = str(phase_root/'hf/token')
    env.update(paths)
    env.update(FLAGS)
    env['MGPU06_RUNTIME_ROOT'] = str(root)
    env['MGPU06_PHASE_ROOT'] = str(phase_root)
    if env.get('HOME') != (os.environ if base_env is None else base_env).get('HOME'):
        raise AssertionError('HOME changed')
    record = dict(schema='mgpu06-runtime-v1', phase=phase, root=str(root), phase_root=str(phase_root),
                  home_unchanged=env.get('HOME'), paths=paths, flags=FLAGS,
                  numerical_or_scheduler_changes=False)
    with (phase_root/'runtime.json').open('x') as stream:
        json.dump(record,stream,indent=2); stream.flush(); os.fsync(stream.fileno())
    return env, record


def verify_environment(env=None):
    """Require the pre-import launcher; detect inherited or changed path settings."""
    env = os.environ if env is None else env
    reject_home_cache_features(env)
    phase = Path(env['MGPU06_PHASE_ROOT'])
    record = json.loads((phase/'runtime.json').read_text())
    if record['phase'] != 'bootstrap' or record['home_unchanged'] != env.get('HOME'):
        raise ValueError('Invalid bootstrap clock/cache environment')
    for key, value in {**record['paths'], **record['flags'],
                       'MGPU06_RUNTIME_ROOT':record['root']}.items():
        if env.get(key) != value:
            raise ValueError('Runtime environment changed: '+key)
    return record


def verify_sources(repo):
    pins = json.loads((Path(repo)/'scripts/mgpu06/runtime-sources.json').read_text())
    for name, version in pins['versions'].items():
        if importlib.metadata.version(name) != version:
            raise ValueError('Unreviewed runtime version: '+name)
    site = importlib.metadata.distribution('vllm').locate_file('')
    for name, expected in pins['files'].items():
        if hashlib.sha256((site/name).read_bytes()).hexdigest() != expected:
            raise ValueError('Unreviewed runtime cache source: '+name)
    return pins


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',required=True,type=Path)
    p.add_argument('--repo',required=True,type=Path)
    p.add_argument('command',nargs=argparse.REMAINDER)
    a=p.parse_args()
    command=a.command[1:] if a.command[:1]==['--'] else a.command
    if not command: p.error('Command required')
    os.umask(0o077)
    verify_sources(a.repo)
    env, record=prepare(a.root,'bootstrap',a.repo)
    print(json.dumps(record),flush=True)
    os.execvpe(command[0],command,env)


if __name__=='__main__':
    main()
