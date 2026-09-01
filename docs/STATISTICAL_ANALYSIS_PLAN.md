# STATISTICAL_ANALYSIS_PLAN.md

Pre-registered before any confirmatory result generation. The resampling
unit throughout is the **workload window**, never the individual request and
never a single (policy, window) row treated as independent of other policies'
rows on that same window — policy rows sharing a window are correlated by
construction and must be resampled together (block bootstrap over windows).

## A. Ranking stability

- **Kendall's tau** and **Spearman's rho** between the policy ranking on
  source/split X and source/split Y, computed on the metric(s) in §E.
- **Top-k overlap** (k ∈ {3, 5}) between the two rankings' best-k policies.
- Confidence intervals via block bootstrap (resample windows with
  replacement within a source, recompute the ranking, repeat ≥2,000 times).

## B. Pairwise rank reversal

For every ordered pair (A, B) in the primary panel
(`configs/policies/canonical_policy_registry.yaml`), estimate:
- **Frequency**: fraction of (source, load, metric) cells where A beats B
  vs. cells where B beats A, with a block-bootstrap CI.
- **Effect size**: standardized difference in the relevant metric at the
  cells where a reversal occurs (not just a sign flip on noise).

## C. Synthetic-to-real transfer

Compare the ranking obtained on `workloads/synthetic.py`-generated stress
families against the ranking obtained on real-trace-derived windows
(source-OOD split, `configs/splits/source_ood.yaml`), using the same tau/rho/
top-k measures as §A. Report separately per real source, not pooled, since
pooling would hide which real source(s) the synthetic families do or do not
represent.

## D. Load dependence

Repeat §A/§B within each of LOW/PRE_KNEE/KNEE/OVERLOAD
(`docs/LOAD_CALIBRATION_PROTOCOL.md`) and report how tau/reversal-frequency
changes across the load grid, per source family.

## E. Metric dependence

Compute every ranking in §A–D under each of: goodput
(`arrival_normalized_weighted_goodput`, matching the HF seed dataset's
existing metric name for compatibility), throughput, completion rate, TTFT,
TPOT, end-to-end latency, SLO violation rate, p95/p99 tail latency. Report
tau between metric-M ranking and metric-N ranking as its own robustness
statistic (a scheduler ranking that flips between mean latency and p99
latency is itself a headline-worthy instability, independent of §A–D).

## F. Benchmark sample complexity

Subsample workload windows at increasing n (e.g. n ∈ {5, 10, 20, 40, ..., full})
without replacement, recompute the ranking at each n, and estimate:
- probability of recovering the full-data ranking (exact match and top-k
  match) as a function of n, via repeated subsampling (≥500 draws per n).
- the n at which this probability first exceeds a pre-registered threshold
  (0.9), reported per source family and per metric.

## G. Rank-reversal explanation (offline / explanatory only)

Relate `WindowDescriptor` fields
(`src/robustbench/descriptors/window_descriptors.py`) to whether a given
window is a reversal site for a given pair (A, B), via a simple, pre-specified
model (e.g. logistic regression of reversal-indicator on
burstiness_b, prompt_tokens_cv, output_tokens_cv, long_context_fraction,
concurrency_proxy — no model search over descriptor sets after seeing which
ones "work"). **This is explanatory only** — per `docs/CLAIM_BOUNDARIES.md`,
it must never be repackaged as an online selector.

## Multiple-testing correction

Any family of hypothesis tests sharing a §A–E axis (e.g. all pairwise
reversal tests within one load level) uses Benjamini-Hochberg FDR control at
q=0.05, applied per family, not globally across all sections at once (global
correction would be needlessly conservative given the sections ask
different, pre-declared questions).

## What is explicitly out of scope for this plan

Selecting the "winning" scheduler, computing exploitability/regret, or
constructing a portfolio/selector from any of the above — see
`docs/CLAIM_BOUNDARIES.md` and `docs/OVERLAP_LEDGER.md`.
