#!/usr/bin/env python3
"""Reuse durable MGPU00 runner with explicit MGPU02 contract and audit hooks."""
import importlib.util
from pathlib import Path

from robustbench.mgpu02.audit import audit_events
from robustbench.mgpu02.contract import CONTRACT, require_smoke
from robustbench.mgpu02.startup import PinnedPrompt, verify_sources

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('mgpu02_base_smoke', ROOT / 'scripts/mgpu00/smoke.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
base.SPEC = dict(base.SPEC, chunked_prefill=True, semantic_contract=CONTRACT,
                 max_prompt_tokens=256, long_prefill_token_threshold=0)
base.SCHEDULERS = {
    'native_fcfs': 'robustbench.mgpu02.vllm_scheduler.WholePrefillNativeScheduler',
    'slai_mgpu00_checked': 'robustbench.mgpu02.vllm_scheduler.WholePrefillSlaiScheduler',
}
base.EXTRA_SERVER_ARGS = ['--long-prefill-token-threshold', '0']


def require_compatible(**kwargs):
    require_smoke(**kwargs)
    verify_sources(ROOT / 'artifacts/mgpu02/source-inspection/upstream.json')


def load_pinned_prompt(model_path, progress):
    progress.event('pinned_prompt_verification_started')
    tokenizer = PinnedPrompt(model_path, ROOT / 'scripts/mgpu02/prompt.json')
    progress.event('pinned_prompt_verified', tokenizer_files_sha256=tokenizer.fixture['tokenizer_files_sha256'])
    return tokenizer


original_join = base.join_and_validate


def join_and_audit(result, events, requests, policy):
    result = original_join(result, events, requests, policy)
    result['mgpu02_audit'] = audit_events(events, policy,
        {**{r.metadata.request_id: r.output_tokens for r in requests}, 'fixture-warmup': 4})
    return result


base.require_compatible_smoke = require_compatible
base.load_tokenizer = load_pinned_prompt
base.join_and_validate = join_and_audit

if __name__ == '__main__':
    base.main()
