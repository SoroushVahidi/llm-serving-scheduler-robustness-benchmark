#!/usr/bin/env python3
"""Wulver real-vLLM engineering readiness gate.

ENGINEERING_ONLY_NOT_SCIENTIFIC_EVIDENCE.

This script intentionally uses only fabricated prompts. It does not load or
submit Azure, BurstGPT, Bailian/Qwen, or frozen scientific RQ6 cases.
"""
from __future__ import annotations

import argparse
import concurrent.futures as futures
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from robustbench.real_llm.load_calibration_harness import RatePoint, run_rate_ladder
from robustbench.real_llm.vllm_process import start_vllm_server, wait_for_server_ready

SCHEDULER_CLS = "robustbench.real_llm.slai_plugin.slai_vllm_scheduler.LSSPSlaiVLLMScheduler"
FIXTURE_ID = "slai_forced_decode_hold_6req_tbt_2_2_2_decode_limit_2_v1"
NEGATIVE_CONTROL_ID = "slai_negative_control_6req_decode_limit_6_v1"
STAMP = "ENGINEERING_ONLY_NOT_SCIENTIFIC_EVIDENCE"

FIXTURE = [
    ("lssp_forced_tight_1", "tight"),
    ("lssp_forced_tight_2", "tight"),
    ("lssp_forced_medium_3", "medium"),
    ("lssp_forced_medium_4", "medium"),
    ("lssp_forced_loose_5", "loose"),
    ("lssp_forced_loose_6", "loose"),
]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _run(cmd: list[str], *, timeout: int = 60) -> str:
    return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT, timeout=timeout).strip()


def _run_best_effort(cmd: list[str], *, timeout: int = 60) -> str:
    try:
        return _run(cmd, timeout=timeout)
    except Exception as exc:
        return f"COMMAND_FAILED: {exc!r}"


def _env_probe(repo: Path, venv: Path) -> dict[str, Any]:
    freeze = _run([str(venv / "bin/python"), "-m", "pip", "freeze"], timeout=120)
    probe = _run([
        str(venv / "bin/python"),
        "-c",
        (
            "import sys, vllm, torch; "
            "print(sys.version.split()[0]); "
            "print(vllm.__version__); "
            "print(torch.__version__); "
            "print(torch.version.cuda); "
            "print(torch.cuda.is_available()); "
            "print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NO_CUDA')"
        ),
    ], timeout=180).splitlines()
    nvidia = _run_best_effort([
        "nvidia-smi",
        "--query-gpu=index,name,driver_version,memory.total",
        "--format=csv,noheader",
    ], timeout=30)
    nvidia_full = _run_best_effort(["nvidia-smi"], timeout=30)
    return {
        "python": probe[0],
        "vllm": probe[1],
        "torch": probe[2],
        "torch_cuda": probe[3],
        "torch_cuda_available": probe[4],
        "torch_gpu_name": probe[5],
        "nvidia_smi": nvidia.splitlines(),
        "nvidia_smi_full": nvidia_full.splitlines(),
        "pip_freeze_sha256": hashlib.sha256(freeze.encode()).hexdigest(),
        "pip_freeze_lines": len(freeze.splitlines()),
        "git_sha": _run(["git", "-C", str(repo), "rev-parse", "HEAD"]),
    }


def _prompt(rid: str, cls: str, max_tokens: int) -> str:
    return (
        f"{STAMP}. Synthetic scheduler smoke request {rid} in TBT tier {cls}. "
        "Continue with short neutral words about request scheduling until the token limit."
    )


def _post_one(base_url: str, model: str, rid: str, cls: str, max_tokens: int) -> dict[str, Any]:
    body = {
        "model": model,
        "prompt": _prompt(rid, cls, max_tokens),
        "max_tokens": max_tokens,
        "min_tokens": max_tokens,
        "ignore_eos": True,
        "temperature": 0.0,
        "request_id": rid,
        "vllm_xargs": {"lssp_class_id": cls, "lssp_fixture_id": FIXTURE_ID, "stamp": STAMP},
    }
    t0 = time.monotonic()
    with httpx.Client(base_url=base_url, timeout=180.0) as client:
        resp = client.post("/v1/completions", json=body)
        latency = time.monotonic() - t0
        return {
            "request_id": rid,
            "class_id": cls,
            "status_code": resp.status_code,
            "latency_seconds": latency,
            "ok": resp.status_code == 200,
            "usage": (resp.json().get("usage") if resp.status_code == 200 else None),
            "error": None if resp.status_code == 200 else resp.text[:500],
        }


def _run_concurrent_fixture(base_url: str, model: str, *, max_tokens: int) -> list[dict[str, Any]]:
    with futures.ThreadPoolExecutor(max_workers=len(FIXTURE)) as pool:
        futs = [pool.submit(_post_one, base_url, model, rid, cls, max_tokens) for rid, cls in FIXTURE]
        return [f.result() for f in futs]


