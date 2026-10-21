#!/usr/bin/env python3
"""CPU-only cache-location probe; invoke through runtime.py with CUDA_VISIBLE_DEVICES=''."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
from robustbench.mgpu06.runtime import verify_environment, verify_sources

record = verify_environment()
pins = verify_sources(Path(__file__).resolve().parents[2])
if os.environ.get('CUDA_VISIBLE_DEVICES') != '':
    raise ValueError('CPU probe requires explicitly hidden GPUs')
print('CPU_PROBE_STAGE import torch',flush=True)
import torch
print('CPU_PROBE_STAGE import triton',flush=True)
import triton
print('CPU_PROBE_STAGE import vllm.envs',flush=True)
import vllm.envs as venv
print('CPU_PROBE_STAGE import HF/transformers',flush=True)
from huggingface_hub import constants as hf
from transformers.utils import hub
print('CPU_PROBE_STAGE import Torch cache helpers',flush=True)
from torch._inductor.runtime.cache_dir_utils import cache_dir
from triton.runtime.cache import get_cache_manager

print('CPU_PROBE_STAGE effective path and filesystem checks',flush=True)
phase = Path(record['phase_root'])
actual = {'torch_hub':torch.hub.get_dir(), 'torch_inductor':cache_dir(),
          'tempfile':tempfile.gettempdir(),
          'vllm_cache':venv.VLLM_CACHE_ROOT,'vllm_config':venv.VLLM_CONFIG_ROOT,
          'vllm_assets':venv.VLLM_ASSETS_CACHE,'vllm_rpc':venv.VLLM_RPC_BASE_PATH,
          'hf_home':hf.HF_HOME,'hf_hub':hf.HF_HUB_CACHE,'hf_assets':hf.HF_ASSETS_CACHE,
          'hf_xet':hf.HF_XET_CACHE,'hf_token':hf.HF_TOKEN_PATH,'hf_modules':hub.HF_MODULES_CACHE}
manager = get_cache_manager('mgpu06-cpu-probe')
actual['triton_write'] = manager.put('CPU-only cache probe', 'probe.txt')
for name, path in actual.items():
    if not Path(path).resolve().is_relative_to(phase):
        raise ValueError('Cache escapes private phase: '+name)
# Exercise the actual project filesystem and vLLM-length UNIX socket path.
address = str(Path(venv.VLLM_RPC_BASE_PATH)/('0'*36))
with socket.socket(socket.AF_UNIX) as sock:
    sock.bind(address)
Path(address).unlink()
child = json.loads(subprocess.check_output([sys.executable,'-B','-c',
    'import json,os,tempfile;print(json.dumps(dict(home=os.environ["HOME"],tmp=tempfile.gettempdir(),triton=os.environ["TRITON_CACHE_DIR"])))'],text=True))
assert child == dict(home=os.environ['HOME'],tmp=os.environ['TMPDIR'],triton=os.environ['TRITON_CACHE_DIR'])
assert not torch.cuda.is_initialized()
print(json.dumps(dict(status='CPU_CACHE_PROBE_PASS',actual_paths=actual,child=child,
                     gpu_initialized=False,pins=pins,runtime=record),indent=2))
