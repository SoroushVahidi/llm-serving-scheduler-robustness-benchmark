# Diagnostic retry 1434644

Submitted 2026-10-21 at approximately 16:40:51 UTC. Exactly one retry.
Execution commit: `77ddb6fe93fd77ee6bce8883b911696789917b7e`.
Later ledger commits do not change the remote execution checkout.

Account ikoutis; partition gpu; QoS standard; explicit gpu:a100:1; one node;
16 CPUs; 32 GiB; 20-minute hard limit; automatic requeue disabled.
Maximum allocated GPU-hours: 1/3. No matrix, pilot or distributed execution.

Remote worktree: `/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-mgpu00`.
Output parent: that worktree's `artifacts/mgpu00/probe-retry`.

Submission from the remote worktree:

```sh
/apps/slurm/current/bin/sbatch --parsable \
  --account=ikoutis --partition=gpu --qos=standard --gres=gpu:a100:1 \
  --export=ALL,MGPU00_REPO=/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-mgpu00,MGPU00_OUT_PARENT=/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-mgpu00/artifacts/mgpu00/probe-retry,MGPU00_EXPECTED_SHA=77ddb6fe93fd77ee6bce8883b911696789917b7e \
  --output=/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-mgpu00/artifacts/mgpu00/probe-retry/slurm-%j.out \
  --error=/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-mgpu00/artifacts/mgpu00/probe-retry/slurm-%j.err \
  scripts/mgpu00/smoke.sbatch
```

## Evidence paths relative to output parent

- `slurm-1434644.out`, `slurm-1434644.err`
- `job-1434644/device/device_probe.events.jsonl`: fsynced observations and query errors
- `job-1434644/device/device_probe.raw.json`: completed raw collection or collection error
- `job-1434644/device/device_verification.json`: named checks and old predicates evaluated on new evidence
- `job-1434644/progress/device_probe.events.jsonl`: smoke stage transitions
- `job-1434644/gpu_provenance.json`: only after independent identity verification
- `job-1434644/native_fcfs-rep0.server.log`, `slai_mgpu00_checked-rep0.server.log`
- Per-policy `.raw_replay.json` and `.validated.json`: raw versus validated serving evidence
- `job-1434644/failure.json` or `summary.json`: failure versus both mechanisms passing

Raw/progress files do not exist while queued. Their existence alone is not a pass.
A Slurm termination may leave incomplete journals without a failure.json.

## Later inspection (read-only; no new submission)

```sh
ssh -T -o BatchMode=yes wulver \
  '/apps/slurm/current/bin/sacct -n -P -j 1434644 --format=JobID,State,ExitCode,Elapsed,AllocTRES,NodeList'
ssh -T -o BatchMode=yes wulver \
  'cat /project/ikoutis/sv96/github/llm-serving-scheduler-lssp-mgpu00/artifacts/mgpu00/probe-retry/job-1434644/device/device_verification.json'
ssh -T -o BatchMode=yes wulver \
  'cat /project/ikoutis/sv96/github/llm-serving-scheduler-lssp-mgpu00/artifacts/mgpu00/probe-retry/job-1434644/progress/device_probe.events.jsonl'
```

For the later outcome, inspect Slurm exit/elapsed/resources plus all named device
checks, then both validated round files and the summary. Failure/timeout or
missing rounds must not be called a pass. Even a complete minimal smoke provides
no reproducibility or TP2-readiness evidence. No automated follow-up is scheduled.

## Initial monitoring snapshot

**RUNNING_HEALTHY** at the final initial-health snapshot, 2026-10-21
16:42:51 UTC (two minutes after submission; 107 allocated seconds). Slurm
reported RUNNING on n0003, one full-A100 typed GRES, no error output.
Monitoring stops here; the job remains managed by Slurm.

All **15 independent identity checks passed**. Physical identity:

- CUDA ordinal 0; CUDA_VISIBLE_DEVICES=0; NVML index 0.
- CUDA model NVIDIA A100-SXM4-80GB, 85,093,777,408 bytes (~79.25 GiB).
- NVML physical memory 85,899,345,920 bytes (80 GiB).
- CUDA raw UUID `ce14abd6-e9d0-44be-b887-ba3276440e00`.
- NVML and physical-parent UUID `GPU-ce14abd6-e9d0-44be-b887-ba3276440e00`.
- CUDA/NVML PCI address `00000000:01:00.0`.
- NVML handle is not MIG; current and pending MIG modes both 0 (disabled).
- Matching selected nvidia-smi UUID/model/PCI/mode; no inventory-only inference.

The legacy predicates evaluated on this new evidence fail exactly
`raw_cuda_uuid_equals_nvml_uuid` and `raw_cuda_uuid_starts_GPU_prefix`.
PyTorch's `_CUuuid` string lacks the GPU prefix that NVML supplies, despite
matching UUID bytes/identity. This physically reproduces the old verifier's
formatting defect using the same installed Torch build. It does not recover the
old job's missing UUID/memory/MIG values or rule out additional old failures.

At this snapshot the progress journal ended at `device_verified`; neither
mechanism round had started, no server logs existed, and there was no final
summary or failure file. Physical vLLM, replay and scheduler validation therefore
remain **unestablished**, not passed. No reproducibility/TP2 claim is made.

Committed initial evidence is in `artifacts/mgpu00/probe-retry-status/`:
`job-1434644-initial.json`, `job-1434644-device.raw.json`, and
`job-1434644-device.verification.json`. These are immutable snapshots, not live
completion records. Later inspection must read the remote outputs and accounting.
