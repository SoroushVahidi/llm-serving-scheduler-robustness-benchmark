"""Registry mapping a source-dataset name to its adapter class.

Kept deliberately tiny: adding a new source means adding one adapter module and one
registry entry, nothing else. See docs/EXTERNAL_WORKLOAD_CANONICAL_SCHEMA.md and
docs/BENCHMARK_V2_PUBLIC_TRACE_SELECTION.md for which sources are actually selected
for Benchmark v2 (registration here does not imply selection).
"""
from __future__ import annotations

from .adapters.base import TraceAdapter

_REGISTRY: dict[str, type[TraceAdapter]] = {}


def register(name: str):
    def _decorator(cls: type[TraceAdapter]) -> type[TraceAdapter]:
        if name in _REGISTRY and _REGISTRY[name] is not cls:
            raise ValueError(f"adapter name '{name}' already registered to a different class")
        _REGISTRY[name] = cls
        return cls
    return _decorator


def get_adapter(name: str) -> type[TraceAdapter]:
    if name not in _REGISTRY:
        raise KeyError(f"no adapter registered for '{name}'; known: {sorted(_REGISTRY)}")
    return _REGISTRY[name]


def registered_names() -> list[str]:
    return sorted(_REGISTRY)
