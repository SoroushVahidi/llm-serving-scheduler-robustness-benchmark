# Claim-to-evidence register — M1

**VERIFIED** means the stated bounded fact was checked against the specified preserved data or source. It does not mean population validity or physical fidelity. **DISPUTED** means prose conflicts with evidence or overstates it. **UNVERIFIED** means evidence/analysis is missing or not independently checked in this phase. No frozen data was changed.

Paths below are repository-relative unless marked external. `D` = `dataset/v1.1.0`; `A` = `D/scientific/analysis`; `M` = `D/manifests`; `E` = `paper/tompecs-m1/evidence`. Input bytes/hashes and full external paths are in `E/numerical-audit.json`. This supersedes stale manuscript claim ledgers for M1 review only.

| ID | Claim / scope | Status | Exact evidence and check | Draft disposition |
|---|---|---|---|---|
| C01 | Three sources, 40 windows each, 200 requests/window | VERIFIED | `M/ranking_portability_pilot_v2_windows_index.json`, all 120 records | Retained |
| C02 | 13 executed policies, 11 primary + two style approximations; six regions | VERIFIED | `D/data/tables/policy_registry.parquet`, `D/scientific/campaign/consolidated.json`, `E/numerical-audit.json` | Separate execution and ranking panels |
| C03 | 9,360 configurations / 18,720 successful unique executions | VERIFIED | Entire campaign key set and success fields; release validator | Retained; no calibration or extensions added to denominator |
| C04 | rep0/rep1 are independent stochastic replications | DISPUTED | 9,360 pairs have identical scientific numeric/telemetry fields; frozen deterministic design | Explicitly determinism verification, window resampling only |
| C05 | All numerical/telemetry repetition pairs match | VERIFIED | `audit.py`, exact JSON/NaN-aware field comparison; dataset validator | Retained; not every provenance byte claimed identical |
| C06 | 18 ANWG Kendall point estimates, 0.551–1.000 | VERIFIED | Independently average original cell values and call scipy tau-b; all 18 match `A/ranking_correlations.json` | Full saved CI table; intervals not regenerated |
| C07 | 906 stable, 48 microscopic, 36 supported / 990 | VERIFIED | `A/pairwise_reversals.json`; independent classification from stored margins/CIs; differences independently match matrix | Retained |
| C08 | All 36 supported reversals belong to one policy pair | DISPUTED | Counter over original 36 records: SLAI–vLLM 10; Sarathi–SLAI 9; chunked-vLLM–SLAI 9; Sarathi–vLLM 4; chunked-vLLM–vLLM 4 | Corrected to five pairs in abstract/results |
| C09 | All 36 involve BurstGPT; region counts 0/6/6/6/10/8 | VERIFIED | Original conditions/regions in `A/pairwise_reversals.json` | Retained; no physical interpretation |
| C10 | All 36 carry the saved FDR support flag | VERIFIED | `supported_after_fdr` fields | Describes recorded procedure; no global/type-I guarantee |
| C11 | Practical and statistical criteria never disagree because wide-CI class is zero | DISPUTED | `src/robustbench/ranking_portability/analysis/reversal_analysis.py` stops before CI evaluation for microscopic records | Remove converse inference |
| C12 | Friedman omnibus was never implemented | DISPUTED | `A/ranking_correlations.json` contains 66 omnibus records; `analysis/stats.py: friedman_omnibus` | Corrected; no fresh omnibus analysis claimed |
| C13 | Calibration had 301/720 zero-completion records | DISPUTED | `M/ranking_portability_phase11_raw_fifo_calibration.json`: 720 rows, **0** with completion_fraction=0 | Corrected to preserved-file observation; historical prose discrepancy retained here |
| C14 | Calibration zero completions imply missing outcomes for all policies | DISPUTED | Calibration and campaign are different records/configurations | Remove inference; report actual campaign count |
| C15 | Campaign zero-completion unique configs: 211 overall, 48 primary | VERIFIED | All rep0 records; 422 rows with both passes | Explicit missing-observation scope |
| C16 | Chronology counts 60/30/30 apply to BurstGPT | DISPUTED | Index: 60/30/30 across all sources; **20/10/10 per source** | Corrected |
| C17 | Temporal correlations uniformly high | DISPUTED | `A/temporal_robustness.json`: BurstGPT tercile range includes −0.10 at LOW; other source/split ranges retained | Preserve negative exception; no pooling |
| C18 | Cross-metric median tau 0.419, 202 negative, top-1 316/990 | VERIFIED | External `cross_metric_correlations.json`; all 990 point estimates/top choices independently reconstructed from campaign, no mismatches | Explicit post-campaign analysis |
| C19 | 31.9% top-1 agreement means unique best policies disagree 68.1% | DISPUTED | Stable ID tie break in `analysis/stats.py`; 1,010/1,980 metric sides have tied maxima | Describe deterministic top-choice agreement, not unique optima |
| C20 | 54,450 metric-pair/policy-pair records: 3,244 raw supported, 3,207 FDR-supported | VERIFIED | External `cross_metric_pairwise_disagreements.json`; class counts 45,800/5,205/201/3,244 | Record-level tally, not independent sample size or rederived CI |
| C21 | No aggregate cross-metric comparison is undefined | VERIFIED | 990 saved OK conditions and point reconstruction | Does not mean no missing policy/window values |
| C22 | Source-out means 0.948 / 0.633 / 0.618 tied to the named omitted sources | DISPUTED | `A/telemetry_explanation.json/robustness/strata`: omit BurstGPT .948009; omit Azure .618254; omit Bailian .632556 | Correct swapped Azure/Bailian assignments |
| C23 | Family-exclusion mean range .707–.792; four-region .728 vs .733 | VERIFIED | Means from actual robustness strata in same file, now captured in numerical audit | Retained; not new executions |
| C24 | Metric-definition sensitivity implemented | DISPUTED | Component-status metadata says true; no corresponding result stratum or implementing calculation; generated table-data notes gap | No result asserted; conflict disclosed |
| C25 | Finite-reference recovery: first ≥.9 exact n=30 Azure; n=40 others | VERIFIED | `A/sample_complexity.json` and reproduced `rq4_sample_complexity` table | n=40 trivial full-reference recovery; not population sample complexity |
| C26 | SLO extension: 30 comparisons, median .872, 13 top-choice changes | VERIFIED | External frozen `full/ranking_robustness.json` | Post-campaign status preserved |
| C27 | 72 nontrivial SLO reversal checks: 52 persist, 6 direction changes, 10 unsupported, 4 disappear | VERIFIED | External `full/reversal_persistence.json`; omit 36 primary identity checks | Retained denominators |
| C28 | No reversal is contradicted under alternative SLO definitions | DISPUTED | Six `DIRECTION_CHANGE` records | Remove blanket sentence |
| C29 | 19,800 SLO-extension executions, zero failures | UNVERIFIED at full-row level in M1 | Saved status says n_input_rows=19,800; raw `full/results.json` located but not fully revalidated here | Remove zero-failure assertion; identify count as recorded extension size |
| C30 | 42 usable descriptor regression fits / 990 | VERIFIED | `A/telemetry_explanation.json`, converged and n_observations≥20 | No SE/significance/causal inference |
| C31 | 400-window classifier accuracies and feature-ablation values | UNVERIFIED in M1 | Earlier characterization reports located; no raw-model refit/held-out reconstruction performed | Removed from central portability evidence, historical text preserved |
| C32 | Synthetic-to-real pilot 176/176 and 21/24 undefined statistics | UNVERIFIED in M1 | Historical prose/pilot references, no complete independent row audit here | No numerical transfer claim; RQ3 remains unresolved |
| C33 | Historical GPU comparison used a full 80GB A100 | DISPUTED | MGPU00 `HISTORICAL_AUDIT.md`, 240 A100_10g allocations / 9.5GiB visible | Correct to legacy MIG observations |
| C34 | RQ6 establishes faithful SLAI-vs-native ranking transfer/non-transfer | DISPUTED | Missing metadata transport, synthetic clock, admission/replay defects; PR4–8 scope | No faithful physical ranking conclusion |
| C35 | CPU P1/P2 tests and synthetic ACKs establish physical execution | DISPUTED | P1/P2A/P2B contracts explicitly reject that inference | Explicit limitations |
| C36 | General partial prefill, KV pressure, TP2/DP2 supported | DISPUTED | PR4–8 contracts; P2B representability/no-rollback boundary | Unsupported, future separate gates |
| C37 | All Azure/Bailian window medians exceed 256 source tokens | VERIFIED | All descriptor records in frozen index; PR4 report agrees | Not a retokenization/exact exclusion-fraction claim |
| C38 | Windows/providers are statistically independent | UNVERIFIED | Fixed non-overlapping IDs/sampling does not establish exchangeability of production streams; Azure/BurstGPT provider lineage shared | Qualify bootstrap/generalization assumptions |
| C39 | Novel statistical ranking/reversal algorithm | DISPUTED as proposed framing | Standard tau-b, bootstrap and BH tools | Contribution is methodology/application and empirical characterization |
| C40 | Public artifact/repository availability and complete release coverage | UNVERIFIED current publication state | Private repository metadata; local v1.1.0 is complete for simulator matrix, old public-availability prose stale | No unconditional current-public-access claim; author release check |
| C41 | Every original figure/table value matches raw evidence | VERIFIED for four generated table-data files; LIMITED for graphics | All four table JSONs regenerated identically excluding timestamp/checkout stamp; three figure bytes identical; two retained plots visually inspected | Full independent PDF plotted-point extraction not done; raw figure generation lineage preserved |
| C42 | Bibliography fully verified | UNVERIFIED | 40 keys; primary link/title retrieval, missing metadata and blocked links; `E/bibliography-links.json` | Orca URL corrected to primary USENIX; Bailian URL added from pinned attribution; final metadata review required |
| C43 | All extensions/main results were preregistered | DISPUTED | Frozen primary plan versus explicitly post-campaign metric/SLO contracts | Keep extension timing explicit; local freeze is not external preregistration certification |
| C44 | Every figure/table claim was automatically generated, no number entered by hand | DISPUTED as manuscript wording | Original TeX contains literal numerals and wrong pair/count prose | Remove blanket automation claim; distinguish preserved plots, regenerated tables and audited prose |

| C45 | ANWG requires strictly before the deadline | DISPUTED as wording | `src/robustbench/core/metrics.py` specifies completion_time <= deadline; inherited ANWG tests pass | Clarify at-or-before boundary; no metric code/result change |

## Limits of independent validation

Eight direct numerical checks pass. They import no production analysis transition/classification code, use original campaign values for point estimates, and independently implement saved-record classification. They **do not** independently regenerate 2,000-draw intervals, validate bootstrap calibration, prove BH assumptions under screening/dependence, or audit physical raw runner logs anew. The inherited four-table generator check is a reproducibility check, not a second independent statistical oracle. Public-release validator checks hashes and schema, not scientific interpretation. Counts of these checks are separate from the 32 pytest tests.

Retain all contradictions for author adjudication. The draft changes prose prospectively; it does not assert that a historical submitted PDF contained the corrected statements.
