#!/usr/bin/env python3
"""One-GPU engineering smoke, never a ranking experiment or pilot launcher."""
import argparse
import asyncio
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import time

from robustbench.mgpu00.gpu_probe import Journal

import httpx

from robustbench.mgpu00.metadata import RequestMetadata
from robustbench.mgpu00.provenance import ExperimentIdentity, canonical_hash, collect_gpu_provenance, write_new_json
from robustbench.mgpu00.replay import PreparedRequest, make_client, replay

MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"
SPEC = {"stamp": "ENGINEERING_ONLY_NOT_RANKING_EVIDENCE", "model": MODEL, "revision": REVISION,
        "requests": 12, "prompt_tokens": 128, "output_tokens": 128,
        "arrivals": "four requests at each of 0, 0.2, 0.4 seconds", "repetitions": 2,
        "decode_limit": 2, "max_dispatch_delay_s": .02, "max_dispatch_p95_s": .01,
        "max_inflight": 32, "max_model_len": 512, "max_num_batched_tokens": 4096,
        "max_num_seqs": 16, "dtype": "bfloat16", "gpu_memory_utilization": .2,
        "eager": True, "async_scheduling": False, "chunked_prefill": False,
        "prefix_caching": False, "tp": 1, "pp": 1, "dp": 1}


def read_events(path):
    events = []
    for line in path.read_text(errors="replace").splitlines():
        if "MGPU00_EVENT " in line:
            events.append(json.loads(line.split("MGPU00_EVENT ", 1)[1]))
    return events


def join_and_validate(result, events, requests, policy):
    lookup = {r.metadata.request_id: r.metadata.xargs() for r in requests}
    received = {e["metadata"]["lssp_request_id"]: e for e in events if e["event"] == "received"}
    admitted = {e["request_id"]: e for e in events if e["event"] == "admitted"}
    missing = sorted(set(lookup) - (received.keys() & admitted.keys()))
    if missing:
        raise RuntimeError(f"Missing scheduler receipt/admission: {missing}")
    for row in result["rows"]:
        rid = row["request_id"]
        if received[rid]["metadata"] != lookup[rid]:
            raise RuntimeError("Scheduler metadata differs from prepared request")
        row["scheduler_received_s"] = received[rid]["monotonic_s"] - result["client_start_monotonic_s"]
        row["server_admission_s"] = admitted[rid]["monotonic_s"] - result["client_start_monotonic_s"]
        row["server_queue_s"] = row["server_admission_s"] - row["scheduler_received_s"]
        row["admission_to_client_completion_s"] = row["completion_s"] - row["server_admission_s"]
        if row["scheduler_received_s"] < row["dispatch_s"] or row["server_queue_s"] < 0:
            raise RuntimeError("Clock/causal-order mismatch; do not combine cross-host monotonic clocks")
    held = [e for e in events if e["event"] == "held" and e["request_id"] in lookup]
    result["scheduler_diagnostics"] = {"metadata_verified": len(lookup), "admissions_verified": len(lookup),
        "hold_events": len(held), "held_requests": sorted({e["request_id"] for e in held}),
        "held_classes": sorted({e["class_id"] for e in held}),
        "semantic_mismatches": sum(e["event"] == "semantic_mismatch" for e in events)}
    priorities = {e["request_id"]: e for e in events if e["event"] == "priority_set" and e["request_id"] in lookup}
    decisions = [e for e in events if e["event"] == "decision_verified" and e["decoding"]]
    result["scheduler_diagnostics"]["priority_assignments_verified"] = len(priorities)
    result["scheduler_diagnostics"]["checked_decode_batches"] = len(decisions)
    if policy == "slai_mgpu00_checked":
        if len(priorities) != len(lookup) or not decisions:
            raise RuntimeError("No evidence that received classes affect the actual scheduler")
        for rid, event in priorities.items():
            if event["class_id"] != lookup[rid]["lssp_class_id"]:
                raise RuntimeError("Wrong scheduling class applied")
    if policy == "slai_mgpu00_checked" and not held:
        raise RuntimeError("SLAI mechanism not activated; smoke invalid")
    if policy == "native_fcfs" and held:
        raise RuntimeError("Native baseline unexpectedly has SLAI hold events")
    if not result["valid_replay"] or result["dispatch_delay_p95_s"] > SPEC["max_dispatch_p95_s"]:
        raise RuntimeError("Replay saturation, dispatch delay or incomplete-request gate failed")
    return result


