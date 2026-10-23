# Contribution-to-evidence matrix

Baseline: PR #25 head `d73192df32fd14ec025eb8b9dab72da401eb65ae`.
This revision interprets existing evidence; it executes no scientific experiment.

Central argument: nominally different scheduling rules can induce identical per-request transitions under a specified execution contract. Establishing that equivalence, or explaining an inactive rule, requires examining the contract and policy mechanisms. Rankings then describe the remaining behaviors at a particular aggregation level and objective.

| Contribution | Existing evidence and manuscript location | Scientific distinction | Boundary |
|---|---|---|---|
| Effective behavior versus policy identity (RQ1) | Section 3.3: at most `512 K <= 4096 < 32768` units of work; identical waiting prefix, per-request spans, batch-end timestamps and release rules give induction from the shared initial state. All 1,440 original matched terminal comparisons agree. | Separates a state-transition invariant from equal aggregate metrics; four labels represent three observed terminal behaviors. | The theorem concerns these adaptations and the original contract. It does not establish native-system equivalence. |
| Mechanistic explanation of inactivity (RQ2) | Section 3.4, Eq. (1): before a first urgent decision, every omitted-ready-decode batch must spend at least `B-(K-1)` units of prefill work. Thus `delta floor(P/[B-(K-1)]) < 0.495 s` is sufficient for inactivity. `urgency-analysis/{STRUCTURAL_FINDINGS.md,certificates.csv,independent-check.json}`. | Converts an observed zero activation count into a reachability bound under explicit assumptions. Original nonbinding execution has the stronger zero-anchor-age invariant. | Requires fixed batch time, finite prompt work, no recomputation or idle jump while a ready decode remains resident, and `B>K-1`. Metric deadlines are hidden and cannot exercise the fixed gate. This is not a general equivalence theorem or a necessary activation condition. |
| Comparison-level trade-offs (RQ3) | Sections 5–6; `supplement/c01-source-capacity-means.csv`, `tables/reversals.tex`, `editorial-revision/reduced-comparisons.{json,tex}`. Six source/capacity means: SLO versus chunked mean latency lower 11.3–34.0%, finite-window throughput lower 1.65–4.01%; BurstGPT mean window-p95 higher 3.72%/18.97%. | Relates the residual behavior set to the coexistence of aggregate practical stability and local/objective-dependent preferences. | Established scheduling trade-offs are not claimed as new phenomena. These are descriptive selected-corpus comparisons, not population guarantees or GPU forecasts. |

## Populations and comparison rules

- Original source means: **0/2,376** strict-10% reversals; `3 source pairs × 6 settings × 2 capacities × 11 endpoints × 6 policy pairs`. Each source mean uses all 40 windows at fixed setting/capacity/metric.
- Reduced source means: **0/864**; `3 × 6 × 2 × 8 endpoints × 3 behavior pairs`. Removal is post hoc, not a newly independent experiment.
- Original within-source window pairs: **34,394/1,847,700 eligible**; cross-source window pairs: **109,913/3,788,640 eligible**. These compare *different windows*.
- Original comparisons within the *same window*: settings **920/236,853**, capacity **350/47,418**, metric choice **11,795/473,580 eligible**.
- Reduced view retains within-source-window reversals **18,732/670,637**, cross-source-window reversals **61,880/1,374,720**, and cross-metric reversals **4,492/120,288 eligible**. Overlapping pairs are dependent.
- The unchanged rule requires opposing signed relative preferences each strictly beyond 10%; ties with nonzero losing values remain eligible, while zero losing values are unestimable. Exact equality and the predeclared numerical near-tie tolerance answer separate questions.
- Separate budget sensitivity (Section 5.6): 72 cells, three input-selected BurstGPT windows, two existing settings, eight slots, four adaptations, budgets 32,768/2,048/1,024. All **12 perturbed chunked/decode matches** agree; **0/576** strict-10% preference reversals across budgets. This is not a new cross-source result or an extension of the nonbinding proof. At 1,024, SLO omits **42/35,976** ready-decode opportunities; across all 18 saved SLO cells, urgent opportunities are **0/107,844**. Existing journal reconstruction supports these counts.

Reproducibility, conformance checks, known-truth historical calibration, and the retrospectively selected request timeline support interpretation. They are not additional scheduler contributions, independent replications, or a causal decomposition of mechanisms. The revised manuscript preserves them without making them the novelty headline.
