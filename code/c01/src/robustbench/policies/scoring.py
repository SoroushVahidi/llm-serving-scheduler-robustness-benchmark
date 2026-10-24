"""
Shared scoring utilities for all scheduling policies.

All policies should use these functions so comparisons are fair and parameter
choices are centralised in the YAML config.  Default alpha/beta values are
provided as module-level constants; policies may override them per-instance.

Nomenclature
------------
service_proxy   — predicted wall-clock service time (steps) for a waiting request
slack           — remaining time budget after service
urgency         — inverse slack; higher = more urgent
load_proxy      — fraction of GPU capacity currently in use
"""
from __future__ import annotations

from typing import Optional

from ..core.types import ObservableGPUState, ObservableRequest


# Default service-proxy weights used by all style baselines
DEFAULT_ALPHA = 0.5   # weight on prompt_tokens
DEFAULT_BETA  = 1.0   # weight on predicted_output_tokens
_EPS = 1e-9


def predicted_service_proxy(
    req: ObservableRequest,
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
) -> float:
    """Estimated number of decode steps to service request `req`.

    service_proxy = alpha * prompt_tokens + beta * predicted_output_tokens

    This is a linear approximation that acknowledges both prefill and decode
    costs even when the simulator does not model prefill separately.
    """
    return alpha * req.prompt_tokens + beta * req.predicted_output_tokens


def deadline_slack(
    req: ObservableRequest,
    now: float,
    service_proxy: Optional[float] = None,
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
) -> float:
    """Remaining time before deadline after expected service.

    slack = slo_deadline - now - service_proxy_in_seconds
    Negative slack means the request is already likely to miss its deadline.
    """
    if service_proxy is None:
        service_proxy = predicted_service_proxy(req, alpha, beta)
    # service_proxy is in steps; convert to seconds via step_size if needed.
    # Phase 1 leaves it unit-less (policies compare slacks relatively).
    return req.slo_deadline - now - service_proxy


def urgency_score(
    req: ObservableRequest,
    now: float,
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
) -> float:
    """Higher urgency = smaller remaining slack = prioritise first.

    Returns 1 / max(slack, eps).
    """
    slack = deadline_slack(req, now, alpha=alpha, beta=beta)
    return 1.0 / max(slack, _EPS)


def weighted_shortest_processing_score(
    req: ObservableRequest,
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
) -> float:
    """WSPT score: service_proxy / priority.  Lower = schedule first."""
    proxy = predicted_service_proxy(req, alpha, beta)
    return proxy / max(req.priority, _EPS)


def kv_fill_ratio(gpu: ObservableGPUState) -> float:
    """Fraction of KV-cache capacity in use (0–1)."""
    return gpu.current_kv_tokens / max(gpu.max_kv_tokens, 1)


def seq_fill_ratio(gpu: ObservableGPUState) -> float:
    """Fraction of sequence slots in use (0–1)."""
    return len(gpu.active_request_ids) / max(gpu.max_active_sequences, 1)


def remaining_kv(gpu: ObservableGPUState) -> int:
    """Free KV-cache tokens available for new requests."""
    return gpu.max_kv_tokens - gpu.current_kv_tokens


def remaining_seq_slots(gpu: ObservableGPUState) -> int:
    """Free sequence slots available for new requests."""
    return gpu.max_active_sequences - len(gpu.active_request_ids)


def remaining_batch_slots(gpu: ObservableGPUState) -> int:
    """Free batch-token slots (Phase 1: same as seq slots)."""
    return gpu.max_batch_tokens - len(gpu.active_request_ids)


def gpu_load_score(gpu: ObservableGPUState) -> float:
    """Composite load score in [0, 1].  Higher = busier GPU."""
    seq = seq_fill_ratio(gpu)
    kv = kv_fill_ratio(gpu)
    return 0.5 * seq + 0.5 * kv


def post_admission_utilisation(
    gpu: ObservableGPUState,
    req: ObservableRequest,
) -> float:
    """Utilisation after hypothetically admitting `req` (for MostAllocated-style)."""
    new_seq = len(gpu.active_request_ids) + 1
    new_kv  = gpu.current_kv_tokens + req.prompt_tokens
    seq_u = new_seq / max(gpu.max_active_sequences, 1)
    kv_u  = new_kv  / max(gpu.max_kv_tokens,         1)
    return 0.5 * seq_u + 0.5 * kv_u
