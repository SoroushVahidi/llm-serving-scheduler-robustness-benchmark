# Review and CPU validation record

This is a specification review, not implementation or physical validation of v2. The 32 literal cases are proposed expectations, **not 32 executed scheduler tests**. No GPU, inference, Slurm, Wulver scheduling probe, Actions, new scientific experiment or manuscript work occurred. New files are confined to this directory. Previous evidence remains in its original locations.

## Authority and preserved state

- Repository: `SoroushVahidi/llm-serving-scheduler-robustness-benchmark`.
- Reviewed draft PR #4 head: `efc5243898d18bbb62ccb51dcf66a0767827dac6`; stacked on draft PR #3 at `b14992716c20b36d26e6f28e60b2c8e0b8b09a07`. PR #4 metadata was checked through GitHub read-only before work.
- Isolated branch: `research/lssp-serving-contract-v2-draft`, rooted at that exact PR #4 head. Source/evidence/protocol authority was recovered from the stack, not assumed from an unrelated checkout.
- The 29 preserved MGPU02/MGPU05/MGPU06 script/manifest and protocol file hashes still match the inherited preservation inventory. [preservation.json](evidence/preservation.json) records them.
- Known pre-existing checkout anomaly: `dataset/v1.1.0/scientific/campaign/consolidated.json` is reported modified by Git's LFS filtering, but its 37,252,923 raw bytes match the baseline blob (SHA `73adf7d97f06985ec8f8e1c2f794fd43178433eb198e1c00705e817f4bde9c26`). It was not edited, staged or repaired. No existing worktree was reset or cleaned.
- Recorded prior evidence: 271 distinct CPU tests for PR #4; older 283 figure comprised 250 local tests plus 33 overlapping Wulver checks. No new full-suite claim is made here. Recorded MGPU06 state remains hardware-blocked, no submitted pair and zero consumed GPU-hours; no fresh Slurm inquiry was necessary for this specification. MGPU03 bounded serving acceptance does not validate MGPU05 measurement additions or this draft.

## Commands and actual outcomes

Commands were run from the isolated repository root with Python `/home/soroush/modal-venv/bin/python`. Package identities are in [sources.json](evidence/sources.json). Checks use the locally installed pinned source; this is not a new Wulver-environment validation.

```sh
CUDA_VISIBLE_DEVICES='' HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
/home/soroush/modal-venv/bin/python -B -m pytest -q -p no:cacheprovider \
  tests/mgpu02/test_fidelity_boundaries.py \
  tests/mgpu02/test_contract.py tests/mgpu02/test_simulator_limits.py
```

**43 passed, zero failures, 14 existing PyTorch deprecation warnings, 1.57 seconds**. [Raw log](evidence/cpu-tests.log). Includes real native CPU scheduler/KV characterization with synthetic outputs, PR #4 negative admission/telemetry cases, unsupported configuration rejection and historical simulator limitations. No model runner or CUDA inference was executed.

```sh
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 \
/home/soroush/modal-venv/bin/python -B \
  docs/serving-contract/v2.0.0-draft.1/check_runtime_boundary.py
```

**PASS_CPU_ONLY:** four actual native scalar observations (int 0; float 0.0, 0.0, 0.5) accepted by PR #4. CUDA remained uninitialized. The probe itself hides CUDA and enables offline asset behavior. [Raw log](evidence/runtime-boundary.log). This is an additional focused probe, not four separately counted pytest tests. No guard was weakened.

```sh
python3 -B docs/serving-contract/v2.0.0-draft.1/validate_documents.py
git diff --cached --check
```

Document checks cover draft/approval status, 32 case identities, literal budget/progress/LST arithmetic, links, all A01–A16 references, preserved hashes and recomputed frozen descriptor statistics. [Check log](evidence/document-checks.json). They deliberately do not execute a proposed scheduler, assert general semantic fidelity or claim independent human approval. The staged whitespace check applies only to the new directory.

Five installed vLLM files were fetched read-only from tag `v0.27.1` and all five SHA-256 values match; 11 supporting SLAI files were fetched from immutable commit `5098a7aba05e3edbcfa3a509d6cc9cd248fc4380`. URLs and hashes are recorded. A short local PyArrow metadata inspection confirmed the preserved workload table has 120 descriptor rows, not a corpus of raw target-tokenized requests. No full trace scans or downloads occurred.

## Evidence limits and integrity

`evidence/SHA256.json` seals all files in this draft directory except itself. The seal authenticates the reviewed package, not the truth of a physical execution. Independent author/reviewer approval and future CPU/model-runner implementations are still required. Current positive probes cannot establish cancellation race handling, output-prefix preservation through actual GPU recomputation, long-context coverage, per-token generation observability, TP/DP collective correctness or instrumentation overhead.

No next implementation stage or GPU resources are authorized by a passing document check. See the unresolved [decision matrix](AUTHOR_DECISIONS.md) and [implementation order](IMPLEMENTATION_PLAN.md).
