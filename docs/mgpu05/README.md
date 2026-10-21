# MGPU05 — measurement integrity and engineering repeatability

**DRAFT for author review. No GPU experiment or Slurm submission was performed.**

This change builds on PR #2 / `f88f6fb97be1e012573b8136507104f8d513e67d`, which contains the MGPU02 implementation baseline `4332b08b17e5b789e20a4fe042a6b007f0d43dd6`. It adds new modules/scripts; it does not rewrite MGPU00–MGPU03 evidence, the scheduler core, historical datasets, manuscripts or frozen protocol fields.

MGPU03 job 1435222 established the bounded physical serving/mechanism baseline described in the author's MGPU05 context: 12 requests completed per mechanism, independent decision agreement, meaningful SLAI activation and whole-prefill compliance. That evidence does not establish the new measurement path, output content identity, individual emission timing, repeated-run precision or wider workload support. Original evidence stays at:

`/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-mgpu02/artifacts/mgpu02/physical-smoke/job-1435222`

## Deliverables

- [Measurement contract](MEASUREMENTS.md): identities, synthetic payload evidence, independent decoding, clocks, metric eligibility and missing-data rules.
- [Repeatability protocol](REPEATABILITY.md): exact 24-execution ceiling, twelve paired allocations, first-pair gate, controls, analysis and resource limits.
- [Main-study readiness](READINESS.md): explicit boundary against the draft research protocol and author decisions.
- [Frozen proposed plan](../../scripts/mgpu05/design.json), [software/model pins](../../scripts/mgpu05/environment.json), [API source pins](../../scripts/mgpu05/api-sources.json).
- [Prepared launcher](../../scripts/mgpu05/repeatability.sbatch), [runner](../../scripts/mgpu05/repeatability.py), [read-only independent revalidation](../../scripts/mgpu05/validate.py).
- [Exact changed-file inventory](../../artifacts/mgpu05/changed-files.txt) and [content hashes](../../artifacts/mgpu05/evidence-sha256.json).
- Code: `src/robustbench/mgpu05/`; focused tests: `tests/mgpu05/`; CPU evidence: `artifacts/mgpu05/local-validation/`.

## Local verification

Run directly, with no Actions and no CUDA devices:

```bash
CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1 /home/soroush/modal-venv/bin/python -m pytest \
  tests/mgpu00 tests/mgpu02 tests/test_anwg_metric.py tests/mgpu05 -q
bash -n scripts/mgpu05/repeatability.sbatch
```

The vLLM integration tests construct real CPU scheduler/KV objects and supply synthetic runner completions. HTTP integration uses a CPU loopback server. Neither performs model inference. Hand-specified measurement histories have independent expected IDs, token sequences, timestamps and SLO classifications; negative histories corrupt them one at a time. Existing MGPU00/MGPU02 tests remain unchanged.

Test result and limitations are recorded in [local validation](../../artifacts/mgpu05/local-validation/RESULTS.md). CPU assets were verified using the pinned local snapshot; model weights were hashed, not loaded. Three additional API/identity sources were compared byte-for-byte to vLLM's upstream v0.27.1 tag. No physical validation claim follows from these checks.
