"""Launch/stop a local vLLM OpenAI-compatible API server as a subprocess,
for real-system validation engineering (docs/REAL_SYSTEM_VALIDATION_PLAN.md).

This is infrastructure only: it starts a server process, waits for it to
report ready, and stops it cleanly. It does not select scientific
validation cases and does not interpret any generated text.
"""
from __future__ import annotations

import contextlib
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import List, Optional

import httpx


@dataclass
class VLLMServerHandle:
    process: subprocess.Popen
    host: str
    port: int
    log_path: str
    command: List[str] = field(default_factory=list)

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def is_alive(self) -> bool:
        return self.process.poll() is None

    def stop(self, timeout_s: float = 20.0) -> int:
        if self.process.poll() is not None:
            return self.process.returncode
        self.process.terminate()
        try:
            self.process.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=timeout_s)
        return self.process.returncode


def start_vllm_server(
    *,
    model: str,
    host: str = "127.0.0.1",
    port: int = 8100,
    log_path: str,
    extra_args: Optional[List[str]] = None,
    gpu_memory_utilization: float = 0.5,
    max_model_len: Optional[int] = None,
    scheduling_policy: Optional[str] = None,  # "fcfs" | "priority"
    enable_chunked_prefill: Optional[bool] = None,
    vllm_executable: Optional[str] = None,
) -> VLLMServerHandle:
    """Start `vllm serve <model>` as a background subprocess, stdout/stderr
    redirected to `log_path`. Does not block until ready -- call
    `wait_for_server_ready` separately.
    """
    exe = vllm_executable or "vllm"
    cmd: List[str] = [
        exe, "serve", model,
        "--host", host,
        "--port", str(port),
        "--gpu-memory-utilization", str(gpu_memory_utilization),
    ]
    if max_model_len is not None:
        cmd += ["--max-model-len", str(max_model_len)]
    if scheduling_policy is not None:
        cmd += ["--scheduling-policy", scheduling_policy]
    if enable_chunked_prefill is True:
        cmd += ["--enable-chunked-prefill"]
    elif enable_chunked_prefill is False:
        cmd += ["--no-enable-chunked-prefill"]
    if extra_args:
        cmd += list(extra_args)

    log_f = open(log_path, "w")
    proc = subprocess.Popen(
        cmd, stdout=log_f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
    )
    return VLLMServerHandle(process=proc, host=host, port=port, log_path=log_path, command=cmd)


def wait_for_server_ready(handle: VLLMServerHandle, timeout_s: float = 600.0, poll_interval_s: float = 2.0) -> bool:
    """Poll the OpenAI-compatible /v1/models endpoint until it responds, the
    process exits, or timeout. Returns True iff the server became ready
    while the process was still alive.
    """
    deadline = time.monotonic() + timeout_s
    url = f"{handle.base_url}/v1/models"
    while time.monotonic() < deadline:
        if not handle.is_alive():
            return False
        with contextlib.suppress(Exception):
            resp = httpx.get(url, timeout=5.0)
            if resp.status_code == 200:
                return True
        time.sleep(poll_interval_s)
    return False


def gpu_memory_used_mib(gpu_index: int = 0) -> Optional[int]:
    """Best-effort GPU memory query via nvidia-smi; returns None if
    unavailable (e.g. no NVIDIA GPU / driver on this host)."""
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                f"--id={gpu_index}",
                "--query-gpu=memory.used",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=10,
        )
        return int(out.strip().splitlines()[0])
    except Exception:
        return None
