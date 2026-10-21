# Partial-prefill, long-prompt, KV and admission fidelity review

2026-10-21. **Engineering investigation and CPU validation only.** No GPU allocation, model forward pass, Slurm submission, workload campaign, Actions run, manuscript modification or change to an approved experiment was performed. General partial-prefill/KV/distributed serving remains unsupported.

## Authority and preservation

Repository: `SoroushVahidi/llm-serving-scheduler-robustness-benchmark` (private).
The Git remote, local branch, Wulver checkout and live draft PR metadata agree:

| Component | Authoritative identity |
|---|---|
| MGPU02 checked serving / PR #1 | `research/lssp-mgpu00-integrity-20261021`, `4332b08b17e5b789e20a4fe042a6b007f0d43dd6` |
| Draft research protocol / PR #2 | `research/lssp-protocol01-20261021`, `f88f6fb97be1e012573b8136507104f8d513e67d` |
| MGPU05 measurement baseline | `b397b0258e32f5c1277477e0a024040302ebb00e` |
| Current MGPU05/MGPU06 / PR #3 | `research/lssp-mgpu05-measurement-20261021`, `b14992716c20b36d26e6f28e60b2c8e0b8b09a07` |
| This isolated review branch | `research/lssp-prefill-kv-fidelity-20261021`, based on the exact PR #3 head |

Original local checkout: `/home/soroush/repos/llm-serving-scheduler-lssp-mgpu05`; clean when inspected. New worktree: `/home/soroush/repos/llm-serving-scheduler-lssp-fidelity`. The Wulver checkout `/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-mgpu05` is clean and detached at `b149927`. No remote checkout was changed. Other worktrees/branches were listed for identification, not cleaned or audited broadly.

New-worktree creation repeated the known Git LFS warning for `dataset/v1.1.0/scientific/campaign/consolidated.json`. Its 37,252,923 raw bytes equal the HEAD blob, SHA-256 `73adf7d97f06985ec8f8e1c2f794fd43178433eb198e1c00705e817f4bde9c26`. It was not edited or staged. Git may continue to display this pre-existing filter discrepancy as modified; it is not a task change.

[Preservation inventory](evidence/preserved-files.json) verifies **29 tracked files** under `scripts/mgpu02`, `scripts/mgpu05`, `scripts/mgpu06` and `docs/study-protocol/lssp-protocol01` byte-for-byte against the baseline. Frozen thresholds, policies, workloads, manifests, protocol decisions and the approved first-pair configuration are unchanged. The new branch is a review candidate, not a replacement execution commit for MGPU06.

The execution authority is the actual installed Wulver vLLM 0.27.1 code, with version/source checks, not a simulator policy bearing a similar name. Four relevant files (scheduler, KV manager, request and scheduler configuration) were freshly hashed locally, on Wulver and from upstream v0.27.1; all match. See [source identity](evidence/source-identity.json). Simulator policy references target other versions, including vLLM v0.4.2 for chunked prefill; they cannot establish modern-engine fidelity.

## Verified baseline status

- `docs/mgpu06/VALIDATION.md`, PR #3 and preserved `artifacts/mgpu06/cache-isolation-20261021T2325Z/REPORT.json` on Wulver agree: **no genuine MGPU06 submission, job ID null, zero MGPU05/MGPU06 GPU-hours consumed or committed** at the recorded 22:44 UTC gate. Its scheduling simulation was not a submitted job. This review did not make another scheduling probe.
- The earlier **283 passes = 250 local + 33 focused Wulver passes**, with overlap; it is not a 283-distinct-test suite or a full Wulver regression. Raw local mirrors retain `local-tests-final.log` and `wulver/focused-tests.log` under the original checkout's `artifacts/mgpu06/cache-isolation/`.
- MGPU03 supplies the previously accepted bounded physical engineering baseline. **MGPU05's new instrumentation has CPU validation, not physical validation.** The first-pair physical gate remains open. No preliminary performance outcome was used here.
- The old smoke/warmup is 128 tokens. Approved MGPU06 Block 0 instead has 16 scored requests with prompt lengths repeating **1/256/64/128** and output limits **256/128/256/64**, plus the common 128-input/4-output warmup. Its payload SHA remains `c3d16b156d61e918c1b89725c8ca8855489994b9f64f4164df558fa0a5bd1ca5`. Calling the entire prospective pair a 128-token workload would be inaccurate.

