"""
SCORPIO-inspired SLO guard baseline policy.

Manuscript label: "SCORPIO-style SLO guard" or "SCORPIO-inspired TTFT/TPOT guard baseline"

IMPORTANT: This is NOT an official SCORPIO reproduction.  It is a deterministic,
simulator-compatible approximation of SCORPIO's policy-level ideas:

1. **TTFT / deadline guard** — deprioritize or skip requests whose predicted prefill
   (TTFT proxy) cannot fit in the remaining deadline budget.
2. **TPOT / decode pressure guard** — under high KV utilization or active decode load,
   penalize long predicted decode work and throttle admissions via a credit budget.
3. **Composite urgency scoring** — combine laxity, priority, age, and decode-pressure
   penalty into a deterministic admission rank.
4. **Admission throttling** — when system pressure is high, limit new admissions per step
   using a refilling credit budget (token-bucket style proxy for SCORPIO rate control).

Online deployable: YES
Uses future information: NO
SLO-aware: YES
KV/token-budget aware: YES

TTFT / TPOT modelling note
--------------------------
The simulator records TTFT/TPOT only post-hoc on completed requests.  This policy uses
documented **proxies** at scheduling time:

* **TTFT proxy** = ``step_size * alpha * prompt_tokens`` (estimated prefill duration)
* **TPOT / decode pressure proxy** = ``decoding_count / max_active_sequences`` per GPU,
  combined with ``kv_fill_ratio`` from observable GPU state.

Units
-----
All laxity and slack thresholds are in **seconds**, consistent with ``AdmissionControlPolicy``.
Service estimates use ``step_size`` to convert decode-step proxies to seconds.
"""
from __future__ import annotations

from ..core.action import Action
from ..core.types import ObservableGPUState, ObservableRequest, ObservableState
from .base import BasePolicy
from .scoring import (
    DEFAULT_ALPHA,
    DEFAULT_BETA,
    kv_fill_ratio,
    predicted_service_proxy,
)

_EPS = 1e-9


