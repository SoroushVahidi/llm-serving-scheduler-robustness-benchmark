# Fidelity, coverage and exclusion gates

**DRAFT.** PASS means evidence for a specified case/contract; FAIL means an observed violation; NOT VERIFIED means no adequate evidence. None can be inferred from a process returning zero alone.

## Present state

| Behavior | Status at protocol preparation | Boundary |
|---|---|---|
| MGPU02 bounded scheduler/reference logic | 151 local tests reported by MGPU02; not rerun here | CPU/synthetic-runner evidence only |
| Whole-prefill sufficient budget bound | Supported analytically in declared contract | N=16, P=256, B=4096; not a KV-memory proof |
| General partial prefill, KV preemption, TP/DP/PP/context parallelism | Explicitly rejected by MGPU02 | New contracts and independent validation required |
| Full-A100 native and checked-SLAI physical acceptance | NOT VERIFIED by this protocol review | MGPU03 accounting completed; serving evidence is reserved for separate review |
| L40, main-size model, additional policies, distributed behavior | NOT VERIFIED | No inference from A100 smoke or local tests |
| Historical 240 physical runs | Historical 10 GB MIG evidence with replay/metadata limitations | Not faithful full-GPU policy-ranking validation |

The MGPU02 bound is R+(N−R)P≤NP=4096 for R active decodes and at most N−R newly admitted prompts. Held decodes occupy active capacity. It prevents budget-driven splitting only when every effective prompt (including template/special tokens) is ≤256, one token per decode is scheduled, no speculative/prefix/other work changes the accounting, and native behavior matches the contract. It neither guarantees allocation success nor supports long-context behavior.

## Quantified mismatch with existing workloads

A read-only computation on the frozen 120-window descriptor manifest produced:

| Source | Windows | Windows with median prompt >256 | Windows with p99 prompt >256 |
|---|---:|---:|---:|
| Azure 2024 | 40 | 40 | 40 |
| Bailian/Qwen | 40 | 40 | 40 |
| BurstGPT | 40 | 9 | 38 |

Input SHA-256: `d78ec1087fedae02174ca093a9860c70468be336ccb1d7e6de756c81ba331e53`; path and reproducing computation are in [review inventory](evidence/review_inventory.json) and [validator](validate_protocol.py). These are **source-reported length descriptors**, not newly measured tokenized prompts or exact excluded-request fractions. They show that a 256-token-only study would omit important prefill/contention regimes. Quantiles alone cannot give exact retained coverage. The 16-active cap also changes queueing, admission and attainable batching; it does not cap the number of offered/waiting arrivals and must never be implemented as a client concurrency limit.

Before main-window freeze, audit raw request coverage by source, class, input/output length, prompt+output context, burstiness and temporal stratum. Publish counts and fractions outside P, context, output and active/KV support, both request-weighted and token-work-weighted. Separate raw-token conventions from actual target-tokenizer length. Do not trim, rescale lengths, discard long windows or reduce the trace to ≤16 concurrent requests without labeling a new restricted scientific question and obtaining author approval. Main-study GO requires a credible declared coverage domain and validated semantics for its long-prefill/decode-heavy/overload cases. “Common support” cannot silently exclude the mechanism of interest.

## Required gates per policy × deployment

| Gate | Mandatory evidence / PASS | FAIL or NOT VERIFIED response |
|---|---|---|
| F0 identity | Clean pinned execution checkout; model/tokenizer/config/workload/software hashes; full GPU identity and effective flags | No timed comparison; preserve diagnostics |
| F1 independent specification | State machine, observable inputs, tie rules, budgets, deadline clock, admission, partial-progress and KV victim rules written independently of adapter output | No policy identity claim |
| F2 differential conformance | Hand-computed and separately coded reference cases for each class, equal arrivals/deadlines, long/short prompts, decode contention, empty/overload queues and boundary budgets | Stop affected contract at first mismatch; no weakening assertions |
| F3 real execution | Intended request/token decisions equal native scheduling and actual runner progress, including finish/free/hold transitions | Log plan/native/runner separately; a claimed decision alone is insufficient |
| F4 metadata/time | Request IDs/classes/SLOs survive ingress/router/engine; arrival/send/dispatch/first-token/completion events valid and clock-calibrated | No deadline or class-specific inference |
| F5 partial/KV | Correct paused-prefill offsets and first-token transitions; conservation of computed tokens/blocks; documented admission/preemption/recompute rules exercised | Explicit rejection; no silent fallback to native victims or partial behavior |
| F6 distributed | TP rank agreement, collective/error synchronization, per-rank progress; DP exactly-once routing/receipt/completion and per-replica accounting; replicated class behavior | TP2/DP2 NO-GO; two successful processes are not distributed validation |
| F7 replay/errors | Open-loop offered trace preserved; no omitted/duplicate IDs, hidden concurrency cap or tokenization in timed dispatch; errors/timeouts/incomplete responses classified | Reject harness-invalid comparison; retain all evidence |
| F8 instrumentation | Profile/event overhead measured against paired unprofiled runs; proposed ≤2% primary-goodput perturbation or separate profiled stratum | Do not use perturbed profiles as primary performance runs |
| F9 evidence | Durable per-run manifests, checksums, logs, raw events, analysis version; bounded startup/drain, exit propagation and cleanup | Incomplete reproducibility is NOT VERIFIED |

F2/F3 acceptance requires zero decision mismatches in the mandatory corpus. Include deliberate bad metadata, missing class, malformed deadlines, over-budget prompts, output/context overflow, wrong software hashes, unsupported distributed flags, native allocation refusal, preemption requests and crash/timeout injection. Unsupported inputs must fail explicitly; such deliberate negative cases are successful rejection tests, not successful inference.

SLAI requires special care: its internal LST and moving batch-time estimate are not an absolute request E2E deadline. MGPU02 uses completed-batch wall time including host overhead and a bounded native adapter; those semantics must be described and compared to the pinned external implementation before broadening claims. A native VTC/EDF/SPF label is insufficient without a specification. The simulator registry's `faithful` labels do not confer real-runtime fidelity.

## Exclusion ledger and changed contracts

Every planned execution and request has a stable ID and status. Pre-input invalidity, unsupported semantic domain, infrastructure interruption, policy refusal, valid overload, deadline miss and conformance failure are different categories. Report all counts by source/policy/deployment. Exclusions may be made only by the frozen rule; publish a flow from candidate rows to analyzed windows and requests.

If a required behavior cannot be implemented faithfully, choose between (a) additional implementation under a new versioned contract, (b) an explicitly narrower approved question, or (c) removing an entire comparison before outcome collection with an amendment. Do not select a narrow domain because its rankings look favorable. Old and new contracts are never pooled as if their mechanisms were identical.