## Findings and severity

Severity is relative to the claim at risk, not evidence that the accepted bounded MGPU03 smoke failed.

| Concern | Verified behavior / discrepancy | Severity and disposition |
|---|---|---|
| Partial prefill in serving | Chunking is enabled, but `WholePrefillChecks` rejects prompt >256, continuing partial state, partial token plans and mismatched completions. It does not implement paused-prefill SLAI. | **Blocking for general serving claims**, intentional supported-domain limit. No extension made. |
| Native progress vs execution | Native computed-token counters advance at scheduling. Nonfinal prefill chunks can return zero samples; final prefill can return the first generated token. The adapter's one-sample-per-scheduled-request invariant is correct only inside its whole-prefill domain. | **High if extended by simply raising the cap.** CPU native state tables added; GPU completion and timing still require physical validation. |
| Long prompts | All 40 Azure and 40 Bailian historical windows have source-reported medians >256. Context is also capped at 512 including output. | **Blocking for realistic-trace coverage.** No truncation, filtering, new sampling or frozen-field change. |
| Native KV pressure | Actual block allocator can refuse waiting admission or preempt running requests. Full-input fit is a feasibility check, not eager allocation of every input block, and does not guarantee future decode capacity. | **Blocking for general KV claims.** Existing checked path rejects mismatches and preemption; tests distinguish native mechanics from support. |
| Simulator execution/KV | First sample requires a later step than prefill completion; recompute resets generated-token count and first-token time; shared GPU execution does not enforce a native decode allocation boundary. | **High for native-equivalence/ranking transfer claims.** Reproduced in CPU unit fixtures; historical simulator behavior unchanged. |
| Simulator policy/admission coupling | Shadow policy progress and block tables are separate from shared execution. A policy's per-request token choices are not carried as an exact token plan in `Action`; service-model flags, chunk caps and admission rejection can diverge from shadow assumptions. | **High for broad fidelity claims.** Requires versioned execution/observation contract, not a small historical patch. |
| Engine identity reuse | A different workload ID can reuse an engine ID. While active, metadata is overwritten before native duplicate handling raises; after completion native accepts it while the adapter's admitted-ID history persists. | **High latent evidence-integrity defect. Fixed** by rejecting engine-ID reuse before mutation, including after completion. No collision was shown in the approved fixture. |
| Invalid KV telemetry | NaN/out-of-range values could silently select an SLAI memory-offset branch; `None` raised after batch counters changed. | **Medium latent fail-closed defect. Fixed** by validating a finite [0,1] fraction before changing batch history/LST. Invalid values were injected in CPU tests, not observed on the GPU. |

### A. Partial-prefill and policy semantics

For the checked path, at most R running decodes and N−R newly admitted prefills need `R + (N−R)P <= NP` tokens. With N=16, P=256, B=4096, no speculation/prefix reuse, synchronous single-batch execution and zero long-prefill threshold, this is a sufficient **token-budget** bound. SLAI-held decodes still occupy active/KV capacity. The proof is not a KV-memory guarantee and does not cover long prompts.