class ScorpioStyleSloGuardPolicy(BasePolicy):
    """SCORPIO-inspired SLO guard with deadline, decode-pressure, and credit throttling."""

    name = "scorpio_style_slo_guard"

    def __init__(
        self,
        step_size: float = 0.001,
        alpha: float = DEFAULT_ALPHA,
        beta: float = DEFAULT_BETA,
        laxity_threshold: float = 0.0,
        ttft_slack_threshold: float = 0.0,
        kv_utilization_threshold: float = 0.65,
        decode_pressure_threshold: float = 0.70,
        queue_overload_factor: float = 3.0,
        admission_budget_refill: float = 2.0,
        admission_budget_max: float = 4.0,
        admission_cost: float = 1.0,
        priority_weight: float = 1.0,
        age_bonus: float = 0.05,
        decode_penalty_weight: float = 0.35,
        long_decode_token_threshold: int = 256,
    ) -> None:
        self.step_size = step_size
        self.alpha = alpha
        self.beta = beta
        self.laxity_threshold = laxity_threshold
        self.ttft_slack_threshold = ttft_slack_threshold
        self.kv_utilization_threshold = kv_utilization_threshold
        self.decode_pressure_threshold = decode_pressure_threshold
        self.queue_overload_factor = queue_overload_factor
        self.admission_budget_refill = admission_budget_refill
        self.admission_budget_max = admission_budget_max
        self.admission_cost = admission_cost
        self.priority_weight = priority_weight
        self.age_bonus = age_bonus
        self.decode_penalty_weight = decode_penalty_weight
        self.long_decode_token_threshold = long_decode_token_threshold
        self._admission_budget = admission_budget_max

    def reset(self) -> None:
        self._admission_budget = self.admission_budget_max

    def _est_seconds(self, req: ObservableRequest) -> float:
        return predicted_service_proxy(req, self.alpha, self.beta) * self.step_size

    def _prefill_proxy_seconds(self, req: ObservableRequest) -> float:
        """TTFT proxy: estimated prefill duration if admitted now."""
        return self.alpha * req.prompt_tokens * self.step_size

    def _laxity(self, req: ObservableRequest, now: float) -> float:
        return req.slo_deadline - now - self._est_seconds(req)

    def _ttft_proxy_slack(self, req: ObservableRequest, now: float) -> float:
        """Remaining deadline budget for predicted prefill after admission."""
        return req.slo_deadline - now - self._prefill_proxy_seconds(req)

    @staticmethod
    def _decode_pressure(gpu: ObservableGPUState) -> float:
        return gpu.decoding_count / max(gpu.max_active_sequences, 1)

    def _system_pressures(
        self, state: ObservableState
    ) -> tuple[float, float, float]:
        if not state.gpu_states:
            return 0.0, 0.0, 0.0
        kv_p = max(kv_fill_ratio(g) for g in state.gpu_states)
        dec_p = max(self._decode_pressure(g) for g in state.gpu_states)
        total_cap = sum(g.max_active_sequences for g in state.gpu_states)
        queue_p = len(state.waiting_queue) / max(total_cap, 1)
        return kv_p, dec_p, queue_p

    def _guard_active(
        self,
        kv_pressure: float,
        decode_pressure: float,
        queue_pressure: float,
        mean_laxity: float,
    ) -> bool:
        return (
            kv_pressure >= self.kv_utilization_threshold
            or decode_pressure >= self.decode_pressure_threshold
            or queue_pressure >= self.queue_overload_factor
            or mean_laxity < 0.0
        )

    def _composite_score(
        self,
        req: ObservableRequest,
        now: float,
        guard_active: bool,
        decode_pressure: float,
    ) -> float:
        lax = self._laxity(req, now)
        urgency = 1.0 / max(lax, _EPS)
        age = now - req.arrival_time
        decode_load = self.beta * req.predicted_output_tokens
        penalty = 0.0
        if guard_active:
            penalty = self.decode_penalty_weight * decode_load * decode_pressure
        return (
            urgency
            + self.priority_weight * req.priority
            + self.age_bonus * age
            - penalty
        )

    def _sort_key(
        self,
        req: ObservableRequest,
        now: float,
        guard_active: bool,
        decode_pressure: float,
    ) -> tuple:
        score = self._composite_score(req, now, guard_active, decode_pressure)
        lax = self._laxity(req, now)
        return (
            -score,
            lax,
            -req.priority,
            req.arrival_time,
            req.request_id,
        )

    def select_action(self, state: ObservableState) -> Action:
        admit: dict[int, list[int]] = {g.gpu_id: [] for g in state.gpu_states}
        if not state.waiting_queue:
            return Action(admit=admit)

        self._admission_budget = min(
            self.admission_budget_max,
            self._admission_budget + self.admission_budget_refill,
        )

        now = state.time
        kv_p, dec_p, queue_p = self._system_pressures(state)
        min_laxity = -self.laxity_threshold
        min_ttft_slack = -self.ttft_slack_threshold

        laxities: list[float] = []
        candidates: list[ObservableRequest] = []
        for req in state.waiting_queue:
            lax = self._laxity(req, now)
            ttft_slack = self._ttft_proxy_slack(req, now)
            if lax < min_laxity or ttft_slack < min_ttft_slack:
                continue
            candidates.append(req)
            laxities.append(lax)

        if not candidates:
            return Action(admit=admit)

        mean_laxity = sum(laxities) / len(laxities)
        guard_active = self._guard_active(kv_p, dec_p, queue_p, mean_laxity)

        if guard_active and kv_p >= self.kv_utilization_threshold:
            candidates = [
                req for req in candidates
                if req.predicted_output_tokens <= self.long_decode_token_threshold
                or self._laxity(req, now) < 0.5
            ]
            if not candidates:
                return Action(admit=admit)

        candidates.sort(
            key=lambda r: self._sort_key(r, now, guard_active, dec_p)
        )

        max_admits = (
            max(1, int(self._admission_budget))
            if guard_active
            else len(candidates)
        )

        gpu_idx = 0
        n_gpus = len(state.gpu_states)
        admitted = 0

        for req in candidates:
            if guard_active and admitted >= max_admits:
                break
            placed = False
            for offset in range(n_gpus):
                gpu = state.gpu_states[(gpu_idx + offset) % n_gpus]
                if self._feasible_on_gpu(gpu, req):
                    admit[gpu.gpu_id].append(req.request_id)
                    gpu.active_request_ids.append(req.request_id)
                    gpu.current_kv_tokens += req.prompt_tokens
                    gpu_idx = (gpu_idx + offset + 1) % n_gpus
                    placed = True
                    admitted += 1
                    if guard_active:
                        self._admission_budget = max(
                            0.0, self._admission_budget - self.admission_cost
                        )
                    break
            if not placed:
                gpu_idx = (gpu_idx + 1) % n_gpus

        return Action(admit=admit)
