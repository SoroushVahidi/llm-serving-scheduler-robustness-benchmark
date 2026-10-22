# Validation, reproducibility and preservation

**Final result: 583 distinct tests passed, 0 failed, 0 skipped** — unchanged 508-test baseline plus 75 P2B tests. Fourteen inherited Torch deprecation warnings remain. Pytest runtime was 58.50 seconds; this is CPU test runtime, not serving performance. One new test exhaustively checks 48 feasible plans; those plans are not added to the pytest node count.

All tests ran locally through Codex in **tmux session `lssp-p2b-validation`, window `final3`**. Final worker PID **520614**, started **2026-10-22 02:01:46 UTC**, finished **02:02:58 UTC**, shell exit **0**, retained pane `dead=1`, `exit=0`. Persistent external directory:

`/home/soroush/.local/state/lssp-p2b-validation/final3`

The final phase checkpoint is `REGRESSION_COLLECTION_AND_SOURCE_HASHES_COMPLETE`. Exact command, working directory, worker/test PIDs, tmux pane, environment, timestamps, status and exit are in [evidence/final](evidence/final/). [Raw test log](evidence/final/cpu-regression.raw.txt), [collected nodes](evidence/final/test-nodes.txt), [counts](evidence/final/counts.json), [tested source hashes](evidence/final/tested-source-hashes.json) and [native fixture](evidence/final/native-control-fixture.json) are durable mirrors. The literal test plan is constructed before native acceptance; its separate [independent intent](evidence/final/independent-intents.json) is persisted alongside the fixture afterward. This is not a crash-safe write-ahead journal.

Use the versioned [worker script](run_cpu_validation.sh) in a **new, named tmux window and new output directory**. It rejects directory reuse and records startup/PID/command/checkpoints/final exit; it never submits jobs or starts models. The actual final invocation was:

```bash
tmux new-window -d -P -F '#{window_id}' -t lssp-p2b-validation -n final3 \
 'bash /home/soroush/repos/llm-serving-scheduler-lssp-v2-p2b/docs/serving-contract/p2b-0.1.0/run_cpu_validation.sh /home/soroush/.local/state/lssp-p2b-validation/final3'
```

The returned window had `remain-on-exit` enabled. Do not repeat that exact destination; use a fresh suffix for future authorized CPU checks. No duplicate worker was launched; new windows followed completed runs only. The final regression completed before a two-minute health wait was necessary; no healthy worker was interrupted.

The worker runs the existing `/home/soroush/modal-venv/bin/python` with `CUDA_VISIBLE_DEVICES=''`, offline HF/Transformers, bytecode/plugin/cache-provider writes disabled, `PYTHONPATH=src`, and baseline test umask `0022`. The containing evidence directory is private (`0700`). Targets:

```text
tests/mgpu00 tests/mgpu02 tests/mgpu05 tests/mgpu06 tests/test_anwg_metric.py
tests/serving_v2 tests/serving_v2_p2a tests/serving_v2_p2b
```

## Other CPU checks

- [Source register](SOURCE_DEVIATIONS.md), original source pins and constrained-method digest match; installed/global vLLM remains unchanged. Only the owned CPU instance receives the hook.
- Offline packaging twice with fixed `SOURCE_DATE_EPOCH`, identical wheel hashes, no index/install and isolated stdlib-only reference imports: [packaging](evidence/packaging.json). Executed in tmux `packaging`, exit evidence retained.
- Independent P2B referee accepts the native CPU fixture against separately retained intents, complete CPU work and KV drain, **transport closure false / physical NOT VERIFIED**.
- [Preservation check](check_preservation.py) verifies original seals, frozen bytes, source/test hashes and absence of old tracked-file changes: [result](evidence/preservation.json). Executed in tmux `preservation`; this does not run a scheduler or model.
- Source/tests/docs whitespace check excludes original raw logs/patch context; raw traceback whitespace is retained rather than edited.

## Preserved diagnostics, not pooled results

Development logs are retained under `evidence/development*`. The first guarded patch construction refused an ambiguous text anchor; using a unique whole-line context fixed patch identification. A test originally requested invalid native B2/N16; the paused-before-strict case was corrected to valid B3/N3 and P7, retaining its intended ordering test. The exhaustive-case metadata was arithmetically corrected from 58 to **48 = 8+12+12+16**; all native outcomes and oracle expectations already passed.

The [first full run](evidence/first-full-umask-failure/) passed 579 tests and failed an inherited permissions fixture because private worker `umask 077` changed its explicit `mkdir(0755)` result to 0700. The wrapper now launches tests with baseline `umask 022`, preserving the private evidence parent. No inherited permission test/guard changed. A subsequent 580-pass run is retained in [pre-final-guard-run](evidence/pre-final-guard-run/); the final 583-pass run additionally validates low-level CPU opt-in and queue-object identity. Counts are distinct nodes in the final run, never the sum of runs.

## Preservation and next gate

PR #7 head/ancestry verified; [PR stack record](evidence/pr-stack.json). All **29 frozen script/protocol hashes**, original **20 v2**, **27 P1** and **31 P2A** files/evidence seals remain intact. No existing source/test, historical simulator, frozen experiment/configuration, manuscript, dataset, source data or prior evidence file was edited.

The inherited `dataset/v1.1.0/scientific/campaign/consolidated.json` LFS-filter anomaly remains untouched/unstaged. Raw bytes equal the baseline: 37,252,923 bytes, SHA-256 `73adf7d97f06985ec8f8e1c2f794fd43178433eb198e1c00705e817f4bde9c26`. No reset/clean/repair was performed. Existing worktrees/branches and approved MGPU06 execution authority were preserved.

No GPU/model inference, Slurm/Wulver, paid cloud, Actions/CI, merge, manuscript change, scientific workload or ranking experiment occurred. **GPU-hours: 0.** General pressure, distributed behavior, actual runner execution and numerical LST remain unsupported. GO for author review and a separately scoped CPU execution-attestation bridge; NO-GO for physical serving or full SLAI/ranking claims. The whole native method is not transactional; late failures intentionally stop with preserved partial mutation.
