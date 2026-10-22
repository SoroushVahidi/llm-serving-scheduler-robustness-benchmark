> **Current supplement:** [artifact-readiness verification](artifact-release/VERIFICATION.md) adds full local payload checks and focused contract reasoning. The numerical evidence map below remains unchanged.

# Claim-to-evidence verification

Authority: final review PR #17 at `6b2eedd7aa254986b85c1bb901587641cbeac8b0`; prewrite audit PR #16 at `d22c7751af9c563d5a4d8a304c007f26112c4d12`. All C01 claims are finite-corpus descriptions. All STAT01 claims identify the synthetic scenario and uncertainty family.

Saved inputs are under `evidence/inputs/` with `.json.gz` suffix; full uncompressed and stored SHA-256 values are in `evidence/input-hashes.json`. The input names below omit that directory/suffix. No historical file is edited to make a claim pass.

| Claim / manuscript location | Immutable evidence and verification | Scope |
|---|---|---|
| 5,760 cells; 120 windows × six settings × four adaptations × two capacities; 144 reuse | `c01-manifest`, `c01-absolute_metrics`, `c01-complete`; Cartesian coverage independently rechecked by the frozen oracle | Cell identities, not stochastic repetitions |
| Every request completes; 1,152,000 request executions; no horizon censoring | All absolute rows; PR #17 full terminal-record recomputation; fresh count checks | Repeated conditions, not independent requests |
| Mean/p95 latency and throughput ranges; TPOT counts 103–200 | Full absolute rows, fresh extrema checks | Model seconds; conditional TPOT definition retained |
| Aggregate mean-latency improvement 11.3–34.0%; throughput reduction 1.65–4.01% | Equal-window/equal-setting means regenerated in `numerical-checks.json` and source/capacity CSV | Six specified aggregates, not all individual cells |
| BurstGPT p95 +3.72% / +18.97%; Bailian four-slot ANWG −3.12% | Same source/capacity means and all-window displays | Mean window-p95, never pooled-request p95 |
| Chunked/decode equivalence 1,440/1,440 | Absolute metric equality freshly checked; PR #17 compared all terminal records (`c01-record-check`) | Restricted adaptations, not native vLLM/Sarathi equivalence |
| At most 4/8 residents; chunked work ≤4,096 <32,768; urgency gate cannot bind | Frozen C01 protocol and `policies.py` at pilot execution `9aed0206de66886e9feb0b003b59f0b7dfea68c9`; common progress/anchor rules | Structural consequence, no new intervention experiment |
| Peak used KV 47,872 / 62,880 | All absolute rows, fresh maxima | Reservation-induced concurrency; no native eviction claim |
| Arrivals and deadline slack both divide by factor; factor ranges | `_rebase_and_scale`, inherited code lines 59–95; all saved load factors | Joint arrival/deadline stress, not isolated load intervention |
| Azure LOW→HIGH mean latency/throughput/ANWG example | Fixed source/setting/capacity means in `c01-window_aggregates` | Descriptive contrast with altered deadlines |
| Source-mean reversals 0/2,376 | `c01-reversals`; full oracle integer-ratio threshold checks | Strict >10% at both endpoints; tied nonzero pairs eligible |
| Other axes: 34,394 / 109,913 / 920 / 350 / 11,795 reversals, all denominators | Complete `c01-reversals`; all 26,136 groups independently checked | Dependent pair counts, not probabilities from independent trials |
| Source-mean top equal/intersect/full-rank equality 307/323/247 of 396 | `c01-source_mean_rankings`; fresh direct pairing | Different estimands from strict practical reversals |
| Exact ties; SLO unique winner counts; per-source mean-latency winners | `c01-rankings`, `c01-ranking_frequencies`; full oracle + fresh summaries | No arbitrary tie-breaking |
| Completion and throughput redundancy | All completed rows; same matched workload and observation-time denominator | Eleven endpoints are not eleven independent confirmations |
| Mean-TPOT maximum difference 1.80e−16 s; top-set changes 1,129 and 104 | Absolute rows and exact/sensitivity ranking records; fresh checks | Numerical distinctions have no practical meaning |
| Metric top-set equality/intersection 27,915/57,602 of 79,200 | Fresh complete pair enumeration from saved rankings | Includes redundant metrics and ties |
| Chronology difference ranges, negative counts 8/24/0 and 6/20/0 | `c01-window_aggregates` block/stratum records; fresh direct checks | Unequal-duration descriptive blocks |
| Historical 36/990 archived-rule records | Preserved M2 statistical audit / PR #17 review | Neither a confirmed population count nor reproduced C01 phenomenon |
| STAT01 134,000 studies, 18 scenarios; six precision stops, twelve maxima | `stat-checkpoint`, `stat-completion`, final saved looks | Completion does not imply precision or calibration |
| Original eight, actual-source comparator, eight exact additions | `stat-launch`; frozen protocol and amendment | Nine additions are post-diagnosis |
| Expanded historical-source IID/block/AR FDR and coverage bounds | `stat-look-s00/s08/s10-n08000`, `expanded_postdiagnosis` → `legacy_source_screened_BH` | All main table values use the 17-method family |
| 45 concern / 74 inconclusive / 9 compatible / 16 abstain | Original-family method screens, all scenarios | Dependent classifications; compatible ≠ exact calibration |
| Boundary, missingness, power and coverage examples | Relevant final looks; availability counts and explicit method/family fields in CSV | No selected/unconditional coverage substitution |
| Original failure at scenario 11 replicate 6628 | PR #17 saved-record replay and `stat-sample-check`; amendment | Frozen port, actual source, and mathematical threshold stay distinct |
| 31 reuse differences; final maximum endpoint differences | PR #17 reuse audit; final original/expanded method comparisons | Aggregate equality does not certify equal rejection vectors |
| Event verification is not physical-model validation | Frozen execution contract, PR #17 check scope, Sargent primary reference | No GPU accuracy or ranking-transfer claim |

## RQ and contribution alignment

- **RQ1 / contributions 1–2:** Sections 3–5 specify comparison identities and report absolute performance, completion, unfavorable tails/throughput, and resource/setting interpretation. Tables 1–4 and Figures 1–3 support the answer.
- **RQ2 / contribution 3:** Section 6 reports the null source-mean finding, nonzero other-axis reversals, exact ties, endpoint redundancy, and chronology. Tables 5–6 and Figure 4 support the answer.
- **RQ3 / contribution 4:** Section 7 distinguishes historical arithmetic, execution conformance, and calibration; Table 7 gives a concise diagnostic. Appendix A and the complete endpoint supplement support the detailed limits.

`evidence/numerical-checks.json` holds regenerated headline counts and percentages. `evidence/validation/validation.json` records the independent complete C01 report oracle, narrative checks, 7,200 endpoint CSV comparisons, reference closure, compilation diagnostics, and preservation checks. Claims about exhaustive prior event/study validation are attributed to the completed campaigns and PR #17; M3 does not falsely claim fresh replay of all raw journals or generation of new studies.

## Stale-claim review

The M3 abstract, introduction, RQ answers, discussion, and conclusion consistently use the common-model object. Removed as current claims: general ranking instability, population significance of historical reversals, an active urgency mechanism, complete original SLAI validation, native GPU fidelity, pure-load ANWG effects, independent provider sampling, independent deterministic repetitions, pooled-request interpretations of average p95, and a universal replacement inference method. Earlier artifacts still contain their historical wording and remain unchanged.
