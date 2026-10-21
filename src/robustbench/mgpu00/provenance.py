"""Deployment identity and compute-node-only physical-device verification."""
from dataclasses import asdict, dataclass
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import socket
import subprocess

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


def verify_full_a100(record):
    if record.get("cuda_device_count") != 1:
        raise ValueError("Smoke must see exactly one CUDA device")
    d = record["devices"][0]
    if ("A100" not in d["model"] or d["mig_device"] or d["mig_mode_current"] != 0 or
        d["cuda_memory_bytes"] < 75 * 1024**3 or
        d["cuda_uuid"] != d["nvml_uuid"] or not d["cuda_uuid"].startswith("GPU-")):
        raise ValueError("Full A100 identity not independently verified")
    if "gres/gpu:a100:1" not in record["slurm_job_description"]:
        raise ValueError("Explicit full-A100 Slurm allocation not verified")
    return "FULL_GPU_VERIFIED"


def collect_gpu_provenance():
    # This function initializes CUDA. Never call from a login/local-test process.
    if not os.environ.get("SLURM_JOB_ID") or not os.environ.get("SLURMD_NODENAME"):
        raise RuntimeError("Device probe requires an allocated Slurm compute node")
    if socket.gethostname().startswith("login"):
        raise RuntimeError("GPU probe prohibited on login nodes")
    import torch
    import pynvml as nv
    nv.nvmlInit()
    def string(x):
        return x.decode() if isinstance(x, bytes) else str(x)
    devices = []
    for index in range(torch.cuda.device_count()):
        p = torch.cuda.get_device_properties(index)
        uuid = string(p.uuid)
        handle = nv.nvmlDeviceGetHandleByUUID(uuid.encode())
        is_mig = bool(nv.nvmlDeviceIsMigDeviceHandle(handle))
        parent = nv.nvmlDeviceGetDeviceHandleFromMigDeviceHandle(handle) if is_mig else handle
        mig_current, mig_pending = nv.nvmlDeviceGetMigMode(parent)
        devices.append({"cuda_ordinal": index, "model": p.name, "cuda_uuid": uuid,
                        "cuda_memory_bytes": p.total_memory, "nvml_uuid": string(nv.nvmlDeviceGetUUID(handle)),
                        "parent_uuid": string(nv.nvmlDeviceGetUUID(parent)),
                        "parent_model": string(nv.nvmlDeviceGetName(parent)),
                        "parent_memory_bytes": nv.nvmlDeviceGetMemoryInfo(parent).total,
                        "mig_device": is_mig, "mig_mode_current": mig_current, "mig_mode_pending": mig_pending,
                        "mig_gpu_instance_id": nv.nvmlDeviceGetGpuInstanceId(handle) if is_mig else None,
                        "mig_compute_instance_id": nv.nvmlDeviceGetComputeInstanceId(handle) if is_mig else None})
    result = {"node": socket.gethostname(), "slurmd_nodename": os.environ["SLURMD_NODENAME"],
              "slurm_job_id": os.environ["SLURM_JOB_ID"], "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
              "cuda_device_count": torch.cuda.device_count(), "devices": devices,
              "software": {"cuda": torch.version.cuda, "driver": string(nv.nvmlSystemGetDriverVersion()),
                           "torch": torch.__version__, "vllm": importlib.metadata.version("vllm"),
                           "nccl": list(torch.cuda.nccl.version())},
              "slurm_job_description": subprocess.check_output([
                  "/apps/slurm/current/bin/scontrol", "show", "job", "-o", os.environ["SLURM_JOB_ID"]], text=True),
              "nvidia_smi_L": subprocess.check_output(["nvidia-smi", "-L"], text=True)}
    nv.nvmlShutdown()
    result["allocation_kind"] = verify_full_a100(result)
    return result


def write_new_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
