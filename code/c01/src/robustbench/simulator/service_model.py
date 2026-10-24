"""
Service-time model for the simulator.

Phase 1 default (enable_prefill_modeling=False)
-----------------------------------------------
* Prefill is instantaneous (zero cost).
* Each decode step produces 1 output token per active request.
* All existing Phase 1 tests use this mode.

Phase 1.5 (enable_prefill_modeling=True)
-----------------------------------------
* Prefill must complete before decoding can start.
* Each step processes up to max_prefill_chunk_tokens per request in prefill.
* Total per-GPU token budget is step_token_budget:
    decode slots   = n_active_decoding  (1 per request)
    prefill slots  = min(max_prefill_chunk_tokens, prefill_remaining) per request
  If decode_first=True the decode budget is guaranteed first; prefill only
  gets the remainder (Sarathi-style stall-free principle).

  Historical note (default `enable_decode_prefill_contention=False`):
  `decode_first` has NO observable effect on execution in this mode --
  `GPUState._step_phase15` always reserves the full decode budget first
  regardless of the flag's value, for every Phase-1.5 policy. This was
  identified as a dead branch (see
  docs/decode_prefill_contention_execution_model.md); it is preserved
  exactly as-is by default because a large body of existing experiment
  configs (`configs/*.yaml`, selector-dataset generation) set
  `decode_first=False` while relying on the simulator's actual (buggy but
  consistent) decode-protected behavior. See `enable_decode_prefill_
  contention` below for the corrected, opt-in behavior.

Disaggregated prefill/decode (enable_disaggregation=True)
-----------------------------------------------------------
Opt-in; see docs/distserve_faithful_scheduler_reference.md. When a request
finishes prefill on a GPUConfig(role="prefill") GPU, instead of continuing
to decode in place (the Phase 1.5 behavior above), it is handed off into a
"migrating" state for migration_transfer_delay seconds before becoming
eligible for admission onto a GPUConfig(role="decode") GPU. Defaults to
False / 0.0 (no behavior change for any existing config). Requires
enable_prefill_modeling=True to have an observable effect (a request must
have a genuine prefill phase to hand off from).

Live cross-instance relocation (llumnix_migration_delay)
-----------------------------------------------------------
Opt-in; see docs/llumnix_faithful_scheduler_reference.md. Independent of
`enable_disaggregation`/`migration_transfer_delay` above (a genuinely
separate mechanism -- see that field's own docstring in
simulator/request.py's RequestPhase.RELOCATING for why the two are not
conflated): the wall-clock seconds a live migration of an already-active
request between two ordinary (role=None) GPUs/instances takes, applied via
Action.migrate. Defaults to 0.0 (no behavior change for any existing
config, and independently configurable from `migration_transfer_delay` so
an experiment could in principle use both disaggregation and Llumnix-style
migration at once with different delays for each).

TODO (Phase 2+)
---------------
* Memory-bandwidth-limited decode slow-down at large batch sizes.
* Realistic GPU FP16 FLOPS model for prefill.
* Heterogeneous GPU throughput multipliers.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceModel:
    step_size: float = 0.001          # wall-clock seconds per decode step

    # --- Phase 1.5 prefill parameters (ignored when enable_prefill_modeling=False) ---
    enable_prefill_modeling: bool = False
    prefill_cost_per_token: float = 1.0        # budget tokens consumed per prompt token
    max_prefill_chunk_tokens: int = 512        # max prefill tokens processed per step
    step_token_budget: int = 4096             # total token budget per GPU per step
    decode_first: bool = False                 # guarantee decode budget before prefill
    allow_chunked_prefill: bool = True         # allow multi-step chunked prefill

    # --- Decode/prefill execution-contention model (opt-in; see
    # docs/decode_prefill_contention_execution_model.md). Default False
    # preserves the historical (dead-branch) behavior exactly:
    # `decode_first` has no observable effect, decode is always given its
    # budget first regardless of the flag. When True, `decode_first`
    # becomes genuinely load-bearing:
    #   decode_first=True  -> Sarathi-style decode-protected execution
    #                         (identical formula to the historical
    #                         default; decode is unconditionally
    #                         guaranteed its budget before any prefill).
    #   decode_first=False -> vLLM-chunked-prefill-style shared execution:
    #                         decode and prefill requests compete for ONE
    #                         combined per-step budget, consumed in a
    #                         single FCFS-by-arrival-time pass (matching
    #                         vLLM v0.4.2's `_schedule_running` with no
    #                         decode-priority phase) -- a request later in
    #                         that order can receive zero progress this
    #                         step if the budget runs out first.
    enable_decode_prefill_contention: bool = False

    # --- Disaggregated prefill/decode (opt-in; see docs/distserve_faithful_scheduler_reference.md) ---
    enable_disaggregation: bool = False        # hand off prefill-done requests instead of continuing in place
    migration_transfer_delay: float = 0.0      # wall-clock seconds a handoff takes; 0.0 = zero-cost mode

    # --- Live cross-instance relocation (opt-in; see docs/llumnix_faithful_scheduler_reference.md) ---
    llumnix_migration_delay: float = 0.0       # wall-clock seconds a live migration takes; 0.0 = zero-cost mode

    # --- Legacy (Phase 1 compat, not actively used in Phase 1.5) ---
    prefill_tokens_per_step: int = 512         # kept for doc purposes

    def compute_prefill_tokens(self, prompt_tokens: int) -> int:
        """Number of prompt tokens that must be processed before decode starts.

        When enable_prefill_modeling=False: always 0 (instant prefill).
        When True: prompt_tokens × prefill_cost_per_token, rounded up.
        """
        if not self.enable_prefill_modeling:
            return 0
        return max(0, math.ceil(prompt_tokens * self.prefill_cost_per_token))

    def prefill_steps(self, prompt_tokens: int) -> int:
        """Minimum steps to complete prefill for a request (for planning only)."""
        total = self.compute_prefill_tokens(prompt_tokens)
        if total == 0:
            return 0
        return math.ceil(total / max(1, self.max_prefill_chunk_tokens))

    def decode_time(self, output_tokens: int) -> float:
        """Wall-clock seconds to decode `output_tokens` (single request)."""
        return output_tokens * self.step_size
