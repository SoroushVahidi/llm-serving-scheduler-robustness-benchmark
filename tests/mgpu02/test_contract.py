import pytest
from robustbench.mgpu02.contract import validate_config, require_smoke
from robustbench.mgpu00.slai import UnsupportedSemantics


@pytest.mark.parametrize('field', ['tensor_parallel_size', 'pipeline_parallel_size',
    'data_parallel_size', 'decode_context_parallel_size', 'prefill_context_parallel_size'])
def test_distributed_rejected(scheduler_factory, field):
    config = scheduler_factory().vllm_config
    setattr(config.parallel_config, field, 2)
    with pytest.raises(UnsupportedSemantics, match='parallelism'):
        validate_config(config)


@pytest.mark.parametrize('group,field,value', [
    ('scheduler_config', 'max_num_scheduled_tokens', 4095),
    ('scheduler_config', 'long_prefill_token_threshold', 128),
    ('scheduler_config', 'async_scheduling', True),
    ('scheduler_config', 'enable_chunked_prefill', False),
    ('cache_config', 'enable_prefix_caching', True),
    ('scheduler_config', 'is_multimodal_model', True)])
def test_unsupported_config_rejected(scheduler_factory, group, field, value):
    config = scheduler_factory().vllm_config
    setattr(getattr(config, group), field, value)
    with pytest.raises(UnsupportedSemantics):
        validate_config(config)


@pytest.mark.parametrize('field', ['speculative_config', 'kv_transfer_config', 'ec_transfer_config', 'lora_config'])
def test_unsupported_execution_features_rejected(scheduler_factory, field):
    config = scheduler_factory().vllm_config
    setattr(config, field, object())
    with pytest.raises(UnsupportedSemantics):
        validate_config(config)


def test_only_reviewed_smoke_configuration_passes():
    assert require_smoke(model='Qwen/Qwen2.5-0.5B-Instruct', version='0.27.1', chunked_prefill=True)
    with pytest.raises(UnsupportedSemantics):
        require_smoke(model='Qwen/Qwen2.5-0.5B-Instruct', version='0.27.1', chunked_prefill=False)


@pytest.mark.parametrize('cls_name', ['WholePrefillNativeScheduler', 'WholePrefillSlaiScheduler'])
@pytest.mark.parametrize('bad', ['distributed', 'transfer', 'async'])
def test_contract_rejection_precedes_native_construction(scheduler_factory, monkeypatch, cls_name, bad):
    from robustbench.mgpu00.vllm_scheduler import InstrumentedNativeScheduler
    from robustbench.mgpu02 import vllm_scheduler
    config = scheduler_factory().vllm_config
    if bad == 'distributed':
        config.parallel_config.tensor_parallel_size = 2
    elif bad == 'transfer':
        config.kv_transfer_config = object()
    else:
        config.scheduler_config.async_scheduling = True
    def forbidden(*args, **kwargs):
        raise AssertionError('Unsupported config reached native constructor')
    monkeypatch.setattr(InstrumentedNativeScheduler, '__init__', forbidden)
    with pytest.raises(UnsupportedSemantics):
        getattr(vllm_scheduler, cls_name)(vllm_config=config)
