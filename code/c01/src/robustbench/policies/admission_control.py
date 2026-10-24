"""
Admission Control baseline policy.

This is a simple, deployable admission-control baseline for SLO-aware LLM
serving research.  It filters waiting requests by a laxity threshold before
scheduling, dropping requests that are already too late to meet their SLO
with high probability.

IMPORTANT: This is NOT a reproduction of Tempo, JITServe, SCORPIO, or any
other published admission-control system.  It is a simple deterministic
baseline designed to isolate the admission-control effect in simulation.

Online deployable: YES
Uses future information: NO (uses only online-observable fields)
SLO-aware: YES (laxity-based filtering)
KV/token-budget aware: YES (respects GPU capacity)

Units
-----
All time quantities in this policy are in **seconds**:

- ``req.slo_deadline``: absolute deadline (seconds)
- ``state.time`` (``now``): current simulator time (seconds)
- ``step_size``: simulator step duration (seconds per step, default 0.001)
- ``service_proxy``: estimated service time in **decode steps** (dimensionless)
- ``service_proxy_seconds = service_proxy * step_size``
- ``laxity (seconds) = slo_deadline - now - service_proxy_seconds``

``laxity_threshold`` is therefore in **seconds**.  A threshold of 0.0 means
"admit a request only if its estimated service time fits within its remaining
deadline."  The default ``float("inf")`` disables filtering entirely.

Algorithm
---------
1. Compute estimated service time for each waiting request (in seconds):
       est_s = step_size * (alpha * prompt_tokens + beta * predicted_output_tokens)
2. Compute laxity (seconds):
       laxity = slo_deadline - now - est_s
3. Filter: keep only requests with laxity >= -laxity_threshold
4. Sort survivors by:
       (a) laxity ascending          (most urgent first)
       (b) priority descending
       (c) estimated service time ascending
       (d) slo_deadline ascending
       (e) request_id ascending      (deterministic tie-break)
5. Greedily assign each request to any GPU with sufficient capacity.

Tie-breaking is fully deterministic.  The policy is stateless between steps.
"""
from __future__ import annotations

from ..core.action import Action
from ..core.types import ObservableRequest, ObservableState
from .base import BasePolicy
from .scoring import DEFAULT_ALPHA, DEFAULT_BETA, predicted_service_proxy


class AdmissionControlPolicy(BasePolicy):
    """Laxity-filtered admission-control scheduling baseline.

    Parameters
    ----------
    laxity_threshold : float, **seconds**
        Requests with laxity (in seconds) < ``-laxity_threshold`` are skipped
        for this scheduling step.  They remain in the queue and may be admitted
        in a later step if conditions improve.

        * ``float("inf")`` (default) — no filtering; acts as urgency-sorted
          admission over all waiting requests.
        * ``0.0`` — admit only requests whose estimated service time fits
          within the remaining deadline (``laxity >= 0``).
        * Positive value ``T`` — admit requests with laxity >= ``-T`` seconds,
          giving some slack for prediction error.

    step_size : float, **seconds per step**
        Simulator step duration in seconds.  Used to convert the service proxy
        (in decode steps) to seconds so that ``laxity`` is unit-consistent.
        Default ``0.001`` matches the typical simulator configuration
        ``step_size: 0.001``.  Override this if your config uses a different
        step size.

    alpha : float
        Prefill cost coefficient in the service-time proxy
        (``alpha * prompt_tokens`` decode steps).
    beta : float
        Decode cost coefficient in the service-time proxy
        (``beta * predicted_output_tokens`` decode steps).
    """

    name = "admission_control"

    def __init__(
        self,
        laxity_threshold: float = float("inf"),
        step_size: float = 0.001,
        alpha: float = DEFAULT_ALPHA,
        beta: float = DEFAULT_BETA,
    ) -> None:
        self.laxity_threshold = laxity_threshold
        self.step_size = step_size
        self.alpha = alpha
        self.beta = beta

    def _est_seconds(self, req: ObservableRequest) -> float:
        """Estimated service time in seconds."""
        return predicted_service_proxy(req, self.alpha, self.beta) * self.step_size

    def _laxity(self, req: ObservableRequest, now: float) -> float:
        """Laxity in seconds: remaining time budget after estimated service."""
        return req.slo_deadline - now - self._est_seconds(req)

    def select_action(self, state: ObservableState) -> Action:
        admit: dict[int, list[int]] = {g.gpu_id: [] for g in state.gpu_states}

        if not state.waiting_queue:
            return Action(admit=admit)

        now = state.time

        # Filter by laxity threshold (all values in seconds)
        min_laxity = -self.laxity_threshold
        candidates = [
            req for req in state.waiting_queue
            if self._laxity(req, now) >= min_laxity
        ]

        # Sort survivors deterministically
        def sort_key(r: ObservableRequest):
            lax = self._laxity(r, now)
            est = self._est_seconds(r)
            return (
                lax,           # ascending: most urgent first
                -r.priority,   # descending: higher priority first
                est,           # ascending: shorter estimated service first
                r.slo_deadline,
                r.request_id,
            )

        candidates.sort(key=sort_key)

        # Greedy GPU assignment
        gpu_idx = 0
        n_gpus = len(state.gpu_states)

        for req in candidates:
            placed = False
            for offset in range(n_gpus):
                gpu = state.gpu_states[(gpu_idx + offset) % n_gpus]
                if self._feasible_on_gpu(gpu, req):
                    admit[gpu.gpu_id].append(req.request_id)
                    gpu.active_request_ids.append(req.request_id)
                    gpu.current_kv_tokens += req.prompt_tokens
                    gpu_idx = (gpu_idx + offset + 1) % n_gpus
                    placed = True
                    break
            if not placed:
                gpu_idx = (gpu_idx + 1) % n_gpus

        return Action(admit=admit)
