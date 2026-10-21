# MGPU00 device-probe repair and one diagnostic retry

Base: `4e145b6fcd0fde786d17ad8fda5f109b839dc212`, draft PR #1.
This follow-up leaves the historical audit, all historical results, and all
manuscript corrections unchanged.

## What can be diagnosed about job 1434545

The saved traceback identifies the compound predicate in the old
`verify_full_a100`, after the exactly-one-CUDA-device check and before the Slurm
GRES check. It also establishes that the CUDA-property and NVML queries reached
that predicate without throwing. It does **not** identify which of these failed:
A100 model name; non-MIG handle; disabled MIG mode; >=75 GiB visible memory;
raw CUDA/NVML UUID equality; or the CUDA UUID's literal `GPU-` prefix.

No raw values were retained, so the exact historical subcondition/root cause
cannot be recovered from the existing artifacts. Slurm accounting confirms
`gres/gpu:a100=1` on n0003, not the CUDA-visible identity. A new allocation can
explain a reproducible probe defect but cannot retroactively supply the old
allocation's missing evidence. The new verification report evaluates each old
predicate against **new evidence only**, clearly labeled as such.

Confirmed code defects: validation preceded persistence; unrelated conditions
shared one error; raw UUID string/prefix comparisons confused representation
with identity. The latter can reject equivalent complete UUIDs, as a focused
fixture demonstrates, but is not asserted as the historical cause.

## Mapping and strict verification

CUDA_VISIBLE_DEVICES can contain an ordinal remapped by the job cgroup, rather
than the corresponding NVML physical-device index. We retain the selector,
CUDA ordinal, NVML index, UUIDs, PCI IDs, Slurm GRES/environment, and cgroup
context separately. No mapping assumes these indices are equal. Device lookup
uses the CUDA UUID, with complete canonical prefix alternatives for a bare UUID;
there is no index-based, partial-UUID, PCI-only or inventory-only fallback.

Normalization accepts complete UUIDs with case/prefix representation differences,
but preserves the distinction between `GPU-`, `MIG-`, and legacy
`MIG-GPU-.../GI/CI` identities. A bare CUDA UUID may match the full physical
NVML UUID only when the separate non-MIG handle, disabled MIG modes, memory,
parent, model and PCI checks all pass. CUDA UUID bytes, when available, must
also agree with its textual representation.

The gate requires one CUDA-visible A100 with >=75 GiB (the expected full 80 GB
Wulver class), full physical NVML identity, current/pending MIG mode disabled,
matching physical parent UUID, CUDA/NVML PCI agreement, and full A100 Slurm GRES.
CUDA/NVML memory totals may differ by at most 2 GiB while both independently
satisfy the full-memory threshold; exact byte equality is not assumed across
APIs/reservations. Missing mandatory evidence fails closed.

nvidia-smi inventory is diagnostic context, never proof that a listed card is
allocated. A successful selected-UUID query is checked for contradictory UUID,
model, memory, PCI address and MIG mode. A failed supplementary nvidia-smi query
is recorded; it cannot substitute for mandatory CUDA/NVML verification.

## Durable evidence

`device/device_probe.events.jsonl` records query start/result/error events and
flushes/fsyncs each event. This preserves completed observations even if a later
query crashes or Slurm terminates the process. It starts before importing Torch.
After collection, `device/device_probe.raw.json` and
`device/device_verification.json` are written/fsynced **before** any identity
exception. Writes are exclusive; old evidence cannot be overwritten.

Raw context includes selected Slurm variables (not the full environment),
`scontrol show job -d -o`, nvidia-smi inventory and selected UUID, Torch UUID
string/type/bytes/properties, CUDA capacity, NVML identity/model/memory/index/PCI,
parent and MIG GI/CI where applicable, software versions, `/proc/self/cgroup`,
cgroup mount information, accessible v1 devices.list, and /dev/nvidia* node
numbers. Cgroup v2 device BPF enforcement is explicitly not inferred or queried
with elevated privileges. Permission/unsupported-query errors are recorded.
No GPU query is permitted outside a Slurm compute-node context.

Every mandatory identity condition gets a named pass/failure reason. A
collection exception also produces a raw error record and failed check report;
its previously collected values remain in the durable event journal.

## Validation and execution boundary

57 local tests pass, including 30 added probe cases and the 27 prior tests.
Cases cover full A100, MIG with a full parent, missing/contradictory metadata,
UUID formats, index remapping, nvidia-smi disagreement, failures with preserved
raw evidence, a mid-collection crash, and rejection outside a Slurm allocation.
The collector itself is exercised with fake Torch/NVML bindings; no local GPU
workload is used. Evidence is under `artifacts/mgpu00/probe-repair-validation/`.
Shell syntax, Python compilation and source diff checks also pass.

One retry is authorized: account ikoutis, gpu partition, standard QoS,
`gpu:a100:1`, one node, 16 CPUs, 32 GiB, 20-minute ceiling, no automatic requeue.
The account association grants standard QoS; its inspected GPU exclusion is L40,
not A100. The ceiling is 1/3 allocated GPU-hour. No extra job or automatic retry.

Identity failure stops before vLLM. Success permits only two short rounds:
native once, then guarded SLAI once (12 requests each, same pinned 0.5B model).
Existing class-receipt, actual scheduling/hold, replay timing and completion
gates remain in force. No reproducibility claim is possible with one round per
mechanism. There is no 24-run matrix, 144-run pilot or TP2 validation.

`progress/device_probe.events.jsonl` records smoke stages. Per-policy server
logs contain MGPU00_EVENT metadata/admission/scheduling records; raw replay and
validated result files are distinct. `failure.json` preserves unsuccessful
attempts; `summary.json` exists only after both rounds pass. A Slurm timeout may
leave only partial journals/logs and is never interpreted as a pass.

## Authoritative references

- [Slurm GRES GPU management](https://slurm.schedmd.com/gres.html): CUDA visibility
  and cgroup remapping; NVML numbering versus device-file numbering.
- [NVIDIA NVML device queries](https://docs.nvidia.com/deploy/archive/R535/nvml-api/group__nvmlDeviceQueries.html):
  UUID lookup and the distinction between CUDA and NVML device indices.
- [NVIDIA MIG device names](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/mig-device-names.html):
  physical and MIG identities/device nodes.

Job ID, executed commit, initial status and later-inspection commands are recorded
in the retry submission ledger after submission. Monitoring ends approximately
two minutes after submission; queued status is not a validated running job.