def _parse_events(log_path: Path) -> dict[str, Any]:
    events: dict[str, list[dict[str, Any]]] = {"SLAI_HOLD": [], "SLAI_RELEASE": [], "SLAI_SCHEDULE": []}
    line_re = re.compile(r"(SLAI_(?:HOLD|RELEASE|SCHEDULE)) step=(\d+) request_id=([^ ]+)")
    for line in log_path.read_text(errors="replace").splitlines():
        match = line_re.search(line)
        if not match:
            continue
        kind, step, request_id = match.groups()
        events[kind].append({"step": int(step), "request_id": request_id})
    ids_by_kind = {k: sorted({e["request_id"] for e in v}) for k, v in events.items()}
    return {
        "counts": {k: len(v) for k, v in events.items()},
        "ids_by_kind": ids_by_kind,
        "events_path": str(log_path),
    }


def _start_server(args: argparse.Namespace, run_dir: Path, label: str, *, slai: bool, decode_limit: int | None):
    log_path = run_dir / f"{label}_server.log"
    old_limit = os.environ.get("LSSP_SLAI_DECODE_LIMIT")
    old_events = os.environ.get("LSSP_SLAI_LOG_EVENTS")
    os.environ["LSSP_SLAI_LOG_EVENTS"] = "1" if slai else "0"
    if decode_limit is not None:
        os.environ["LSSP_SLAI_DECODE_LIMIT"] = str(decode_limit)
    elif "LSSP_SLAI_DECODE_LIMIT" in os.environ:
        del os.environ["LSSP_SLAI_DECODE_LIMIT"]
    extra = ["--dtype", args.dtype, "--tensor-parallel-size", str(args.tensor_parallel_size), "--generation-config", "vllm"]
    if slai:
        extra += ["--scheduler-cls", SCHEDULER_CLS]
    handle = start_vllm_server(
        model=args.model,
        port=args.port,
        log_path=str(log_path),
        max_model_len=args.max_model_len,
        gpu_memory_utilization=args.gpu_memory_utilization,
        scheduling_policy="priority" if slai else "fcfs",
        extra_args=extra,
        vllm_executable=str(args.venv / "bin/vllm"),
    )
    if old_events is None:
        os.environ.pop("LSSP_SLAI_LOG_EVENTS", None)
    else:
        os.environ["LSSP_SLAI_LOG_EVENTS"] = old_events
    if old_limit is None:
        os.environ.pop("LSSP_SLAI_DECODE_LIMIT", None)
    else:
        os.environ["LSSP_SLAI_DECODE_LIMIT"] = old_limit
    return handle, log_path


def _server_round(args: argparse.Namespace, run_dir: Path, label: str, *, slai: bool, decode_limit: int | None, work):
    handle, log_path = _start_server(args, run_dir, label, slai=slai, decode_limit=decode_limit)
    ready = wait_for_server_ready(handle, timeout_s=args.server_timeout, poll_interval_s=2.0)
    result: dict[str, Any] = {"label": label, "ready": ready, "command": handle.command, "log_path": str(log_path)}
    try:
        if not ready:
            result["process_returncode"] = handle.process.poll()
            result["error"] = "server_not_ready"
            return result
        result.update(work(handle.base_url))
    finally:
        result["stop_returncode"] = handle.stop(timeout_s=30.0)
        time.sleep(2)
    result["events"] = _parse_events(log_path)
    result["traceback_count"] = log_path.read_text(errors="replace").count("Traceback")
    result["cuda_error_count"] = len(re.findall(r"CUDA error|cuda runtime error", log_path.read_text(errors="replace"), re.I))
    return result


