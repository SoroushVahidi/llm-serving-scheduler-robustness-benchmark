# Experimental matrix and controls

**DRAFT.** Recommendations here are provisional until [author decisions](AUTHOR_DECISIONS.md) and the preregistration freeze are complete. No cells are authorized for execution.

## Deployment factor

| ID | Hardware | Organization | Allocated GPUs | Primary routing |
|---|---|---|---:|---|
| a100_1 | Full A100, exact SKU/memory pinned | TP1, one engine | 1 | One ingress queue |
| a100_tp2 | Same A100 SKU | TP2, one engine | 2 | One ingress queue |
| a100_dp2 | Same A100 SKU | Two TP1 engines / replicas | 2 | Deterministic round-robin by original request ordinal |
| l40_1 | Full L40, not L40S | TP1, one engine | 1 | One ingress queue |
| l40_tp2 | Same L40 SKU | TP2, one engine | 2 | One ingress queue |
| l40_dp2 | Same L40 SKU | Two TP1 engines / replicas | 2 | Same deterministic round-robin rule |

DP2 means replicated dense-model serving, not expert parallelism, sequence parallelism or prefill/decode disaggregation. Specify whether the implementation uses an external router or native DP; the recommendation is two explicit TP1 replicas with a logged external router. Both replicas use the same policy and SLO classes; do not silently bypass MGPU02's distributed rejection by labeling replicas independent. The complete routed service requires a new fidelity gate.

Primary directed transfer edges: a100_1→a100_tp2, a100_1→a100_dp2, l40_1→l40_tp2, l40_1→l40_dp2, a100_1→l40_1, a100_tp2→l40_tp2, a100_dp2→l40_dp2. Policy reversals are symmetric facts; transfer-regret decisions use these directions. Reverse-direction recommendations are secondary.

A100 TP4/DP4, PP, multi-node, dynamic parallelism and disaggregation are extensions. They are not implicitly represented by TP2/DP2.

## Four distinct mechanism candidates

| Candidate ID | Independently specified mechanism | Current physical status / required work |
|---|---|---|
| native_fcfs | Pinned vLLM native waiting-queue FCFS plus its actual decode/chunk budgeting | MGPU02 bounded adapter exists; MGPU03 acceptance review pending |
| prompt_spf | Shortest known prompt first at admission; ordinal ties; same common decode/KV rules as baseline; no future output oracle | New mechanism specification and real adapter required; classical policy, not a claimed external reproduction |
| token_fair | Pinned VTC-style tenant token-service accounting including idle/backlogged transitions | New reference and adapter required; do not relabel existing simulator weighted fair share as VTC |
| checked_slai | Class-aware prefill ordering and measured-time critical decode selection/holding | Only bounded whole-prefill contract exists; general partial-prefill/KV and TP/DP semantics are blockers |

All four share model, kernels, cache mode, scheduling API and deployment controls. Each pair must have an independently written adversarial fixture yielding different intended choices; performance separation is not a selection gate. A policy may remain tied in measured performance. If VTC or full SLAI cannot be faithfully implemented, do not silently substitute a convenient policy: propose an explicit panel amendment before performance collection. Sarathi is a possible replacement/extension only after distinguishing its actual mechanism from native modern chunking. DistServe and Shift Parallelism require a separate whole-system stratum.

Use online-observable prompt length, class and accumulated service only. Actual future output length may determine controlled replay length, but is withheld from scheduler priority decisions. Define tenant overlays and their provenance; the three sources do not provide a uniform native tenant identity. Recommended tenant overlay: a fixed, balanced eight-tenant assignment by request-ID hash, independent of class/length, with a skewed-tenant sensitivity experiment. Report fairness as secondary, since request goodput is not VTC's complete objective.

## Model, tokenizer and generated work

Retain Qwen2.5-0.5B-Instruct only for engineering validation against the approved MGPU02 revision. For the main study, recommend one dense autoregressive 7–8B model, preferably the same Qwen2.5 family, with BF16 support on both accelerators, a tokenizer/configuration available at immutable revisions, a redistributable usage recipe, and validated TP2 head/weight partitioning. Qwen2.5-7B-Instruct is a **candidate**, not an approved checkpoint or a proven memory fit. Pin model revision, weight-shard/config/tokenizer/chat-template hashes and license before selecting windows. Require model weights plus measured peak activations and declared KV headroom to fit the smallest single-GPU deployment. No architecture-specific quantization or context reduction in the primary comparison.

Choose context and output limits from source-length coverage and memory feasibility, not from scheduler wins. Freeze exact numerical limits after that outcome-blind audit. Record special tokens/chat-template effects and prompt+output feasibility for every request. Reconstruct deterministic, exact-token-length synthetic prompts when source text is absent; verify lengths with the selected tokenizer before timed replay. This preserves a declared compute-shape trace, not the original language, answer quality or authentic prefix reuse. Prefix caching is disabled in the primary study; no semantic-quality conclusion is justified.

Use fixed output-token work (ignore EOS where supported and validated), common decoding settings and request seeds. Log actual generated counts and terminal reason. Separate any natural-EOS sensitivity study because hardware-dependent output changes can change work. Never shorten a prompt/output silently to make a request fit.

## Sources, selection and freeze

Use BurstGPT without-fails v2/file 2, Azure 2024 conversation, and Bailian/Qwen general trace B. Source hashes in [design_manifest.json](design_manifest.json) are inherited frozen identities from the repository, not newly acquired files. Raw source re-verification is a prelaunch gate. BurstGPT and Azure are distinct releases with related provider provenance, not independent providers. The without-fails source excludes original production failures; our injected/observed serving failures still count.

