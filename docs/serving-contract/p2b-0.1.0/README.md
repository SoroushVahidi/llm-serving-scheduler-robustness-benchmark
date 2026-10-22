# P2B / 0.1.0 — enforceable CPU scheduling control

**CPU-only implementation. Physical execution NOT VERIFIED. No serving activation.**

Base draft PR #7 was verified at `df4b13d269d64a949a9dd910b6a65e61718dbc29`; ancestry #6 `810b987dd873215d1a872eca83fd5c50770ca434`, #5 `ee1868618db9afc89160e1d0daf92b54829a80bc`, #4 `efc5243898d18bbb62ccb51dcf66a0767827dac6`, #3 `b14992716c20b36d26e6f28e60b2c8e0b8b09a07`. All remain open drafts. This additive worktree/branch is `research/lssp-v2-p2b-control`. The authoritative documents for measurement/cache limits, admission integrity, prospective semantics, P1 and P2A were reviewed. Prior approvals, evidence and MGPU06 execution authority are unchanged.

P2A correctly refused plans that native vLLM enlarged, supplemented or reordered. P2B installs an **instance-local, source-pinned constrained copy of native `Scheduler.schedule()`**. Six guarded insertion sites (nine added lines in the generated native-method diff) restrict selected requests and token counts before their allocations and stop on allocation refusal before native victim selection. The original allocator, block manager, request classes, output construction and runner-output processing execute unchanged. The global class and installed package are not modified. This is a small explicit local patch, **not an upstream extension API or a native-equivalence claim**.

The wrapper validates complete plans before changing queues/current step/KV/progress. It applies selected order, runs the constrained native method, checks exact returned work, and restores canonical queue ordering after success. It never restores KV/progress after failure. Unexpected failures can leave allocations or optimistic state changed; the whole instance stops before any runner submission. No rollback or retry is claimed.

**Representability limit:** native code has a resident phase followed by a waiting-admission phase. A plan placing selected waiting work before selected resident work is rejected **before mutation**. There is no hidden reordering. The implemented S02 partial profile avoids that unsupported interleaving: paused prefill then new prefill, holding decodes whenever prefill is selected; otherwise ordinal decode service. This is not the complete critical/prefill/residual SLAI algorithm.

Profiles are distinct:

- Prior **native FCFS** remains unchanged in P2A; its source-based counterexamples still pass unchanged.
- `lssp-native-span-control/0.1.0`: exact explicit external plans within the stated domain; no implicit policy priority.
- `lssp-slai-s02-prefill-control/0.1.0`: delegated S02 admission/paused-prefill subset, explicitly incomplete SLAI.

Review [approval/amendment](APPROVAL.md), [control and attestation contract](CONTRACT.md), [native-source deviations](SOURCE_DEVIATIONS.md), [conformance](CONFORMANCE.md), and [validation/evidence](VALIDATION.md).

**Next phase:** GO for author review and a separately scoped CPU execution-attestation bridge design. NO-GO for physical serving, complete numerical-LST SLAI, general pressure/preemption/recomputation, cross-phase interleaving, distributed execution or ranking experiments. No new resource authorization is supplied. S04 general pressure, S05 numerical feedback, S07 model/trace choices and S08 remain gates.
