#!/usr/bin/env python3
"""Read all 240 frozen RQ6 tasks and accounting records; emit JSON to stdout.

Run on the login node using the standard-library Python interpreter. No GPU
queries, allocations, imports of project/framework code, or remote writes.
Classification requires *both* allocation and CUDA-visible memory evidence.
UUIDs cannot be reconstructed from a parent-name-only inventory.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

FROZEN_SHA = "703a752762348bd911c9d93f17731fa5244b38f9"
MANIFEST_HASH = "172efb13b30efea440a18644ef852fa2d0b8cc6fee93ea730981b2ac868bd670"
MEMORY = re.compile(r"Free memory on device \(([\d.]+)/([\d.]+) GiB\)")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def classify(allocated, capacities):
    if not capacities:
        return "UNVERIFIABLE"
    if "gres/gpu:a100_10g=1" in allocated and all(8 <= x <= 11 for x in capacities):
        return "MIG_VERIFIED"
    # Do not infer a full GPU merely from a parent inventory or a large model name.
    if "gres/gpu:a100=1" in allocated and all(75 <= x <= 81 for x in capacities):
        return "FULL_GPU_VERIFIED"
    return "UNVERIFIABLE"


def audit(root, accounting):
    root = Path(root)
    directory = root / "artifacts/real_vllm/validation/rq6" / MANIFEST_HASH
    by_index = {}
    for path in directory.glob("*/*/*.json"):
        value = json.loads(path.read_text())
        index = int(value["slurm_array_task_id"])
        if index in by_index:
            raise ValueError("Duplicate historical array index: %s" % index)
        by_index[index] = (path, value)
    columns = ["job_id", "state", "exit_code", "node", "requested_tres", "allocated_tres",
               "elapsed_seconds", "start", "end"]
    records = {}
    for line in accounting.splitlines():
        fields = line.split("|")
        if len(fields) == len(columns) and re.fullmatch(r"1222413_\d+", fields[0]):
            records.setdefault(int(fields[0].split("_")[1]), []).append(dict(zip(columns, fields)))
    rows = []
    for index in range(240):
        row = {"array_index": index, "classification": "UNVERIFIABLE",
               "accounting": records.get(index, []), "allocated_device_uuid": None,
               "parent_gpu_uuid": None, "mig_gpu_instance_id": None,
               "mig_compute_instance_id": None, "evidence": [], "missing_fields": []}
        if index not in by_index:
            row["missing_fields"].append("historical result JSON")
            rows.append(row)
            continue
        path, value = by_index[index]
        row.update({k: value.get(k) for k in ("policy", "source", "window_id", "repo_sha", "gpu",
                    "run_status", "slurm_job_id", "workload_manifest_content_sha256",
                    "calibration_manifest_sha256", "validation_manifest_sha256")})
        capacities = []
        parent_names = set()
        for candidate, kind in [(path, "result"), (path.with_suffix(".server.log"), "engine_log"),
                                (directory / ("prologue_task%s.txt" % index), "prologue")]:
            if not candidate.exists():
                row["missing_fields"].append(kind)
                continue
            data = candidate.read_bytes()
            lines = data.decode(errors="replace").splitlines()
            excerpts = []
            for lineno, line in enumerate(lines, 1):
                match = MEMORY.search(line)
                if kind == "engine_log" and match:
                    capacities.append(float(match.group(2)))
                    excerpts.append({"line": lineno, "text": line})
                if kind == "prologue" and line.startswith("NVIDIA "):
                    parent_names.add(line.split(",")[0])
                    excerpts.append({"line": lineno, "text": line})
                # Preserve any UUID evidence without assigning unbound UUIDs to CUDA ordinals.
                if re.search(r"(?:GPU|MIG)-[a-fA-F0-9-]{8,}", line):
                    excerpts.append({"line": lineno, "text": line})
            row["evidence"].append({"path": str(candidate.relative_to(root)), "sha256": digest(data),
                                    "bytes": len(data), "excerpts": excerpts})
        row["cuda_visible_memory_gib_observations"] = capacities
        row["parent_gpu_models_observed"] = sorted(parent_names)
        acc = records.get(index, [])
        if len(acc) == 1:
            row["classification"] = classify(acc[0]["allocated_tres"], capacities)
        else:
            row["missing_fields"].append("unique accounting record")
        row["mig_configuration"] = ("A100 10 GB MIG allocation; exact GI/CI profile not recorded"
                                    if row["classification"] == "MIG_VERIFIED" else None)
        row["missing_fields"] += ["allocated CUDA UUID", "parent UUID mapping", "MIG GI/CI IDs"]
        rows.append(row)
    if set(by_index) - set(range(240)):
        raise ValueError("Unexpected historical array indices")
    return {"schema": "mgpu00-historical-gpu-audit-v1", "audited_at_utc": datetime.now(timezone.utc).isoformat(),
            "historical_root": str(root), "frozen_execution_sha": FROZEN_SHA,
            "accounting_command": "sacct -X -nP -j 1222413 --format=JobID,State,ExitCode,NodeList,ReqTRES,AllocTRES,ElapsedRaw,Start,End",
            "accounting_raw": accounting, "accounting_sha256": digest(accounting.encode()),
            "classification_rule": "allocation type AND matching CUDA-visible device memory; never parent-name-only",
            "summary": dict(Counter(r["classification"] for r in rows)),
            "nodes": dict(Counter(a["node"] for r in rows for a in r["accounting"])), "tasks": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    args = parser.parse_args()
    accounting = subprocess.check_output([
        "/apps/slurm/current/bin/sacct", "-X", "-nP", "-j", "1222413",
        "--format=JobID,State,ExitCode,NodeList,ReqTRES,AllocTRES,ElapsedRaw,Start,End"], text=True)
    print(json.dumps(audit(args.root, accounting), indent=2, sort_keys=True))
