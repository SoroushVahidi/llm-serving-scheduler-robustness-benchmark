"""
Factory for building service models from YAML config dicts.

Supports two service model types:
  type: synthetic   (default) — uses ServiceModel with hand-tuned parameters
  type: calibrated             — uses CalibratedServiceModel backed by GPU measurements

Usage in YAML:
    service_model:
      type: synthetic          # optional; this is the default
      enable_prefill_modeling: true
      prefill_cost_per_token: 1.0
      ...

    service_model:
      type: calibrated
      calibration_file: results/gpu_calibration/service_curves.json
      enable_prefill_modeling: true   # optional, default true for calibrated
      step_size: 0.001                # optional, default 0.001
"""
from __future__ import annotations

import logging
from typing import Union

from .service_model import ServiceModel
from .calibrated_service_model import (
    CalibratedServiceModel,
)

_log = logging.getLogger(__name__)

_VALID_TYPES = ("synthetic", "calibrated")


def build_service_model_from_config(
    cfg: dict,
    default_calibration_file: str = "results/gpu_calibration/service_curves.json",
) -> Union[ServiceModel, CalibratedServiceModel]:
    """Build and return a service model from a config dict.

    Parameters
    ----------
    cfg : dict
        The top-level experiment config dict (not just the service_model section).
    default_calibration_file : str
        Fallback path used when service_model.type is 'calibrated' but
        calibration_file is not specified.

    Returns
    -------
    ServiceModel or CalibratedServiceModel

    Raises
    ------
    ValueError
        If service_model.type is specified but not one of the valid types.
    FileNotFoundError
        If type is 'calibrated' and the calibration file does not exist.
    """
    sim_cfg = cfg.get("simulator", {})
    sm_cfg = cfg.get("service_model", {})

    model_type = sm_cfg.get("type", "synthetic").lower()

    if model_type not in _VALID_TYPES:
        raise ValueError(
            f"Unknown service_model.type={model_type!r}. "
            f"Valid types: {_VALID_TYPES}"
        )

    if model_type == "calibrated":
        cal_file = sm_cfg.get("calibration_file", default_calibration_file)
        step_size = float(sm_cfg.get("step_size", sim_cfg.get("step_size", 0.001)))
        enable_prefill = bool(sm_cfg.get("enable_prefill_modeling", True))
        max_prefill_steps = int(sm_cfg.get("max_prefill_steps", 10_000))

        _log.info("Service model: CalibratedServiceModel (file=%s)", cal_file)
        print(f"  Service model : calibrated  ({cal_file})")
        print(f"  Prefill model : enable={enable_prefill}, step_size={step_size}")

        max_prefill_chunk = int(sm_cfg.get("max_prefill_chunk_tokens", 512))
        step_token_budget = int(sm_cfg.get("step_token_budget", 8192))
        decode_first = bool(sm_cfg.get("decode_first", False))
        enable_decode_prefill_contention = bool(
            sm_cfg.get("enable_decode_prefill_contention", False)
        )

        return CalibratedServiceModel(
            calibration_file=cal_file,
            step_size=step_size,
            max_prefill_steps=max_prefill_steps,
            enable_prefill_modeling=enable_prefill,
            max_prefill_chunk_tokens=max_prefill_chunk,
            step_token_budget=step_token_budget,
            decode_first=decode_first,
            enable_decode_prefill_contention=enable_decode_prefill_contention,
        )

    # synthetic (default)
    step_size = float(sim_cfg.get("step_size", 0.001))
    model = ServiceModel(
        step_size=step_size,
        enable_prefill_modeling=bool(sm_cfg.get("enable_prefill_modeling", False)),
        prefill_cost_per_token=float(sm_cfg.get("prefill_cost_per_token", 1.0)),
        max_prefill_chunk_tokens=int(sm_cfg.get("max_prefill_chunk_tokens", 512)),
        step_token_budget=int(sm_cfg.get("step_token_budget", 4096)),
        decode_first=bool(sm_cfg.get("decode_first", False)),
        allow_chunked_prefill=bool(sm_cfg.get("allow_chunked_prefill", True)),
        enable_decode_prefill_contention=bool(
            sm_cfg.get("enable_decode_prefill_contention", False)
        ),
    )
    _log.info("Service model: synthetic  enable_prefill=%s", model.enable_prefill_modeling)
    print(f"  Service model : synthetic  enable_prefill={model.enable_prefill_modeling}")
    return model