def _forced_hold(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    def work(base_url: str):
        responses = _run_concurrent_fixture(base_url, args.model, max_tokens=args.forced_max_tokens)
        return {"fixture_id": FIXTURE_ID, "decode_limit": 2, "responses": responses}
    out = _server_round(args, run_dir, "slai_forced_hold", slai=True, decode_limit=2, work=work)
    counts = out.get("events", {}).get("counts", {})
    completed = sum(1 for r in out.get("responses", []) if r.get("ok"))
    scheduled = set(out.get("events", {}).get("ids_by_kind", {}).get("SLAI_SCHEDULE", []))
    held = set(out.get("events", {}).get("ids_by_kind", {}).get("SLAI_HOLD", []))
    out["pass_gate"] = bool(
        out.get("ready")
        and completed == len(FIXTURE)
        and counts.get("SLAI_HOLD", 0) > 0
        and counts.get("SLAI_RELEASE", 0) > 0
        and scheduled
        and held
        and out.get("cuda_error_count") == 0
    )
    return out


def _negative_control(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    def work(base_url: str):
        responses = _run_concurrent_fixture(base_url, args.model, max_tokens=args.negative_max_tokens)
        return {"fixture_id": NEGATIVE_CONTROL_ID, "decode_limit": 6, "responses": responses}
    out = _server_round(args, run_dir, "slai_negative_control", slai=True, decode_limit=6, work=work)
    holds = out.get("events", {}).get("counts", {}).get("SLAI_HOLD", 0)
    completed = sum(1 for r in out.get("responses", []) if r.get("ok"))
    out["pass_gate"] = bool(out.get("ready") and completed == len(FIXTURE) and holds == 0 and out.get("cuda_error_count") == 0)
    return out


def _calibration(args: argparse.Namespace, run_dir: Path, scheduler_label: str, *, slai: bool) -> dict[str, Any]:
    def work(base_url: str):
        warmup = _post_one(base_url, args.model, f"calibration_warmup_{scheduler_label}", "tight", 4)
        cal_dir = run_dir / f"calibration_{scheduler_label}"
        meta = run_rate_ladder(
            base_url=base_url,
            model=args.model,
            experiment_id=f"engineering_calibration_{scheduler_label}",
            prompt_buckets=["short"],
            max_tokens_list=[8],
            rate_ladder=[RatePoint(concurrency=1, requests_per_cell=2), RatePoint(concurrency=2, requests_per_cell=2)],
            out_dir=cal_dir,
            seed=20260902,
            timeout_seconds=90,
            stream=False,
        )
        return {
            "scheduler_label": scheduler_label,
            "warmup": warmup,
            "load_search": {
                "rate_ladder": [{"concurrency": 1, "requests_per_cell": 2}, {"concurrency": 2, "requests_per_cell": 2}],
                "operating_boundary_criterion": "engineering smoke criterion: first failed/error cell or exhausted fabricated two-point ladder",
                "stopping_rule": "stop after configured finite synthetic ladder",
            },
            "metadata": meta,
        }
    out = _server_round(args, run_dir, f"calibration_{scheduler_label}", slai=slai, decode_limit=None, work=work)
    aggregated = out.get("metadata", {}).get("aggregated", [])
    out["pass_gate"] = bool(out.get("ready") and out.get("warmup", {}).get("ok") and aggregated and out.get("cuda_error_count") == 0)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--venv", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--model-revision", default=None)
    parser.add_argument("--tokenizer-revision", default=None)
    parser.add_argument("--dtype", default="bfloat16")
    parser.add_argument("--tensor-parallel-size", type=int, default=1)
    parser.add_argument("--max-model-len", type=int, default=1024)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.65)
    parser.add_argument("--port", type=int, default=8127)
    parser.add_argument("--server-timeout", type=int, default=900)
    parser.add_argument("--forced-max-tokens", type=int, default=192)
    parser.add_argument("--negative-max-tokens", type=int, default=32)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.out_dir / "wulver_engineering_gate_summary.json"
    fixture_manifest_path = args.out_dir / "synthetic_fixture_manifest.json"
    fixture_manifest_path.write_text(json.dumps({
        "stamp": STAMP,
        "fixture_id": FIXTURE_ID,
        "negative_control_id": NEGATIVE_CONTROL_ID,
        "requests": [{"request_id": rid, "class_id": cls} for rid, cls in FIXTURE],
        "tbt_tiers": {"tight": 2, "medium": 2, "loose": 2},
        "decode_limit_forced": 2,
        "decode_limit_negative_control": 6,
        "structural_proof": "offset*step_size = 5*0.001 = 0.005 < min TBT 0.1; decode_limit 2 < 6 decode-ready requests",
    }, indent=2, sort_keys=True) + "\n")

    summary: dict[str, Any] = {
        "stamp": STAMP,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        "slurm_partition": os.environ.get("SLURM_JOB_PARTITION"),
        "slurm_node": os.environ.get("SLURMD_NODENAME") or socket.gethostname(),
        "requested_resources": {
            "cpus": os.environ.get("SLURM_CPUS_PER_TASK"),
            "gres": os.environ.get("SLURM_JOB_GPUS") or os.environ.get("CUDA_VISIBLE_DEVICES"),
        },
        "model": {
            "model_id": args.model,
            "model_revision": args.model_revision,
            "tokenizer_revision": args.tokenizer_revision,
            "dtype": args.dtype,
            "tensor_parallel_size": args.tensor_parallel_size,
            "max_model_len": args.max_model_len,
            "gpu_memory_utilization": args.gpu_memory_utilization,
        },
        "env": _env_probe(args.repo, args.venv),
        "fixture_manifest": str(fixture_manifest_path),
        "fixture_manifest_sha256": _sha256_file(fixture_manifest_path),
    }

    summary["forced_hold"] = _forced_hold(args, args.out_dir)
    summary["negative_control"] = _negative_control(args, args.out_dir)
    if summary["forced_hold"]["pass_gate"] and summary["negative_control"]["pass_gate"]:
        summary["calibration_vllm_faithful"] = _calibration(args, args.out_dir, "vllm_faithful", slai=False)
        summary["calibration_slai"] = _calibration(args, args.out_dir, "slai", slai=True)
    else:
        summary["calibration_skipped"] = "forced-hold or negative-control gate failed"

    summary["pass_gate"] = bool(
        summary["forced_hold"].get("pass_gate")
        and summary["negative_control"].get("pass_gate")
        and summary.get("calibration_vllm_faithful", {}).get("pass_gate")
        and summary.get("calibration_slai", {}).get("pass_gate")
    )
    manifest_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"summary_path": str(manifest_path), "pass_gate": summary["pass_gate"]}, sort_keys=True))
    return 0 if summary["pass_gate"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
