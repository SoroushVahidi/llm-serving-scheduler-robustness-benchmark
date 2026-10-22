# Validation record

**508 distinct tests passed, 0 failed, 0 skipped** in the final combined run: 415 inherited tests plus 93 P2A tests. Fourteen existing Torch deprecation warnings remain. The run took 45.41 seconds on this host; that is test runtime, not serving performance. No CUDA/model inference, allocations, Slurm/Wulver, Actions or other CI ran.

One new pytest node exhaustively exercises **216** two-request native CPU schedules (bounds in [CONFORMANCE.md](CONFORMANCE.md)); these are not additional distinct test nodes. Other new cases include real scheduler partial-prefill, batch conservation, deliberate faulty acceptance, corrupted raw records, immutable identities, malformed ACKs, capacity refusal and unresolved S02 counterexamples. ACK token IDs and host-control clock values are synthetic. The clock values are fixture monotonic numbers, **not measured wall time**.

Run from the P2A repository root, using the existing local environment:

```bash
CUDA_VISIBLE_DEVICES='' HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src \
P2A_EVIDENCE_DIR=docs/serving-contract/p2a-0.1.0/evidence \
/home/soroush/modal-venv/bin/python -B -m pytest -q -s -p no:cacheprovider \
 tests/mgpu00 tests/mgpu02 tests/mgpu05 tests/mgpu06 \
 tests/test_anwg_metric.py tests/serving_v2 tests/serving_v2_p2a
```

The preserved invocation redirected stdout/stderr to [cpu-regression.raw.txt](evidence/cpu-regression.raw.txt). Reproduction should redirect to a **new output directory/log**, not overwrite committed evidence. Set `P2A_EVIDENCE_DIR` to that new directory. No dependencies are installed by the test command. For collected-node reproduction, replace `-s` with `--collect-only`; [raw collection](evidence/test-collection.raw.txt) and [unique node list](evidence/test-nodes.txt) preserve the observed result. Counts refer to the final node set, not the sum of repeated development runs.

Other executed local checks:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /home/soroush/modal-venv/bin/python -B \
 docs/serving-contract/p2a-0.1.0/check_documents.py
PYTHONDONTWRITEBYTECODE=1 /home/soroush/modal-venv/bin/python -B \
 docs/serving-contract/p2a-0.1.0/check_packaging.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /home/soroush/modal-venv/bin/python -B \
 docs/serving-contract/p1-0.1.0/check_documents.py
git diff --cached --check -- . ':(exclude)docs/serving-contract/p2a-0.1.0/evidence/*.raw.txt'
```

[Document/preservation results](evidence/document-checks.json), [unchanged P1 checks](evidence/p1-preservation.json), [offline wheel results](evidence/packaging.json), [environment](evidence/environment.json), and [manifest](manifest.json) supplement the raw tests. Packaging builds twice in a disposable external directory, with no index/network/dependency installation and fixed `SOURCE_DATE_EPOCH`; identical wheel hashes and isolated `-I -S` imports are checked. Native/referee modules remain opt-in; referee/type imports require only stdlib and P1's independent reference, not P1 production logic, native vLLM or torch.

The initial combined development run had **506 passes and one test-setup failure**: attempting to set the read-only `use_v2_model_runner` property. The preserved [development log](evidence/development-regression.raw.txt) records it. The test now selects the legacy runner via the actual pinned environment property (`VLLM_USE_V2_MODEL_RUNNER=0`) and confirms rejection; no production validation was weakened. A subsequent source review added identity-based runner-row permutation handling and its pinned-source helper test; the preceding 507-pass run is retained in `evidence/pre-permutation-regression.raw.txt`. Final counts are 508, not the sum of these runs. Initial document checks also encountered evidence-creation order and absent optional wheel metadata; `evidence/development-document-note.txt` records their resolution without dependency installation. Earlier focused implementation iterations are not claimed as final passing counts.

The unfiltered whitespace check reports two trailing-space lines emitted by pytest in the preserved failing development traceback. Raw logs remain byte-for-byte intact. The scoped check above excludes only raw logs and passes for all source, tests, documentation and structured evidence.

## Preservation and evidence scope

- PR #6 head and ancestry rechecked before publication. Changes are only new P2A source/test/document/evidence paths.
- All 29 frozen script/protocol hashes and both original v2/P1 evidence seals checked. Existing MGPU implementations/tests, P1 producer/referee, historical simulator, scripts and study protocol have no diff from the approved base.
- The inherited Git LFS-filter anomaly for `dataset/v1.1.0/scientific/campaign/consolidated.json` remains unstaged and untouched. Its raw bytes equal the baseline: 37,252,923 bytes, SHA-256 `73adf7d97f06985ec8f8e1c2f794fd43178433eb198e1c00705e817f4bde9c26`. It was not reset, cleaned, staged or repaired.
- Existing worktrees/branches/evidence and MGPU06 execution identity/configuration remain unchanged. No frozen protocol field is silently approved.
- [Native CPU fixture](evidence/native-cpu-fixture.json) has real native scheduling/KV snapshots plus separately synthetic ACKs. Independent validation finds complete CPU batches and drained allocation, **not transport closure** or physical validation.
- [SHA-256 seal](evidence/SHA256.json) covers new P2A source, tests, docs and raw evidence, excluding the seal itself. Upstream source hashes are separate from local artifact hashes. This is an integrity record, not a signature or proof of actual GPU execution.

## Next-stage acceptance

The narrow CPU verification boundary is ready for author review. **General SLAI native enforcement is NO-GO**: native schedule can substitute work and has already mutated state before comparison. **Physical validation is NOT VERIFIED**, including executed GPU spans, final-prefill sampling, asynchronous errors/quiescence and overhead. No new physical test or next implementation stage is authorized by this result. Required author choices and the smallest next design task are in [DECISIONS.md](DECISIONS.md).