Preserve native timestamp order and correlated prompt/output lengths. Bailian `input_length`/`output_length` are read as length fields; its `hash_ids` are 16-token blocks. Do not multiply every length by 16 merely because the filename contains `blksz_16`. Reverify upstream units, timestamp resolution and cumulative-context semantics before replay. Existing adapters contain inherited/unverified provenance notes; registry acquisition claims alone do not settle them.

Select nonoverlapping contiguous temporal windows from raw rows, with explicit valid-row and raw-row coordinates, using only arrival/length/source metadata. Stratify across chronology and burstiness/length regimes, with quotas and seed frozen before outcomes. Default candidate windows contain 200 requests for historical comparability; use pilot boundary/warmup checks to decide whether longer contiguous windows are needed. Do not stitch unrelated rows or repeatedly replay a short window to manufacture independent observations. Exclude historical/pilot/development row ranges from confirmatory and held-out pools. If earlier overlap cannot be established, mark affected windows as development-only.

The final immutable window manifest must include source/version/SHA-256, raw and valid row ranges, source window hash, request-ID/token-ID/arrival/SLO/tenant/output-limit hashes, units, adapter revision, stratification probabilities, split role, seeds, tokenizer revision and generated-prompt hash. Keep malformed/missing records and eligibility counts in an exclusion ledger. Zero-output or non-generation records need an explicit eligibility rule and counts; do not convert them silently to one-token requests. Selection cannot depend on a policy result. New window hashes are **null/pending** in this draft; historical hashes are provenance only, not a frozen prospective sample.

Recommended split: separate engineering and calibration pools; chronological development pool for C3/C4; untouched later temporal blocks for C4 evaluation. Freeze split coordinates and counts after precision planning. Hold all versions of a window, repetitions, pressure views and deployments in the same split. Main C2 estimates can use all prespecified confirmatory windows; C4 development outcomes must be disclosed as training, never called held-out. Target hold-out size is determined by risk precision, not a convenient percentage.

## Two operating-pressure comparisons

1. **Equal relative pressure (primary):** use native_fcfs on separate calibration windows to estimate each deployment/source capacity λ* under a fixed service contract. Proposed capacity criterion is ≥90% SLO success with a stable queue/drain criterion; publish the fitted curve and interval. Freeze the largest tested rate meeting both with a conservative uncertainty rule. Apply ρ=0.60 and ρ=0.90 of that reference capacity to **every policy**, without policy-specific retuning. Use identical time scaling for a given source/deployment/region. Capacity must be bracketed: if the lowest rate already fails, extend the bracket within a predeclared calibration budget or declare NO-GO; do not call that point a knee.
2. **Equal arrival rate (key secondary):** use the two A100×1 reference rates for the same source on every deployment. This asks whether the same offered traffic can reuse its ranking. Overload on slower deployments is retained and reported. Deduplicate exact shared cells at A100×1. These are additional cells elsewhere, not free alternative analyses of the relative-pressure runs.

SLO thresholds remain identical across deployments and policies. Select absolute class-specific TTFT/TBT/E2E budgets from an author-approved application contract, or from an explicitly synthetic reference-service convention on separate calibration data. Do not rescale SLOs independently by hardware; that would hide a transfer failure. Freeze class mix (proposed equal thirds), class assignment seed, and one alternative overlay for sensitivity. Exact SLO values remain an author decision. SLAI's internal LST heuristic and the user-visible SLO evaluator are distinct quantities and must both be logged.

## Blocking, randomization and equivalence controls

Pair identical windows and metadata across policies and deployments. A repetition is a fresh timed replay, with reset queues/KV and an independently scheduled allocation/day block where feasible; repeated deterministic simulation is not replication. Use randomized complete policy blocks within window/deployment/pressure, counterbalance order over the whole design, and interleave hardware/deployment blocks over calendar time. Three repetitions are illustrative; they cannot individually balance all four policy orders. Freeze the actual permutation and allocation plan. Keep node/day/order identifiers for inference.

Use more than one physical node per architecture when feasible; a single node per architecture limits inference to those deployment bundles. Record GPU UUID/SKU/memory, MIG disabled, exclusive allocation, power/clock policy, thermal/throttle status, host CPU/RAM/NUMA, driver/CUDA/NCCL, engine source/package hashes, effective flags, collectives topology and network path. NVLink-capable A100 versus PCIe L40 is a hardware+interconnect contrast unless explicitly controlled. Pair TP2 and DP2 on comparable two-GPU pools.

Freeze per-engine sequence/token budgets and cache settings across policies. DP2 doubles replicas and thus aggregate admission capacity if per-engine limits are fixed; TP2 does not. Record both per-engine and aggregate limits and add a matched-aggregate-budget control before attributing a result specifically to routing/parallelism. Raw service goodput is primary; per-GPU goodput is secondary for unequal resource counts. Treat any deployment-specific tuning as a separate, budget-matched tuning stratum.

Start timing only after readiness and fixed warmup; flush warmup requests, reset scheduler service counters, and verify empty queues. Cache/compile state must be matched. Measure startup separately. For each window, use a fixed prelude if pilot checks show empty-start bias; prelude bytes and initial state are paired and excluded from the scored cohort. Duration/drain/warmup choices are frozen before the main study. Validate the load generator at the maximum offered rate without imposing a hidden client semaphore or closed-loop backpressure.
