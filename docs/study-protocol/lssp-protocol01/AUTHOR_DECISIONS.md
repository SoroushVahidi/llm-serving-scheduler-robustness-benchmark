# Author decisions and unresolved blockers

**DRAFT for review.** “Fixed” below means constraints from the task or essential validity requirements, not author approval of this preregistration. “Provisional” means a concrete recommendation. “Unresolved” means execution/final registration is blocked pending a recorded choice or evidence.

## Fixed constraints

- No new GPU jobs/campaigns, GitHub Actions, merges or manuscript-claim edits during this task.
- Preserve frozen measurements; distinguish retrospective evidence, development and prospective confirmation.
- Compare validated mechanisms; do not claim support from names, local tests, startup or Slurm exit alone.
- Preserve offered arrivals, lengths and failures; no silent clipping, source filtering or approximation.
- Permit stable rankings and inconclusive outcomes. Do not require reversals or favorable winners.
- Keep this protocol DRAFT until explicit author approval, with an immutable pre-outcome freeze.

## Decisions requested before implementation/main-study authorization

| ID | Status | Recommended choice | Why approval/evidence is needed |
|---|---|---|---|
| A01 | Unresolved | Position this as a new physical transfer-validity study with explicit attribution to existing LSSP | Confirm publication/submission status and overlap; remote Research Square/Zenodo byte correspondence remains unverified |
| A02 | Provisional | Four mechanisms: native_fcfs, prompt_spf, token_fair, checked_slai | Approve scope; only two bounded adapters exist, and real VTC/expanded SLAI require work |
| A03 | Unresolved | Expand fidelity to long-prefill and required KV behavior before main ranking work | The 256/16 contract excludes important trace regimes; a restricted alternative changes the scientific question |
| A04 | Provisional | Dense 7–8B BF16 model, same family if feasible; retain 0.5B only for engineering | Exact checkpoint/tokenizer/context/output limits and smallest-GPU fit are unverified |
| A05 | Provisional | Six deployments; DP2 as deterministic external round-robin to two TP1 replicas | Approve routing semantics and per-engine versus aggregate admission controls; distributed correctness is unverified |
| A06 | Unresolved | Application-defined absolute TTFT/TBT/E2E budgets, equal class thirds | Specify numbers/provenance; if synthetic, approve the synthesis rule and sensitivity overlay |
| A07 | Provisional | Primary request goodput requiring all token gaps; δ=0.05, h=0.025 | Approve practical importance and verify per-token observability; a different metric must be chosen prospectively |
| A08 | Provisional | ρ=0.60/0.90 of native-reference capacity; ≥90% SLO success plus queue stability for capacity | Approve exact queue/drain/calibration tolerances; calibrated rates and measurement uncertainty are unknown |
| A09 | Provisional | Include equal-relative-pressure primary and common-A100-rate secondary views | Different estimands and extra GPU cost; do not budget both as one matrix |
| A10 | Unresolved | Nonoverlapping raw windows excluding historical/pilot rows; frozen temporal hold-out | Raw units/coordinates/actual-token coverage and new hashes must be verified; 8 windows/source is illustrative |
| A11 | Unresolved | Pilot-selected W/R with clustered simultaneous intervals and independent analysis validation | Statistician review of effective clusters, bootstrap behavior and multiplicity; no power guarantee yet |
| A12 | Provisional | Offline abstaining transfer rule; false-safe ≤5%, coverage ≥25%, net savings >0 | Approve decision utility thresholds; held-out precision may require substantially more windows |
| A13 | Unresolved | Multi-node-per-architecture sampling where available; otherwise deployment-specific claims | A100/L40 host/interconnect confounding cannot be removed by naming the GPU factor |
| A14 | Unresolved | Pilot-derived wall bounds and total cap, including calibration/profiles/failures and 20% planning reserve | No authorized future GPU budget; numerical runtime estimates would currently be invented |
| A15 | Provisional | Prioritize one prespecified mechanism intervention over TP4/second-model expansion | Approve mediator/intervention freeze; causality requires more than telemetry correlation |
| A16 | Unresolved | Separate MGPU03 physical acceptance review, then explicit authorization for Stage 1 | Accounting COMPLETED is not enough; this turn deliberately did not inspect serving outcomes |

## Outstanding implementation work, without authorization to execute it here

1. Independently specify and implement prompt-SPF and token-fair mechanisms; verify every policy-pair distinction.
2. Design a general SLAI partial-prefill/KV contract, or explicitly approve a different narrower scientific scope. Preserve MGPU02 rejection behavior until replaced by a validated new contract.
3. Add TP rank and DP route/replica conformance and consistent timing/metadata transport.
4. Verify full trace-to-token replay, open-loop admission, output conservation, token-level stream timestamps and error accounting at realistic pressure.
5. Implement and validate the frozen statistical analysis and portability-rule evaluation independently of adapter outputs.

No item above is implicitly completed by this protocol. Author review should first settle A01–A07 and the fidelity scope, then authorize a bounded implementation/pilot plan. The six-deployment main study and TP2/DP2 physical execution are currently **NO-GO**.
