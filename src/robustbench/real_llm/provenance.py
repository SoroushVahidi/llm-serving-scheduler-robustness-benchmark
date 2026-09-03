"""Per-run provenance schema for future real-system validation cells
(docs/REAL_SYSTEM_VALIDATION_PLAN.md). Every real-engine cell that will
eventually be executed must be able to populate every field here before
its measurements are treated as evidence.

This module defines the schema only; it does not populate scientific
values and is not itself scientific evidence.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

PROVENANCE_SCHEMA_VERSION = "real_vllm_provenance_v1"


@dataclass(frozen=True)
class RealRunProvenance:
    # Code/protocol identity
    repository_sha: str
    validation_protocol_sha: str
    hardware_manifest_hash: str

    # Hardware/software environment
    gpu_model: str
    gpu_driver_version: str
    cuda_version: str
    python_version: str
    pytorch_version: str
    vllm_version: str

    # Model/serving configuration
    model_id: str
    model_revision: Optional[str]
    dtype: str
    tensor_parallel_size: int
    max_model_len: int
    gpu_memory_utilization: float
    scheduler_mechanism: str
    scheduler_config: str  # opaque, serialized config identity (e.g. a hash or key=value string)

    # Workload/run identity
    workload_manifest_sha256: str
    run_order_seed: Optional[int]
    run_order_scheme: str  # "deterministic_random" | "abba" | "fixed"
    repetition_index: int
    warmup_request_count: int
    measurement_request_count: int

    # Process record
    server_command: str
    client_command: str
    start_time_iso: str
    end_time_iso: str
    exit_status: int

    def validate(self) -> None:
        """Fail closed on any field left as an obviously-unpopulated
        placeholder. Cheap sanity check, not a full schema validator."""
        required_nonempty = [
            "repository_sha", "validation_protocol_sha", "hardware_manifest_hash",
            "gpu_model", "gpu_driver_version", "cuda_version", "python_version",
            "pytorch_version", "vllm_version", "model_id", "dtype",
            "scheduler_mechanism", "scheduler_config", "workload_manifest_sha256",
            "run_order_scheme", "server_command", "client_command",
            "start_time_iso", "end_time_iso",
        ]
        for field_name in required_nonempty:
            value = getattr(self, field_name)
            if value is None or (isinstance(value, str) and not value.strip()):
                raise ValueError(f"RealRunProvenance.{field_name} must be non-empty")
        if self.repetition_index < 0:
            raise ValueError("repetition_index must be >= 0")
        if self.tensor_parallel_size < 1:
            raise ValueError("tensor_parallel_size must be >= 1")

    def to_dict(self) -> dict:
        d = asdict(self)
        d["provenance_schema_version"] = PROVENANCE_SCHEMA_VERSION
        return d
