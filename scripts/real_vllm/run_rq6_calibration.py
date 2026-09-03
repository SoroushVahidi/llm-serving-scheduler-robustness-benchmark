#!/usr/bin/env python3
"""Run one RQ6 per-window real-vLLM calibration (one Slurm array task = one
frozen window), per docs/RQ6_REAL_VLLM_SCIENTIFIC_PROTOCOL_20260902.md's
"Calibration population" section: 120 independent calibrations (3 sources
x 40 windows/source), each against exactly its own 200 frozen requests,
reference policy always `vllm_faithful`.

Starts one vLLM server (once per task, not once per candidate), reuses it
across the whole 32-candidate bisection for this window, then stops it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

import httpx  # noqa: E402

from robustbench.real_llm.calibration_common import PlannedRequest  # noqa: E402
from robustbench.real_llm.rq6_calibration import (  # noqa: E402
    REFERENCE_POLICY,
    bisect_lambda_ref_real,
)
from robustbench.real_llm.vllm_openai_client import call_non_streaming  # noqa: E402
from robustbench.real_llm.vllm_process import start_vllm_server, wait_for_server_ready  # noqa: E402

STAMP_SCIENTIFIC = "RQ6_REAL_VLLM_CALIBRATION"
DEFAULT_MANIFEST_DIR = REPO_ROOT / "artifacts/manifests/rq6_real_vllm"
DEFAULT_CALIBRATION_MANIFEST = REPO_ROOT / "configs/real_vllm/rq6_calibration_manifest_v2_20260903.json"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).decode().strip()


def enumerate_calibration_units(manifest_dir: Path) -> List[Tuple[str, str, Path]]:
    """Deterministic (source, window_id, manifest_path) enumeration across
    all three workload manifests, sorted by (source, window_id) --
    Slurm array index i maps to units[i]. Re-running this enumeration
    against the same manifests always produces the same order (both lists
    are sorted), so a given SLURM_ARRAY_TASK_ID always names the same
    window across resubmissions."""
    units: List[Tuple[str, str, Path]] = []
    for path in sorted(manifest_dir.glob("rq6_workload_*.json")):
        with open(path) as f:
            manifest = json.load(f)
        for w in manifest["windows"]:
            units.append((manifest["source"], w["window_id"], path))
    units.sort(key=lambda u: (u[0], u[1]))
    return units


def load_window_requests(manifest_path: Path, window_id: str) -> List[Dict[str, Any]]:
    with open(manifest_path) as f:
        manifest = json.load(f)
    for w in manifest["windows"]:
        if w["window_id"] == window_id:
            return w["requests"], manifest, w
    raise KeyError(f"window_id {window_id!r} not found in {manifest_path}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    ap.add_argument("--calibration-manifest", type=Path, default=DEFAULT_CALIBRATION_MANIFEST)
    ap.add_argument("--array-index", type=int, default=None,
                     help="0-119; defaults to $SLURM_ARRAY_TASK_ID if unset")
    ap.add_argument("--model", required=True)
    ap.add_argument("--vllm-executable", default="vllm")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8100)
    ap.add_argument("--gpu-memory-utilization", type=float, default=0.65)
    ap.add_argument("--max-model-len", type=int, default=None)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--server-ready-timeout-s", type=float, default=600.0)
    args = ap.parse_args()
    args.calibration_manifest = args.calibration_manifest.resolve()

    array_index = args.array_index
    if array_index is None:
        array_index = int(os.environ["SLURM_ARRAY_TASK_ID"])

    units = enumerate_calibration_units(args.manifest_dir)
    if not (0 <= array_index < len(units)):
        raise ValueError(f"array_index {array_index} out of range [0, {len(units)})")
    source, window_id, manifest_path = units[array_index]
    requests, manifest, window_entry = load_window_requests(manifest_path, window_id)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.out_dir / source / f"{window_id}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    started_at = datetime.now(timezone.utc).isoformat()
    log_path = args.out_dir / source / f"{window_id}.server.log"

    handle = start_vllm_server(
        model=args.model, host=args.host, port=args.port, log_path=str(log_path),
        gpu_memory_utilization=args.gpu_memory_utilization, max_model_len=args.max_model_len,
        scheduling_policy="fcfs",  # vllm_faithful: native FCFS, never a custom --scheduler-cls
        enable_chunked_prefill=False,
        extra_args=["--no-enable-prefix-caching"],
        vllm_executable=args.vllm_executable,
    )
    try:
        ready = wait_for_server_ready(handle, timeout_s=args.server_ready_timeout_s)
        if not ready:
            raise RuntimeError(f"vLLM server did not become ready within {args.server_ready_timeout_s}s")

        client = httpx.Client(base_url=handle.base_url, timeout=300.0)
        metrics_client = httpx.Client(base_url=handle.base_url, timeout=10.0)

        def fetch_metrics() -> str:
            return metrics_client.get("/metrics").text

        def call_fn(prompt_text: str, max_tokens: int, ignore_eos: bool) -> Dict[str, Any]:
            planned = PlannedRequest(
                request_id="rq6-calibration", experiment_id=f"rq6_calibration::{source}::{window_id}",
                model=args.model, prompt_bucket="n/a", max_tokens=max_tokens, concurrency_level=1,
                request_index=0, intended_prompt_tokens=0, prompt_text=prompt_text,
            )
            return call_non_streaming(client, planned, timeout_s=280, extra_body={"ignore_eos": ignore_eos})

        # One untimed warmup request per server start, discarded from all
        # statistics -- matches wulver_engineering_gate.py::_calibration.
        try:
            call_fn("warmup " * 8, 4, True)
        except Exception:
            pass

        result = bisect_lambda_ref_real(
            requests, tokenizer=_load_tokenizer(args.model), model=args.model, call_fn=call_fn,
            fetch_metrics=fetch_metrics, source=source, window_id=window_id,
        )

        output = {
            "stamp": STAMP_SCIENTIFIC,
            "source": source,
            "window_id": window_id,
            "reference_policy": result.reference_policy,
            "workload_manifest_path": str(manifest_path.relative_to(REPO_ROOT)),
            "workload_manifest_sha256": _sha256_file(manifest_path),
            "window_content_sha256": window_entry["content_sha256"],
            "calibration_manifest_path": str(args.calibration_manifest.relative_to(REPO_ROOT))
                if args.calibration_manifest.exists() else str(args.calibration_manifest),
            "calibration_manifest_sha256": _sha256_file(args.calibration_manifest)
                if args.calibration_manifest.exists() else None,
            "candidate_history": [asdict(c) for c in result.candidate_history],
            "real_lambda_ref": result.real_lambda_ref,
            "derived_high_pressure": result.derived_high_pressure,
            "target_slo_violation_rate": 0.005,
            "convergence_status": result.convergence_status,
            "repo_sha": _git_sha(),
            "environment_spec_sha256": _sha256_file(REPO_ROOT / "requirements-real-vllm.txt"),
            "model": args.model,
            "gpu": _nvidia_smi_name(),
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "slurm_array_task_id": os.environ.get("SLURM_ARRAY_TASK_ID", str(array_index)),
            "started_at_utc": started_at,
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        with open(out_path, "w") as f:
            json.dump(output, f, indent=2, sort_keys=True)
        print(f"Wrote {out_path}: real_lambda_ref={result.real_lambda_ref} "
              f"derived_high_pressure={result.derived_high_pressure} status={result.convergence_status}")
    finally:
        handle.stop()


def _load_tokenizer(model: str):
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(model)


def _nvidia_smi_name() -> str:
    try:
        return subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], text=True, timeout=10,
        ).strip().splitlines()[0]
    except Exception:
        return "UNKNOWN"


if __name__ == "__main__":
    main()
