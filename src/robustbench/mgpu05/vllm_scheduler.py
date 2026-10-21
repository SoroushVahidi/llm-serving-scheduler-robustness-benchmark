"""Observation-only subclasses; MGPU02 scheduling/rejection paths stay intact."""
import json
import os
import sys
import time

from robustbench.mgpu02.vllm_scheduler import WholePrefillNativeScheduler, WholePrefillSlaiScheduler
from .evidence import clock_domain, digest


class MeasurementMixin:
    def __init__(self, *args, **kwargs):
        if os.environ.get('LSSP_MGPU05_SYNTHETIC') != '1':
            raise ValueError('Token-ID capture is allowed only for synthetic engineering fixtures')
        provenance = os.environ.get('LSSP_MGPU05_TIMING_PROVENANCE')
        if provenance not in ('physical_candidate', 'synthetic_test'):
            raise ValueError('Explicit timing provenance required')
        self.measurement_clock = time.monotonic
        self.measurement_sequence = 0
        self.measurement_domain = clock_domain()
        super().__init__(*args, **kwargs)
        self.measurement('measurement_contract', clock_domain=self.measurement_domain,
                         provenance=provenance, schema='mgpu05-v1')

    def measurement(self, kind, **fields):
        row = dict(kind=kind, seq=self.measurement_sequence, time_s=self.measurement_clock(),
                   mechanism=self.mechanism, **fields)
        print('MGPU05_EVENT ' + json.dumps(row, sort_keys=True, allow_nan=False),
              file=sys.stderr, flush=True)
        self.measurement_sequence += 1

    def add_request(self, request):
        observed = self.measurement_clock()
        super().add_request(request)
        m = self.mgpu_metadata[request.request_id]
        self.measurement('request_received', observed_s=observed, engine_id=request.request_id,
                         request_id=m.request_id, metadata=m.xargs(),
                         prompt_tokens=request.num_prompt_tokens,
                         prompt_sha256=digest(list(request.prompt_token_ids)),
                         output_limit=request.max_tokens,
                         boundary='scheduler_add_request_entry_not_HTTP_ingress')

    def update_from_output(self, scheduler_output, model_runner_output):
        observed = self.measurement_clock()
        ids = {rid: list(model_runner_output.sampled_token_ids[i])
               for rid, i in model_runner_output.req_id_to_index.items()}
        result = super().update_from_output(scheduler_output, model_runner_output)
        if ids:
            self.measurement('runner_tokens', observed_s=observed, step=self.current_step,
                             token_ids=ids,
                             request_ids={rid: self.mgpu_metadata[rid].request_id for rid in ids},
                             boundary='host_runner_output_callback_not_GPU_generation_or_HTTP_emission')
        return result


class MeasuredNativeScheduler(MeasurementMixin, WholePrefillNativeScheduler):
    pass


class MeasuredSlaiScheduler(MeasurementMixin, WholePrefillSlaiScheduler):
    pass
