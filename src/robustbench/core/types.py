"""
Core data types for the LLM serving simulator.

Phase 1.5 additions
-------------------
* CompletedRequest gains first_token_time and derived TTFT / TPOT properties.
* ObservableGPUState gains prefilling_count and decoding_count so that
  serving-style policies (Sarathi, SplitFuse) can reason about GPU phase.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Request:
    request_id: int
    arrival_time: float
    prompt_tokens: int
    predicted_output_tokens: int
    actual_output_tokens: int        # ground truth — hidden from online policies
    slo_deadline: float              # absolute time by which response must complete
    priority: float                  # higher value = higher importance
    class_id: str                    # e.g. "tight", "medium", "loose"

    def __post_init__(self) -> None:
        if self.prompt_tokens <= 0:
            raise ValueError(f"prompt_tokens must be positive, got {self.prompt_tokens}")
        if self.actual_output_tokens <= 0:
            raise ValueError(f"actual_output_tokens must be positive, got {self.actual_output_tokens}")
        if self.predicted_output_tokens <= 0:
            raise ValueError(f"predicted_output_tokens must be positive, got {self.predicted_output_tokens}")
        if self.arrival_time < 0:
            raise ValueError(f"arrival_time must be non-negative, got {self.arrival_time}")


#: Valid GPUConfig.role values for disaggregated prefill/decode execution
#: (see docs/distserve_faithful_scheduler_reference.md). None (the default)
#: means legacy/colocated: a GPU that runs both prefill and decode, exactly
#: as every existing config already does.
DISAGGREGATION_ROLES = ("prefill", "decode")


@dataclass(frozen=True)
class GPUConfig:
    gpu_id: int
    max_active_sequences: int   # max concurrently active requests
    max_batch_tokens: int       # max tokens processed in one step (all active reqs)
    max_kv_tokens: int          # total KV-cache capacity in tokens
    # Disaggregated prefill/decode execution (opt-in; see
    # docs/distserve_faithful_scheduler_reference.md). None = legacy/colocated
    # GPU, unchanged behavior. Every existing config leaves this unset.
    role: Optional[str] = None

    # Dual-tier cache support (Apt-Serve style)
    hybrid_cache_enabled: bool = False
    hidden_cache_capacity_blocks: int = 0
    hidden_to_kv_memory_ratio: float = 0.1
    cache_switch_latency: float = 0.0
    hidden_restore_latency: float = 0.0
    recomputation_cost_model: str = "full"
    apt_serve_rho: float = 0.5
    apt_serve_ttft_slo: float = 2.0
    apt_serve_tbt_slo: float = 0.05

    def __post_init__(self) -> None:
        if self.max_active_sequences <= 0:
            raise ValueError("max_active_sequences must be positive")
        if self.max_batch_tokens <= 0:
            raise ValueError("max_batch_tokens must be positive")
        if self.max_kv_tokens <= 0:
            raise ValueError("max_kv_tokens must be positive")
        if self.role is not None and self.role not in DISAGGREGATION_ROLES:
            raise ValueError(
                f"role must be one of {DISAGGREGATION_ROLES} or None, got {self.role!r}"
            )

        if self.hybrid_cache_enabled:
            if self.hidden_cache_capacity_blocks <= 0:
                raise ValueError("hidden_cache_capacity_blocks must be positive when hybrid cache is enabled")
            if self.hidden_to_kv_memory_ratio <= 0.0 or self.hidden_to_kv_memory_ratio > 1.0:
                raise ValueError("hidden_to_kv_memory_ratio must be in (0.0, 1.0]")
            if self.cache_switch_latency < 0.0:
                raise ValueError("cache_switch_latency must be non-negative")
            if self.hidden_restore_latency < 0.0:
                raise ValueError("hidden_restore_latency must be non-negative")
            if self.recomputation_cost_model not in ("full", "hidden_restore"):
                raise ValueError(f"unsupported recomputation_cost_model: {self.recomputation_cost_model}")
            if self.apt_serve_rho < 0.0:
                raise ValueError("apt_serve_rho must be non-negative")
            if self.apt_serve_ttft_slo <= 0.0:
                raise ValueError("apt_serve_ttft_slo must be positive")
            if self.apt_serve_tbt_slo <= 0.0:
                raise ValueError("apt_serve_tbt_slo must be positive")
        else:
            if (self.hidden_cache_capacity_blocks != 0 or
                self.hidden_to_kv_memory_ratio != 0.1 or
                self.cache_switch_latency != 0.0 or
                self.hidden_restore_latency != 0.0 or
                self.recomputation_cost_model != "full" or
                self.apt_serve_rho != 0.5 or
                self.apt_serve_ttft_slo != 2.0 or
                self.apt_serve_tbt_slo != 0.05):
                raise ValueError("Hybrid cache fields can only be set when hybrid_cache_enabled=True")


@dataclass
class ObservableRequest:
    """Request view exposed to online scheduling policies.

    actual_output_tokens is intentionally absent; policies must rely on
    predicted_output_tokens instead.
    """
    request_id: int
    arrival_time: float
    prompt_tokens: int
    predicted_output_tokens: int
    slo_deadline: float
    priority: float
    class_id: str

    @staticmethod
    def from_request(r: Request) -> "ObservableRequest":
        return ObservableRequest(
            request_id=r.request_id,
            arrival_time=r.arrival_time,
            prompt_tokens=r.prompt_tokens,
            predicted_output_tokens=r.predicted_output_tokens,
            slo_deadline=r.slo_deadline,
            priority=r.priority,
            class_id=r.class_id,
        )


@dataclass
class ObservableGPUState:
    gpu_id: int
    max_active_sequences: int
    max_batch_tokens: int
    max_kv_tokens: int
    active_request_ids: List[int]
    active_requests_info: List[ObservableRequest]
    current_kv_tokens: int
    tokens_decoded_per_request: Dict[int, int]
    # Phase 1.5: phase-split counts (0 when enable_prefill_modeling=False)
    prefilling_count: int = 0
    decoding_count: int = 0
    # Disaggregated prefill/decode execution (opt-in; mirrors GPUConfig.role).
    # None for every legacy/colocated GPU.
    role: Optional[str] = None
    # Live cross-instance relocation (opt-in; see
    # docs/llumnix_faithful_scheduler_reference.md): requests whose
    # migration transfer to THIS specific GPU has already completed and
    # are awaiting admission here. Distinct from ObservableState's own
    # migrating_queue (disaggregated prefill/decode bridge queue, any
    # decode-role GPU may claim those) -- a relocation always has exactly
    # one fixed destination, fixed at the moment a policy issued
    # Action.migrate. Always empty unless a policy has ever set
    # Action.migrate.
    incoming_migrations: List[ObservableRequest] = field(default_factory=list)

    @property
    def free_sequences(self) -> int:
        return self.max_active_sequences - len(self.active_request_ids)

    @property
    def free_kv_tokens(self) -> int:
        return self.max_kv_tokens - self.current_kv_tokens

    @property
    def utilization(self) -> float:
        if self.max_active_sequences == 0:
            return 0.0
        return len(self.active_request_ids) / self.max_active_sequences

    @property
    def token_budget_used(self) -> int:
        """Batch tokens consumed this step by active decode requests (Phase 1.5)."""
        return self.decoding_count if self.decoding_count > 0 else len(self.active_request_ids)


@dataclass
class ObservableState:
    """Snapshot of the serving system visible to an online scheduling policy."""
    time: float
    waiting_queue: List[ObservableRequest]
    gpu_states: List[ObservableGPUState]
    completed_count: int
    step: int
    # Disaggregated prefill/decode execution (opt-in; see
    # docs/distserve_faithful_scheduler_reference.md): requests that have
    # finished prefill on a role="prefill" GPU and whose transfer delay has
    # already elapsed -- eligible for admission onto a role="decode" GPU via
    # the same Action.admit mechanism. Distinct from waiting_queue, which
    # holds only genuinely-new, needs-prefill requests. Always empty unless
    # ServiceModel.enable_disaggregation is set.
    migrating_queue: List[ObservableRequest] = field(default_factory=list)


@dataclass
class CompletedRequest:
    request: Request
    admission_time: float
    completion_time: float
    gpu_id: int
    first_token_time: float = -1.0   # Phase 1.5: time of first decoded token

    @property
    def latency(self) -> float:
        return self.completion_time - self.request.arrival_time

    @property
    def queuing_delay(self) -> float:
        return self.admission_time - self.request.arrival_time

    @property
    def service_time(self) -> float:
        return self.completion_time - self.admission_time

    @property
    def slo_violated(self) -> bool:
        return self.completion_time > self.request.slo_deadline

    @property
    def slo_slack(self) -> float:
        return self.request.slo_deadline - self.completion_time

    @property
    def ttft(self) -> float:
        """Time to First Token = first_token_time - arrival_time.

        Returns NaN when first_token_time was not recorded (Phase 1 mode).
        """
        if self.first_token_time < 0:
            return float("nan")
        return self.first_token_time - self.request.arrival_time

    @property
    def tpot(self) -> float:
        """Time Per Output Token (mean inter-token latency after first token).

        TPOT = (completion_time - first_token_time) / max(1, output_tokens - 1)

        Returns NaN when first_token_time was not recorded.
        """
        if self.first_token_time < 0:
            return float("nan")
        n_intervals = max(1, self.request.actual_output_tokens - 1)
        return (self.completion_time - self.first_token_time) / n_intervals

    @property
    def prefill_delay(self) -> float:
        """Wall-clock time spent in prefill (admission → first decode token).

        Returns NaN when first_token_time was not recorded.
        """
        if self.first_token_time < 0:
            return float("nan")
        return self.first_token_time - self.admission_time
