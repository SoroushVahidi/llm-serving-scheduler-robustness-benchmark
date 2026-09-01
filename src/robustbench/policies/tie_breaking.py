"""
Deterministic tie-breaking keys for scheduling policies.

All policies should break ties deterministically (by arrival_time then
request_id) to ensure reproducibility under fixed seed.  These helpers
provide consistent composite sort keys.
"""
from __future__ import annotations

from ..core.types import ObservableRequest


def arrival_then_id(req: ObservableRequest) -> tuple:
    """Primary: earliest arrival first; secondary: smallest id."""
    return (req.arrival_time, req.request_id)


def deadline_then_arrival(req: ObservableRequest) -> tuple:
    """Primary: earliest deadline first; tie-break by arrival then id."""
    return (req.slo_deadline, req.arrival_time, req.request_id)


def priority_desc_then_arrival(req: ObservableRequest) -> tuple:
    """Primary: highest priority first (negate for ascending sort); tie-break."""
    return (-req.priority, req.arrival_time, req.request_id)


def output_asc_then_arrival(req: ObservableRequest) -> tuple:
    """Primary: shortest predicted output first; tie-break by arrival then id."""
    return (req.predicted_output_tokens, req.arrival_time, req.request_id)


def prompt_asc_then_arrival(req: ObservableRequest) -> tuple:
    """Primary: shortest prompt first; tie-break by arrival then id."""
    return (req.prompt_tokens, req.arrival_time, req.request_id)


def service_proxy_asc_then_arrival(
    alpha: float = 0.5,
    beta: float = 1.0,
):
    """Return a key function sorting by service proxy ascending."""
    def _key(req: ObservableRequest) -> tuple:
        proxy = alpha * req.prompt_tokens + beta * req.predicted_output_tokens
        return (proxy, req.arrival_time, req.request_id)
    return _key
