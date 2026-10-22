# M2 independent statistical adjudication

Verdict: **numerical reproduction passes; calibrated significance/FDR claims do not pass.** Retain the finite-corpus descriptive findings, with historical labels distinguished from inference. **NO-GO for interpreting these as isolated native scheduler effects or physically validated ranking portability.** This does not make the arithmetic descriptions of the frozen implementations meaningless.

Audit base: PR #9, `366752a76f86dec30190f3e7767124f684378de4`, verified with both GitHub PR metadata and `git ls-remote` before creating the M2 worktree. M1 remains intact. All new computation is CPU-only, post hoc, on preserved outcomes; no new simulation, serving measurement, or external CI execution.

## Evidence and independence

`evidence/statistical-audit.json` contains exact input paths, SHA-256, software versions and summaries. `scripts/audit.py` imports NumPy/SciPy primitives but no production analysis functions. It reconstructs arrays directly from rep0 of the 18,720-cell frozen JSON; deterministic rep equality is independently covered by M1 and the release validator. The independent tau implementation uses policy-pair signs and is checked against SciPy. Friedman is reconstructed from rank sums and tie correction, then cross-checked against SciPy and saved records. `scripts/additional_checks.py` independently reconstructs the primary taxonomy and margins from raw aggregates.

The complete M1 review-package inventory is in `evidence/m1-review-inventory.json`; the review included its entry README, every review ledger, actual revised manuscript, relevant analysis/build scripts, recorded numerical and validation results, source lineage and full PDF text. Archived baseline and intermediate files are preserved. Inventory/parsing of archival logs is not a claim of independent bibliographic verification or new reproduction of every archived experiment.

| Check | Outcome | Evidence |
|---|---|---|
| Source-ranking tau-b intervals | 198/198 reproduced, including all 18 primary | `ranking-intervals.json` |
| Primary saved-supported difference intervals and tail values | 72/72 reproduced, 36 records | `primary-reversal-intervals.json` |
| Primary classifications, differences and margins | 990/990 reconstructed | `additional-checks.json` |
| Cross-metric point tau and ID agreement | 990/990 reproduced | `cross-metric-sets-and-matched.json` |
| Cross-metric difference intervals and tail values | 6,890/6,890 reproduced, all 3,445 records reaching the interval stage | `cross-metric-difference-intervals.json` |
| Cross-metric rank intervals | 6/6 reproduced: ANWG/mean latency, LOW/HIGH_PRESSURE, all sources | `cross-metric-intervals.json` |
| Friedman statistics, tail probabilities, exclusions and dimensions | 66/66 reproduced | `friedman-audit.json`, `friedman-inputs.json` |
| Historical reversal BH flags | No mismatches: primary and cross-metric | `multiplicity-families.json`, summary |

“Reproduced” means `rtol=1e-10, atol=1e-12`; no claim of new coverage calibration. The audit does not rerun all 990 cross-metric rank intervals, nonprimary cross-source reversal intervals, temporal intervals, SLO extension simulations, or sample-recovery draws. It does reproduce the important saved manuscript intervals and the entire cross-metric pairwise interval stage. No unresolved numerical mismatch was found in those checks.

## 1. Window bootstrap, seeds and coverage

The primary pipeline uses `numpy.random.default_rng(0)` (PCG64), **one shared stream**, not an independent seed per table row. It consumes all 198 source-ranking comparisons, in contract metric order, six-region order and lexicographic source-pair order, before primary reversal resampling. Within a comparison it alternates 40-window source draws; the pairwise stage draws 2,000 samples of matched per-window differences for each side. The order of windows inherited from consolidated cells matters. A recorded seed without the stream's preceding consumption, array order and generator is insufficient to reproduce an arbitrary interval in isolation.

