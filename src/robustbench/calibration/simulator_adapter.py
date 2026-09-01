"""
Convert measured service curves to simulator config parameters.

The simulator uses step_size=0.001s (1ms) and abstract token budgets.
This module derives simulator config parameters that match measured GPU behavior.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SimulatorParams:
    """Derived simulator parameters from calibrated service curves."""

    # Prefill cost: how many abstract budget tokens are consumed per prompt token
    # Derived from: a1 (s/token) / step_size (s/step) → budget_tokens per token
    prefill_cost_per_token: float

    # Decode: how many steps correspond to one output token
    # At batch_size=1, decode_time_per_token / step_size ≈ steps per token
    decode_steps_per_token: float

    # Suggested step size based on measured decode latency
    step_size_suggestion: float

    # Human-readable notes about derivation
    notes: dict


def derive_simulator_params(
    curves: Any,
    target_step_size: float = 0.001,
    typical_batch_size: int = 4,
    typical_context_tokens: int = 256,
) -> dict:
    """
    Derive simulator config parameters from measured service curves.

    Parameters
    ----------
    curves : ServiceCurves
        Fitted service curves from curve_fitting.py.
    target_step_size : float
        The simulator's wall-clock step size in seconds (default 0.001 = 1ms).
    typical_batch_size : int
        Batch size used for decode calibration (default 4).
    typical_context_tokens : int
        Typical total context size for decode calibration.

    Returns
    -------
    dict with suggested simulator config values and explanations.
    """
    prefill_params = curves.prefill.params
    decode_params = curves.decode.params

    # prefill_time = a0 + a1 * prompt_tokens
    # Marginal cost per prompt token (ignoring constant a0):
    a1 = prefill_params["a1"]          # seconds per prompt token
    a0 = prefill_params.get("a0", 0.0) # constant overhead

    # prefill_cost_per_token:
    # In simulator: each prompt token consumes `prefill_cost_per_token` budget tokens.
    # Total budget needed for P prompt tokens = P * prefill_cost_per_token.
    # We want the simulator to take the same number of steps as reality.
    # Reality: ceil((a0 + a1*P) / step_size) steps.
    # Simulator: ceil(P * cost / max_chunk) steps.
    # For a simple calibration, we match at P=512 (midpoint of calibration grid).
    reference_P = 512.0
    real_steps_at_ref = (a0 + a1 * reference_P) / target_step_size
    # If max_prefill_chunk_tokens = 512 (default), then simulator steps ≈ P * cost / 512
    # → P * cost / 512 = real_steps_at_ref → cost = real_steps_at_ref * 512 / P
    default_max_chunk = 512.0
    prefill_cost_per_token = (real_steps_at_ref * default_max_chunk) / reference_P

    # Clamp to reasonable range
    prefill_cost_per_token = max(0.1, min(prefill_cost_per_token, 100.0))

    # decode_time_per_token = b0 + b1*batch_size + b2*context_tokens
    b0 = decode_params.get("b0", target_step_size)
    b1 = decode_params.get("b1", 0.0)
    b2 = decode_params.get("b2", 0.0)

    # At typical_batch_size and typical_context_tokens:
    decode_time_per_token = b0 + b1 * typical_batch_size + b2 * typical_context_tokens
    decode_time_per_token = max(1e-6, decode_time_per_token)  # clamp

    # Decode steps per output token
    decode_steps_per_token = decode_time_per_token / target_step_size

    # Suggest step_size based on measured decode at bs=1
    decode_at_bs1 = b0 + b1 * 1 + b2 * typical_context_tokens
    step_size_suggestion = max(decode_at_bs1, 1e-5)  # at least 10 microseconds

    params = SimulatorParams(
        prefill_cost_per_token=prefill_cost_per_token,
        decode_steps_per_token=decode_steps_per_token,
        step_size_suggestion=step_size_suggestion,
        notes={
            "prefill_formula": "prefill_time_s = a0 + a1 * prompt_tokens",
            "a0_intercept_s": a0,
            "a1_slope_s_per_token": a1,
            "decode_formula": "decode_time_per_token_s = b0 + b1*batch_size + b2*context_tokens",
            "b0": b0,
            "b1": b1,
            "b2": b2,
            "reference_prompt_tokens": int(reference_P),
            "real_steps_at_reference": real_steps_at_ref,
            "decode_time_per_token_at_typical_batch_s": decode_time_per_token,
            "typical_batch_size": typical_batch_size,
            "typical_context_tokens": typical_context_tokens,
            "target_step_size_s": target_step_size,
            "warning": (
                "prefill_cost_per_token is calibrated to match measured GPU behavior "
                "at reference_prompt_tokens. Accuracy degrades for very short (<32) or "
                "very long (>2048) prompts outside the calibration grid."
            ),
        },
    )

    return {
        "simulator_params": {
            "step_size": target_step_size,
            "prefill_cost_per_token": round(prefill_cost_per_token, 6),
            "decode_steps_per_token": round(decode_steps_per_token, 4),
            "step_size_suggestion": round(step_size_suggestion, 6),
        },
        "derivation_notes": params.notes,
        "dataclass": params,
    }
