"""
GPU timing measurement primitives.

Measures prefill (TTFT proxy) and decode (TPOT) using CUDA events.

NOTE on what is measured:
- prefill_time here = full forward pass on prompt tokens + generation of exactly 1 new
  token. This is NOT the same as true TTFT from a client perspective (which includes
  network and queuing). At large prompt lengths this measurement is dominated by the
  actual prefill computation.
- decode_time_per_token = (total_generate_time - estimated_prefill_time) / output_tokens.
  This is an approximation because the two forward passes are not fully separable.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass
class MeasurementResult:
    """Container for a single calibration measurement."""

    # Input dimensions
    prompt_tokens: int = 0
    output_tokens: int = 0
    batch_size: int = 1

    # Prefill timing (seconds)
    prefill_time_mean: float = 0.0
    prefill_time_std: float = 0.0
    prefill_time_min: float = 0.0
    prefill_time_max: float = 0.0

    # Decode timing (seconds per token)
    decode_time_per_token_mean: float = 0.0
    decode_time_per_token_std: float = 0.0

    # Memory
    peak_memory_gb: float = 0.0

    # Metadata
    gpu_model: str = ""
    model_name: str = ""
    dtype: str = ""
    timestamp: str = ""
    seed: int = 42

    # Error handling
    skipped: bool = False
    skip_reason: str = ""


@dataclass
class BatchMeasurementResult:
    """Container for a static-batch calibration measurement."""

    prompt_tokens: int = 0
    output_tokens: int = 0
    batch_size: int = 1

    # Total batch latency (seconds)
    total_time_mean: float = 0.0
    total_time_std: float = 0.0
    total_time_min: float = 0.0
    total_time_max: float = 0.0

    # Per-token decode latency for batch
    decode_time_per_token_mean: float = 0.0
    decode_time_per_token_std: float = 0.0

    # Memory
    peak_memory_gb: float = 0.0

    gpu_model: str = ""
    model_name: str = ""
    dtype: str = ""
    timestamp: str = ""
    seed: int = 42
    skipped: bool = False
    skip_reason: str = ""


def _get_gpu_info() -> str:
    """Return GPU model string if CUDA available."""
    try:
        import torch

        if torch.cuda.is_available():
            return torch.cuda.get_device_name(0)
    except ImportError:
        pass
    return "cpu"


def _get_peak_memory_gb() -> float:
    """Return peak GPU memory allocated in GB."""
    try:
        import torch

        if torch.cuda.is_available():
            return torch.cuda.max_memory_allocated() / (1024**3)
    except ImportError:
        pass
    return 0.0


def _timestamp() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def measure_prefill_latency(
    model: Any,
    tokenizer: Any,
    prompt_ids: list[int],
    warmup: int = 2,
    runs: int = 5,
    model_name: str = "",
    dtype: str = "",
    seed: int = 42,
) -> MeasurementResult:
    """
    Measure prefill latency for a single prompt using CUDA events.

    Each run: forward pass on prompt_ids with max_new_tokens=1 (force exactly
    one decode step after prefill).
    Warmup runs are discarded.

    IMPORTANT: This measures prefill + one decode step, not pure prefill.
    At large prompt lengths (>=128 tokens) the measurement is dominated by prefill.
    """
    import torch

    result = MeasurementResult(
        prompt_tokens=len(prompt_ids),
        output_tokens=1,
        batch_size=1,
        gpu_model=_get_gpu_info(),
        model_name=model_name,
        dtype=dtype,
        timestamp=_timestamp(),
        seed=seed,
    )

    try:
        device = next(model.parameters()).device
        input_tensor = torch.tensor([prompt_ids], dtype=torch.long, device=device)
        attention_mask = torch.ones_like(input_tensor)

        times = []

        for run_idx in range(warmup + runs):
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.reset_peak_memory_stats()
                torch.cuda.synchronize()

            if torch.cuda.is_available():
                start_event = torch.cuda.Event(enable_timing=True)
                end_event = torch.cuda.Event(enable_timing=True)
                start_event.record()
            else:
                t0 = time.perf_counter()

            with torch.no_grad():
                _ = model.generate(
                    input_tensor,
                    attention_mask=attention_mask,
                    max_new_tokens=1,
                    do_sample=False,
                    use_cache=True,
                    pad_token_id=tokenizer.eos_token_id,
                )

            if torch.cuda.is_available():
                end_event.record()
                torch.cuda.synchronize()
                elapsed_s = start_event.elapsed_time(end_event) / 1000.0
            else:
                elapsed_s = time.perf_counter() - t0

            if run_idx >= warmup:
                times.append(elapsed_s)

        import numpy as np

        arr = np.array(times)
        result.prefill_time_mean = float(arr.mean())
        result.prefill_time_std = float(arr.std())
        result.prefill_time_min = float(arr.min())
        result.prefill_time_max = float(arr.max())
        result.peak_memory_gb = _get_peak_memory_gb()

    except Exception as e:
        oom = torch.cuda.OutOfMemoryError if hasattr(torch.cuda, "OutOfMemoryError") else RuntimeError
        if isinstance(e, oom) or "out of memory" in str(e).lower():
            result.skipped = True
            result.skip_reason = f"OOM: {e}"
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        else:
            result.skipped = True
            result.skip_reason = f"Error: {type(e).__name__}: {e}"

    return result


def measure_decode_latency(
    model: Any,
    tokenizer: Any,
    prompt_ids: list[int],
    output_tokens: int,
    warmup: int = 2,
    runs: int = 5,
    model_name: str = "",
    dtype: str = "",
    seed: int = 42,
) -> MeasurementResult:
    """
    Measure per-token decode latency.

    Method:
    1. Run generate() with max_new_tokens=output_tokens, measure total time.
    2. Run generate() with max_new_tokens=1 to estimate prefill-only time.
    3. per_token_decode = (total_time - prefill_time) / (output_tokens - 1)
       where we subtract 1 because the first token is measured in the prefill pass.

    Returns per-token decode time in seconds.
    """
    import torch
    import numpy as np

    result = MeasurementResult(
        prompt_tokens=len(prompt_ids),
        output_tokens=output_tokens,
        batch_size=1,
        gpu_model=_get_gpu_info(),
        model_name=model_name,
        dtype=dtype,
        timestamp=_timestamp(),
        seed=seed,
    )

    if output_tokens <= 1:
        result.skipped = True
        result.skip_reason = "output_tokens must be > 1 for decode measurement"
        return result

    try:
        device = next(model.parameters()).device
        input_tensor = torch.tensor([prompt_ids], dtype=torch.long, device=device)
        attention_mask = torch.ones_like(input_tensor)

        total_times = []
        prefill_times = []

        for run_idx in range(warmup + runs):
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()

            # Measure total time (prefill + decode of output_tokens)
            if torch.cuda.is_available():
                s_ev = torch.cuda.Event(enable_timing=True)
                e_ev = torch.cuda.Event(enable_timing=True)
                s_ev.record()
            else:
                t0 = time.perf_counter()

            with torch.no_grad():
                _ = model.generate(
                    input_tensor,
                    attention_mask=attention_mask,
                    max_new_tokens=output_tokens,
                    do_sample=False,
                    use_cache=True,
                    pad_token_id=tokenizer.eos_token_id,
                )

            if torch.cuda.is_available():
                e_ev.record()
                torch.cuda.synchronize()
                total_t = s_ev.elapsed_time(e_ev) / 1000.0
            else:
                total_t = time.perf_counter() - t0

            # Measure prefill-only (1 new token)
            if torch.cuda.is_available():
                s_ev2 = torch.cuda.Event(enable_timing=True)
                e_ev2 = torch.cuda.Event(enable_timing=True)
                torch.cuda.synchronize()
                s_ev2.record()
            else:
                t0p = time.perf_counter()

            with torch.no_grad():
                _ = model.generate(
                    input_tensor,
                    attention_mask=attention_mask,
                    max_new_tokens=1,
                    do_sample=False,
                    use_cache=True,
                    pad_token_id=tokenizer.eos_token_id,
                )

            if torch.cuda.is_available():
                e_ev2.record()
                torch.cuda.synchronize()
                prefill_t = s_ev2.elapsed_time(e_ev2) / 1000.0
            else:
                prefill_t = time.perf_counter() - t0p

            if run_idx >= warmup:
                total_times.append(total_t)
                prefill_times.append(prefill_t)

        total_arr = np.array(total_times)
        prefill_arr = np.array(prefill_times)

        # Derive per-token decode time
        # decode_tokens = output_tokens - 1 (first token included in prefill pass)
        decode_tokens = max(1, output_tokens - 1)
        per_token = (total_arr - prefill_arr) / decode_tokens
        # Clamp negative values (can happen due to measurement noise at short outputs)
        per_token = np.maximum(per_token, 1e-6)

        result.prefill_time_mean = float(prefill_arr.mean())
        result.prefill_time_std = float(prefill_arr.std())
        result.prefill_time_min = float(prefill_arr.min())
        result.prefill_time_max = float(prefill_arr.max())
        result.decode_time_per_token_mean = float(per_token.mean())
        result.decode_time_per_token_std = float(per_token.std())
        result.peak_memory_gb = _get_peak_memory_gb()

    except Exception as e:
        oom = torch.cuda.OutOfMemoryError if hasattr(torch.cuda, "OutOfMemoryError") else RuntimeError
        if isinstance(e, oom) or "out of memory" in str(e).lower():
            result.skipped = True
            result.skip_reason = f"OOM: {e}"
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        else:
            result.skipped = True
            result.skip_reason = f"Error: {type(e).__name__}: {e}"

    return result


def measure_batch_latency(
    model: Any,
    tokenizer: Any,
    prompt_ids_list: list[list[int]],
    output_tokens: int,
    warmup: int = 2,
    runs: int = 3,
    model_name: str = "",
    dtype: str = "",
    seed: int = 42,
) -> BatchMeasurementResult:
    """
    Measure latency for a static batch of prompts (all padded to same length).

    Records peak GPU memory usage.
    """
    import torch
    import numpy as np

    batch_size = len(prompt_ids_list)
    max_len = max(len(ids) for ids in prompt_ids_list)

    result = BatchMeasurementResult(
        prompt_tokens=max_len,
        output_tokens=output_tokens,
        batch_size=batch_size,
        gpu_model=_get_gpu_info(),
        model_name=model_name,
        dtype=dtype,
        timestamp=_timestamp(),
        seed=seed,
    )

    try:
        device = next(model.parameters()).device
        pad_id = tokenizer.eos_token_id if tokenizer.pad_token_id is None else tokenizer.pad_token_id

        # Left-pad all sequences to max_len
        padded = []
        masks = []
        for ids in prompt_ids_list:
            pad_len = max_len - len(ids)
            padded.append([pad_id] * pad_len + ids)
            masks.append([0] * pad_len + [1] * len(ids))

        input_tensor = torch.tensor(padded, dtype=torch.long, device=device)
        attention_mask = torch.tensor(masks, dtype=torch.long, device=device)

        total_times = []

        for run_idx in range(warmup + runs):
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.reset_peak_memory_stats()
                torch.cuda.synchronize()

            if torch.cuda.is_available():
                s_ev = torch.cuda.Event(enable_timing=True)
                e_ev = torch.cuda.Event(enable_timing=True)
                s_ev.record()
            else:
                t0 = time.perf_counter()

            with torch.no_grad():
                _ = model.generate(
                    input_tensor,
                    attention_mask=attention_mask,
                    max_new_tokens=output_tokens,
                    do_sample=False,
                    use_cache=True,
                    pad_token_id=pad_id,
                )

            if torch.cuda.is_available():
                e_ev.record()
                torch.cuda.synchronize()
                elapsed_s = s_ev.elapsed_time(e_ev) / 1000.0
            else:
                elapsed_s = time.perf_counter() - t0

            if run_idx >= warmup:
                total_times.append(elapsed_s)

        arr = np.array(total_times)
        result.total_time_mean = float(arr.mean())
        result.total_time_std = float(arr.std())
        result.total_time_min = float(arr.min())
        result.total_time_max = float(arr.max())
        result.peak_memory_gb = _get_peak_memory_gb()

        # Estimate per-token decode for batch
        if output_tokens > 1:
            result.decode_time_per_token_mean = float(arr.mean()) / output_tokens
            result.decode_time_per_token_std = float(arr.std()) / output_tokens

    except Exception as e:
        oom = torch.cuda.OutOfMemoryError if hasattr(torch.cuda, "OutOfMemoryError") else RuntimeError
        if isinstance(e, oom) or "out of memory" in str(e).lower():
            result.skipped = True
            result.skip_reason = f"OOM: {e}"
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        else:
            result.skipped = True
            result.skip_reason = f"Error: {type(e).__name__}: {e}"

    return result
