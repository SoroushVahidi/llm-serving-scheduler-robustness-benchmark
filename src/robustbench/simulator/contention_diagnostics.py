"""Diagnostic-only per-step decode/prefill contention signals.

Purely observational: recorded alongside the existing
`GPUState.step_active_counts`/`step_kv_used` history from inside
`GPUState._step_phase15`, never consulted by any execution or objective
code. Exists so that a scenario/window can be checked for whether the
`enable_decode_prefill_contention` mechanism (see
docs/decode_prefill_contention_execution_model.md) was actually
*exercised* -- as opposed to inferring that indirectly from whether two
policies' final outcome metrics happen to differ, which conflates "the
mechanism never fired" with "the mechanism fired but had no effect on the
chosen objective" (see the Selector v2 contention-validation pilot's
follow-up audit, docs/selector_v2_contention_frontier_search.md).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StepContentionDiagnostics:
    step_index: int
    time: float
    num_decoding: int
    num_prefilling: int
    decode_tokens_served: int
    # Decoding requests that were present this step but received zero
    # progress -- can only be > 0 under
    # `enable_decode_prefill_contention=True, decode_first=False`; the
    # decode-protected path (`decode_first=True`, or the default legacy
    # path) always serves every decoding request unconditionally, so this
    # is provably always 0 there (see
    # TestContentionDiagnostics::test_decode_protected_never_defers_decode).
    decode_tokens_deferred: int
    prefill_tokens_served: int
    # Prefilling requests that received ZERO chunk progress this step
    # despite having remaining work -- distinct from decode contention:
    # this fires under pure prefill-vs-prefill competition (e.g. two
    # simultaneously-arrived, differently-sized requests, or an admission-
    # order/arrival-order mismatch -- see
    # docs/selector_v2_contention_frontier_search.md) even when no request
    # is decoding at all.
    prefill_requests_stalled: int
    budget_used: int
    budget_total: int

    @property
    def decode_stalled(self) -> bool:
        return self.decode_tokens_deferred > 0

    @property
    def prefill_stalled(self) -> bool:
        return self.prefill_requests_stalled > 0

    @property
    def budget_saturated(self) -> bool:
        return self.budget_total > 0 and self.budget_used >= self.budget_total

    @property
    def prefill_scheduled_while_decode_deferred(self) -> bool:
        """True when, in this same step, prefill work consumed budget
        AND a decoding request was starved of budget -- the specific
        interaction shape "an earlier-priority prefill claim starved a
        pending decode claim" that the original contention_fixtures.py
        family was built to exercise (see that module's docstring for why
        it is structurally hard to sustain via a normal arrival trace)."""
        return self.prefill_tokens_served > 0 and self.decode_tokens_deferred > 0


def summarize(history: list) -> dict:
    """Cheap aggregate summary of a `List[StepContentionDiagnostics]` --
    used by scenario/window classification, not by any policy or metric."""
    if not history:
        return {
            "decode_stalled_steps": 0,
            "cumulative_decode_tokens_deferred": 0,
            "steps_with_prefill_while_decode_deferred": 0,
            "max_decode_tokens_deferred": 0,
            "budget_saturated_steps": 0,
            "budget_saturation_fraction": 0.0,
            "n_steps": 0,
        }
    n = len(history)
    return {
        "decode_stalled_steps": sum(1 for d in history if d.decode_stalled),
        "cumulative_decode_tokens_deferred": sum(d.decode_tokens_deferred for d in history),
        "steps_with_prefill_while_decode_deferred": sum(
            1 for d in history if d.prefill_scheduled_while_decode_deferred
        ),
        "max_decode_tokens_deferred": max(d.decode_tokens_deferred for d in history),
        "prefill_stalled_steps": sum(1 for d in history if d.prefill_stalled),
        "cumulative_prefill_requests_stalled": sum(d.prefill_requests_stalled for d in history),
        "budget_saturated_steps": sum(1 for d in history if d.budget_saturated),
        "budget_saturation_fraction": sum(1 for d in history if d.budget_saturated) / n,
        "n_steps": n,
    }
