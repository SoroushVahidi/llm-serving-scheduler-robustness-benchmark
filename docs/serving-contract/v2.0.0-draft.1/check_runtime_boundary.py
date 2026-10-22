"""CPU-only review probe; no model, CUDA context or contract implementation."""
import importlib.util
import json
import os
import tempfile
from pathlib import Path

os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
import pytest
import torch
from robustbench.mgpu00.metadata import RequestMetadata
from robustbench.mgpu00.slai import Candidate, SlaiCore
from vllm.v1.core.block_pool import BlockPool

root = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('review_fixture', root/'tests/mgpu02/conftest.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
rows = []
with tempfile.TemporaryDirectory(prefix='lssp-contract-cpu-') as tmp, pytest.MonkeyPatch.context() as patch:
    factory = module.scheduler_factory.__wrapped__(Path(tmp), patch)
    for blocks in (1, 9, 17):
        scheduler = factory(blocks=blocks)
        usage = scheduler.get_kv_cache_usage()
        assert type(usage) in (int, float)
        core = SlaiCore(2)
        c = Candidate('r', RequestMetadata('r', 0, 'tight', 0., 30., 1.), 1)
        core.batch_completed(start_s=1., end_s=1.002, progressed=[c], kv_utilization=usage)
        rows.append({'blocks': blocks, 'boundary': 'scheduler.get_kv_cache_usage',
                     'value': usage, 'type': type(usage).__name__, 'accepted': True})
    pool = BlockPool(num_gpu_blocks=17, enable_caching=False, hash_block_size=16)
    allocated = pool.get_new_blocks(8)
    usage = pool.get_usage()
    assert type(usage) is float and usage == .5
    core.batch_completed(start_s=2., end_s=2.002, progressed=[c], kv_utilization=usage)
    rows.append({'blocks':17, 'boundary':'allocated_block_pool.get_usage',
                 'value':usage, 'type':type(usage).__name__, 'accepted':True})
    pool.free_blocks(allocated)
assert not torch.cuda.is_initialized()
print(json.dumps({'status':'PASS_CPU_ONLY', 'observations':rows,
                  'cuda_initialized':torch.cuda.is_initialized(),
                  'scope':'Real native scheduler and block-pool objects, no GPU/runtime inference'}, indent=2))
