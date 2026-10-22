# Final experimental results and M3 readiness review

**Review date:** 2026-10-22. **Verdict: READY_WITH_LIMITATIONS.**

**Recommendation:** Begin the M3 rewrite after author review of this report. The two authorized campaigns have completed, their required in-job validation ran, and the independent checks described below support using their results. No further scientific experiment or Slurm submission is needed for the bounded manuscript proposed here. This is rewrite readiness, not submission readiness or a prediction of acceptance.

This review follows [M3_PREWRITE_AUDIT.md](M3_PREWRITE_AUDIT.md), draft [PR #16](https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark/pull/16), commit `d22c7751af9c563d5a4d8a304c007f26112c4d12`. It preserves that audit's integrated direction: common-model performance evaluation at the center, historical comparisons as motivation, and statistical calibration as a separate diagnostic. All numerical findings below come from completed artifacts, not startup observations. No manuscript, bibliography, figures, frozen protocol or experimental output was changed.

## 1. Actual execution status

Both campaigns have execution state **COMPLETED_SUCCESS**. Slurm reports `COMPLETED`, exit `0:0`, reason `None`. The queue was empty for both IDs at the single successful status inspection, 2026-10-22 **18:09:08 UTC**. `scontrol` no longer retained the job IDs; accounting and persistent artifacts supply their completed records. An initial non-login SSH shell lacked Slurm commands; the immediate login-shell inspection succeeded. Active-status inspection took well under two minutes; there was no waiting for jobs to finish or subsequent polling.

| Field | C01-FULL | STAT01 recovery |
|---|---|---|
| Slurm ID / draft PR | 1440402 / [#15](https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark/pull/15) | 1440206 / [#14](https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark/pull/14) |
| Submitted UTC | 2026-10-22 15:37:41 | 2026-10-22 14:52:38 |
| Started UTC | 2026-10-22 15:37:56 | 2026-10-22 14:52:50 |
| Ended UTC | 2026-10-22 17:04:17 | 2026-10-22 15:10:42 |
| Elapsed / total CPU | 01:26:21 / 01:18:51 | 00:17:52 / 01:01:52 |
| Allocated CPUs / node | 1 / n0006 | 4 / n0006 |
| Batch MaxRSS | 263720K | 1906780K |
| Expected / completed | 5,760 / 5,760 cells | 134,000 / 134,000 studies, 18 scenarios |
| Reused / new | 144 / 5,616 cells | 112,275 / 21,725 studies |
| Last checkpoint UTC | 17:04:17.484260 | 15:10:37.888206 |
| Application status | `EXECUTION_AND_INDEPENDENT_CHECKS_COMPLETE` | `COMPLETE_WITH_ORIGINAL_PRECISION_GAPS` |
| Persistent exit / stderr | `slurm.exit=0`; empty stderr | `slurm.exit=0`; empty stderr |
| Failure / partial evidence | No failure files; no remaining attempt directories | No failure files; no `.part` batch directories |

C01's stdout contains exactly 5,616 cell starts, 5,760 cell-validation events and one completion event. STAT01's stdout contains exactly 5,360 batch starts, 5,360 batch-validation events and its precision-gap completion event. STAT01 completed its allowed design; twelve scenarios reached the maximum count without meeting all precision objectives. That is neither missing computation nor calibration success.

Execution commits remain `2d8342e699f35044044ac518c0b75a3c4a1c768c` for C01-FULL and `1ac4c8dd1421aabad05e6ce243cb911a6ed6c8e1` for STAT01 recovery. Pilot execution remains `9aed0206de66886e9feb0b003b59f0b7dfea68c9`.

## 2. Validation: what was independently checked

### 2.1 C01-FULL

**Fresh review checks on the workstation:**

- Recomputed the canonical launch identity and all **164 launch-file SHA-256 fingerprints**, including frozen inputs, code and validation materials.
- Checked **720 condition records**, 200 requests each, their request fingerprints, frozen manifest agreement, policies and both capacity configurations. Enumerated the Cartesian plan and matched its **5,760 unique identities** against absolute rows, checkpoint entries and stdout validation keys. No duplicate or missing planned identity was found.
- Read all **5,760 per-cell result records**. Their file hashes, run identities, condition/input identities, journal-hash references, validation flags and metric records agree with the final analysis. All **144 copied pilot results** match the frozen reuse-index result and journal fingerprints; the remaining 5,616 carry the distinct full-campaign identity.
- Independently recomputed terminal request conservation, completion, latency/TTFT/TPOT populations, means and p95s, observation time, throughput, token work, goodput and horizon accounting for all cells from saved input and terminal records. Values matched exactly, including the check using stable summation for means. Resource peaks obey the recorded capacities. Terminal records for chunked-FCFS and decode-first are equal in all 1,440 matched conditions.
- Reran the separate analysis oracle locally against the complete saved reports: **5,760 absolute rows, 15,840 rankings, 95,040 matched differences and 26,136 reversal groups**, with complete aggregate/ranking/frequency/source-mean and strict-boundary checks. PASS; approximately 3.3 seconds locally. This independently implemented verifier imports no production analyzer.
- Downloaded and rehashed **24 new-cell journals**, selected as the first nonpilot window per source at HIGH_PRESSURE, both capacities and all four adaptations. Fresh independent event-referee replay passed for all 24, reproducing their metrics. Selection was structural, not based on favorable outcomes.

**Previously executed exhaustive checks, inspected rather than falsely claimed as rerun:** the CPU allocation's `campaign.py` first validates each cell, then `verify_all` rereads every planned journal and checks identity/resource/timing/metric conformance before analysis and the completion marker. The saved marker and independent-analysis PASS, zero exit, complete logs and unchanged code establish that this path finished. This review did **not** repeat all 5,760 journal replays or rehash all journal bytes afresh; it checked every result-record hash and sampled journal bytes in addition to the completed exhaustive validation. Event conformance is not hardware fidelity.

All required analysis outputs exist. Every metric is finite and defined in every cell; no unexplained missing/corrupt/unfinished output was detected. Zero goodput is a valid outcome, not missing data; it makes some relative-margin comparisons unestimable under the frozen rule.

### 2.2 STAT01 recovery

**Fresh review checks on the workstation:**

- Recomputed the recovery launch identity; verified all manifest-listed recovery code/protocol files, original frozen code, historical-reference code, original launch, source inventory/audit hashes, and pinned test-log hash. The pinned log records **118 tests passed**. These tests cover legacy and exact definitions, equality and neighboring floats, sorting/ties, missingness, family sizes, original failure and recovery integrity; they do not by themselves establish calibration.
- Read all **5,360 integrity records**, covering **134,000 studies** in contiguous, nonoverlapping replicate ranges for every scenario. Verified run/original identities, count 25 per batch, validation contract, complete three-file artifact inventories, all 17 method inventories and all 16 endpoint moment inventories.
- Matched **4,491 reused batches / 112,275 studies** to the frozen source ledger, including unchanged original raw/record fingerprints and provenance. The remaining **869 batches / 21,725 studies** are labeled generated under the unchanged campaign namespace. No raw studies were invalidated or discarded. Nine added comparisons were derived for reused studies rather than regenerating them.
- Independently combined batch sufficient statistics with 50-digit decimal arithmetic, then recomputed **7,200 final method–endpoint summaries** across the original-eight and expanded-seventeen reports. Counts agree exactly; the maximum mean/bound difference from sequential floating aggregation is **9.99e-16** and maximum half-width difference **5.55e-17**. Every original calibration-screen decision agrees. These roundoff differences were measured, not resolved by changing rejection rules.
- Checked every recorded look's precision decision, absence of an earlier precision stop, final count and stopping label. Original stopping depends only on the eight frozen methods. Original per-endpoint/look allocation is `.05/(18*8*16*5)`; the distinct expanded report uses `.05/(18*17*16*5)`. No original bound is mixed into an expanded joint-coverage claim.
- Freshly checked **200 saved studies** in eight batches: scenarios 0, 4, 8, 11, 14, 15, 16 and 17; scenario 11 uses batch starting at 6625. Rehashed their raw/original/secondary files and reran the independent referee for all 17 procedures, raw shape/masks/truth, decisions and endpoints. All passed. Also independently compared their legacy BH vectors against SHA-verified frozen historical source code; all 200 agree. No new synthetic study was generated.

**Exhaustive validation already performed in the allocation:** `rv2_run.py` verifies source hashes, preserves reused bytes, independently validates every original/additional record, writes the batch, then reopens it and checks hashes, records and sufficient statistics before atomic publication. All 5,360 published batches have that contract and corresponding validation events. Fresh review did not rehash all 134,000 studies' raw arrays or rerun every record-level oracle; it combines the completed exhaustive read-back with full inventory/moment checks and the 200-study fresh check. No essential unperformed validation requiring another Slurm allocation was identified.

### 2.3 Original failure and numerical definitions

The saved scenario **11, replicate 6628**, original `historical_screened_BH` comparison index **47**, reproduces the old disagreement. Its screened family has **43** entries; the boundary entry has rank **43** and stored p-value **0.05**, hexadecimal `0x1.999999999999ap-5`.

| Interpretation | Threshold / decision |
|---|---|
| Frozen eight-procedure port | `.05*43/43 = 0.049999999999999996`; rejects **false** |
| Exact historical source | `(43/43)*.05 = 0.05`; rejects **true** |
| Mathematical bootstrap-grid comparison | p = 1/20, critical threshold = 1/20; inclusive rejection **true** |

The unchanged old referee still raises `independent multiplicity mismatch` for this saved record. The explicitly separated recovery contracts pass. Legacy fidelity is not mathematical correctness; the eight original methods have not been silently replaced. Analytic p-values in the exact additions mean the exact dyadic values represented by their finite floats, not infinitely precise analytic tails. Bootstrap probabilities are recovered on their exact count grids, with rational thresholds and harmonic constants. This changes arithmetic semantics, not screening, component assumptions, target truth or the underlying test validity.

## 3. C01-FULL findings

These are **descriptive finite-corpus statements**, with the whole window as the analysis unit. Repeated settings, policy pairs, metric pairs and cross-window pairs are dependent descriptions, not independent observations or population frequencies. The original eleven endpoints and all four policy identities remain in the artifact.

### 3.1 Absolute performance and the important trade-off

All **5,760 cells complete all 200 requests**: 1,152,000 request executions across repeated conditions, not that many independent requests. There is **no administrative-horizon censoring**, no missing latency/TTFT/TPOT metric, and completion fraction is exactly one everywhere. TPOT populations range from **103 to 200** completed requests because one-output-token requests have undefined individual TPOT and are correctly excluded. Cell mean latency ranges from **0.008314 to 3.893923 seconds**; cell p95 latency from **0.008560 to 7.300052 seconds**. Token throughput spans **332.489–7,766.685 tokens per simulated second**. These are synthetic model units, not GPU predictions.

The following compact table first averages the six inherited settings within each window, then averages the 40 windows equally. It is not an additional inferential analysis. “p95” is the **mean of window-level p95s**, not pooled-request p95. ANWG uses uniform priorities and synthetic deadlines. Chunked and decode-first are shown together only because their records are exactly equal; both original identities remain preserved.

| Source | KV capacity | Adaptation | ANWG | Mean latency (s) | Mean window p95 (s) | Mean TTFT (s) | Token throughput |
|---|---:|---|---:|---:|---:|---:|---:|
| Azure 2024 | 131072 | Chunked / Decode-first | 0.1746 | 2.8132 | 5.3232 | 2.7042 | 3746.2 |
| Azure 2024 | 131072 | Whole-FCFS | 0.1746 | 2.8145 | 5.3275 | 2.7026 | 3743.5 |
| Azure 2024 | 131072 | SLO-gated | 0.2001 | 1.8559 | 5.1342 | 1.7468 | 3684.4 |
| Azure 2024 | 262144 | Chunked / Decode-first | 0.3174 | 1.3626 | 2.5986 | 1.2536 | 7018.7 |
| Azure 2024 | 262144 | Whole-FCFS | 0.3101 | 1.4092 | 2.6892 | 1.2937 | 6816.5 |
| Azure 2024 | 262144 | SLO-gated | 0.3892 | 0.9357 | 2.5131 | 0.8267 | 6825.8 |
| Bailian/Qwen | 131072 | Chunked / Decode-first | 0.1828 | 2.2655 | 4.2969 | 2.1721 | 3603.2 |
| Bailian/Qwen | 131072 | Whole-FCFS | 0.1799 | 2.3020 | 4.3705 | 2.2057 | 3548.3 |
| Bailian/Qwen | 131072 | SLO-gated | 0.1771 | 1.7205 | 3.9681 | 1.6272 | 3531.4 |
| Bailian/Qwen | 262144 | Chunked / Decode-first | 0.3330 | 1.0417 | 2.0227 | 0.9483 | 6183.4 |
| Bailian/Qwen | 262144 | Whole-FCFS | 0.3189 | 1.1063 | 2.1463 | 1.0065 | 5914.1 |
| Bailian/Qwen | 262144 | SLO-gated | 0.3693 | 0.8087 | 1.9037 | 0.7153 | 5935.7 |
| BurstGPT | 131072 | Chunked / Decode-first | 0.1030 | 0.5225 | 1.0005 | 0.4910 | 3354.9 |
| BurstGPT | 131072 | Whole-FCFS | 0.0889 | 0.5654 | 1.0843 | 0.5318 | 3054.9 |
| BurstGPT | 131072 | SLO-gated | 0.2321 | 0.4448 | 1.0377 | 0.4132 | 3223.4 |
| BurstGPT | 262144 | Chunked / Decode-first | 0.3072 | 0.1907 | 0.3707 | 0.1591 | 5532.1 |
| BurstGPT | 262144 | Whole-FCFS | 0.2129 | 0.2314 | 0.4505 | 0.1959 | 4796.5 |
| BurstGPT | 262144 | SLO-gated | 0.4613 | 0.1692 | 0.4410 | 0.1376 | 5322.3 |

Against chunked-FCFS, SLO-gated lowers these source/capacity aggregate mean latencies by **11.3–34.0%**, but lowers token throughput by **1.65–4.01%** in all six aggregates. On BurstGPT it raises the mean window-p95 latency by **3.72%** at the smaller capacity and **18.97%** at the larger capacity, despite improving the mean and ANWG. On Bailian at the smaller capacity its ANWG is **3.12% lower**, despite **24.05% lower mean latency**. These are informative metric trade-offs; a universal winner would be misleading.

Across the 1,440 window/setting/capacity conditions, SLO-gated is the unique mean-latency winner in **1,146**, unique ANWG winner in **1,004**, unique p95-latency winner in **834**, and unique token-throughput winner in **482**. It wins mean latency uniquely in all **480 Azure** conditions and **468/480 Bailian** conditions, but only **198/480 BurstGPT** conditions. Magnitudes and ties, rather than winner counts alone, should lead the paper.

### 3.2 What is informative, and what follows mechanically from CM-0.1

1. **Two adaptation identities collapse to the same behavior.** Chunked-FCFS and decode-first have identical terminal records and every metric in **1,440/1,440** matched conditions. With at most eight resident/admitted requests and a 512-token prefill cap, their per-batch work is at most **8 × 512 = 4,096**, below the common **32,768** budget. All selected work fits; ordering it differently within a fixed-duration batch does not change progress. This is a model-implied equivalence supported by the records, not empirical evidence that native Sarathi and vLLM are equivalent.
2. **The SLO gate is not the demonstrated mechanism.** In the same chunked action space every resident decode fits every batch. Its anchor is refreshed each step, so the 0.495-second urgency gate cannot become binding along these executions. The distinctive SLO-gated behavior is principally prompt-length admission ordering, with the frozen chunking rules. Its mean/tail/throughput trade-offs are measured; they do not validate SLAI, heterogeneous SLO prioritization or an active urgency mechanism. This follows from the pinned `policies.py` and the capacity/budget invariant, not a new intervention experiment.
3. **The capacity effect is largely a residency effect.** Full-context reservations change the permitted residents from four to eight. Maximum observed used KV is **47,872** at capacity 131,072 and **62,880** at capacity 262,144, below even the smaller nominal capacity. This experiment studies conservative reservation-induced concurrency constraints; it does not establish benefits of native cache eviction, paging or memory pressure at the measured used-token limit.
4. **Several endpoints are redundant in this corpus.** Completion ties everywhere. Because all requests finish, completed-token and emitted-token throughput are equal. At a matched condition, request and token throughput differ only by a fixed workload-specific multiplier, so all three throughput rankings coincide. Eleven frozen endpoints are retained, but they are not eleven independent confirmations.
5. **Exact TPOT ranks can reflect floating-point timestamps.** Chunked/decode-first/SLO-gated yield essentially 1 ms per output interval. The largest difference between chunked and SLO-gated cell mean TPOT is **1.80e-16 seconds**. The frozen near-tie sensitivity changes the mean-TPOT top set in **1,129/1,440** conditions and p95-TPOT in **104/1,440**. These exact-rank distinctions have no practical performance meaning. Retain exact primary records and report the predeclared sensitivity, without changing thresholds after seeing results.

These structural findings constrain novelty. The nontrivial empirical findings are the magnitudes and source/window variation of the remaining performance trade-offs, the relationship between aggregation and reversals, and the effect of reporting conventions. “Four distinct scheduling mechanisms broadly validated” would be overstated.

### 3.3 Inherited settings change deadlines as well as arrivals

A material clarification beyond the prewrite audit: frozen `src/robustbench/calibration/stage0_load_calibration.py:59–95`, `_rebase_and_scale`, divides **both arrival gaps and SLO slack by the compression factor**. All 600 nonbaseline within-window setting comparisons change deadline slack; prompt/output lengths and priorities remain unchanged. The absolute factors vary by window: Azure **22.525–180.873**, Bailian **17.956–186.580**, BurstGPT **102.884–725.020**. Region names are inherited, not calibrated CM saturation labels.

Therefore the ANWG setting axis is a **combined arrival/deadline-stress transformation**, not a pure arrival-rate intervention. A falling ANWG cannot be attributed solely to greater queueing. For example, Azure chunked-FCFS at capacity 131072 has mean latency **2.7858 → 2.8269 s** and token throughput **3745.9 → 3746.3** from LOW to HIGH_PRESSURE, while ANWG falls **0.291375 → 0.112625**. The deadline transformation is essential to interpreting that contrast.

This is documented frozen behavior, not a newly detected execution defect. Preserve it and describe it accurately. No repair, protocol change or rerun is recommended. M3 must resolve this interpretation before making load-effect claims.

### 3.4 Rankings, reversals, ties and chronological sensitivity

A practical reversal requires opposite oriented signs and **strictly greater than 10% relative to the losing value at both endpoints**, compared exactly against the represented values. Zero losing values are unestimable; nonzero ties remain eligible. These totals combine the predeclared four-policy panel, eleven endpoints and dependent comparisons; they must not be interpreted as binomial trials or compared across axes as a causal effect-size decomposition.

| Comparison axis | Reversals | Eligible | All comparisons | Unestimable |
|---|---:|---:|---:|---:|
| Within-source window pairs | 34,394 | 1,847,700 | 1,853,280 | 5,580 |
| Cross-source window pairs | 109,913 | 3,788,640 | 3,801,600 | 12,960 |
| Inherited setting pairs within window | 920 | 236,853 | 237,600 | 747 |
| KV capacities within window/setting | 350 | 47,418 | 47,520 | 102 |
| Metric pairs within window/setting/KV | 11,795 | 473,580 | 475,200 | 1,620 |
| **Source-mean comparisons** | **0** | **2,376** | **2,376** | **0** |

**No source-mean comparison has a strict 10% practical reversal.** This does not mean source rankings are identical: of 396 source-pair/setting/KV/metric comparisons, **307** have equal exact top sets, **323** have intersecting top sets, and **247** have equal full average-rank vectors. Smaller sign changes and ties coexist with the zero practical-reversal finding.

Window-level heterogeneity remains substantial on selected endpoints. For ANWG alone, within-source comparisons yield **8,472/162,900** eligible reversals, cross-source window comparisons **35,352/332,640**, inherited-setting comparisons **603/20,853**, and KV comparisons **198/4,218**. Cross-source windows are a Cartesian comparison, not paired by ordinal. These are not reproductions of the original 36 historical reversals; policy identities, model and estimands differ.

The exact top set is tied in **425/1,440 ANWG**, **289/1,440 mean-latency**, **586/1,440 p95-latency**, **906/1,440 token-throughput**, and **1,440/1,440 completion** conditions. Across all 79,200 metric-pair ranking comparisons, exact top sets are equal in **27,915** and intersect in **57,602**. This includes redundant metrics and numerical TPOT distinctions; it is descriptive bookkeeping, not independent evidence of widespread instability.

All predeclared chronological summaries passed the independent aggregate check. Across four ten-window blocks × six settings × two capacities per source, SLO-gated minus chunked ANWG block means range:

| Source | Difference range | Negative block/setting/capacity combinations |
|---|---:|---:|
| Azure 2024 | −0.0120 to +0.2030 | 8/48 |
| Bailian/Qwen | −0.0300 to +0.2330 | 24/48 |
| BurstGPT | +0.0150 to +0.3275 | 0/48 |

The EARLY/MIDDLE/LATE summaries are consistent with that qualitative contrast: negative differences in **6/36 Azure**, **20/36 Bailian**, and **0/36 BurstGPT** stratum/setting/capacity combinations. The blocks/strata have unequal time spans and are not independent temporal samples. No temporal confidence interval or population stability claim follows.

## 4. STAT01 scientific findings

### 4.1 Completion and precision

Scenarios 3 (`exact_ties_null`) and 17 (`bounded_reversal_n400`) stop at **2,000** and **4,000** studies. The other sixteen have **8,000** each. Scenarios **0, 1, 2, 3, 16 and 17** meet the original precision objective at their final look; **4–15** reach the maximum count with gaps. Original stopping and counts are correct. Secondary methods do not drive stopping and can have inadequate precision. No extension is recommended; report the available bounds and inconclusiveness.

The original report yields **45 calibration-concern**, **74 inconclusive**, **9 empirical-compatibility-with-tolerance**, and **16 outside-domain-abstention** method/scenario outcomes. These 144 entries are dependent diagnostic classifications, not independent calibration trials or a score to optimize.

### 4.2 Complete scenario/method overview

Codes: **C** = calibration concern (FDR lower bound > .05 or ordinary-interval coverage upper bound < .95); **I** = inconclusive; **E** = empirical compatibility with the prespecified tolerance screen (FDR upper ≤ .06 and coverage lower ≥ .94); **A** = abstains outside its domain. These are the **original-eight-family** screens, not expanded-family certificates. “E” permits conservative overcoverage and does not mean exact nominal calibration.

H-S = frozen port screened BH; H-F = full-family BH; H-BY = historical plus-one BY; t = IID t-Holm; c-t = cluster t-Holm; O = covariance-oracle normal-Holm; G = grouped-bootstrap BY; Hf = bounded Hoeffding-Holm.

| Scenario (ID) | n | H-S | H-F | H-BY | t | c-t | O | G | Hf |
|---|---:|---|---|---|---|---|---|---|---|
| IID equal null (0) | 8000 | C | I | I | I | I | I | C | A |
| IID stable null (1) | 8000 | I | I | I | I | I | I | C | A |
| IID near-tie null (2) | 8000 | C | I | I | I | I | I | C | A |
| Exact ties (3) | 2000 | E | E | E | E | E | E | E | A |
| Practical boundary (4) | 8000 | C | I | I | I | I | I | C | A |
| Small sign reversal (5) | 8000 | C | I | I | I | I | I | C | A |
| Medium reversal (6) | 8000 | C | C | I | I | I | I | C | A |
| Large reversal (7) | 8000 | I | I | I | I | I | I | C | A |
| Independent-block null (8) | 8000 | C | C | C | C | I | I | C | A |
| Independent-block reversal (9) | 8000 | C | C | C | C | I | I | C | A |
| AR null (10) | 8000 | C | C | C | C | C | I | C | A |
| AR reversal (11) | 8000 | C | C | C | C | C | I | C | A |
| Unequal variances (12) | 8000 | I | I | I | I | I | I | C | A |
| Mixed distributions (13) | 8000 | I | I | I | I | I | I | C | A |
| MCAR reversal (14) | 8000 | I | I | I | I | I | I | C | A |
| Selective missingness null (15) | 8000 | C | C | C | C | I | C | C | A |
| Bounded reversal, n40 (16) | 8000 | I | I | I | I | I | I | C | E |
| Bounded reversal, n400 (17) | 4000 | I | I | I | I | I | I | I | E |

### 4.3 Supported conclusions, including negative results

**The historical-style discovery rule is not generally calibrated.** To avoid conflating the port and historical source, the following numbers use the explicitly added **`legacy_source_screened_BH`**, with its **expanded-seventeen-family bounds**. The method was added after diagnosis; these are fixed-amendment comparisons, not fresh prospective confirmation.

| Scenario | Practical FDR estimate | Expanded MC bounds | Ordinary diagnostic interval coverage |
|---|---:|---:|---:|
| IID equal null | 0.09025 | [0.06878, 0.11172] | 0.941875 |
| Practical boundary | 0.39500 | [0.36135, 0.42865] | 0.938375 |
| Medium reversal | 0.733158 | [0.71402, 0.75230] | 0.936000 |
| Independent-block null | 0.91800 | [0.89726, 0.93874] | 0.647625 |
| AR null | 0.980375 | [0.96780, 0.99295] | 0.564875 |
| AR reversal | 0.552760 | [0.53855, 0.56697] | 0.563500 |

The block/AR null results are particularly clear failures even with no true sign reversals. The practical-boundary/medium-reversal results also expose a target distinction: screening a noisy point estimate at 10% and testing against zero is not a calibrated test of a population effect exceeding 10%. This is a more important statistical issue than the floating boundary that originally stopped execution.

**Changing the multiplicity family is insufficient under temporal dependence.** The original full-family BH practical FDR is **0.51875** in the block null and **0.778625** in the AR null; its nominal interval coverage remains about **0.648** and **0.565**. Plus-one BY greatly reduces rejections in many scenarios, but it does not repair those interval coverages or identify selectively missing unconditional means.

**Assumption-aligned procedures show the expected limits, not a universal winner.** IID t-Holm has its finite-sample justification under Gaussian IID complete/MCAR paired samples; cluster t-Holm under Gaussian independent clusters; covariance-oracle normal-Holm under its known Gaussian covariance. Their nondegenerate assumption-valid coverage estimates are near .95, but the stringent simultaneous MC bounds generally do not establish the joint empirical-compatibility screen. They are **inconclusive**, not demonstrated miscalibrated merely because a lower bound lies below .94. The oracle is not deployable without its known covariance. Under AR dependence, fixed five-window cluster-t coverage is **0.8600** in the null and **0.864375** with reversal; the clusters are not independent there.

**Low false discovery can coexist with poor coverage or negligible power.** Group-bootstrap BY has ordinary-interval coverage **0.88775** in the IID equal null and **0.759875** in the AR null; no finite-sample guarantee was prespecified. In the block-reversal scenario, cluster-t practical power is approximately **0.00000658**, oracle-normal **0.000296**, and grouped-bootstrap **0**, despite low FDR. In the bounded scenarios, Hoeffding-Holm has **100% observed diagnostic coverage**, zero observed FDR, and power **0** at n40 versus **0.052632** at n400. Its original-family power bounds are approximately [0, 0.00401] and [0.04462, 0.06065]. These conservative results meet the compatibility screen but do not establish a useful generally powerful procedure.

Seven of the nine E entries are the degenerate exact-ties scenario; the other two are bounded Hoeffding. Thus the campaign does **not** deliver a broadly empirically certified replacement for historical inference. The correct manuscript consequence is to retain descriptive common-model claims and reject unsupported historical significance claims.

**Missingness and denominators matter.** In the MCAR scenario, cluster-t ordinary coverage is based on **1,676/8,000** studies emitting an interval; in selective missingness it is **202/8,000**. The latter wide bound is not evidence that selective missingness is harmless. Historical selected-interval coverage is a different endpoint: in the IID equal null it is **0.123834**, averaged over **958 studies with selected intervals**, while the unconditional fixed-contrast diagnostic coverage is **0.941875** over 8,000 studies. Do not pool selected intervals as independent observations or substitute the unconditional coverage for the selected result.

### 4.4 Legacy versus exact additions

The 31 differences identified in the original 112,275-study reuse audit remain recorded as differences between the frozen port and actual historical source, not invalid raw studies. At final aggregation, the largest legacy-versus-port difference among reported endpoint means is **0.00025**. Only `exact_historical_screened_BH` has changed final endpoint means relative to its original method, with maximum change **8.56e-7**; the other seven exact-method endpoint means match their originals. Aggregate equality alone does not prove every individual rejection vector is identical; no such claim is made.

The saved original failing case is independently confirmed in §2.3. None of these small arithmetic differences repairs the large FDR/coverage problems. The 17-method uncertainty expansion is correctly separated from the eight-method reports, but does not erase post-diagnosis selection. Exact threshold comparisons are a numerical definition, not a remedy for invalid p-values, screening, serial dependence, missingness or mismatch between sign and practical-effect truth.

Synthetic calibration does not transfer automatically to historical traces: the 18 generators specify distributions, covariance, missingness and latent truth; the trace windows are selected, temporally related and have no corresponding known population truth. C01 is deterministic finite-corpus description and needs no FDR claim. No historical trace discovery is retroactively validated by these simulations.

## 5. Strongest contribution and readiness decision

### Five principal findings

1. **Stable source-mean practical comparisons coexist with window and metric heterogeneity.** There are zero source-mean strict-10% reversals, but nonzero predeclared window/metric reversals. The paper must distinguish aggregation levels instead of claiming that source rankings generally reverse.
2. **A concrete mean/tail/throughput trade-off survives complete accounting.** SLO-gated improves aggregate mean latency but loses throughput; on BurstGPT its average p95 is worse. All requests complete, so this trade-off is not a completion-survivorship artifact in this corpus.
3. **Model constraints collapse some nominal scheduling distinctions.** Two policies are exactly equivalent here, the urgency gate does not bind, and capacity acts through full-context reservations. These constrain interpretation and explain several predictable outcomes; they are not independent algorithmic innovations.
4. **Rank reporting needs exact identities and practical magnitudes.** Completion/throughput redundancy and sub-femtosecond TPOT distinctions show why counting nominal endpoints or exact winners can exaggerate substantive differences. The frozen sensitivity and absolute metrics already resolve the issue without changing the experiment.
5. **Historical inferential claims fail under explicit synthetic cases.** The numerical implementation repair preserves scientific evidence, but major calibration failures persist. This supports a scoped diagnostic and withdrawal of broad FDR/significance language, not a new universal inference method.

Relative to the prior work reviewed in PR #16, the defensible contribution is a completely traceable **finite-corpus comparison under a shared synthetic contract**, with all conditions retained, quantified performance trade-offs, and explicit separation of comparison validity from inferential validity. It is not discovery of workload dependence, a new ranking statistic, or a superior predictive simulator. Related workload-choice evaluations and profiled simulators remain direct precedents and must be credited. Related LSSP mechanism/headroom studies address different estimands and cannot supply this experiment's native validation.

**Candid strength assessment:** sufficient for a defensible ToMPECS submission attempt after careful rewriting, but moderate rather than decisive novelty. The positive contribution is narrower than the earlier narrative anticipated. A paper claiming broad ranking instability or “four mechanisms validated across 11 independent metrics” would be weak and misleading. A paper explaining the actual trade-offs, invariances, aggregation limits and evidence boundaries is stronger. Acceptance is not assured; another experiment is not recommended.

| Dimension | Assessment |
|---|---|
| Execution completion | Complete for both frozen campaigns. |
| Artifact/conformance validity | Required in-job checks completed; fresh full identity/summary checks and sampled raw checks pass. No detected critical integrity issue. |
| Scientific validity | Supports bounded CM-0.1 finite-corpus descriptions and scenario-specific STAT01 diagnostics. Does not support native or general calibration claims. |
| Contribution strength | Defensible, focused empirical contribution with important null/structural limitations; modest methodological novelty. |
| Rewrite readiness | **READY_WITH_LIMITATIONS — begin M3 after author review.** |
| Final submission readiness | Not yet: writing, provenance/reviewer access, citation/overlap disclosures and current journal requirements remain. |

### P0 audit closure status

| Audit issue | Status after this review | Remaining resolution; no new experiment |
|---|---|---|
| P0-1 — comparison object and completed evidence | **Experimental availability/validation gate resolved.** Shared-contract results are now complete; historical/native equivalence remains unsupported. | Rewrite the central claim and retain model/adaptation identities. |
| P0-2 — inference and implementation identities | **Evidence gate resolved; manuscript correction required.** Final calibration diagnostics and separated numerical definitions are available. | Remove historical FDR guarantees; label original, legacy-source and exact additions and their different uncertainty families. |
| P0-3 — estimand/unit/conditions | **Partly resolved.** Complete support, ties, censoring and denominators are checked. The combined arrival/deadline transformation now needs explicit treatment. | Writing and existing-data reporting; preserve window units, inherited-region labels and descriptive comparisons. |
| P0-4 — reproducibility/provenance/access | **Internal run provenance substantially resolved; submission gate open.** Frozen hashes and reuse agree. | Verify source licenses, reviewer access, archival identities and the scope of reproducibility claims. |
| P0-5 — overlap/status disclosure | **Open.** No new editorial-status evidence was supplied by the completed campaigns. | Author confirms related manuscripts' status; update the stale overlap ledger and document shared windows/code/results. |
| P0-6 — current journal requirements/declarations | **Open.** This results review does not resolve the audit's inaccessible official ToMPECS instructions. | Current official-format/policy check and author declarations; do not infer a page limit from previous builds. |

No P0 can be declared wholly closed in the still-unchanged M2 text. P0-1 and P0-2 now have the necessary experimental evidence; their remaining work is editorial. The new deadline interpretation is a writing/estimand issue, not a reason to alter frozen data. No additional scientific evidence is required for the recommended bounded scope.

## 6. Concise results-to-manuscript map

**Recommended title:** *Scheduler Rankings and Performance Trade-offs in a Common-Model LLM-Serving Evaluation*.

| Main RQ | Principal verified answer | Core display |
|---|---|---|
| RQ1. How do absolute adaptation performances vary across frozen windows, inherited arrival/deadline settings and KV reservations? | All requests complete; SLO-gated lowers mean latency but trades off throughput/tails; doubling reservation capacity changes residency and improves these aggregates. Chunked/decode-first are equivalent here. | Contract/adaptation table; absolute-performance panels by source, setting and capacity; matched-window difference distributions. |
| RQ2. How do aggregation, metric choice and reporting conventions affect rankings and practical reversals? | Zero source-mean strict-10% reversals, nonzero window/metric reversals, many exact ties, redundant throughput ranks and numerical TPOT distinctions. Chronological blocks show source-specific heterogeneity. | Reversal numerator/denominator table, exact/near-tie summary, one chronological block panel; retain all metrics in the supplement. |
| RQ3. What do the historical and synthetic audits permit us to infer from these comparisons? | Historical numerical reproducibility does not imply scheduling comparability or calibrated inference; legacy-source FDR can be inflated even under the IID null and much more under dependence. Arithmetic correction is not statistical repair. | Compact evidence-strata/claim-boundary table and a small representative calibration panel, with all scenarios in the appendix. |

**Main-text historical material:** one comparability table explaining policy-dependent old timing/KV rules; the old 36/990 count only as an archived-rule motivation, explicitly not a confirmed population effect or reproduced CM phenomenon. Full old policy tables, interval replication, physical-engine failure history, descriptor fits and finite-reference recovery should remain supplementary. Do not combine historical and CM outcomes into a single leaderboard.

**STAT01 placement:** a short main-text diagnostic subsection explaining why the common-model analysis is descriptive, with the IID/block/AR null examples and the original-versus-legacy distinction. Put the full 18 × 17 endpoint/scenario results, numerical boundary details, precision/stopping table and uncertainty derivation in an appendix/artifact. Its negative evidence is important, but making calibration a second main paper would dilute the performance-evaluation contribution.

**Most useful figures/tables:** (1) execution/information/reservation contract and adaptation lineage; (2) absolute mean/tail latency, throughput and ANWG small multiples; (3) matched-window mean-versus-tail/throughput differences; (4) practical reversal counts separated by aggregation axis with ties/zero-denominator counts; (5) compact calibration diagnostic, with complete grids supplementary. Source/setting/KV strata and all negative findings remain accessible. No fabricated error bars or confidence levels for C01.

**M2 claims to rewrite/remove:**

- Replace an undifferentiated “reproducible comparison methodology” claim with the specific shared-contract evaluation and its measured trade-offs.
- Remove any suggestion that the original 36 reversals persist under CM-0.1 or establish native scheduler ordering.
- Replace pure “load effect” language for ANWG with the documented combined arrival/deadline stress; retain inherited labels as labels.
- Do not describe the SLO-gated advantage as evidence for an active deadline-aware/SLAI mechanism, or equivalent chunked/decode-first adaptations as distinct observed strategies.
- Keep original exact ranks but explain practical insignificance of tiny TPOT differences and duplication among throughput endpoints.
- Replace nominal statistical support and historical FDR guarantees with archived-rule counts and the validated synthetic calibration limitations.
- Keep finite-reference recovery out of claims about population sample complexity; remove unanswered native transfer/provider-causality RQs.

### Proposed abstract structure — verified numbers only

This is an outline, not an M3 abstract draft:

1. **Problem:** comparative scheduler rankings require an identified workload, metric and execution contract; historical comparisons mixed these elements.
2. **Design:** 120 frozen 200-request windows, three sources, six inherited arrival/deadline settings, four adaptations and two reservation capacities; **5,760 validated cells**, including **144 reused** pilot cells. Synthetic CPU discrete-event model, descriptive equal-window analysis.
3. **Main result:** all cells complete all requests; two adaptations have identical records in **1,440/1,440** matched conditions. SLO-gated lowers the six source/capacity aggregate mean latencies by **11.3–34.0%** versus chunked-FCFS while lowering throughput by **1.65–4.01%**; BurstGPT mean window-p95 rises **3.72%/18.97%** at the two capacities.
4. **Ranking result:** **0/2,376** source-mean strict-10% reversals, alongside **34,394/1,847,700** eligible within-source-window comparisons and **11,795/473,580** eligible metric comparisons meeting the rule. If space is tight, retain the null source-mean result and describe heterogeneity qualitatively rather than overload the abstract with dependent pair counts.
5. **Inference boundary:** **134,000** synthetic calibration studies show that arithmetic fidelity does not confer error control; if one number is retained, identify the legacy-source IID-null FDR **0.09025** and its scope. Conclude with finite-corpus/model validity, not native GPU performance or general guarantees.

## 7. Supporting evidence, exact paths and verification limits

### Persistent Wulver evidence

C01 root:

`/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-c01-full-20261022/`

- `launch.json`, `reuse_index.json`, `research/lssp-c01-full/PROTOCOL.md`, `input_manifest.json`, `campaign.py`, `verify_analysis.py` (the latter four under `research/lssp-c01-full/`).
- `inputs/full-inputs.json`, `inputs/phase12-freeze.json`, `research/lssp-c01/policies.py`, `validator.py` (validator under `research/lssp-c01/`).
- `src/robustbench/calibration/stage0_load_calibration.py:59–95` for arrival/deadline scaling.
- `runs/c01-full-167b9074e5711420/checkpoint.json`, `complete.json`, `slurm.exit`, `cells/*/{result.json,events.jsonl.gz}`; reused cells under `reused/`.
- `runs/c01-full-167b9074e5711420/analysis/{absolute_metrics,pairwise,rankings,ranking_frequencies,window_aggregates,source_mean_rankings,reversals,independent_analysis_validation}.json`.
- `logs/c01-full-167b9074e5711420-1440402.out` and `.err`.

STAT01 root:

`/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-stat01-recovery-v2-20261022/`

- `launch.json`, `source-batches.json`, `source-audit.json`, `code/AMENDMENT.md`, `code/rv2_run.py`, `code/rv2_reference.py`, `code/rv2_methods.py`, `code/rv2_summary.py`.
- `runs/stat01-recovery-v2-061933a64e27da20/{checkpoint,completion}.json`, `slurm.exit`, and `look-sXX-nNNNNN.json` for every completed precision look.
- `runs/stat01-recovery-v2-061933a64e27da20/batches/scenario-XX/rep-NNNNNN/{raw.npz,studies.json.gz,secondary.json.gz,integrity.json}`.
- Original failure's recovered batch: `runs/stat01-recovery-v2-061933a64e27da20/batches/scenario-11/rep-006625/`, zero-based element 3.
- `logs/tests-pinned.txt`, `logs/preflight.txt`, `logs/stat01-recovery-v2-061933a64e27da20-1440206.out` and `.err`.
- Unchanged original code/reference/source root: `/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-stat01-454168a00524/`.

### Review evidence retained on the workstation

`/home/soroush/lssp-m3-final-review-evidence-20261022/`

This directory contains read-only-source copies used by the review, transfer archives, the review scripts and their outputs. It is outside the Git worktree; only this Markdown report is committed.

| Review evidence | Purpose |
|---|---|
| `check_c01.py`, `c01-record-check.json` | All launch/input/result fingerprints, identities, reuse and terminal-metric checks. |
| `c01-independent-summary-check.json` | Fresh complete `verify_analysis.verify` result against saved absolute rows and reports. |
| `check_c01_journals.py`, `c01-journal-sample-index.json`, `c01-sample-event-check.json` | Exact selection and fresh replay of 24 new-cell journals. |
| `check_stat_inventory.py`, `stat-inventory-check.json` | Complete batch/provenance inventory, independent decimal moment/bound calculation and stop/screen checks. |
| `check_stat_samples.py`, `stat-sample-check.json` | 200 saved-record referee checks, historical-source fidelity and original failure. |
| `analyze_c01.py`, `c01-findings.txt`; `analyze_stat.py`, `stat-findings.txt`, `stat-final-methods.json` | Reproducible saved-summary extraction for the main numerical review. |

The local checks only read experimental copies and write review outputs. They do not call the simulator or synthetic-study generator. Full event replay, if ever requested for a new external review, should be performed on suitable compute resources; this report does not authorize another allocation. Existing exhaustive in-job validation was sufficient to avoid that dependency here.

Selected SHA-256 anchors:

| Artifact | SHA-256 |
|---|---|
| C01 `complete.json` | `11c9c08432878932c0fca0501b2befd83f333dedf2686d3a5693d27a7a3fea72` |
| C01 independent analysis validation | `c48c0b8472c49309a0f7f3227ed2ea40c50345bfc93baa44d4f7347ae160df70` |
| C01 absolute metrics | `5700c4bbd7386b7227d678b6b09a715010c29ccdbdb8654e7dd93bde1c585666` |
| STAT01 `completion.json` | `a658e16039d5a9be8b496792e038637df1cdf7507ff16b7de3411a79ac15e01e` |
| STAT01 final checkpoint | `a261866365b74bd6b240fb1916a0ce3c4bbc8ee76d08097b9dcb2048dc693c13` |
| Fresh C01 record-check result | `299af051c09f60acfec655f49ec968ecb98e90ed19467419c40ac77c78299dcf` |
| Fresh STAT01 inventory-check result | `e99f86351448072f1f298e93dcc4f57eb8ea6abe47a57d54ad54907c5d3ab8e6` |
| Fresh STAT01 sample-check result | `c0b8644a43292c6021d2fc62c3a4093e979ad3b8156106fe4737db9e2cadb0a5` |

**Stop point:** author review of this report, then authorization for M3 rewriting. No additional experiments, job submissions, protocol changes, Actions runs, PR merges or manuscript rewrite were performed. The existing hydrated-LFS anomaly is preserved outside this report-only change. Current author instructions, access/licensing, related-paper status and final manuscript claims remain submission tasks; they do not require another scientific campaign.
