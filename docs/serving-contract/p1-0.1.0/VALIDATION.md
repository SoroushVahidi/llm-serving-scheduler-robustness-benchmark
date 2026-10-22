# Validation and evidence / P1 0.1.0

Authoritative base: draft PR #5 `ee1868618db9afc89160e1d0daf92b54829a80bc`, verified through GitHub before creating `research/lssp-v2-p1-ledger` in an isolated worktree. PRs #3–#5 remain drafts. Existing worktrees and evidence were preserved. Prior documentation is not retrospectively relabeled as approved or executed; see the prospective [amendment](APPROVAL_AMENDMENT.md).

## Direct CPU validation

One combined invocation, without duplicated test paths:

```sh
CUDA_VISIBLE_DEVICES='' HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src \
/home/soroush/modal-venv/bin/python -B -m pytest -q -s -p no:cacheprovider \
  tests/mgpu00 tests/mgpu02 tests/mgpu05 tests/mgpu06 \
  tests/test_anwg_metric.py tests/serving_v2
```

**415 distinct passed; 0 failed; 0 skipped**, 14 existing PyTorch deprecation warnings, 12.66 seconds. **271 existing + 144 P1 tests**. The earlier targeted development runs are not added to this count. [Raw combined log](evidence/cpu-regression.raw.txt). Existing tests exercise native vLLM scheduler/KV objects with synthetic runner replies, not model execution. P1 tests and referee have no vLLM/Torch dependencies. No fresh Wulver or GPU validation is claimed.

The six exhaustive test nodes contain **170 deterministic complete histories**; bounds/configuration and per-grid counts are in [CONFORMANCE.md](CONFORMANCE.md) and the raw log. They are included in the 144 tests, not 170 additional pytest tests. Seed: none; exhaustive traversal. Journal corruptions and a deliberately broken production transition independently fail reference validation. All such rejection tests count as passing tests, not successful inference.

```sh
PYTHONDONTWRITEBYTECODE=1 /home/soroush/modal-venv/bin/python -B \
  docs/serving-contract/p1-0.1.0/check_packaging.py
python3 -B docs/serving-contract/p1-0.1.0/check_documents.py
python3 -B docs/serving-contract/v2.0.0-draft.1/validate_documents.py
git diff --cached --check
```

Offline wheel build uses an external temporary copy, `--no-deps --no-build-isolation --no-index`, fixed SOURCE_DATE_EPOCH and isolated `python -I -S` imports. It confirms the new modules are packaged, the referee imports without the producer, and no heavy dependencies load. [Packaging output](evidence/packaging.json). Existing pyproject and package version remain unchanged; P1's evidence schema has its own version.

[Preservation/document result](evidence/document-checks.json) verifies all 29 inherited frozen script/protocol hashes, all 20 PR #5 specification/evidence files, corpus identity, existing runtime/simulator/tests and protocol paths, Python syntax, reference import independence and local document links. [Original specification check](evidence/original-specification-check.json) is an unmodified PR #5 checker; its statements that v2 is unimplemented remain historical draft-package scope, not a claim that P1 does not exist.

The first documentation assembly check correctly detected a referenced check log before it had been generated. Generating that output and rerunning resolved the link failure; [initial diagnostic](evidence/document-check-initial.txt) is retained. This was not a pytest failure or a changed specification expectation.

The known LFS checkout anomaly for `dataset/v1.1.0/scientific/campaign/consolidated.json` persists: Git reports modified, but the 37,252,923 raw bytes match the baseline blob SHA `73adf7d97f06985ec8f8e1c2f794fd43178433eb198e1c00705e817f4bde9c26`. It is not edited, repaired or staged. No frozen MGPU06 commit/configuration is changed.

A deterministic [16-event journal](evidence/fixture-journal.json) is retained for independent CLI review, along with its [referee output](evidence/fixture-validation.json). It exercises split prefill, first emission, external preemption, replay of the known prefix, second emission, coalesced client observation and cleanup. This is an additional CPU fixture check, not an additional pytest test or physical measurement:

```sh
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 /home/soroush/modal-venv/bin/python -B \
  docs/serving-contract/p1-0.1.0/record_fixture.py > fixture.json
PYTHONPATH=src /home/soroush/modal-venv/bin/python -B -m \
  robustbench.serving_v2.reference fixture.json --require-complete
```

[Local package versions](evidence/environment.json) include an explicitly absent standalone `wheel` distribution: an initial unconditional metadata lookup failed, then recorded that absence. The offline setuptools wheel build passed; no package installation or environment change was needed.

## Evidence classes

| Evidence | Established | Not established |
|---|---|---|
| PR #5 expectations | Original 32-case corpus preserved | Full corpus implemented or approved |
| P1 CPU conformance | Request-local state, identity, output/work conservation and independent journal agreement within tests/bounds | Policy priorities, batch selection, native acceptance or actual physical execution |
| Existing native CPU regressions | Pinned native decision/state behavior under synthetic replies; PR #4 guards retained | GPU samples, pressure serving or MGPU06 physical acceptance |
| Packaging/preservation | Opt-in imports, no dependencies/paths altered, frozen evidence unchanged | Hot-path overhead, crash-safe physical capture or production readiness |

No GPU allocations, CUDA inference, model execution, Slurm/Wulver work, external cloud jobs, Actions or other CI, merges, manuscripts, datasets or ranking experiments. Tests ran directly through Codex. Commit/PR use `[skip ci]`; no workflow was invoked. Short CPU checks completed directly; no background job required.

## Reproduction limits

Raw logs retain synthetic host times and local environment messages; reruns need not be byte-identical. Event ordering for identical supplied inputs is deterministic (tested). Token symbols are fixtures, not predictions from a model. Allocation records are caller-supplied, not generated by an allocator. Performance eligibility, true token-emission timing, content correctness and distributed fidelity remain NOT VERIFIED. No numeric SLAI thresholds/offsets were added.

The SHA256 evidence seal covers new source, tests and this prospective documentation; it excludes itself to avoid a circular hash. The original PR #5 evidence seal is preserved separately. Independent author review remains required before P2, as detailed in README.md.
