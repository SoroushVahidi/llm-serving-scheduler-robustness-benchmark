"""Real CPU-side vLLM scheduler/KV manager; synthetic runner completions only."""
from pathlib import Path
from vllm.v1.structured_output import StructuredOutputManager

import pytest
import torch
from vllm.config import (CacheConfig, DeviceConfig, ModelConfig, ParallelConfig,
                         SchedulerConfig, VllmConfig)
from vllm.v1.kv_cache_interface import FullAttentionSpec, KVCacheConfig, KVCacheGroupSpec
from vllm.v1.core.single_type_kv_cache_manager import register_all_kvcache_specs
from vllm.v1.core.kv_cache_utils import init_none_hash
from vllm.utils.hashing import sha256
from robustbench.mgpu02.vllm_scheduler import WholePrefillNativeScheduler, WholePrefillSlaiScheduler


@pytest.fixture
def scheduler_factory(tmp_path, monkeypatch):
    monkeypatch.setenv('LSSP_MGPU00_DECODE_LIMIT', '2')
    monkeypatch.setenv('HF_HUB_OFFLINE', '1')
    monkeypatch.setenv('TRANSFORMERS_OFFLINE', '1')
    # Configuration only, no weights, network, model runner, CUDA allocation or
    # forward pass. Use the pinned model's real config from the source fixture.
    model_path = Path(__file__).parent / 'qwen-config'
    init_none_hash(sha256)
    def make(slai=True, blocks=10000, slots=16, chunked=True, checked=True, budget=4096):
        model = ModelConfig(model=str(model_path), tokenizer=str(model_path),
                            skip_tokenizer_init=True, dtype='bfloat16', max_model_len=512,
                            enforce_eager=True)
        config = VllmConfig(model_config=model,
            scheduler_config=SchedulerConfig(max_model_len=512, is_encoder_decoder=False,
                max_num_seqs=slots, max_num_batched_tokens=budget,
                enable_chunked_prefill=chunked, async_scheduling=False,
                policy='priority' if slai else 'fcfs', watermark=0.0),
            cache_config=CacheConfig(block_size=16, enable_prefix_caching=False),
            parallel_config=ParallelConfig(), device_config=DeviceConfig(device='cpu'))
        config.cache_config.num_gpu_blocks = blocks
        kv = KVCacheConfig(num_blocks=blocks, kv_cache_tensors=[], kv_cache_groups=[
            KVCacheGroupSpec(['layer'], FullAttentionSpec(block_size=16, num_kv_heads=1,
                                                        head_size=1, dtype=torch.float32))])
        register_all_kvcache_specs(config)
        cls = WholePrefillSlaiScheduler if slai else WholePrefillNativeScheduler
        if not checked:
            from vllm.v1.core.sched.scheduler import Scheduler
            cls = Scheduler
        events = []
        class CapturingScheduler(cls):
            def event(self, kind, **fields):
                events.append(dict(event=kind, **fields))
        obj = CapturingScheduler(vllm_config=config, kv_cache_config=kv,
                  structured_output_manager=StructuredOutputManager(config), block_size=16)
        obj.test_events = events
        obj.test_time = 10.
        obj.mgpu_clock = lambda: obj.test_time
        return obj
    return make
