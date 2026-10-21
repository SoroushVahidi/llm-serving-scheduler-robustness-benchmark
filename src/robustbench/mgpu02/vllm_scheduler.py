"""Restricted no-split adapter, with native scheduling and completion checks.

No model forward pass is replaced. A native allocation mismatch invalidates the
run before returning a schedule to the engine; completion checks are distinct.
"""
import os

from vllm.v1.request import RequestStatus
from robustbench.mgpu00.slai import SlaiCore, UnsupportedSemantics
from robustbench.mgpu00.vllm_scheduler import InstrumentedNativeScheduler, LSSPSlaiVLLMScheduler
from .contract import CONTRACT, MAX_PROMPT_TOKENS, validate_config


class WholePrefillChecks:
    def initialize_contract(self):
        self.mgpu_pending = None
        self.event('contract_verified', contract=CONTRACT, max_prompt_tokens=MAX_PROMPT_TOKENS,
                   token_budget=self.max_num_scheduled_tokens, max_active=self.max_num_running_reqs)

    def add_request(self, request):
        # Keep engine identity unique for the lifetime of the evidence journal,
        # including completed requests. Native vLLM accepts streaming updates
        # or reuse after completion, but this contract supports neither. Reject
        # before the inherited adapter can overwrite metadata/admission history.
        if request.request_id in self.mgpu_metadata:
            raise ValueError('Duplicate engine request identity')
        if (request.status != RequestStatus.WAITING or request.num_computed_tokens != 0
                or request.num_output_tokens or request.resumable or request.mm_features
                or request.prompt_embeds is not None or request.lora_request is not None
                or request.structured_output_request is not None
                or request.kv_transfer_params or request.ec_transfer_params):
            raise UnsupportedSemantics('Requires fresh text-only unstructured requests')
        if not 1 <= request.num_prompt_tokens <= MAX_PROMPT_TOKENS:
            raise UnsupportedSemantics('Prompt exceeds whole-prefill contract boundary')
        if request.num_prompt_tokens + request.max_tokens > self.max_model_len:
            raise UnsupportedSemantics('Prompt plus output exceeds context boundary')
        # Ordinal is the declared stable tie-breaker; duplicate ordinals make
        # the bounded integer priority encoding ambiguous.
        from robustbench.mgpu00.metadata import RequestMetadata
        metadata = RequestMetadata.from_request(request)
        if metadata.ordinal >= 1_000_000:
            raise ValueError('Workload ordinal exceeds bounded priority encoding')
        if any(m.ordinal == metadata.ordinal for m in self.mgpu_metadata.values()):
            raise ValueError('Duplicate workload ordinal')
        return super().add_request(request)

    def _preempt_request(self, *args, **kwargs):
        raise UnsupportedSemantics('KV preemption is outside the whole-prefill contract')

    def schedule(self, throttle_prefills=False):
        if throttle_prefills or self.mgpu_pending is not None:
            raise UnsupportedSemantics('Throttled or overlapping scheduling is unsupported')
        if self.skipped_waiting:
            raise UnsupportedSemantics('Skipped waiting state is unsupported')
        for r in self.running:
            if (r.status != RequestStatus.RUNNING or r.num_computed_tokens < r.num_prompt_tokens
                    or r.num_tokens_with_spec - r.num_computed_tokens != 1
                    or r.num_output_placeholders or r.next_decode_eligible_step > self.current_step):
                raise UnsupportedSemantics('Partial-prefill/decode state outside checked domain')
        for r in self.waiting:
            if r.status != RequestStatus.WAITING or r.num_computed_tokens or r.num_preemptions:
                raise UnsupportedSemantics('Resumed or partially computed waiting request')
        before = {r.request_id: (r, r.num_computed_tokens, r.num_output_tokens)
                  for r in [*self.running, *self.waiting]}
        native_expected = {r.request_id: 1 for r in self.running}
        slots = self.max_num_running_reqs - len(self.running)
        native_expected.update({r.request_id: r.num_prompt_tokens for r in list(self.waiting)[:slots]})
        def describe(r):
            m = self.mgpu_metadata[r.request_id]
            return dict(engine_id=r.request_id, request_id=m.request_id, ordinal=m.ordinal,
                        class_id=m.class_id, prompt_tokens=r.num_prompt_tokens)
        self.event('decision_input', step=self.current_step + 1,
                   running=[dict(describe(r), lst_s=self.mgpu_core.lst.get(r.request_id))
                            if hasattr(self, 'mgpu_core') else describe(r) for r in self.running],
                   waiting=[describe(r) for r in self.waiting],
                   max_active=self.max_num_running_reqs, token_budget=self.max_num_scheduled_tokens,
                   decode_limit=self.mgpu_core.decode_limit if hasattr(self, 'mgpu_core') else None)
        output = super().schedule(throttle_prefills=False)
        if output.preempted_req_ids:
            raise UnsupportedSemantics('Preemption invalidates the whole-prefill contract')
        if self.mechanism == 'native_fcfs' and output.num_scheduled_tokens != native_expected:
            raise UnsupportedSemantics('Native FCFS allocation deviated (including KV admission pressure)')
        for rid, tokens in output.num_scheduled_tokens.items():
            request, computed, _ = before[rid]
            expected = request.num_prompt_tokens if computed == 0 else 1
            if tokens != expected or request.num_computed_tokens != computed + tokens:
                raise UnsupportedSemantics('Native partial-prefill/progress mismatch')
        planned = dict(output.num_scheduled_tokens)
        if planned:
            self.mgpu_pending = (planned, {rid: before[rid] for rid in planned})
        self.event('whole_prefill_verified', step=self.current_step, tokens=planned, contract=CONTRACT)
        return output

    def update_from_output(self, scheduler_output, model_runner_output):
        pending = self.mgpu_pending
        if pending is None:
            if scheduler_output.num_scheduled_tokens:
                raise UnsupportedSemantics('Completion without a checked schedule')
            return super().update_from_output(scheduler_output, model_runner_output)
        planned, before = pending
        runner = model_runner_output
        if (scheduler_output.num_scheduled_tokens != planned
                or len(runner.req_ids) != len(set(runner.req_ids))
                or set(runner.req_ids) != set(planned)
                or runner.req_id_to_index != {rid: i for i, rid in enumerate(runner.req_ids)}
                or len(runner.sampled_token_ids) != len(planned)
                or any(len(ids) != 1 for ids in runner.sampled_token_ids)):
            raise UnsupportedSemantics('Model-runner completion differs from scheduled requests/tokens')
        if runner.num_nans_in_logits and any(runner.num_nans_in_logits.values()):
            raise UnsupportedSemantics('Nonfinite model-runner logits')
        output = super().update_from_output(scheduler_output, model_runner_output)
        for rid, (request, computed, generated) in before.items():
            if (request.num_computed_tokens != computed + planned[rid]
                    or request.num_output_tokens != generated + 1):
                raise UnsupportedSemantics('Native completion failed to advance the expected state')
        self.event('execution_verified', step=self.current_step, tokens=planned,
                   sampled_tokens={rid: 1 for rid in planned}, contract=CONTRACT)
        self.mgpu_pending = None
        return output


class WholePrefillNativeScheduler(WholePrefillChecks, InstrumentedNativeScheduler):
    def __init__(self, *args, **kwargs):
        validate_config(kwargs['vllm_config'] if 'vllm_config' in kwargs else args[0])
        super().__init__(*args, **kwargs)
        self.initialize_contract()
        if self.scheduler_config.policy != 'fcfs':
            raise UnsupportedSemantics('Native control requires FCFS')


class WholePrefillSlaiScheduler(WholePrefillChecks, LSSPSlaiVLLMScheduler):
    # Same SLAI core and hold mechanism; the new, explicit deployment contract
    # replaces the old constructor's unconditional chunking rejection.
    def __init__(self, *args, **kwargs):
        validate_config(kwargs['vllm_config'] if 'vllm_config' in kwargs else args[0])
        InstrumentedNativeScheduler.__init__(self, *args, **kwargs)
        self.initialize_contract()
        if self.scheduler_config.policy != 'priority':
            raise UnsupportedSemantics('SLAI requires priority admission')
        self.mgpu_core = SlaiCore(int(os.environ['LSSP_MGPU00_DECODE_LIMIT']))
        self.mgpu_batch = None
