"""
Internal (simulator-side) request state.

Phase 1.5 additions
-------------------
* prefill_remaining : prompt tokens still to process before decode can start.
  Zero when enable_prefill_modeling=False (backward-compat Phase 1 behaviour).
* first_token_time  : wall-clock time when the first decode token was produced
  (= TTFT anchor).  -1.0 if not yet recorded.

Disaggregated prefill/decode addition (opt-in; see
docs/distserve_faithful_scheduler_reference.md)
-------------------------------------------------
* RequestPhase.MIGRATING : a request that finished prefill on a
  role="prefill" GPU and is awaiting transfer completion before it is
  eligible for admission onto a role="decode" GPU. Only ever produced when
  ServiceModel.enable_disaggregation is set; no existing code path
  produces or checks this phase.
* transfer_ready_time : wall-clock time at which this request's transfer
  delay elapses (only meaningful while phase == MIGRATING). -1.0 for every
  request that never migrates.

Live cross-instance relocation addition (opt-in; see
docs/llumnix_faithful_scheduler_reference.md)
-------------------------------------------------
* RequestPhase.RELOCATING : an already-active (typically already-decoding)
  request that a policy has moved off its current GPU/instance toward a
  specific OTHER instance for load-balancing/fragmentation/priority
  reasons -- NOT a disaggregated prefill->decode handoff (RequestPhase.
  MIGRATING; see above). Deliberately a separate phase and a separate
  simulator-level container (Simulator._relocating), reusing
  `transfer_ready_time` for the timestamp field (same concept: "when does
  this request become admission-eligible elsewhere") but never sharing the
  bridge queue's any-decode-GPU-may-claim-it semantics -- a relocating
  request has one fixed destination, tracked in
  `migration_destination_gpu_id`. Only ever produced when a policy sets
  Action.migrate; no existing policy does.
* migration_destination_gpu_id : the gpu_id this request must be admitted
  onto once its relocation transfer completes (only meaningful while
  phase == RELOCATING). -1 for every request that never relocates.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from ..core.types import Request


class RequestPhase(Enum):
    WAITING     = auto()
    ACTIVE      = auto()     # covers both prefill and decode sub-phases
    MIGRATING   = auto()     # disaggregated prefill/decode mode only -- see module docstring
    RELOCATING  = auto()     # live cross-instance relocation only -- see module docstring
    COMPLETED   = auto()


@dataclass
class InternalRequest:
    """Mutable request state tracked by the simulator."""
    request: Request
    phase: RequestPhase = RequestPhase.WAITING
    gpu_id: int = -1
    current_tier: str = "kv" 
    admission_time: float = -1.0
    completion_time: float = -1.0
    tokens_decoded: int = 0
    # Phase 1.5 fields (zero = no prefill / Phase 1 backward-compat)
    prefill_remaining: int = 0       # prompt tokens left to prefill
    first_token_time: float = -1.0   # time of first decoded token output
    # Disaggregated prefill/decode field (opt-in; -1.0 = not migrating)
    transfer_ready_time: float = -1.0
    # Live cross-instance relocation field (opt-in; -1 = not relocating)
    migration_destination_gpu_id: int = -1

    # ------------------------------------------------------------------ #
    # Phase properties
    # ------------------------------------------------------------------ #

    @property
    def is_prefilling(self) -> bool:
        return self.phase == RequestPhase.ACTIVE and self.prefill_remaining > 0

    @property
    def is_decoding(self) -> bool:
        return self.phase == RequestPhase.ACTIVE and self.prefill_remaining == 0

    @property
    def request_id(self) -> int:
        return self.request.request_id

    # ------------------------------------------------------------------ #
    # KV footprint
    # ------------------------------------------------------------------ #

    @property
    def kv_tokens(self) -> int:
        """Current KV-cache footprint.

        Phase 1 (no prefill): all prompt tokens allocated immediately on admission.
        Phase 1.5 (with prefill): KV grows as prefill processes; full prompt_tokens
        only after prefill completes.  During decode, KV grows by tokens_decoded.
        """
        if self.phase == RequestPhase.WAITING:
            return 0
        prefilled = self.request.prompt_tokens - self.prefill_remaining
        return prefilled + self.tokens_decoded

    @property
    def is_complete(self) -> bool:
        return (
            self.prefill_remaining == 0
            and self.tokens_decoded >= self.request.actual_output_tokens
        )

    # ------------------------------------------------------------------ #
    # Advance methods
    # ------------------------------------------------------------------ #

    def advance_prefill(self, chunk_tokens: int) -> bool:
        """Process `chunk_tokens` prefill tokens.  Returns True when prefill done."""
        if self.phase != RequestPhase.ACTIVE:
            raise RuntimeError(
                f"Request {self.request_id}: advance_prefill called in phase {self.phase}"
            )
        self.prefill_remaining = max(0, self.prefill_remaining - chunk_tokens)
        return self.prefill_remaining == 0

    def advance_decode(self, current_time: float = -1.0) -> bool:
        """Advance by one decode token.  Returns True when request completes.

        Records first_token_time on the first call (first output token).
        `current_time` is the wall-clock timestamp at end of the decode step.
        """
        if self.phase != RequestPhase.ACTIVE:
            raise RuntimeError(
                f"Request {self.request_id}: advance_decode called in phase {self.phase}"
            )
        if self.prefill_remaining > 0:
            raise RuntimeError(
                f"Request {self.request_id}: advance_decode called before prefill done"
            )
        self.tokens_decoded += 1
        if self.first_token_time < 0 and self.tokens_decoded == 1:
            self.first_token_time = current_time
        return self.is_complete
