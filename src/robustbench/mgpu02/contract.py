"""Sufficient no-split bound; not a general chunked-SLAI implementation."""
from robustbench.mgpu00.slai import UnsupportedSemantics

CONTRACT = 'mgpu02-whole-prefill-v1'
MAX_PROMPT_TOKENS = 256


def validate_config(config):
    p, s, m = config.parallel_config, config.scheduler_config, config.model_config
    if any(getattr(p, name) != 1 for name in (
        'tensor_parallel_size', 'pipeline_parallel_size', 'data_parallel_size',
        'decode_context_parallel_size', 'prefill_context_parallel_size')):
        raise UnsupportedSemantics('TP/PP/DP/context parallelism requires separate validation')
    if any(getattr(config, key) is not None for key in (
        'speculative_config', 'kv_transfer_config', 'ec_transfer_config', 'lora_config')):
        raise UnsupportedSemantics('Speculation, KV/encoder transfer and LoRA are unsupported')
    if not config.use_v2_model_runner or config.max_concurrent_batches != 1:
        raise UnsupportedSemantics('Requires V2 runner with a single in-flight batch')
    if s.async_scheduling or not s.enable_chunked_prefill:
        raise UnsupportedSemantics('Requires synchronous scheduling and enabled chunked prefill')
    if s.long_prefill_token_threshold != 0:
        raise UnsupportedSemantics('Partial-prefill threshold must be zero')
    budget = s.max_num_scheduled_tokens
    budget = s.max_num_batched_tokens if budget is None else budget
    # With R running decodes and at most N-R admissions, tokens <=
    # R + (N-R)*P <= N*P. Holds still occupy active/KV capacity.
    if budget < s.max_num_seqs * MAX_PROMPT_TOKENS:
        raise UnsupportedSemantics('Token budget does not prove whole-prefill bound N*P')
    if (m.hf_config.model_type != 'qwen2' or m.runner_type != 'generate'
            or m.is_encoder_decoder or s.is_multimodal_model):
        raise UnsupportedSemantics('Only reviewed Qwen2 text generation is supported')
    if config.cache_config.enable_prefix_caching:
        raise UnsupportedSemantics('Prefix caching is outside the whole-prefill contract')


def require_smoke(*, model, version, chunked_prefill):
    if model != 'Qwen/Qwen2.5-0.5B-Instruct' or version != '0.27.1' or chunked_prefill is not True:
        raise UnsupportedSemantics('MGPU02 requires pinned Qwen/vLLM and enabled chunked prefill')
    # Full effective configuration is checked by both scheduler constructors.
    return CONTRACT