M2 uses the same index stream in vectorized arrays and independently computes mean policy outcomes, tau-b and percentile endpoints. Missing conditional values are skipped per policy as in the historical aggregation. Every source/region has all 40 window IDs represented by at least one policy; the ranking code discards draws whose policy vector is constant and hence tau is undefined. This occurs in 30/198 comparisons, totaling 3,287 discarded draws, with at most 277/2,000 in a condition. For primary ANWG the Azure–BurstGPT and Bailian–BurstGPT LOW comparisons discard 10 and 12 draws respectively. Their nominal intervals therefore use 1,990 and 1,988 valid draws. Primary ANWG has no missing cell values: undefined resampled rank statistics are a different issue. Conditioning on defined resamples is an additional coverage qualification.

The cross-metric extension hashes `source|region|metric_a|metric_b` with CRC32 for rank intervals and appends policy IDs and side `a`/`b` for difference intervals. The rank bootstrap uses the same sampled windows for both metrics. **The pairwise difference bootstraps do not**: they use separate marginal streams. This corrects M1's overly general statement that cross-metric bootstraps always share a sequence. Separate marginal intervals are reproducible; they do not estimate a joint cross-metric distribution.

Percentile intervals are nominal central 95% resampling intervals, not established 95% confidence coverage. They require a defensible sampling target, window exchangeability/independence appropriate to the bootstrap, and suitable regularity. With only 11 policies, rank correlation is discrete and discontinuous at equal means; there are substantial exact ties. Boundary/degenerate endpoints such as 1.000 are not coverage evidence. Deterministic rep1 adds no stochastic degrees of freedom. We have not estimated population coverage from this single selected corpus.

## 2. Reversal taxonomy, margins, IUT and multiplicity

The strict sequence is undefined/margin-unestimable → same sign/tie → opposite signs but at least one margin ≤10% → interval stage. The relative margin is the absolute difference divided by the absolute losing policy value (after direction normalization for cross-metric analysis). A nonzero difference with zero loser is unestimable, not an infinite practical pass. The threshold is strictly greater than 10%, not greater than or equal. The point-margin rule neither tests a population 10% effect nor supplies an uncertainty bound for that ratio.

All 990 primary records reproduce: 906 stable, 48 microscopic and 36 saved-supported; none undefined or wide-interval. Five policy pairs account for 36 records, with shared data and many overlapping comparisons. The class's name remains an immutable data label, not a verified statistical conclusion. Stable and microscopic rows generally have no intervals; they cannot be called statistically nonsignificant by default.

The quantity called a “two-sided sign test” in production code is `min(1, 2 min(mean(bootstrap_mean <= 0), mean(bootstrap_mean >= 0)))`. It is **not** an exact binomial sign test, and does not use a centered/null bootstrap. Its null calibration is not established here. `max(p_x,p_y)` is an intersection-union combination only under valid component tests for the intended component nulls. Two nonzero differences are also not the same hypothesis as a specified directional reversal exceeding a practical population margin. Data-selected signs and margins complicate that interpretation.

BH uses only records passing the same-data sign/margin screens: six primary families of at most 165 possible records, and 990 cross-metric families of at most 55 records. Independence or positive regression dependence of valid null p-values has not been established. Screening changes family size and the null distribution among retained tests. An ordinary BH calculation on selected bootstrap tail fractions therefore does **not** justify either global or within-family 5% FDR control. The maximum combination itself does not require independence if the component p-values are valid; the failure here is not simply that its two sides are dependent.

Primary empirical two-sided values have resolution 0.001; 30/36 combined values are zero. Zero tail draws cannot mean zero error probability. Adding more draws addresses Monte Carlo resolution, not the sampling/null/selection assumptions.

### Post-hoc arithmetic sensitivity (not discovery inference)

| Interpretation applied to saved tail fractions | Primary saved-supported passing | Cross-metric saved-supported passing |
|---|---:|---:|
| Historical screened-family BH | 36 | 3,207 |
| Full enumerated family; untested placeholders=1 | 30 | 3,006 |
| Same full family, each tail count +1 / 2,001, then double and cap | 30 | 2,971 |
| Same +1/full family with BY harmonic-factor adjustment | 0 | 1,940 |

