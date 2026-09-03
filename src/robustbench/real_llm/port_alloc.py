"""Collision-resistant dynamic port allocation for real-vLLM Slurm array
tasks.

Replaces the calibration launcher's known-buggy scheme
(`scripts/real_vllm/run_rq6_calibration.sbatch`:
`PORT=$((8100 + SLURM_ARRAY_TASK_ID % 100))`), which collided whenever two
array indices shared a residue mod 100 on the same node (task 19 vs task
119, both `% 100 == 19`; diagnosed and recorded in
docs/LSSP_NEW_CHAT_HANDOFF_20260903.md). That scheme derives a port from the
array index alone, with no availability check, so a fixed number of
concurrently-scheduled tasks on one node WILL collide once the array is
larger than the modulus.

This module instead asks the OS for an actually-free ephemeral port
(`bind((host, 0))`, then read back the OS-assigned port), which is correct
by construction for concurrency on one node: the kernel never hands out an
already-bound port. The remaining risk is a bind-time-to-vLLM-start-time
TOCTOU race (another process could grab the same port in between) -- this is
inherent to "ask, then release, then reuse" port allocation on any POSIX
system, not specific to this design, and is mitigated by the caller
(`scripts/real_vllm/run_rq6_validation.py`) retrying with a freshly
allocated port if the vLLM server process fails to become ready.
"""
from __future__ import annotations

import socket
from dataclasses import dataclass


@dataclass(frozen=True)
class PortAllocation:
    port: int
    host: str
    method: str


def allocate_port(host: str = "127.0.0.1") -> PortAllocation:
    """Binds a throwaway TCP socket to `(host, 0)`, letting the OS assign a
    currently-free ephemeral port, reads the assigned port back, then closes
    the socket immediately so the caller (vLLM) can bind it. `SO_REUSEADDR`
    is set only to allow immediate rebinding of a port that was itself very
    recently released (standard practice); it does not weaken the
    free-port guarantee -- the OS still only assigns `getsockname()[1]` from
    ports it currently considers free at bind time.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, 0))
        port = s.getsockname()[1]
    return PortAllocation(port=port, host=host, method="os_ephemeral_bind0")