def stop_server(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


def run_round(*, directory, model_path, executable, provenance, git_sha, policy, repetition, tokenizer):
    prefix = f"{policy}-rep{repetition}"
    body_ids = tokenizer.encode("scheduler integrity fixture", add_special_tokens=False)
    prompt_ids = tuple((body_ids * (128 // len(body_ids) + 1))[:128])
    requests = [PreparedRequest(RequestMetadata(f"fixture-r{i}", i,
                  ["loose", "tight", "medium"][i % 3], (i // 4) * .2, 30. + (i // 4) * .2, 1.),
                  prompt_ids, 128) for i in range(12)]
    workload_hash = canonical_hash([r.payload(MODEL) for r in requests])
    identity = ExperimentIdentity(MODEL, REVISION, MODEL, REVISION, "bfloat16", 512,
               provenance["devices"][0]["model"], provenance["allocation_kind"], 1, 1, 1, 1, 1,
               policy, SPEC, workload_hash, canonical_hash({"engineering_fixture": SPEC, "calibration": "not_a_scientific_load_calibration"}),
               repetition, git_sha, provenance["software"], "ENGINEERING_FORCED_CONTENTION")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    scheduler = "LSSPSlaiVLLMScheduler" if policy == "slai_mgpu00_checked" else "InstrumentedNativeScheduler"
    command = [executable, "serve", str(model_path), "--served-model-name", MODEL,
               "--revision", REVISION, "--tokenizer-revision", REVISION,
               "--host", "127.0.0.1", "--port", str(port), "--dtype", "bfloat16",
               "--max-model-len", "512", "--max-num-batched-tokens", "4096", "--max-num-seqs", "16",
               "--gpu-memory-utilization", "0.2", "--enforce-eager", "--no-async-scheduling",
               "--no-enable-chunked-prefill", "--no-enable-prefix-caching",
               "--tensor-parallel-size", "1", "--pipeline-parallel-size", "1", "--data-parallel-size", "1",
               "--scheduling-policy", "priority" if policy == "slai_mgpu00_checked" else "fcfs",
               "--scheduler-cls", "robustbench.mgpu00.vllm_scheduler." + scheduler]
    log_path = directory / f"{prefix}.server.log"
    start = time.monotonic()
    environment = dict(os.environ, LSSP_MGPU00_DECODE_LIMIT="2", VLLM_USE_FLASHINFER_SAMPLER="0",
                       HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", TOKENIZERS_PARALLELISM="false",
                       VLLM_CACHE_ROOT=str(directory / "cache/vllm"),
                       TORCHINDUCTOR_CACHE_DIR=str(directory / "cache/torchinductor"),
                       CUDA_CACHE_PATH=str(directory / "cache/cuda"))
    result = None
    with log_path.open("x") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=environment)
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=3., trust_env=False) as client:
                deadline = start + 600
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise RuntimeError(f"Server exited {process.returncode}; inspect {log_path}")
                    try:
                        if client.get("/v1/models").status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(2)
                else:
                    raise RuntimeError("Server readiness timeout")
            ready_s = time.monotonic() - start
            async def execute():
                async with make_client(f"http://127.0.0.1:{port}", 32) as client:
                    warm = PreparedRequest(RequestMetadata("fixture-warmup", 999999, "tight", 0., 30., 1.), prompt_ids, 4)
                    warm_result = await replay([warm], model=MODEL, client=client, max_inflight=1,
                        timeout_s=60., max_dispatch_delay_s=1.)
                    if warm_result["completed"] != 1:
                        raise RuntimeError("Warmup failed")
                    return await replay(requests, model=MODEL, client=client, max_inflight=32,
                        timeout_s=120., max_dispatch_delay_s=SPEC["max_dispatch_delay_s"])
            result = asyncio.run(execute())
            write_new_json(directory / f"{prefix}.raw_replay.json", result)
        finally:
            stop_server(process)
    result = join_and_validate(result, read_events(log_path), requests, policy)
    record = {"stamp": SPEC["stamp"], "identity": asdict(identity), "experiment_id": identity.experiment_id,
              "execution_id": canonical_hash({"experiment_id": identity.experiment_id, "hardware": provenance}),
              "hardware": provenance, "server_command": command, "readiness_seconds": ready_s,
              "round_allocated_seconds": time.monotonic()-start, "result": result,
              "server_log_sha256": hashlib.sha256(log_path.read_bytes()).hexdigest()}
    write_new_json(directory / f"{prefix}.validated.json", record)
    print(json.dumps({"round": prefix, "status": "PASS", "diagnostics": result["scheduler_diagnostics"],
                      "dispatch_p95_s": result["dispatch_delay_p95_s"], "allocated_seconds": record["round_allocated_seconds"]}), flush=True)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--model-path", required=True, type=Path)
    parser.add_argument("--vllm-executable", required=True)
    parser.add_argument("--diagnostic-minimal", action="store_true", help="One round per mechanism; no reproducibility claim")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    progress = Journal(args.out / "progress")
    if args.diagnostic_minimal:
        SPEC["repetitions"] = 1
    try:
        progress.event("smoke_started", diagnostic_minimal=args.diagnostic_minimal, slurm_job_id=os.environ.get("SLURM_JOB_ID"))
        if args.model_path.name != REVISION:
            raise RuntimeError("Model snapshot is not the pinned immutable revision")
        progress.event("device_probe_started")
        provenance = collect_gpu_provenance(args.out / "device")
        progress.event("device_verified", allocation_kind=provenance["allocation_kind"])
        write_new_json(args.out / "gpu_provenance.json", provenance)
        print(json.dumps({"gate": "device_identity", "status": provenance["allocation_kind"],
                          "node": provenance["node"], "memory_bytes": provenance["devices"][0]["cuda_memory_bytes"]}), flush=True)
        git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(args.model_path, local_files_only=True)
        rounds = []
        # Fresh server per round; ABBA blocks startup/order effects. No cell retries.
        sequence = [("native_fcfs", 0), ("slai_mgpu00_checked", 0)]
        if not args.diagnostic_minimal:
            sequence += [("slai_mgpu00_checked", 1), ("native_fcfs", 1)]
        for policy, rep in sequence:
            progress.event("round_started", policy=policy, repetition=rep)
            rounds.append(run_round(directory=args.out, model_path=args.model_path, executable=args.vllm_executable,
                                   provenance=provenance, git_sha=git_sha, policy=policy, repetition=rep, tokenizer=tokenizer))
            progress.event("round_passed", policy=policy, repetition=rep)
        if len({r["identity"]["workload_sha256"] for r in rounds}) != 1:
            raise RuntimeError("Workload identity differs between policy/repetition rounds")
        summary = {"status": "COMPLETED_SUCCESS", "stamp": SPEC["stamp"], "spec": SPEC,
                   "git_commit": git_sha, "slurm_job_id": provenance["slurm_job_id"],
                   "elapsed_seconds": time.monotonic()-started, "gpu_count": 1,
                   "gpu_hours": (time.monotonic()-started)/3600, "rounds": [r["experiment_id"] for r in rounds],
                   "reproducibility": "NOT_TESTED_ONE_ROUND_PER_MECHANISM" if args.diagnostic_minimal else "two fresh-engine repetitions per mechanism; identical input shapes, complete token counts and metadata; timing is measured, not assumed deterministic",
                   "pilot_go": False, "pilot_blockers": ["TP2 not validated or enabled", "general partial-prefill/KV-pressure fidelity not established", "full-device workload calibration not performed"]}
        write_new_json(args.out / "summary.json", summary)
        progress.event("smoke_passed", summary=summary)
        print(json.dumps(summary), flush=True)
    except Exception as exc:
        progress.event("smoke_failed", error=f"{type(exc).__name__}: {exc}")
        write_new_json(args.out / "failure.json", {"status": "FAILED", "stamp": SPEC["stamp"],
                       "error": f"{type(exc).__name__}: {exc}", "elapsed_seconds": time.monotonic()-started,
                       "slurm_job_id": os.environ.get("SLURM_JOB_ID")})
        raise
    finally:
        progress.stream.close()


if __name__ == "__main__":
    main()
