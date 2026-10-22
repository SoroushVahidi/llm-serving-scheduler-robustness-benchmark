# Single authorized STAT01 recovery submission

Execution status at the bounded startup observation: **RUNNING_HEALTHY**.
This is not a completed experiment or a calibration verdict.

- Draft PR: #14, stacked on #13.
- Execution commit: `1ac4c8dd1421aabad05e6ce243cb911a6ed6c8e1`.
- Slurm ID: **1440206**.
- Submitted: 2026-10-22 **14:52:38 UTC**.
- Started: 2026-10-22 **14:52:50 UTC**.
- Startup snapshot began: **14:54:04.981648 UTC**; its checkpoint was updated
  **14:54:07.173893 UTC**, within two minutes of submission.
- Node: `n0006`; four CPUs, 8 GiB requested, no GPUs, maximum `09:00:00`.
- Canonical run identity:
  `061933a64e27da208dc782865f7a5f39e5788357b11b37df7899c423226de319`.
- Run ID: `stat01-recovery-v2-061933a64e27da20`.

Separate deployment:

```text
/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-stat01-recovery-v2-20261022/
```

Exact submission argv, exported environment, response and time are preserved in
`evidence/submission.json`. It invokes `sbatch` on the manifest-hashed
`code/recovery.sbatch` through the gated `code/submit_once.py`. `/project` resolves
to `/mmfs1/project` on Wulver; the recorded argv uses that canonical spelling.
The distinct manifest is `evidence/launch.json`; the preflight PASS, binding all
code/protocol/source hashes and 112,275 reusable studies, is in `evidence/preflight.txt`.

Paths beneath the separate deployment:

```text
launch.json
submission-intent.json
submission.json
logs/tests-pinned.txt
logs/preflight.txt
logs/stat01-recovery-v2-061933a64e27da20-1440206.out
logs/stat01-recovery-v2-061933a64e27da20-1440206.err
runs/stat01-recovery-v2-061933a64e27da20/checkpoint.json
runs/stat01-recovery-v2-061933a64e27da20/batches/
```

At the snapshot Slurm reported RUNNING, elapsed about 1m16s. The checkpoint
recorded **7,250 reused studies**, **zero generated studies**, and RUNNING.
Stdout showed newly validated reused batches and subsequent batch starts;
stderr was empty and no failure records existed. The full captured Slurm records,
checkpoint and log tails are in `evidence/startup.json`.

Monitoring ended after this one snapshot. No later completion is inferred.
Expected remaining work at launch: derive nine separate comparisons for all
112,275 audited originals, generate the 21,725 missing studies under unchanged
streams/stopping, and independently validate every published recovery batch.
Recovered computation and scientific interpretation require a later output review.

All original source files, failed-run checkpoints/artifacts, historical evidence,
C01 and M2 remain unchanged. Only this separate recovery was submitted. GitHub
Actions showed zero runs on this branch at submission; commits carry `[skip ci]`.
