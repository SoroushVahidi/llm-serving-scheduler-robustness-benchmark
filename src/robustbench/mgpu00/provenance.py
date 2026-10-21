"""Deployment identity and compute-node-only physical-device verification."""
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re

from . import EXPERIMENT_VERSION


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class ExperimentIdentity:
    model: str
    model_revision: str
    tokenizer: str
    tokenizer_revision: str
    precision: str
    max_model_len: int
    gpu_model: str
    allocation_kind: str
    gpu_count: int
    nodes: int
    tensor_parallel: int
    pipeline_parallel: int
    data_parallel: int
    policy: str
    policy_parameters: dict
    workload_sha256: str
    calibration_sha256: str
    repetition: int
    git_commit: str
    environment: dict
    operating_region: str
    experiment_version: str = EXPERIMENT_VERSION

    def __post_init__(self):
        for name in ("workload_sha256", "calibration_sha256"):
            if not re.fullmatch("[0-9a-f]{64}", getattr(self, name)):
                raise ValueError(f"Missing/invalid {name}")
        for name in ("model_revision", "tokenizer_revision", "git_commit"):
            if not re.fullmatch("[0-9a-f]{40}", getattr(self, name)):
                raise ValueError(f"Immutable 40-character commit required: {name}")
        for name in ("max_model_len", "gpu_count", "nodes", "tensor_parallel", "pipeline_parallel", "data_parallel"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(name)
        if self.gpu_count != self.tensor_parallel * self.pipeline_parallel * self.data_parallel:
            raise ValueError("GPU count must equal TP x PP x DP")
        if self.repetition < 0 or self.allocation_kind not in {"FULL_GPU_VERIFIED", "MIG_VERIFIED"}:
            raise ValueError("Invalid repetition/allocation")
        if not all(self.environment.get(k) for k in ("cuda", "driver", "torch", "vllm", "nccl")):
            raise ValueError("Incomplete software provenance")

    @property
    def experiment_id(self):
        return f"{self.experiment_version}-{canonical_hash(asdict(self))}"


# Kept here as the public API used by existing callers/tests.
from .gpu_probe import verify_full_a100, probe_and_verify, collect_raw


def collect_gpu_provenance(diagnostic_directory):
    return probe_and_verify(diagnostic_directory, collect_raw)


def write_new_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
