# Bounded smoke submission 1434545

Submitted 2026-10-21 at approximately 16:27:17 UTC. This is the only MGPU00
submission. Code commit: `3aaaa3012193091519cbdf5e5e27ea87a9f4b25e`.
Later documentation commits do not change the remote execution worktree.

Requested resources: account `ikoutis`, partition `gpu`, QoS `low`, one node,
one full `gpu:a100:1`, 16 CPUs, 32 GiB RAM, 45 minutes, no automatic requeue.
Hard allocated-GPU-time ceiling: 0.75 GPU-hour; no automatic retries.

Remote isolated worktree:
`/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-mgpu00`.
Its content and recorded executable modes matched the submitted commit.
No historical worktree was modified. Existing environment packages were used;
no installation was performed. The installed vLLM scheduler source hash matched
the locally tested pin. Wulver package metadata: Torch 2.13.0, vLLM 0.27.1,
httpx 0.28.1, nvidia-ml-py 13.610.43, transformers 5.16.1. Local tests used
transformers 5.8.1, so the physical check is also needed for that environment
difference. Both use the same immutable model/tokenizer snapshot.

Submission command, from that worktree:

```sh
/apps/slurm/current/bin/sbatch --parsable \
  --export=ALL,MGPU00_REPO=/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-mgpu00,MGPU00_OUT_PARENT=/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-mgpu00/artifacts/mgpu00/smoke,MGPU00_EXPECTED_SHA=3aaaa3012193091519cbdf5e5e27ea87a9f4b25e \
  --output=/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-mgpu00/artifacts/mgpu00/smoke/slurm-%j.out \
  --error=/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-mgpu00/artifacts/mgpu00/smoke/slurm-%j.err \
  scripts/mgpu00/smoke.sbatch
```

Log paths under the remote worktree:

- `artifacts/mgpu00/smoke/slurm-1434545.out`
- `artifacts/mgpu00/smoke/slurm-1434545.err`
- `artifacts/mgpu00/smoke/job-1434545/` (created only after job startup)

Initial accounting: PENDING, reason Priority, elapsed 00:00:00, no assigned node
or allocated TRES. No log files existed yet. Submission is not successful
physical validation. Allocation identity, replay timing, scheduling activation,
completion and actual GPU usage remain unverified until result inspection.

The final startup snapshot is recorded below. The job had already ended at the
single final check within the user's approximately three-minute startup window.

## Final startup snapshot

**FAILED.** At 2026-10-21 16:30:08 UTC, Slurm reported exit code 1:0,
elapsed 00:02:36, node `n0003`, and allocated TRES
`billing=32,cpu=16,gres/gpu:a100=1,gres/gpu=1,mem=32G,node=1`.
Allocated GPU usage: `1 * 156 / 3600 = 0.043333... GPU-hours`.

The first device-identity gate raised
`ValueError: Full A100 identity not independently verified`.
No vLLM server was started and no warmup or workload requests were executed.
No scheduler activation, metadata receipt, replay timing or reproducibility
diagnostics exist for this physical attempt. No retries were submitted.

The gate checks model, visible memory, MIG mode/handle and CUDA/NVML UUID
equality. Its compound failure does not identify which check failed: the probe
raised before its raw record was written. This is an observability defect in
MGPU00 itself and must be repaired before a separately reviewed retry. The
Slurm allocation label alone cannot establish full-device CUDA identity, and
the failure alone cannot establish that this was a MIG allocation. Do not infer
either conclusion from the available evidence. No further device query was
attempted after allocation termination.

Committed evidence: `artifacts/mgpu00/smoke-status/job-1434545-startup.txt`
(final accounting and complete traceback) and
`artifacts/mgpu00/smoke-status/job-1434545-failure.json`.

The immediate blocker is independent device verification. Other unresolved
gates remain: full end-to-end metadata receipt, actual SLAI activation, controlled
physical replay timing, repeated successful mechanisms, general prefill/KV
semantics and TP2 support. **The 144-run pilot is NO GO.**