The placeholders only preserve enumeration in this sensitivity. They are not newly calculated p-values for the skipped comparisons. The plus-one step is `min(1,(2000*p+2)/2001)` for each two-sided tail value, minimum `2/2001`. The BY factor is the harmonic sum over the full family. **None of these columns is endorsed as calibrated FDR control**, including the zero-primary column; BY also needs valid component p-values. The sensitivity is not a reason to select the most favorable column.

A separate point-margin sensitivity, with no new interval stages, finds 42/36/30/26 opposite-sign records exceeding 5%/10%/15%/20% in both conditions. Only 10% is historical. These are point-gate counts, not alternative supported-reversal counts; six newly eligible at 5% do not acquire intervals by implication. This bounded check is in the audit package, not substituted into the paper's headline.

## 3. The 66 Friedman records

Exact matrices are in `friedman-inputs.json`, with window IDs, policy columns and values for each metric/region. Blocks are all **120 pooled windows**, one observation per policy after rep collapse. Sources are not treatments. The code retains a policy only if present and defined in every block: 18 always-defined metric/region records have 11 treatments; 48 conditional records have 10, excluding `vllm_faithful`. No pooled conditional omnibus therefore includes the primary policy that suffers zero completions.

M2 independently ranks each block (average ranks for ties), computes
`Q = [12/(n*k*(k+1))*sum_j R_j^2 - 3*n*(k+1)] / C`,
with `C = 1 - sum_blocks,sum_ties(t^3-t)/(n*(k^3-k))`, and evaluates the chi-square tail with `k-1` degrees of freedom. All saved statistics, p-values, n/k and exclusion lists match; the p range is approximately 2.26e-194 to 2.38e-126. Six-region BH within each metric rejects all because these arithmetic values are tiny. Small values do not overcome model assumptions.

Under the relevant block-design/null assumptions Friedman concerns differences among policy rank distributions/average ranks pooled over windows. It is **not a source-by-policy interaction or rank-portability test**. A uniform policy advantage across all sources can yield a large statistic with no reversal; changes can cancel in pooled average ranks. The analysis computes Friedman first but does not gate or otherwise calibrate subsequent pairwise tests using it. It does not establish the five-pair reversal conclusion.

