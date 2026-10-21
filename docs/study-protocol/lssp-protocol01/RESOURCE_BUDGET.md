# Sample size and resource budget

**DRAFT. No campaign budget or new GPU allocation is approved.** Resource consumption from this task: **0 GPU-hours**. Future durations, capacity curves and variance components remain unknown. MGPU03 performance is deliberately not used to choose sample size or hypotheses.

## Pilot-based sample-size selection

After fidelity gates, separately authorize a bounded, prespecified pilot spanning sources, both pressure regions and deployment types on **development-only** windows. Include fresh repetitions on different allocation/day blocks. Collect startup/warmup/drain time, paired normalized-goodput variance, between-window variance, day/node effects, deadline failures and instrumentation overhead. Select cells by design factors, not anticipated or observed winners. Keep failed/incomplete pilot attempts in cost accounting; pilot outcomes are not later called preregistered confirmation.

For a paired effect, use the planning approximation

`SE² ≈ σ_window²/W + σ_repeat²/(W·R)`.

For a deployment interaction, estimate those variances from **paired differences of differences**, preserving covariance, not four independent run variances. Inflate for temporal/day clustering and uncertainty in the variance estimates; use an upper confidence estimate or conservative range. Sources are fixed strata; do not divide uncertainty by three as if providers were independent. Repetition count cannot compensate for too few independent windows.

Choose W and R to achieve both:

1. Simultaneous interval half-width ≤h=0.025 for the prespecified primary contrasts where feasible.
2. At least 90% planned probability of distinguishing an alternative meaningfully beyond the decision boundary (proposed effect 0.10 versus practical boundary δ=0.05), using the frozen multiplicity procedure.

For a rough planning bound, `W ≥ (c + z_0.90)²(σ_window² + σ_repeat²/R)/(0.10−0.05)²`, where c is the simultaneous critical value. For precision alone replace the denominator by h² and numerator by c². These are approximations, not claimed power calculations for the final bootstrap. Simulate the **planned analysis** using pilot covariance/clustering, including ties, missingness, heteroskedasticity and the null; publish seeds/code and precision/power curves. Choose the smallest balanced design satisfying approved criteria within the cap. If none fits, reduce the question with approval or report expected inconclusiveness; do not lower δ after seeing results.

Use pilot variance to choose R (illustratively 2–4) and spend remaining resources on independent windows. Freeze W/R, temporal-block definition, node allocation, final hypotheses and stopping rule before main outcomes. No significance-driven optional stopping. A blinded nuisance-variance update is possible only if explicitly registered with a hard maximum; otherwise a sample-size change is an amendment. Main cells whose intervals remain wide are reported inconclusive.

C4 has its own sample requirement: accepted held-out decision clusters must support the false-safe-risk and coverage bounds. Main C2 power does not establish C4 power. Overlapping edges or repeated requests cannot manufacture independent decision counts. If the C4 requirement dominates the budget, a valid result is “insufficient evidence to certify transfer.”

## Matrix arithmetic

The user illustration is **one load view**:

`6 deployments ×4 policies ×3 sources ×8 windows/source ×2 pressures ×3 repetitions = 3,456 executions`.

GPU weights are `[1,2,2,1,2,2]`, summing to 10. Thus these executions contain **5,760 GPU-executions**, not 3,456 single-GPU executions. At an assumed *entire allocated slot* of 10 minutes each this is **960 GPU-hours**; at 35 minutes it is **3,360 GPU-hours**. These are arithmetic scenarios, not measured or recommended wall times, and include startup only if the quoted slot includes it.

If the common-rate view reuses exactly the A100×1 anchor cells and all other rates differ, total unique executions are `(6+5)×4×3×8×2×3 = 6,336`, with **10,944 GPU-executions**. At 10 minutes per full slot that is **1,824 GPU-hours**; at 35 minutes, **6,384 GPU-hours**. An intentionally conservative no-deduplication upper scenario is 6,912 executions /11,520 GPU-executions /1,920 GPU-hours at 10 minutes. Deduplicate only identical deployment/policy/window/rate/seed/state contracts; overlapping conceptual labels do not justify double-counting evidence.

## Allocation estimator and enforceable cap

For each future job j, let g_j be allocated GPUs, S_j startup, U_j fixed warmup, T_j replay, D_j drain, L_j logging/cleanup, all seconds:

`H_expected = Σ_j g_j·E[S_j+U_j+T_j+D_j+L_j]/3600`.

Use pilot upper quantiles plus uncertainty for planning, separately by model/deployment. Set readiness bounds from diagnosed initialization phases (asset read, model load, compile/capture and API readiness), not by repeatedly increasing a timeout. Pretokenize and hash prompts outside the timed replay, as MGPU02 does. Cached assets/compile reuse are permitted only under a fixed cache-state policy shared by all policies; timing changes require equivalence checks and startup remains separately reported. If multiple cells share a job, count startup once and verify state reset/warm-cache equivalence; randomized order and paired warm state remain necessary. Any batching of jobs must be represented explicitly, not estimated as zero startup.

The enforceable maximum is `H_cap = Σ_authorized_jobs g_j·wall_limit_j/3600`, plus separately authorized replacements/extensions. No auto-requeue or unbounded retries. A queue wait is not allocated GPU time. Report calibration, fidelity, main, profiles/interventions, model extensions and failed-job consumption separately. Contingency (proposed 20%) is a planning reserve, not permission to retry; include it in the approved total cap and require a replacement decision ledger.

| Budget component | Required future input | Present value |
|---|---|---|
| Stage 1 | 24 slots, measured startup/drain and per-slot wall bound | UNSET; no allocation authorized |
| Stage 2 conformance/calibration/variance | Explicit cells, GPU weights, cap per cell | UNSET |
| Main relative-pressure | W/R selected by precision/power; time distribution by deployment | 3,456 illustration only |
| Additional common-rate | Exact deduplication ledger and time bounds | Up to 2,880 additional cells in the 8×3 illustration |
| C3 profiles/interventions | Outcome-blind subset size, profile overhead, intervention replications | UNSET |
| C4 | Held-out independent clusters, target-reference probe/training costs | UNSET |
| Extensions and replacements | Separate author approval, explicit wall bounds | UNSET |

The MGPU03 accounting record corresponds to `1010/3600 = 0.280556` allocated GPU-hours for its parent job. Do not add batch/extern steps again. Its prior authorized cap was `35/60 = 0.583333…` GPU-hours. This accounting disclosure is not a prediction of main-study runtime and does not use its serving performance.
