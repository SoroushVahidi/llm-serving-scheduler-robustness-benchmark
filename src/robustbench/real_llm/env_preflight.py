"""Fail-fast dependency preflight for the real-vLLM engineering/scientific path.

Job 1219300 (Wulver, 2026-09-02) reached the calibration round of
scripts/real_vllm/wulver_engineering_gate.py -- after paying for a GPU
allocation, a model load, and two full server rounds -- before crashing on
`ModuleNotFoundError: No module named 'pandas'` inside
calibration_common.aggregate_results. The venv had vllm/torch but was never
given the rest of this repo's declared runtime dependencies.

This module gives every real-vLLM launcher (engineering or scientific) a way
to check the same import surface in milliseconds, before requesting GPU
resources or starting a server, with a clear listing of what is missing
rather than a mid-run traceback.
"""
from __future__ import annotations

import importlib

# Import name -> requirement it satisfies. Mirrors requirements-real-vllm.txt;
# update both together.
REQUIRED_MODULES: dict[str, str] = {
    "numpy": "numpy",
    "pandas": "pandas>=2.0 (used by calibration_common.aggregate_results)",
    "scipy": "scipy>=1.10",
    "dateutil": "python-dateutil (pandas runtime dependency)",
    "yaml": "pyyaml>=6.0",
    "httpx": "httpx (real-vLLM HTTP client)",
    "torch": "torch==2.13.0 (pinned; see requirements-real-vllm.txt)",
    "vllm": "vllm==0.27.1 (pinned; SLAI plugin requires v1 SchedulerInterface)",
}


class RealVLLMEnvironmentError(RuntimeError):
    """Raised when the active Python environment is missing a required import."""


def check_environment(required: dict[str, str] | None = None) -> None:
    """Raise RealVLLMEnvironmentError listing every missing module at once.

    Checking all of them up front (rather than failing on the first missing
    import) avoids the fix-one-crash-on-the-next cycle that a plain import
    traceback produces.
    """
    modules = required if required is not None else REQUIRED_MODULES
    missing = []
    for module_name, requirement in modules.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(f"  - {module_name}: {requirement}")
    if missing:
        raise RealVLLMEnvironmentError(
            "Real-vLLM environment preflight failed. Missing modules:\n"
            + "\n".join(missing)
            + "\n\nInstall via requirements-real-vllm.txt into the active venv "
            "before launching this job. Do not pip install inside a running "
            "scientific Slurm job."
        )
