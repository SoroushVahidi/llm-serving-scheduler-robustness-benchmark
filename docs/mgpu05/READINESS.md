# Readiness, research-protocol comparison and author decisions

## Separate gates

| Scope | MGPU05 verdict | Meaning and remaining gate |
|---|---|---|
| Measurement instrumentation | **GO for author review / first bounded physical validation** | CPU independent-validator, HTTP and actual scheduler-object tests; durable raw evidence, fail-closed offline checks. New physical timing/content-capture behavior is NOT VERIFIED |
| Bounded single-A100 engineering repeatability | **GO for staged preparation; first pair only eligible for separate authorization** | At most 24 executions /10 GPU-hours; exact target preflight and author approval first. Remaining 22 are **NO-GO until first-pair physical review passes**. No job was launched |
| Realistic workload experiments | **NO-GO** | P≤256 and N≤16 remain. All 40 Azure and all 40 Bailian median source-reported prompt lengths exceed P. No truncation or relabeling as realistic coverage |
| TP2/DP2 | **NO-GO** | Explicitly unsupported by existing adapter; no rank/routing/clock/collective validation |
| Main ranking-transfer study | **NO-GO** | Four mechanisms, realistic domains, L40/comparable deployment controls, overhead and held-out methodology still require work; no manuscript performance claim |

These are eligibility verdicts, not permission to submit. No physical test was performed in MGPU05, and no byte/numerical reproducibility or timing precision result is claimed. The existing MGPU03 engineering acceptance is preserved; MGPU05's new capture path adds observations and overhead requiring a new, bounded gate.

## Comparison with PR #2's draft protocol

Reference: `docs/study-protocol/lssp-protocol01/`, commit `f88f6fb97be1e012573b8136507104f8d513e67d`. The earlier draft's “MGPU03 NOT VERIFIED” text is its historical status at preparation, not an edit target here. The author's subsequent accepted MGPU03 audit supplies the bounded baseline for this task.

| Protocol contribution/gate | MGPU05 progress | Remaining work |
|---|---|---|
| C1 / F1–F4, F7, F9 | Two existing mechanisms retain their checks; raw request/API/engine identity, sample counts, independent text decoding, clock domains, error accounting, independent revalidation and seals added | Physically validate new capture, incomplete/error paths where required; audit LST/clock semantics for any expanded contract; no claim that semantically correct natural-language answers have been proved |
| Realistic prefill / F5 | Existing whole-prefill mathematical bound and fail-closed guards remain | Independently specify partial-progress state, prefill/decode budget competition, TTFT transitions and class/admission behavior; CPU differential and physical validation before expanding domain |
| KV behavior / F5 | Unexpected admission refusal, preemption, resumed/partial state still rejected | Explicit victim selection/recompute/block accounting, pressure telemetry, independent KV conservation and physical pressure fixtures; no inference from B4096 to adequate KV memory |
| Four-policy C1 | Only native FCFS and checked SLAI are physically established in old bounded path | Specify at least two genuinely distinct additional mechanisms; implement native-execution fidelity, metadata/clock tests and distinguishability fixtures for each. Simulator names do not count |
| C2 A100/L40 ×single/TP2/DP2 | Proposed repeatability is one full A100 80GB, one small model, equal offered paired streams | L40 memory fit, GPU/NUMA/PCI/NVLink/topology and power/clock controls, common software kernels/precision policy, equal-resource and equal-arrival/relative-pressure definitions, per-deployment fidelity; no cross-architecture equivalence inferred |
| TP2 | No broadened support | Rank-level decision/token agreement, collective synchronization/cost, error propagation, KV ownership and per-rank timestamps; reset and warmup equivalence |
| DP2 | No broadened support | Exactly-once ingress/routing/admission/completion, global vs replica policy definition, router queueing, replica load and clocks, failure handling; local deadline clocks cannot silently stand in for global SLOs |
| C3 mechanism explanation / F8 | Queueing, observed prefill/decode decisions, holds and callbacks become auditable | Independent instrumentation-overhead validation (draft proposes ≤2% primary-goodput perturbation or separate profiled stratum); real KV/communication/routing observations and prospective mechanism interventions. Logging may alter measured SLAI batch times |
| C4 held-out portability | No predictive rule fitted, no workloads selected by results | Freeze development/held-out split at independent window/deployment level; define practical transfer margins, feature availability, nested model fitting, uncertainty and recalibration criteria; held-out evaluation requires main-study evidence |
| Statistical design | Three paired engineering repeats with transparent imprecision and censoring | Pilot-informed window/repetition sizing, hierarchical uncertainty, multiple-comparison control, practical-equivalence margins; stable or inconclusive rankings must remain reportable |

## Fixed candidate decisions vs approval choices

**Implemented candidate invariants:** no >256-token prompts; B4096/N16/context512; no TP/DP/PP>1, partial prefills, KV preemption, prefix caching or speculative outputs; synthetic-only full-content capture; monotonic-domain checks; coalesced observations never become invented token times; malformed/incomplete evidence never becomes physical PASS; no retries/arrays/automatic continuation.

**Proposed for approval:** exact synthetic windows and spread/burst arrivals; seed and 12-block order; MGPU05 Stage 1 amendment; engineering SLO conventions; dispatch thresholds; identical warmup/fresh-server policy; 50-minute paired-allocation bound and initial 24-execution/10-hour ceiling; first-pair review gate; descriptive 10% variability/precision flags. The frozen main-study SLOs, trace windows, model selection and hypotheses are not replaced by these engineering choices.

**Outstanding author choices:** approve the bounded pilot and its amendment, or revise before outcomes; decide how much unobserved individual-token timing is acceptable for the engineering objective; commission a separate overhead experiment before any primary performance claim; choose and justify the long-prompt/KV semantic extension and additional policy implementations; approve main model/deployments and held-out split later. No author answer is inferred from elapsed time.

## Environment and limitations of validation

Local CPU tests ran with Python 3.12.3, vLLM 0.27.1, Torch 2.13.0+cu130, Transformers 5.8.1, Tokenizers 0.22.2, HTTPX 0.28.1 and NumPy 2.3.5. CUDA devices were hidden and no model forward pass ran. Target Wulver read-only inspection found Python 3.12.14, Torch 2.13.0, Transformers 5.16.1 and Tokenizers 0.23.1 (same vLLM/HTTPX/NumPy). `environment.json` pins the **target Wulver** versions; local CPU validation is explicitly not a full target-environment test run.

Read-only Wulver checks hashed the actual model/tokenizer/generation config and three new API dependencies, and exercised the Rust tokenizer for the pinned synthetic text. They agree with local/upstream expectations. The scheduler dependencies retain MGPU02's source pins. Target preflight must still verify the complete source/environment/model set on the reviewed checkout immediately before any allocation. No package upgrade, target checkout edit, server startup or GPU probe was performed during preparation.

Minimal next task: after author review, provision a clean dedicated MGPU05 Wulver checkout at the final tested commit; run CPU preflight; authorize **block 0 only** to physically audit the new capture. Do not automatically launch the other 22 executions. If the new measurement path fails, retain raw evidence and correct it before proposing one bounded retest.
