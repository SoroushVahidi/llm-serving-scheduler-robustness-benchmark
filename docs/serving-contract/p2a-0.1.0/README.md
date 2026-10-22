# P2A / 0.1.0 — native CPU acceptance boundary

**Implemented CPU conformance; physical status NOT VERIFIED. General SLAI native-plan enforcement: NO-GO.**

Authority is the author's P2A request. Base PR #6 was verified at `810b987dd873215d1a872eca83fd5c50770ca434`, with #5 `ee1868618db9afc89160e1d0daf92b54829a80bc`, #4 `efc5243898d18bbb62ccb51dcf66a0767827dac6`, and #3 `b14992716c20b36d26e6f28e60b2c8e0b8b09a07` in its ancestry. New work is additive on `research/lssp-v2-p2a-native-boundary`. No prior source, protocol, experiment manifest or observation is superseded.

The supported path is explicit proposal → **actual pinned native FCFS `Scheduler.schedule()`** → strict comparison → P1 admission/plans → separately supplied **synthetic CPU ACK plus actual `ModelRunnerOutput` type** → native `update_from_output()` → verified P1 ACKs. Planning never advances P1 acknowledged progress. This runs real CPU scheduling/KV objects, not a replacement scheduler or model runner. It does not import/instantiate/execute the GPU model runner.

The source does not expose an arbitrary per-request token-plan argument. For example, proposing `[0,1)` for a two-token prompt with spare budget yields native `[0,2)`; proposing just B when A is first yields A and possibly B. The adapter records that mismatch, commits no P1 work and stops. **This is detection, not enforcement.** Since native scheduling already mutates block ownership and optimistic counters, a refused instance must be abandoned. There is no rollback, implicit retry or runner submission. The next general SLAI integration must stop at this boundary until an enforceable source-backed interface is reviewed.

The CPU ACK interface deliberately cannot claim physical execution. It requires `provenance="synthetic_cpu"`, exact batch/step/epoch/spans and validity mask, successful completion and quiescence. Native `ModelRunnerOutput` alone contains none of the necessary span/epoch/quiescence attestations. Failed, incomplete or nonquiescent batches poison the boundary and preserve the prior accepted ledger. They do not fabricate terminal success or classify unacknowledged work as unexecuted.

Read:

- [API and evidence contract](API.md)
- [Native/source interface register](SOURCE_REGISTER.md)
- [S02/S04 recommendations and retained author decisions](DECISIONS.md)
- [Conformance and unresolved cases](CONFORMANCE.md)
- [Validation, commands and preservation](VALIDATION.md)

Next-stage verdict: **GO for author review of this CPU verification boundary; NO-GO for general partial-prefill SLAI serving, pressure handling, physical ACK fidelity, TP2/DP2, or ranking experiments.** P2B needs an explicit S02 choice, a reviewed way to constrain native scheduling before runner submission, and an execution ACK design. S04 pressure semantics, S07 and S08 remain unresolved. No resource authorization is added; MGPU06's approved configuration and execution commit are unchanged.
