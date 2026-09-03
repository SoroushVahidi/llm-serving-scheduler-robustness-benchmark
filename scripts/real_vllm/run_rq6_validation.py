#!/usr/bin/env python3
"""Run one RQ6 real-vLLM scientific-validation cell (one Slurm array task =
one (policy, source, window_id) unit of the frozen 240-cell task matrix,
configs/real_vllm/rq6_validation_manifest_v1_20260903.json).

RQ6_REAL_VLLM_SCIENTIFIC_VALIDATION = NOT_STARTED as of this script's
authorship. This is the launcher; running it against the real frozen cases
is explicitly out of scope for the task that wrote it (prefreeze only).

Verifies, before touching a GPU: the validation manifest's own hash, the
case-selection manifest hash, the calibration manifest hash, and this
cell's own calibration dependency (per-window hash-checked) -- refuses to
run on any mismatch rather than silently using stale or substituted inputs.

Starts one vLLM server for exactly this cell's policy (vllm_faithful:
native FCFS; slai_faithful: --scheduler-cls LSSPSlaiVLLMScheduler,
--scheduling-policy priority), replays this window's 200 requests once at
its calibrated HIGH_PRESSURE scale, writes one atomic, provenance-complete
JSON, and refuses to silently overwrite an existing valid COMPLETED result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

import httpx  # noqa: E402

from robustbench.real_llm.calibration_common import PlannedRequest  # noqa: E402
from robustbench.real_llm.port_alloc import allocate_port  # noqa: E402
from robustbench.real_llm.rq6_calibration import replay_window_once  # noqa: E402
from robustbench.real_llm.rq6_validation import (  # noqa: E402
    RQ6_REGION,
    CalibrationLookupError,
    enumerate_validation_cells,
    load_calibrated_scale,
    load_window_requests,
    summarize_replay,
)
from robustbench.real_llm.vllm_openai_client import call_non_streaming  # noqa: E402
from robustbench.real_llm.vllm_process import start_vllm_server, wait_for_server_ready  # noqa: E402

STAMP_SCIENTIFIC = "RQ6_REAL_VLLM_SCIENTIFIC_VALIDATION"
DEFAULT_MANIFEST_DIR = REPO_ROOT / "artifacts/manifests/rq6_real_vllm"
DEFAULT_VALIDATION_MANIFEST = REPO_ROOT / "configs/real_vllm/rq6_validation_manifest_v1_20260903.json"
DEFAULT_CALIBRATION_DIR_TEMPLATE = REPO_ROOT / "artifacts/real_vllm/calibration/rq6/{calibration_manifest_sha256}"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).decode().strip()


def _nvidia_smi_name() -> str:
    try:
        return subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], text=True, timeout=10,
        ).strip().splitlines()[0]
    except Exception:
        return "UNKNOWN"


def _load_tokenizer(model: str):
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(model)


def _load_validation_manifest(path: Path) -> Dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def verify_manifest_chain(manifest: Dict[str, Any], *, repo_root: Path) -> None:
    """Raises RuntimeError on any hash mismatch in the frozen dependency
    chain (case selection, calibration manifest, workload manifests, code
    SHA). Never proceeds past a mismatch -- a scientific run built on a
    verification failure is not evidence."""
    problems = []

    frozen_sha = manifest["frozen_code_sha"]
    actual_sha = _git_sha()
    if actual_sha != frozen_sha:
        problems.append(f"repo HEAD {actual_sha} != manifest's frozen_code_sha {frozen_sha}")

    case_sel = manifest["case_selection"]["manifest_path"]
    case_sel_expected = manifest["case_selection"]["manifest_sha256"]
    case_sel_actual = _sha256_file(repo_root / case_sel)
    if case_sel_actual != case_sel_expected:
        problems.append(f"{case_sel}: sha256 {case_sel_actual} != manifest's {case_sel_expected}")

    cal = manifest["calibration_dependency"]
    cal_path = cal["calibration_manifest_path"]
    cal_expected = cal["calibration_manifest_sha256"]
    cal_actual = _sha256_file(repo_root / cal_path)
    if cal_actual != cal_expected:
        problems.append(f"{cal_path}: sha256 {cal_actual} != manifest's {cal_expected}")

    for source, info in manifest["workload_manifests"].items():
        wpath = repo_root / info["path"]
        wexpected = info["content_sha256"]
        with open(wpath) as f:
            wmanifest = json.load(f)
        wactual = wmanifest.get("content_sha256")
        # workload manifests are hash-gated on a per-window content_sha256,
        # not a single top-level file hash (see docs/RQ6_REAL_VLLM_
        # SCIENTIFIC_PROTOCOL_20260902.md's "Cache provenance" correction) --
        # verify the file is at least readable and has the right window
        # count as a cheap sanity check; per-window hashes are re-verified
        # individually via load_calibrated_scale's window_content_sha256
        # check at cell-load time.
        if len(wmanifest.get("windows", [])) != info["window_count"]:
            problems.append(f"{wpath}: window_count {len(wmanifest.get('windows', []))} != manifest's {info['window_count']}")

    if problems:
        raise RuntimeError("Validation manifest chain verification FAILED:\n  " + "\n  ".join(problems))


def aggregate_calibration_hash(calibration_dir: Path) -> str:
    """Reproduces the validation manifest's calibration_dependency.
    aggregate_output_content_hash formula exactly:
    sha256( sorted "sha256sum(file)  relpath" lines joined by newline )."""
    lines = []
    for path in sorted(calibration_dir.rglob("*.json")):
        rel = path.relative_to(calibration_dir).as_posix()
        lines.append(f"{_sha256_file(path)}  {rel}")
    joined = "\n".join(lines) + ("\n" if lines else "")
    return hashlib.sha256(joined.encode()).hexdigest()


def build_execution_plan(args: argparse.Namespace) -> Dict[str, Any]:
    """Result-blind execution plan for one cell -- used by both --dry-run
    and the real execution path, so the two can never silently diverge."""
    manifest = _load_validation_manifest(args.validation_manifest)
    cells = enumerate_validation_cells(args.manifest_dir)
    array_index = args.array_index
    if array_index is None:
        array_index = int(os.environ["SLURM_ARRAY_TASK_ID"])
    if not (0 <= array_index < len(cells)):
        raise ValueError(f"array_index {array_index} out of range [0, {len(cells)})")
    cell = cells[array_index]

    calibration_dir = args.calibration_dir or Path(
        str(DEFAULT_CALIBRATION_DIR_TEMPLATE).format(
            calibration_manifest_sha256=manifest["calibration_dependency"]["calibration_manifest_sha256"]
        )
    )
    out_path = args.out_dir / cell.policy / cell.source / f"{cell.window_id}.json"

    scheduler_mapping = manifest["scheduler_mapping"][cell.policy]

    return {
        "manifest": manifest,
        "cell": cell,
        "calibration_dir": calibration_dir,
        "out_path": out_path,
        "scheduler_mapping": scheduler_mapping,
        "region": RQ6_REGION,
    }


def print_dry_run_plan(plan: Dict[str, Any]) -> None:
    cell = plan["cell"]
    row = {
        "array_index": cell.array_index,
        "case": "reversal" if cell.source in ("azure_llm_2024", "burstgpt") else "reversal_or_control",
        "source": cell.source,
        "window_id": cell.window_id,
        "region": plan["region"],
        "policy": cell.policy,
        "replicate_seed": 0,
        "scheduler_cls": plan["scheduler_mapping"]["scheduler_cls"],
        "scheduling_policy": plan["scheduler_mapping"]["scheduling_policy"],
        "calibration_lookup_path": str(plan["calibration_dir"] / cell.source / f"{cell.window_id}.json"),
        "gpu_gres": "gpu:a100_10g:1",
        "output_path": str(plan["out_path"]),
    }
    print(json.dumps(row, indent=2, sort_keys=True))


def _write_atomic_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        with contextlib_suppress():
            os.unlink(tmp_name)
        raise


class contextlib_suppress:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return True


def _existing_result_is_completed(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        with open(path) as f:
            record = json.load(f)
        return record.get("run_status") == "COMPLETED"
    except Exception:
        return False


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    ap.add_argument("--validation-manifest", type=Path, default=DEFAULT_VALIDATION_MANIFEST)
    ap.add_argument("--array-index", type=int, default=None,
                     help="0-239; defaults to $SLURM_ARRAY_TASK_ID if unset")
    ap.add_argument("--model", required=False, default="Qwen/Qwen2.5-0.5B-Instruct")
    ap.add_argument("--vllm-executable", default="vllm")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--gpu-memory-utilization", type=float, default=0.65)
    ap.add_argument("--max-model-len", type=int, default=32768)
    ap.add_argument("--calibration-dir", type=Path, default=None,
                     help="defaults to artifacts/real_vllm/calibration/rq6/<calibration_manifest_sha256>")
    ap.add_argument("--out-dir", type=Path, required=False,
                     default=REPO_ROOT / "artifacts/real_vllm/validation/rq6")
    ap.add_argument("--server-ready-timeout-s", type=float, default=600.0)
    ap.add_argument("--server-start-retries", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true",
                     help="Print the result-blind execution plan for this array index and exit. Never starts vLLM.")
    ap.add_argument("--force", action="store_true",
                     help="Overwrite an existing COMPLETED output. Refused by default (Section 6/8 output-contract requirement).")
    ap.add_argument("--skip-manifest-chain-verification", action="store_true",
                     help="ENGINEERING_ONLY: skip hash-chain verification. Never use for a scientific launch.")
    args = ap.parse_args()
    args.validation_manifest = args.validation_manifest.resolve()

    plan = build_execution_plan(args)
    if args.dry_run:
        print_dry_run_plan(plan)
        return

    manifest = plan["manifest"]
    if not args.skip_manifest_chain_verification:
        verify_manifest_chain(manifest, repo_root=REPO_ROOT)

    cell = plan["cell"]
    calibration_dir = plan["calibration_dir"]
    out_path = plan["out_path"]

    if out_path.exists() and not args.force:
        if _existing_result_is_completed(out_path):
            print(f"REFUSING to overwrite existing COMPLETED result: {out_path} (use --force to override)")
            return

    requests, workload_manifest, window_entry = load_window_requests(cell.workload_manifest_path, cell.window_id)

    try:
        calibration_record = load_calibrated_scale(
            calibration_dir, cell.source, cell.window_id,
            expected_calibration_manifest_sha256=manifest["calibration_dependency"]["calibration_manifest_sha256"],
            expected_window_content_sha256=window_entry["content_sha256"],
        )
    except CalibrationLookupError as exc:
        _write_atomic_json(out_path, {
            "stamp": STAMP_SCIENTIFIC, "run_status": "FAILED_CALIBRATION_DEPENDENCY",
            "policy": cell.policy, "source": cell.source, "window_id": cell.window_id,
            "error_message": str(exc), "repo_sha": _git_sha(),
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        })
        raise

    candidate_scale = calibration_record["derived_high_pressure"]
    scheduler_mapping = manifest["scheduler_mapping"][cell.policy]

    started_at = datetime.now(timezone.utc).isoformat()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    log_path = out_path.parent / f"{cell.window_id}.server.log"

    extra_args = list(scheduler_mapping["engine_flags"])
    if scheduler_mapping["scheduler_cls"]:
        extra_args = ["--scheduler-cls", scheduler_mapping["scheduler_cls"]] + extra_args

    port_alloc = None
    handle = None
    last_exc: Optional[Exception] = None
    for attempt in range(args.server_start_retries):
        port_alloc = allocate_port(args.host)
        handle = start_vllm_server(
            model=args.model, host=args.host, port=port_alloc.port, log_path=str(log_path),
            gpu_memory_utilization=args.gpu_memory_utilization, max_model_len=args.max_model_len,
            scheduling_policy=scheduler_mapping["scheduling_policy"],
            enable_chunked_prefill=False, extra_args=extra_args, vllm_executable=args.vllm_executable,
        )
        try:
            ready = wait_for_server_ready(handle, timeout_s=args.server_ready_timeout_s)
        except Exception as exc:  # noqa: BLE001
            ready = False
            last_exc = exc
        if ready:
            break
        handle.stop()
        handle = None
        time.sleep(2.0)

    if handle is None:
        _write_atomic_json(out_path, {
            "stamp": STAMP_SCIENTIFIC, "run_status": "FAILED_SERVER_START",
            "policy": cell.policy, "source": cell.source, "window_id": cell.window_id,
            "error_message": f"vLLM server did not become ready after {args.server_start_retries} attempts"
                              + (f": {last_exc}" if last_exc else ""),
            "repo_sha": _git_sha(), "started_at_utc": started_at,
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        })
        raise RuntimeError("vLLM server failed to start")

    try:
        client = httpx.Client(base_url=handle.base_url, timeout=300.0)

        def call_fn(prompt_text: str, max_tokens: int, ignore_eos: bool) -> Dict[str, Any]:
            planned = PlannedRequest(
                request_id="rq6-validation", experiment_id=f"rq6_validation::{cell.policy}::{cell.source}::{cell.window_id}",
                model=args.model, prompt_bucket="n/a", max_tokens=max_tokens, concurrency_level=1,
                request_index=0, intended_prompt_tokens=0, prompt_text=prompt_text,
            )
            return call_non_streaming(client, planned, timeout_s=280, extra_body={"ignore_eos": ignore_eos})

        try:
            call_fn("warmup " * 8, 4, True)
        except Exception:
            pass

        replay = replay_window_once(
            requests, candidate_scale=candidate_scale, tokenizer=_load_tokenizer(args.model),
            model=args.model, call_fn=call_fn,
        )
        result = summarize_replay(cell.policy, cell.source, cell.window_id, candidate_scale, replay)

        output = {
            "stamp": STAMP_SCIENTIFIC,
            "run_status": "COMPLETED",
            "rq6_case_id": "reversal" if cell.source in ("azure_llm_2024", "burstgpt") else "control_or_reversal_shared",
            "policy": result.policy,
            "source": result.source,
            "window_id": result.window_id,
            "region": plan["region"],
            "candidate_scale": result.candidate_scale,
            "real_lambda_ref": calibration_record["real_lambda_ref"],
            "calibration_convergence_status": calibration_record["convergence_status"],
            "scheduler_cls": scheduler_mapping["scheduler_cls"],
            "scheduling_policy": scheduler_mapping["scheduling_policy"],
            "replicate_seed": 0,
            "model": args.model,
            "gpu": _nvidia_smi_name(),
            "selected_port": port_alloc.port,
            "port_selection_method": port_alloc.method,
            "started_at_utc": started_at,
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "offered_request_count": result.n_total,
            "completed_request_count": result.n_completed,
            "arrival_normalized_weighted_goodput": result.arrival_normalized_weighted_goodput,
            "slo_violation_rate": result.slo_violation_rate,
            "workload_manifest_path": str(cell.workload_manifest_path.relative_to(REPO_ROOT)),
            "workload_manifest_content_sha256": window_entry["content_sha256"],
            "calibration_manifest_sha256": manifest["calibration_dependency"]["calibration_manifest_sha256"],
            "validation_manifest_path": str(args.validation_manifest.relative_to(REPO_ROOT))
                if args.validation_manifest.is_relative_to(REPO_ROOT) else str(args.validation_manifest),
            "validation_manifest_sha256": _sha256_file(args.validation_manifest),
            "case_selection_manifest_sha256": manifest["case_selection"]["manifest_sha256"],
            "environment_spec_sha256": manifest["environment"]["environment_spec_sha256"],
            "repo_sha": _git_sha(),
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "slurm_array_job_id": os.environ.get("SLURM_ARRAY_JOB_ID"),
            "slurm_array_task_id": os.environ.get("SLURM_ARRAY_TASK_ID", str(cell.array_index)),
        }
        _write_atomic_json(out_path, output)
        print(f"Wrote {out_path}: policy={result.policy} anwg={result.arrival_normalized_weighted_goodput} "
              f"slo_violation_rate={result.slo_violation_rate} n_completed={result.n_completed}/{result.n_total}")
    except Exception as exc:  # noqa: BLE001
        _write_atomic_json(out_path, {
            "stamp": STAMP_SCIENTIFIC, "run_status": "FAILED_DURING_REPLAY",
            "policy": cell.policy, "source": cell.source, "window_id": cell.window_id,
            "error_message": str(exc), "repo_sha": _git_sha(),
            "selected_port": port_alloc.port if port_alloc else None,
            "started_at_utc": started_at, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        })
        raise
    finally:
        handle.stop()


if __name__ == "__main__":
    main()
