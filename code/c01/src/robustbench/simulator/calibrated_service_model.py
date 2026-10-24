"""
Calibrated service model using measured GPU performance curves.

Loads a service_curves.json file and uses fitted predictions to estimate
prefill steps and decode steps from token counts.

This is an OPTIONAL alternative to the synthetic ServiceModel.
The original service_model.py is NOT modified. All Phase 1.5 experiments
remain fully reproducible using ServiceModel.

Usage in YAML config:
    service_model:
      type: calibrated
      calibration_file: results/gpu_calibration/service_curves.json
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union


@dataclass
class CalibratedServiceModel:
    """
    Service model backed by measured GPU performance curves.

    Mirrors the interface of ServiceModel but derives timing from
    GPU calibration data rather than synthetic parameters.

    Parameters
    ----------
    calibration_file : str or Path
        Path to service_curves.json produced by fit_service_curves.py.
    step_size : float
        Wall-clock seconds per simulator step (should match service_curves.step_size).
        Default 0.001 (1 ms).
    max_prefill_steps : int
        Hard upper bound on returned prefill step count (safety clamp). Default 10000.
    enable_prefill_modeling : bool
        If False, compute_prefill_steps always returns 0 (instant prefill, Phase 1 mode).
    """

    calibration_file: Union[str, Path] = "results/gpu_calibration/service_curves.json"
    step_size: float = 0.001
    max_prefill_steps: int = 10_000
    enable_prefill_modeling: bool = True

    # ---- ServiceModel interface compatibility fields ----
    # These fields let gpu.py's _step_phase15 work with CalibratedServiceModel
    # without modification. Values are calibration-informed defaults.
    max_prefill_chunk_tokens: int = 512   # tokens processed per prefill chunk per step
    step_token_budget: int = 8192         # total token budget per GPU per step
    decode_first: bool = False            # guarantee decode budget before prefill
    # Opt-in decode/prefill execution-contention model (see
    # docs/decode_prefill_contention_execution_model.md and
    # ServiceModel's own field of the same name). Default False preserves
    # historical behavior exactly.
    enable_decode_prefill_contention: bool = False
    # Disaggregated prefill/decode fields (opt-in; see
    # docs/distserve_faithful_scheduler_reference.md). Defaults match
    # ServiceModel's own defaults (disaggregation off).
    enable_disaggregation: bool = False
    migration_transfer_delay: float = 0.0
    # Live cross-instance relocation field (opt-in; see
    # docs/llumnix_faithful_scheduler_reference.md). Default matches
    # ServiceModel's own default (migration off).
    llumnix_migration_delay: float = 0.0

    # These are populated on first use via _load_curves()
    _curves: Optional[object] = None
    _loaded: bool = False

    def __post_init__(self) -> None:
        self._load_curves()

    def _load_curves(self) -> None:
        """Load and cache service curves from JSON."""
        from ..calibration.curve_fitting import load_service_curves

        path = Path(self.calibration_file)
        if not path.exists():
            raise FileNotFoundError(
                f"Calibration file not found: {path}\n"
                "Run the calibration pipeline to generate it:\n"
                "  python scripts/run_gpu_calibration.py "
                "--config configs/gpu_calibration/calibration_grid.yaml\n"
                "  python scripts/fit_service_curves.py "
                "--input results/gpu_calibration/raw_measurements.csv "
                "--output results/gpu_calibration/service_curves.json"
            )
        self._curves = load_service_curves(path)
        self._loaded = True

    def compute_prefill_steps(self, prompt_tokens: int, batch_size: int = 1) -> int:
        """
        Predict the number of simulator steps to complete prefill.

        Uses: prefill_time_s = a0 + a1 * prompt_tokens
              steps = ceil(prefill_time_s / step_size)

        Out-of-range prompt_tokens are extrapolated with a warning.

        Returns
        -------
        int >= 1 (if enable_prefill_modeling) or 0
        """
        if not self.enable_prefill_modeling:
            return 0

        if prompt_tokens <= 0:
            return 0

        params = self._curves.prefill.params
        a0 = params.get("a0", 0.0)
        a1 = params.get("a1", 0.0)

        # Linear extrapolation
        prefill_time_s = a0 + a1 * prompt_tokens
        prefill_time_s = max(0.0, prefill_time_s)

        steps = math.ceil(prefill_time_s / self.step_size)
        steps = max(1, min(steps, self.max_prefill_steps))

        return steps

    def compute_decode_step_time(
        self, batch_size: int = 1, context_tokens: int = 256
    ) -> float:
        """
        Predict the wall-clock time (seconds) for one decode step.

        Uses: decode_time_per_token_s = b0 + b1*batch_size + b2*context_tokens

        Returns seconds per output token for the given batch size and context.
        """
        params = self._curves.decode.params
        b0 = params.get("b0", self.step_size)
        b1 = params.get("b1", 0.0)
        b2 = params.get("b2", 0.0)

        decode_time_s = b0 + b1 * batch_size + b2 * context_tokens
        return max(1e-6, decode_time_s)

    # ------------------------------------------------------------------
    # Interface compatibility with ServiceModel (Phase 1.5 mirror)
    # ------------------------------------------------------------------

    def compute_prefill_tokens(self, prompt_tokens: int) -> int:
        """
        Return abstract prefill token count (used for budget accounting).

        For CalibratedServiceModel we return the raw prompt_tokens because
        the calibrated model bypasses the 'cost_per_token' abstraction.
        """
        if not self.enable_prefill_modeling:
            return 0
        return max(0, prompt_tokens)

    def prefill_steps(self, prompt_tokens: int) -> int:
        """Alias for compute_prefill_steps (ServiceModel interface compatibility)."""
        return self.compute_prefill_steps(prompt_tokens)

    def decode_time(self, output_tokens: int, batch_size: int = 1) -> float:
        """Wall-clock seconds to decode output_tokens tokens."""
        per_token = self.compute_decode_step_time(batch_size=batch_size)
        return output_tokens * per_token


def load_calibrated_service_model_from_config(
    config: dict,
    default_calibration_file: str = "results/gpu_calibration/service_curves.json",
) -> CalibratedServiceModel:
    """
    Instantiate CalibratedServiceModel from a YAML service_model config section.

    Config format:
        service_model:
          type: calibrated
          calibration_file: results/gpu_calibration/service_curves.json
          step_size: 0.001            # optional, default 0.001
          enable_prefill_modeling: true  # optional, default true

    Parameters
    ----------
    config : dict (the service_model: section of a YAML)
    default_calibration_file : str fallback path

    Returns
    -------
    CalibratedServiceModel
    """
    cal_file = config.get("calibration_file", default_calibration_file)
    step_size = float(config.get("step_size", 0.001))
    enable_prefill = bool(config.get("enable_prefill_modeling", True))
    max_steps = int(config.get("max_prefill_steps", 10_000))

    return CalibratedServiceModel(
        calibration_file=cal_file,
        step_size=step_size,
        max_prefill_steps=max_steps,
        enable_prefill_modeling=enable_prefill,
    )
