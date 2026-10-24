"""
Benchmark backend: Hugging Face Transformers + PyTorch.

Loads the model once and runs the full calibration grid.
Single-request and static-batch mode (no continuous batching).

Limitations:
- No continuous batching (HF Transformers generate() is static)
- No KV cache sharing across requests
- Batch measurements use padding which slightly inflates measured times
- Does not model inter-request scheduling overhead
"""
from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Any

from .measurement import (
    MeasurementResult,
    measure_batch_latency,
    measure_decode_latency,
)
from .prompt_generator import generate_prompt_of_length


CSV_COLUMNS = [
    "prompt_tokens",
    "output_tokens",
    "batch_size",
    "run_id",
    "prefill_time_s",
    "decode_time_per_token_s",
    "total_time_s",
    "peak_memory_gb",
    "gpu_model",
    "model_name",
    "dtype",
    "skipped",
    "skip_reason",
    "timestamp",
]


class BenchmarkBackend:
    """
    Load a HF model once and run a calibration grid.

    Parameters
    ----------
    model_name : str
    dtype : str   e.g. 'bfloat16'
    device_map : str  e.g. 'auto'
    seed : int
    """

    def __init__(
        self,
        model_name: str,
        dtype: str = "bfloat16",
        device_map: str = "auto",
        seed: int = 42,
        trust_remote_code: bool = False,
    ) -> None:
        self.model_name = model_name
        self.dtype = dtype
        self.device_map = device_map
        self.seed = seed

        print(f"[BenchmarkBackend] Loading model {model_name} (dtype={dtype}) ...")
        t0 = time.perf_counter()

        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        torch_dtype = getattr(torch, dtype, torch.bfloat16)

        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=trust_remote_code,
            padding_side="left",
        )
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # Use `dtype` for transformers >=5.0 compatibility (torch_dtype deprecated)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            dtype=torch_dtype,
            device_map=device_map,
            trust_remote_code=trust_remote_code,
        )
        self.model.eval()

        elapsed = time.perf_counter() - t0
        print(f"[BenchmarkBackend] Model loaded in {elapsed:.1f}s")

        # Get GPU model string
        try:
            import torch as _torch
            self.gpu_model = _torch.cuda.get_device_name(0) if _torch.cuda.is_available() else "cpu"
        except Exception:
            self.gpu_model = "unknown"

    def _write_csv_row(self, writer: Any, result: MeasurementResult, run_id: int) -> None:
        total_t = result.prefill_time_mean + result.decode_time_per_token_mean * result.output_tokens
        writer.writerow({
            "prompt_tokens": result.prompt_tokens,
            "output_tokens": result.output_tokens,
            "batch_size": result.batch_size,
            "run_id": run_id,
            "prefill_time_s": "" if result.skipped else result.prefill_time_mean,
            "decode_time_per_token_s": "" if result.skipped else result.decode_time_per_token_mean,
            "total_time_s": "" if result.skipped else total_t,
            "peak_memory_gb": result.peak_memory_gb,
            "gpu_model": result.gpu_model,
            "model_name": result.model_name,
            "dtype": result.dtype,
            "skipped": result.skipped,
            "skip_reason": result.skip_reason,
            "timestamp": result.timestamp,
        })

    def run_calibration_grid(
        self,
        grid_config: dict,
        output_csv: str | Path = "results/gpu_calibration/raw_measurements.csv",
    ) -> list[MeasurementResult]:
        """
        Run calibration grid over all (prompt_length × output_length × batch_size) combinations.

        Parameters
        ----------
        grid_config : dict with keys:
            prompt_lengths, output_lengths, batch_sizes,
            warmup_runs, measurement_runs, seed
        output_csv : path to CSV output

        Returns
        -------
        list of MeasurementResult
        """
        prompt_lengths = grid_config["prompt_lengths"]
        output_lengths = grid_config["output_lengths"]
        batch_sizes = grid_config["batch_sizes"]
        warmup = grid_config.get("warmup_runs", 2)
        runs = grid_config.get("measurement_runs", 5)
        seed = grid_config.get("seed", self.seed)

        total_combos = len(prompt_lengths) * len(output_lengths) * len(batch_sizes)
        print(f"[BenchmarkBackend] Grid: {total_combos} combinations, warmup={warmup}, runs={runs}")

        output_csv = Path(output_csv)
        output_csv.parent.mkdir(parents=True, exist_ok=True)

        # Pre-generate all prompts
        print("[BenchmarkBackend] Generating prompts for grid ...")
        prompt_cache: dict[int, list[int]] = {}
        for pl in prompt_lengths:
            pdata = generate_prompt_of_length(self.tokenizer, pl, seed=seed)
            prompt_cache[pl] = pdata["input_ids"]
            print(f"  prompt_len={pl}: realized={pdata['realized_length']}")

        all_results: list[MeasurementResult] = []
        combo_idx = 0
        grid_start = time.perf_counter()

        file_exists = output_csv.exists()
        with open(output_csv, "a", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=CSV_COLUMNS)
            if not file_exists:
                writer.writeheader()

            for pl in prompt_lengths:
                for ol in output_lengths:
                    for bs in batch_sizes:
                        combo_idx += 1
                        elapsed = time.perf_counter() - grid_start
                        if combo_idx > 1:
                            rate = elapsed / (combo_idx - 1)
                            remaining = rate * (total_combos - combo_idx + 1)
                            eta_str = f"ETA {remaining/60:.1f}min"
                        else:
                            eta_str = "ETA ?"

                        print(
                            f"[{combo_idx}/{total_combos}] prompt={pl} output={ol} batch={bs}  "
                            f"({elapsed:.0f}s elapsed, {eta_str})"
                        )

                        prompt_ids = prompt_cache[pl]

                        if bs == 1:
                            # Single-request measurement
                            result = measure_decode_latency(
                                self.model,
                                self.tokenizer,
                                prompt_ids,
                                output_tokens=ol,
                                warmup=warmup,
                                runs=runs,
                                model_name=self.model_name,
                                dtype=self.dtype,
                                seed=seed,
                            )
                        else:
                            # Batch measurement (returns BatchMeasurementResult, convert)
                            batch_result = measure_batch_latency(
                                self.model,
                                self.tokenizer,
                                [prompt_ids] * bs,
                                output_tokens=ol,
                                warmup=warmup,
                                runs=min(runs, 3),  # fewer runs for batch (slower)
                                model_name=self.model_name,
                                dtype=self.dtype,
                                seed=seed,
                            )
                            # Convert to MeasurementResult
                            result = MeasurementResult(
                                prompt_tokens=pl,
                                output_tokens=ol,
                                batch_size=bs,
                                prefill_time_mean=batch_result.total_time_mean,
                                prefill_time_std=batch_result.total_time_std,
                                prefill_time_min=batch_result.total_time_min,
                                prefill_time_max=batch_result.total_time_max,
                                decode_time_per_token_mean=batch_result.decode_time_per_token_mean,
                                decode_time_per_token_std=batch_result.decode_time_per_token_std,
                                peak_memory_gb=batch_result.peak_memory_gb,
                                gpu_model=batch_result.gpu_model,
                                model_name=batch_result.model_name,
                                dtype=batch_result.dtype,
                                timestamp=batch_result.timestamp,
                                seed=seed,
                                skipped=batch_result.skipped,
                                skip_reason=batch_result.skip_reason,
                            )

                        all_results.append(result)
                        self._write_csv_row(writer, result, run_id=combo_idx)
                        csvfile.flush()

                        if result.skipped:
                            print(f"  SKIPPED: {result.skip_reason}")
                        else:
                            print(
                                f"  prefill={result.prefill_time_mean*1000:.2f}ms  "
                                f"decode_per_tok={result.decode_time_per_token_mean*1000:.3f}ms  "
                                f"mem={result.peak_memory_gb:.2f}GB"
                            )

        n_ok = sum(1 for r in all_results if not r.skipped)
        n_skip = sum(1 for r in all_results if r.skipped)
        total_elapsed = time.perf_counter() - grid_start
        print(
            f"\n[BenchmarkBackend] Grid complete: {n_ok} succeeded, "
            f"{n_skip} skipped, total={total_elapsed/60:.1f}min"
        )
        print(f"[BenchmarkBackend] Results saved to {output_csv}")
        return all_results

    def run_validation_grid(
        self,
        grid_config: dict,
        output_csv: str | Path = "results/gpu_calibration/validation_measurements.csv",
    ) -> list[MeasurementResult]:
        """Run held-out validation grid. Same logic as calibration grid."""
        return self.run_calibration_grid(grid_config, output_csv=output_csv)