The pinned native scheduler schedules running requests before waiting requests, clipping work by remaining token budget, threshold, context and allocation conditions. A running partial prefill is still a running request; the implementation should not be described as an unconditional global sort of every decode ahead of every partial prefill. [Native source](https://github.com/vllm-project/vllm/blob/v0.27.1/vllm/v1/core/sched/scheduler.py#L439) governs exact behavior; the [optimization guide](https://docs.vllm.ai/en/v0.27.1/configuration/optimization/#chunked-prefill) provides general tuning guidance.

New literal CPU reference tables check a 300-token prompt with B128 as 128/128/44 input tokens followed by one decode token; synthetic sample lists are empty/empty/[42]/[43]. A resident decode consumes one token and a newly admitted 300-token prompt receives 127/127/46. These tests use the **unmodified native scheduler**, not relaxed checked-SLAI guards, and never run a model.

SLAI's pinned reference has critical decodes, paused prefills, new admissions and residual decodes, with its own memory-victim decisions. Extending only `MAX_PROMPT_TOKENS` would not implement those mechanisms. Progress must be separated into scheduled, executed and sampled state; first LST must follow the final successful prefill; preemption must retain output-prefix identity and account for recomputation. See [pinned SLAI source](https://github.com/agrimUT/SLAI/blob/5098a7aba05e3edbcfa3a509d6cc9cd248fc4380/sarathi/core/scheduler/slai_scheduler.py). The current core's measured monotonic callback duration, class TBTs, stable ordinal ties and bounded holds are disclosed adaptations, not a proof of every original mechanism.

### B. Recorded workload coverage

Recomputed only from the existing hashed window-index descriptors:

| Source | Historical windows | Window median range (source tokens) | Medians >128 | Medians >256 |
|---|---:|---:|---:|---:|
| Azure | 40 | 628.5–1595 | 40 | 40 |
| Bailian | 40 | 343.5–1150 | 40 | 40 |
| BurstGPT | 40 | 140.5–620.5 | 40 | 9 |

[Coverage evidence](evidence/workload-coverage.json) records the input hash. These are source-reported window quantiles, not independently retokenized text or exact per-request exclusion fractions. They establish substantial missing length coverage, not a newly approved workload distribution. Short synthetic fixtures deliberately avoid multi-iteration prefills, large-context occupancy, admission head-of-line blocking and recomputation. They cannot validate portability for these mechanisms. The protocol's future model/context selection, length-unit checks, immutable token manifests and exclusions remain unresolved as originally recorded.

### C. KV and simulator distinctions

`KVCacheManager.allocate_slots` checks block availability and a configured admission watermark, then allocates blocks needed for the scheduled prefix. `scheduler_reserve_full_isl=True` first checks that the full **current input sequence** fits; it does not reserve a maximum future output length. Native CPU tests show 17 total blocks (one null block) admit a 256-token prompt with B128, leaving eight free blocks after the first chunk and zero after the second. Nine total blocks cannot admit that prompt even though its first chunk alone fits. A separate 128-token fixture fills eight usable blocks: requesting token 129 triggers recomputation, frees blocks, resets computed progress, and **retains its sampled output prefix**. See [KV implementation](https://github.com/vllm-project/vllm/blob/v0.27.1/vllm/v1/core/kv_cache_manager.py#L344).

By contrast, `simulator/constraints.py` counts full candidate prompts against current token footprints; `InternalRequest.kv_tokens` grows with simulated prefill/output progress. Policy-specific shadow managers reserve full prompts and implement their own victims; shared `GPUState` is not the native allocator. A unit fixture with capacity 16 can progress from 16 to 17 KV tokens without a policy intervention. This proves a shared-layer limitation, not that every historical policy run overflowed. `GPUState.evict(..., preserve_progress=False)` also discards generated progress and TTFT history; native recompute retains generated tokens for replay. Correcting these differences requires an explicit revised simulator contract and prospective validation, preserving historical outputs and labels.

No GPU KV-capacity measurement, fragmentation calibration, OOM test or communication measurement was performed. The tiny CPU KV configuration is a deterministic allocation fixture, not a hardware memory model.

### D. Admission and identity

Native control uses its FCFS waiting queue. Checked SLAI encodes `(class TBT tier, prompt length, ordinal)` for priority admission, then executes its critical/prefill/noncritical plan through native scheduling and checks the resulting token map. Absolute evaluation deadlines are not SLAI LSTs or EDF admission keys. The new one-slot fixture explicitly checks FIFO vs class-priority admission despite opposing evaluation deadlines.

Active-sequence admission is separate from client dispatch, scheduler receipt, first scheduling and completion. Held requests retain slots. Waiting capacity under overload is not itself an error; unexpectedly refused native KV admission invalidates a checked run. Unsupported streaming/resume, distributed, partial-prefill and KV-preemption cases remain rejected. Server callbacks and client stream-chunk times are still not GPU token-emission timestamps.

The only production-code edits are the two rejection guards above. Valid unique-ID streams and finite KV observations follow the same decisions. The approved MGPU06 manifest and launcher are unchanged, and the original execution checkout remains at its approved baseline.

## Validation and reproducibility

Commands ran directly through Codex in the isolated worktree with:

```bash
export CUDA_VISIBLE_DEVICES='' HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1
# Before the repair, on baseline production code plus the new tests:
python -B -m pytest -q -p no:cacheprovider tests/mgpu02/test_fidelity_boundaries.py
# After the repair:
python -B -m pytest -q -p no:cacheprovider tests/mgpu00 tests/mgpu02 tests/mgpu05 tests/mgpu06
# Additional historical-simulator characterization and the original metric suite:
python -B -m pytest -q -p no:cacheprovider tests/mgpu02/test_simulator_limits.py tests/test_anwg_metric.py
bash -n scripts/mgpu02/smoke.sbatch scripts/mgpu05/repeatability.sbatch
git diff --check -- src tests docs/fidelity-review-20261021
```

- Before repair: **12 failed /6 passed**, reproducing all six engine-ID and six KV-observation defects. [Failure evidence](evidence/before-repair.txt). Its tracked copy strips trailing whitespace only; the unchanged raw output remains locally at `artifacts/fidelity-review-20261021/before-repair.raw.txt`, with its hash in the validation summary.
- After repair: **260 passed /0 failed** in the MGPU suite; then **11 passed /0 failed** in the nonoverlapping additional suite. **271 distinct final passing tests**, including 21 additions to the previous 250 local suite. [Regression](evidence/cpu-regression.txt), [additional checks](evidence/cpu-additional.txt).
- Each invocation reports 14 pre-existing Torch deprecation warnings. Syntax and whitespace checks pass. The entire historical repository suite was not run.
- Local environment: Python 3.12.3, vLLM 0.27.1, Torch 2.13.0+cu130, Transformers 5.8.1, tokenizers 0.22.2. Wulver remains Python 3.12.14, Torch 2.13.0, Transformers 5.16.1, tokenizers 0.23.1 per its retained preflight. The four native source files match, but this is **not a fresh Wulver test run or full dependency-equivalence claim**.
- All native runner replies and times in these unit tests are synthetic. No physical TTFT, TPOT, goodput, content quality or ranking was measured. Static/source inspection and CPU tests cannot establish CUDA execution, instrumentation overhead or physically correct long-context behavior.

## Decisions, ranking implications and next gate

**Verified:** the bounded checked path prevents accidental acceptance of general chunking/KV pressure. The two latent evidence-input defects are reproduced and repaired. Historical source lengths substantially exceed its domain. Native and simulated progress/memory semantics differ.

**Engineering assumptions:** source-identical CPU control flow is useful evidence for native decisions, but runtime completion still needs a physical gate. Shadow-state agreement requires assumptions about service-model settings; it is not guaranteed by a policy name. No measured ranking consequence follows from this investigation.

**Unresolved scientific questions:** longer prefills change compute contention, KV growth and admission; these can change relative policy behavior across deployments, but neither a reversal nor its direction has been shown. Restarting generated progress in a simulator can alter TTFT/work accounting under pressure; there is no correction factor established for historical results.

Author review is needed before: (1) adopting a new partial-prefill/SLAI state contract and faithful victim/recompute semantics; (2) choosing context/model/output limits and explicit trace eligibility rules from outcome-blind coverage; (3) deciding how to version simulator semantics and separate old evidence; (4) approving physical long-prompt/KV fixtures and any replacement execution commit. None is silently resolved by this patch.

| Next-stage gate | Verdict |
|---|---|
| Review these two guards and CPU characterization | **GO for review** |
| Run previously approved MGPU06 first pair during this task | **NO-GO; explicitly not authorized here** |
| Claim new instrumentation physically validated | **NO-GO; first-pair review outstanding** |
| Realistic long-prompt / partial-prefill / pressure serving | **NO-GO; semantic extension and CPU/physical conformance required** |
| Four-policy / L40 / TP2 / DP2 / ranking-transfer study | **NO-GO; existing fidelity and protocol gates remain** |

Recommended next action: review this draft patch and approve a separate, versioned partial-prefill/KV semantic specification, using the native tables as conformance anchors and independently specifying SLAI paused-prefill/victim/LST decisions. Preserve MGPU06's existing first-pair gate; it can validate bounded instrumentation later under separate authorization and available resources, but cannot resolve realistic long-prompt or KV-pressure fidelity. Do not start a larger campaign.
