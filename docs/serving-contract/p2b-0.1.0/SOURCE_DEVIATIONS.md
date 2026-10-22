# Native-source decision and deviation register

Pinned vLLM **v0.27.1**, release commit `6e448d0ea9bf3d88d898b65449ca6dc2aec170ac`; pinned SLAI `5098a7aba05e3edbcfa3a509d6cc9cd248fc4380`. [Source hashes](evidence/source-hashes.json) retain installed identity and exact upstream URLs. Scheduler and scheduler configuration were compared again byte-for-byte with upstream; the other selected installed files match the preserved P2A pins. This is a selected source closure, not a hermetic binary/runtime attestation.

The reviewed [`SchedulerConfig.scheduler_cls/get_scheduler_cls`](https://github.com/vllm-project/vllm/blob/v0.27.1/vllm/config/scheduler.py) selects an entire scheduler class; it exposes no exact per-request span hook. [`Scheduler.schedule`](https://github.com/vllm-project/vllm/blob/v0.27.1/vllm/v1/core/sched/scheduler.py#L439) computes running work, allocates KV, then traverses waiting requests. `num_computed_tokens` advances optimistically after scheduling. Merely adjusting a returned plan is too late, and merely reducing the total budget cannot prevent extra requests or enforce individual spans. P2A's exact rejection guards are preserved.

P2B chooses an instance-local **constrained copy of the pinned method**, built from verified source. Six exact insertion anchors must each match once; the full generated method must match the frozen patch digest. It is compiled in a copy of the native method namespace, bound only to the owned native Scheduler object. No installed source, global class, package import or default serving entry point is replaced. The original native code carries Apache-2.0 attribution in the upstream source; the stored patch identifies that source and makes all changes explicit.

| Native location | P2B change | Purpose / evidence |
|---|---|---|
| Running request fetch | Skip IDs absent from approved spans | Held residents retain slots and KV, receive zero work; positive holds and corrupted-extra-work tests |
| Before running `allocate_slots` | Replace computed upper-bound count with checked exact count | Cannot enlarge a requested chunk; start must still match current native progress |
| Running allocation-refusal branch | Raise before victim selection/removal | No preemption or refund/victim logic runs; refusal test retains output prefix and stops |
| Waiting queue head | Stop at any ID absent from approved spans | No extra admission when budget remains; selected requests explicitly ordered ahead of deferrals |
| Before waiting `allocate_slots` | Apply same exact span-count check | Partial initial prefill allowed under unchanged full-input-fit gate |
| Waiting allocation-refusal branch | Raise immediately | Prevent continuing into alternate work or treating partial acceptance as full success |

The concrete [scheduler.patch](evidence/scheduler.patch) has **nine added lines at six sites**; native allocator/request/wire construction and `update_from_output` are unchanged. The wrapper adds read-only validation, explicit queue ordering, canonical queue restoration after success, exact return verification and stop-on-failure. Those are additional declared control semantics outside the nine-line native diff.

**Frozen hook ID:** `vllm-0.27.1-exact-span-hook/0.1.0`.
**Patched method SHA-256:** `062195e45fa2fa4d16d68081a26ebf3dcc55fad1007e927e009a14b1dbd455e4`.
[Patch identity](evidence/patch-identity.json) and independent reference pin agree. Changing upstream bytes, insertion anchors or resulting method requires a new reviewed version. No fallback to an unpatched scheduler is allowed.

## Preserved interfaces and known limits

- `KVCacheManager.allocate_slots/get_block_ids`, full-attention block managers and native null/free/owned accounting remain actual native code. P2A's all-live lifetime-fit bound remains a conservative no-pressure domain check, not virtual reservation or a new workload admission criterion.
- Native `SchedulerOutput` new/cached offsets and token counts are unmodified. Actual CPU Scheduler and KV objects produce them; a simulator does not fabricate native acceptance.
- Native V2 runner `sort_batch_req_ids` may permute rows. The unchanged P2A bijective ID/index checks allow layout permutation; canonical attested spans bind identity/positions. No GPU runner or kernel executes here.
- Native `update_from_output` remains responsible for output prefix, cap completion, in-flight accounting and release. P2B retains P1 atomic ledger application and P2A checks; those do **not** make native scheduling atomic.
- Exact external plans are representable only when selected resident work precedes selected new admissions. Waiting-before-resident interleaving is an explicit pre-mutation refusal. Supporting full SLAI's waiting-before-residual-decode phase in one batch needs another reviewed change; this patch does not approximate it by hidden reordering.
- Unexpected late refusal can leave earlier allocations in place. A fault snapshot and permanently stopped instance are retained. No rollback, victim, retry, recomputation or physical quiescence is inferred.

## SLAI adaptation and semantic separation

[`SLAIScheduler._schedule/_post_batch_processing`](https://github.com/agrimUT/SLAI/blob/5098a7aba05e3edbcfa3a509d6cc9cd248fc4380/sarathi/core/scheduler/slai_scheduler.py) supplies the source motivation for binary strict admission, shortest prompt and persistent paused FIFO. The new mapping, immutable original length, explicit ordinal tie and native final-prefill sampling are named adaptations. The partial P2B policy intentionally omits critical/residual numerical LST, memory-dependent feedback and source victims. It holds decodes during selected prefill work; that is **not literal full SLAI equivalence**. Source-specific measured-batch constants are neither copied nor invented.

No historical simulator, bounded checked adapter, MGPU03 observation, frozen MGPU05/MGPU06 execution or preregistration is relabeled. Comparison of this new partial profile with full source SLAI or physical native FCFS requires separately specified scientific evidence.
