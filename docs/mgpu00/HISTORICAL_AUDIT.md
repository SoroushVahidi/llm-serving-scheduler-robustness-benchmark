# LSSP-MGPU00: retrospective RQ6 integrity audit

This is a correction report on a new working branch, not a rewrite of historical
evidence or a replacement dataset. Audit date: 2026-10-21. The execution commit
is `703a752762348bd911c9d93f17731fa5244b38f9`; the validation-manifest hash is
`172efb13b30efea440a18644ef852fa2d0b8cc6fee93ea730981b2ac868bd670`.

## Scope and evidence

All 240 array indices of Slurm job `1222413` were joined to their result JSON,
server log, prologue and historical Slurm accounting record. No sampling was
used. Each of the 720 original files is identified by path, size and SHA-256 in
[`rq6_gpu_audit.json`](../../artifacts/mgpu00/historical/rq6_gpu_audit.json).
The complete `sacct` output, query, timestamp, evidence excerpts and classification
rule are retained there. Unknown identifiers are null, not inferred.

Reproducer: [`audit_rq6.py`](../../scripts/mgpu00/audit_rq6.py), run through
noninteractive SSH with its source on stdin. It reads files and invokes `sacct`;
it does not query a GPU, allocate a node or write to the remote filesystem.

| Classification | Tasks | Evidence |
|---|---:|---|
| MIG_VERIFIED | 240 | AllocTRES contains `gres/gpu:a100_10g=1`; every task's engine log reports 9.5 GiB CUDA-visible capacity |
| FULL_GPU_VERIFIED | 0 | No task satisfies the full-device rule |
| UNVERIFIABLE | 0 | Allocation class is verifiable for every task; individual UUIDs remain unverifiable |

Node distribution: `n0001`: 196 tasks; `n0089`: 43; `n0091`: 1. All 240 result
JSONs identify the recorded execution commit. Slurm reports all 240 COMPLETED,
exit code 0:0. Job completion is not proof of policy fidelity.

For every task:

- Requested and allocated GPU type: A100 10 GB MIG resource, count one.
- CUDA-visible device capacity: 9.5 GiB, observed in its engine log.
- Parent inventory: NVIDIA A100-SXM4-80GB cards, queried without an allocated-device
  UUID filter. It identifies the parent hardware family, not which parent served
  the task and not the CUDA allocation's capacity.
- CUDA-device UUID, parent UUID mapping, MIG GPU-instance ID and compute-instance
  ID: not recorded in the inspected task artifacts; not recoverable from names.
- Exact GI/CI profile beyond the named 10 GB allocation: unknown. A 10 GB label
  alone does not identify the instance's exact compute-slice profile.

## Supported and unsupported manuscript statements

Supported: 240 recorded physical executions of the legacy runner, two configured
policy paths, three sources, 40 windows/source, the recorded numerical results,
A100 parent hardware, and a 10 GB MIG allocation with 9.5 GiB visible to CUDA.

Unsupported/incorrect: the allocation was a full 80 GB GPU; the `a100_10g` label
was merely a tag without MIG meaning; parent-name queries established allocated
device identity. The working manuscript now explicitly corrects these claims.

Not established: allocated UUIDs, exact MIG profile, repeat-run variability,
full-GPU equivalence, TP/PP/DP behavior, and faithful class-aware SLAI execution.
The corrected source is in `paper/sections/real_system.tex` and
`paper/sections/limitations.tex`. The published PDF, release tags, dataset
versions, historical scripts/manifests and numerical results remain unchanged.
No journal or preprint host has been contacted.

## Confirmed measurement problems

1. **Missing class transport.** At the frozen execution commit, the validation
   runner sends only `ignore_eos` in `extra_body`. The plugin looks for
   `lssp_class_id` in `SamplingParams.extra_args`. Missing classes silently map
   to the loose/fallback TBT. Recorded `class_id` in a workload manifest is not
   evidence the server received it.
2. **Client queueing.** `rq6_calibration.py:144` fixes 32 executor workers;
   workers sleep until an arrival and remain occupied during HTTP completion.
   Further arrivals can wait in the client. At line 172, prompt construction
   happens after the planned dispatch instant. Neither actual dispatch time nor
   injection lag is recorded in the historical result schema.
3. **Synthetic physical clock.** The old plugin computes `current_step * .001`.
   Hardware-dependent iteration duration is therefore disconnected from its
   TBT deadlines and safety-margin time unit. Its decode limit defaults to 128,
   whereas the historical client allows only 32 outstanding requests.
4. **Adapter fidelity.** The old adapter estimates noncritical decode budget
   before accounting for competing prefills, can refresh LST for an intended
   rather than actually scheduled request, and temporarily removes held work
   from `running`, changing native active-capacity accounting. These are not
   solved merely by transporting classes or raising client concurrency.
5. **Calibration interpretation.** 77/120 historical calibration searches were
   already violating the SLO at the lower bound. They are terminal observations,
   not verified saturation knees. Scaling arrivals and SLO budgets together also
   mixes demand pressure with stricter deadlines.

The historical numbers are left intact and described as observations of that
legacy implementation. They cannot establish a faithful SLAI-vs-native
hardware ranking. MGPU00 engineering checks are a separate evidence class.