Assumptions include independent blocks, meaningful comparable responses within blocks and a suitable repeated-measures/null approximation. Source/session dependence and implementation comparability remain open. Completeness achieved by dropping a policy changes the panel and limits the relation to pairwise results. See [SciPy's definition and approximation caveats](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.friedmanchisquare.html) and [Demšar's primary comparative-methods paper](https://jmlr.org/papers/v7/demsar06a.html).

The saved Kendall and Spearman analytic p-values operate over policy coordinates and test association of those vectors. They are not window-sampling p-values. The selected, related policy implementations are not random independent draws from a population of policies. M2 does not use those analytic significance flags as portability evidence.

## 4. Dependence and external validity

All 40 windows/source come from one source file. Native valid-row ranges do not overlap; minimum gaps are 13,437 Azure, 194 Bailian and 4,785 BurstGPT rows. Maximum gaps differ greatly (see `additional-checks.json`); these are irregularly spaced selected windows, not a dense stationary time series. Frozen sampler seeds and nonoverlap prove reproducible selection, not temporal/session independence or representative random sampling. Pilot reuse (10 windows/source) also precludes calling this an independent replication of the pilot.

Azure and BurstGPT share infrastructure lineage, while Bailian comes from Alibaba. Separate publication is not independent provider sampling. Cross-source draws treat each collection separately without estimating possible shared environmental dependence. Within a window, policies, metrics and transformed load regions share inputs; comparison families overlap in sources and policy pairs. These reuse structures invalidate any interpretation of 990 or 54,450 as independent sample sizes.

**Post-hoc stress test:** group consecutive valid-row-ordered selected windows into eight nonoverlapping groups of five; resample groups, keeping paired policy differences, for 2,000 draws. Seed `20261022 + 2*record_index + side_index` is recorded per row. Thirty of 36 records retain zero-excluding intervals on both sides. This tests one plausible stronger-dependence grouping, not an optimized block length or validated coverage estimate. All 36 rows are reported, including losses. It cannot estimate provider-level variance from two infrastructure lineages. No independence claim is inferred from persistence.

## 5. Missingness and matched support

The 48 primary zero-completion configurations are all `vllm_faithful`: seven Azure and one Bailian window in each region. Its completion-conditioned means use 33/39 windows; other policies generally use 40. ANWG is complete. An undefined conditional metric is an informative consequence of no completion, not missing at random.

Historical point differences are differences of separately observed means. Historical bootstrap differences are averages of paired differences on observed intersections. **Those are different estimands** when support differs. Hence the latter intervals cannot be presented as confidence intervals for the former. The raw missingness is not an arithmetic defect; joining a point estimate to an interval for a different target is an inferential defect.

Two explicitly separate M2 diagnostics:

* Common-panel, two-metric support: every policy has both metrics on a retained window. 366 conditions retain 40 windows, 312 retain 33, and 312 retain 39. Median tau is 0.4184886007 (historical rounded median 0.419), 202 remain negative, ID agreement stays 316/990, and 81 individual taus change.
* Pairwise support: within each metric, use windows observed for both policies. Differences change in 5,890/54,450 records, including 2,720/3,244 saved-supported records. None of the 3,244 loses the opposite-sign/both-10% point gates; none of the affected saved-supported cases has a matched sign opposed to its saved interval. Full affected records are retained. New interval-stage eligibility is not treated as a new discovery count.

These checks do not remove survivorship: even on the same window, different policies complete different requests. No assumption identifies unobserved latency for a policy that completes none. Report conditional and arrival-based objectives separately.

## 6. Ties and 31.9% agreement

Historical top choice uses value then lexicographic policy ID. Exactly reproducing 316/990 is therefore computationally correct but cannot establish 68.1% disagreement of unique optima. There are 1,010 tied sides of 1,980. Post-hoc exact-maximizer sets intersect in 572/990 (57.8%), are equal in 179/990 (18.1%), and have mean Jaccard overlap 0.32935. Only 257 conditions have unique optima on both sides (97 of those agree). These are alternative questions, not corrections to the historical 316 count. Exact ties are used; no epsilon selected after inspecting outcomes.

## Scientific dispositions

* Retain primary tau points, historical interval endpoints, taxonomy counts and frozen metric/SLO results with bounded labels.
* Withdraw “statistically supported at 95%” and verified within-family FDR language. Reproducible nominal intervals are not calibrated confidence statements here.
* Remove pooled Friedman as evidence of source ranking heterogeneity. Retain its existence, inputs, arithmetic and restricted interpretation.
* Keep the missing-support mismatch visible even though descriptive practical gates persist in this corpus.
* Treat native-policy superiority, faithful reversal transfer and isolated scheduler effects as **NO-GO**. Policy-specific instant/prefill-aware service modes and KV enforcement mix scheduler behavior with model differences. No frozen-outcome reanalysis identifies a counterfactual common service model.
* A conditional historical simulator case study remains defensible. Whether that narrower contribution warrants ToMPECS acceptance is a separate, currently unfavorable referee judgment.

The dependency discussion is grounded in the [Benjamini–Yekutieli primary paper](https://doi.org/10.1214/aos/1013699998), rather than a claim that arbitrary dependence can always be fixed by applying BH. Workload resampling precedent has a different unit and structural preservation strategy ([Zakay–Feitelson, ICPE 2013](https://research.spec.org/icpe_proceedings/2013/proceedings/p149.pdf)); its validity does not transfer automatically to LSSP windows. Reproduction commands, failed-development diagnostics and environment are in `VALIDATION.md`.
